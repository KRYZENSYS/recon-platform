"""Audit logging for compliance (SOC2, GDPR, HIPAA)"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from flask import Blueprint, request, g
from models import db, AuditLog, User
from functools import wraps

logger = logging.getLogger(__name__)


class AuditLogger:
    """Comprehensive audit logging for compliance"""
    COMPLIANCE_STANDARDS = ["SOC2", "GDPR", "HIPAA", "PCI-DSS", "ISO27001"]

    def __init__(self):
        self.retention_days = int(os.getenv("AUDIT_RETENTION_DAYS", "2555"))  # 7 years for SOC2

    def log(self, action: str, user_id: int = None, resource_type: str = None, resource_id: str = None, details: dict = None, severity: str = "info", compliance_tags: List[str] = None) -> AuditLog:
        """Log audit event"""
        try:
            entry = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                details=json.dumps(details or {}),
                ip_address=request.remote_addr if request else None,
                user_agent=request.headers.get('User-Agent', '')[:500] if request else None,
                severity=severity,
                compliance_tags=','.join(compliance_tags or []),
                timestamp=datetime.utcnow(),
            )
            db.session.add(entry)
            db.session.commit()
            logger.info(f"AUDIT: {action} by user={user_id} resource={resource_type}:{resource_id}")
            return entry
        except Exception as e:
            logger.error(f"Audit log failed: {e}")
            db.session.rollback()
            return None

    def log_login(self, user_id: int, success: bool, method: str = "password"):
        self.log("auth.login", user_id=user_id if success else None, resource_type="session", details={"success": success, "method": method}, severity="info" if success else "warning", compliance_tags=["SOC2", "GDPR"])

    def log_logout(self, user_id: int):
        self.log("auth.logout", user_id=user_id, resource_type="session", severity="info", compliance_tags=["SOC2"])

    def log_failed_login(self, username: str, reason: str):
        self.log("auth.failed", resource_type="session", details={"username": username, "reason": reason}, severity="warning", compliance_tags=["SOC2", "GDPR"])

    def log_password_change(self, user_id: int):
        self.log("auth.password_change", user_id=user_id, resource_type="user", resource_id=user_id, severity="info", compliance_tags=["SOC2", "GDPR", "HIPAA"])

    def log_data_access(self, user_id: int, resource_type: str, resource_id: str, action: str = "read"):
        self.log(f"data.{action}", user_id=user_id, resource_type=resource_type, resource_id=resource_id, severity="info", compliance_tags=["GDPR", "HIPAA", "PCI-DSS"])

    def log_data_export(self, user_id: int, data_type: str, count: int, format: str = "json"):
        self.log("data.export", user_id=user_id, resource_type="data", details={"data_type": data_type, "count": count, "format": format}, severity="warning", compliance_tags=["GDPR", "SOC2"])

    def log_data_delete(self, user_id: int, data_type: str, resource_id: str, reason: str = None):
        self.log("data.delete", user_id=user_id, resource_type=data_type, resource_id=resource_id, details={"reason": reason}, severity="warning", compliance_tags=["GDPR", "HIPAA"])

    def log_admin_action(self, admin_id: int, action: str, target_user_id: int = None, details: dict = None):
        self.log(f"admin.{action}", user_id=admin_id, resource_type="user", resource_id=target_user_id, details=details, severity="warning", compliance_tags=["SOC2"])

    def log_security_event(self, event_type: str, details: dict, severity: str = "warning"):
        self.log(f"security.{event_type}", resource_type="system", details=details, severity=severity, compliance_tags=["SOC2", "PCI-DSS"])

    def log_api_call(self, user_id: int, endpoint: str, method: str, status_code: int):
        self.log("api.call", user_id=user_id, resource_type="api", details={"endpoint": endpoint, "method": method, "status": status_code}, severity="info" if status_code < 400 else "warning", compliance_tags=["SOC2"])

    def log_payment(self, user_id: int, amount: float, currency: str, status: str, payment_id: str):
        self.log("payment.process", user_id=user_id, resource_type="payment", resource_id=payment_id, details={"amount": amount, "currency": currency, "status": status}, severity="info" if status == "success" else "warning", compliance_tags=["PCI-DSS", "SOC2"])

    def log_2fa(self, user_id: int, action: str, success: bool):
        self.log(f"auth.2fa.{action}", user_id=user_id if success else None, resource_type="user", resource_id=user_id, details={"success": success}, severity="info" if success else "warning", compliance_tags=["SOC2"])

    def query(self, filters: dict = None, page: int = 1, per_page: int = 100) -> Dict:
        """Query audit logs with filters"""
        query = AuditLog.query
        if filters:
            if "user_id" in filters: query = query.filter(AuditLog.user_id == filters["user_id"])
            if "action" in filters: query = query.filter(AuditLog.action.like(f"%{filters['action']}%"))
            if "resource_type" in filters: query = query.filter(AuditLog.resource_type == filters["resource_type"])
            if "severity" in filters: query = query.filter(AuditLog.severity == filters["severity"])
            if "from_date" in filters: query = query.filter(AuditLog.timestamp >= filters["from_date"])
            if "to_date" in filters: query = query.filter(AuditLog.timestamp <= filters["to_date"])
            if "compliance" in filters: query = query.filter(AuditLog.compliance_tags.like(f"%{filters['compliance']}%"))
        total = query.count()
        logs = query.order_by(AuditLog.timestamp.desc()).limit(per_page).offset((page - 1) * per_page).all()
        return {"total": total, "page": page, "per_page": per_page, "logs": [self._to_dict(l) for l in logs]}

    def _to_dict(self, log: AuditLog) -> Dict:
        return {"id": log.id, "user_id": log.user_id, "action": log.action, "resource_type": log.resource_type, "resource_id": log.resource_id, "details": json.loads(log.details) if log.details else {}, "ip_address": log.ip_address, "user_agent": log.user_agent, "severity": log.severity, "compliance_tags": log.compliance_tags.split(",") if log.compliance_tags else [], "timestamp": log.timestamp.isoformat() if log.timestamp else None}

    def export(self, filters: dict = None, format: str = "json") -> bytes:
        """Export audit logs (for compliance audits)"""
        result = self.query(filters, page=1, per_page=100000)
        if format == "json": return json.dumps(result["logs"], indent=2, default=str).encode()
        elif format == "csv":
            import csv, io
            output = io.StringIO()
            if result["logs"]:
                writer = csv.DictWriter(output, fieldnames=result["logs"][0].keys())
                writer.writeheader()
                for log in result["logs"]: writer.writerow(log)
            return output.getvalue().encode()
        return b""


_audit_logger = None
def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None: _audit_logger = AuditLogger()
    return _audit_logger


def audit_action(action: str, severity: str = "info", compliance_tags: List[str] = None):
    """Decorator to auto-audit endpoint calls"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask_login import current_user
            user_id = current_user.id if current_user.is_authenticated else None
            try:
                result = f(*args, **kwargs)
                get_audit_logger().log(action, user_id=user_id, resource_type=request.endpoint, details={"method": request.method, "path": request.path}, severity=severity, compliance_tags=compliance_tags)
                return result
            except Exception as e:
                get_audit_logger().log(f"{action}.failed", user_id=user_id, resource_type=request.endpoint, details={"error": str(e)}, severity="error", compliance_tags=compliance_tags)
                raise
        return wrapper
    return decorator


audit_bp = Blueprint("audit", __name__, url_prefix="/api/v1/audit")


@audit_bp.route("/logs", methods=["GET"])
@audit_action("audit.view", compliance_tags=["SOC2"])
def list_audit_logs():
    from flask_login import current_user
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False): return {"error": "Admin only"}, 403
    filters = {k: v for k, v in request.args.items() if k in ["user_id", "action", "resource_type", "severity", "compliance"]}
    if "from_date" in request.args: filters["from_date"] = datetime.fromisoformat(request.args["from_date"])
    if "to_date" in request.args: filters["to_date"] = datetime.fromisoformat(request.args["to_date"])
    return get_audit_logger().query(filters, page=int(request.args.get("page", 1)), per_page=int(request.args.get("per_page", 100)))


@audit_bp.route("/export", methods=["GET"])
@audit_action("audit.export", severity="warning", compliance_tags=["SOC2", "GDPR"])
def export_audit_logs():
    from flask_login import current_user
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False): return {"error": "Admin only"}, 403
    fmt = request.args.get("format", "json")
    return get_audit_logger().export(format=fmt)


@audit_bp.route("/compliance/<standard>", methods=["GET"])
@audit_action("audit.compliance_report", compliance_tags=["SOC2"])
def compliance_report(standard):
    from flask_login import current_user
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False): return {"error": "Admin only"}, 403
    standard = standard.upper()
    if standard not in AuditLogger.COMPLIANCE_STANDARDS: return {"error": "Unknown standard"}, 400
    now = datetime.utcnow()
    if standard == "SOC2": period = now - timedelta(days=90)
    elif standard == "GDPR": period = now - timedelta(days=365)
    elif standard == "HIPAA": period = now - timedelta(days=180)
    elif standard == "PCI-DSS": period = now - timedelta(days=90)
    else: period = now - timedelta(days=30)
    logs = get_audit_logger().query({"compliance": standard, "from_date": period, "to_date": now}, page=1, per_page=10000)
    return {"standard": standard, "period": {"from": period, "to": now}, "total_events": logs["total"], "events": logs["logs"][:100]}
