"""Security module: auth decorators, audit, password, CSRF, account lockout"""
import os
import secrets
import hashlib
import hmac
import re
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, abort, current_app
from flask_login import current_user
from models import db, User, AuditLog, ApiKey, UserSession

logger = logging.getLogger(__name__)

PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{12,}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    if not PASSWORD_REGEX.match(password):
        return False, "Password must contain uppercase, lowercase, digit, and special character"
    if password.lower() in ("password", "12345678", "qwerty12345"):
        return False, "Password too common"
    return True, "OK"


def validate_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


def hash_ip(ip: str) -> str:
    salt = current_app.config.get("IP_HASH_SALT", "default-salt")
    return hashlib.sha256(f"{salt}{ip}".encode()).hexdigest()


def get_client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "0.0.0.0").split(",")[0].strip()


def get_device_info() -> dict:
    ua = request.headers.get("User-Agent", "")
    if "Mobile" in ua or "Android" in ua or "iPhone" in ua:
        device = "Mobile"
    elif "Tablet" in ua or "iPad" in ua:
        device = "Tablet"
    else:
        device = "Desktop"
    browser = "Unknown"
    if "Chrome" in ua and "Edg" not in ua: browser = "Chrome"
    elif "Firefox" in ua: browser = "Firefox"
    elif "Safari" in ua and "Chrome" not in ua: browser = "Safari"
    elif "Edg" in ua: browser = "Edge"
    elif "Opera" in ua or "OPR" in ua: browser = "Opera"
    return {"device": device, "browser": browser, "user_agent": ua[:512]}


def audit_log(action: str, resource_type: str = None, resource_id: str = None, details: dict = None, status: str = "success"):
    try:
        log = AuditLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action, resource_type=resource_type, resource_id=str(resource_id) if resource_id else None,
            ip_address=get_client_ip(), user_agent=request.headers.get("User-Agent", "")[:512],
            details=details or {}, status=status,
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.exception(f"Audit log failed: {e}")
        db.session.rollback()


def check_account_lockout(user: User) -> bool:
    if user.locked_until and user.locked_until > datetime.utcnow():
        return True
    if user.locked_until and user.locked_until <= datetime.utcnow():
        user.locked_until = None
        user.failed_login_count = 0
        db.session.commit()
    return False


def record_failed_login(user: User):
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= 5:
        user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        audit_log("account.locked", "user", user.id, {"reason": "too_many_failed_logins"}, "warning")
    db.session.commit()


def reset_failed_login(user: User):
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    user.last_ip = get_client_ip()
    db.session.commit()


def create_session(user: User) -> UserSession:
    info = get_device_info()
    session = UserSession(
        user_id=user.id, ip_address=get_client_ip(), user_agent=info["user_agent"],
        device=f"{info['device']} · {info['browser']}",
    )
    db.session.add(session)
    db.session.commit()
    return session


# === Decorators ===
def require_api_key(f):
    """API key authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        key_record = ApiKey.query.filter_by(key=api_key, is_active=True).first()
        if not key_record:
            audit_log("api.invalid_key", status="failure")
            return jsonify({"error": "Invalid API key"}), 401
        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            return jsonify({"error": "API key expired"}), 401
        key_record.last_used = datetime.utcnow()
        db.session.commit()
        request.api_key = key_record
        request.current_user = key_record.user
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Unauthorized"}), 401
            if current_user.role not in roles and not current_user.is_admin:
                audit_log("access.denied", "user", current_user.id, {"required_role": list(roles), "user_role": current_user.role}, "failure")
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    return require_role("admin", "superadmin")(f)


def superadmin_required(f):
    return require_role("superadmin")(f)


def verified_email_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Unauthorized"}), 401
        if not current_user.is_verified:
            return jsonify({"error": "Email verification required"}), 403
        return f(*args, **kwargs)
    return decorated


def check_plan_limit(limit_key: str):
    """Check user's plan limit (e.g. 'scans_per_month')"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Unauthorized"}), 401
            limits = current_user.get_plan_limits()
            limit = limits.get(limit_key, 0)
            if limit == -1:  # unlimited
                return f(*args, **kwargs)
            # Check current usage
            from models import Scan
            if limit_key == "scans_per_month":
                count = Scan.query.filter(
                    Scan.user_id == current_user.id,
                    Scan.created_at >= datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                ).count()
                if count >= limit:
                    return jsonify({"error": f"Plan limit reached. Upgrade to Pro for more {limit_key.replace('_', ' ')}.", "current": count, "limit": limit}), 402
            elif limit_key == "concurrent_scans":
                count = Scan.query.filter(Scan.user_id == current_user.id, Scan.status.in_(["pending", "running"])).count()
                if count >= limit:
                    return jsonify({"error": f"Too many concurrent scans ({count}/{limit})"}), 429
            return f(*args, **kwargs)
        return decorated
    return decorator


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature:
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def sanitize_input(text: str, max_length: int = 1000) -> str:
    if not text:
        return ""
    text = text.strip()[:max_length]
    # Remove control characters
    text = "".join(c for c in text if c.isprintable() or c in "\n\t")
    return text


def is_safe_url(target: str) -> bool:
    from urllib.parse import urlparse
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(request.urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def generate_secure_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def init_security(app):
    """Initialize security features"""
    from flask import g
    @app.before_request
    def security_before_request():
        g.start_time = datetime.utcnow()
        g.ip = get_client_ip()
        # Log suspicious activity
        ua = request.headers.get("User-Agent", "")
        if not ua or len(ua) < 10:
            logger.warning(f"Suspicious request from {g.ip}: no UA")
        # Block known bad paths
        if any(p in request.path.lower() for p in [".env", "wp-admin", "phpmyadmin", ".git/"]):
            audit_log("security.suspicious_path", details={"path": request.path}, status="warning")
            abort(404)


def create_default_admin():
    """Create default admin user from env"""
    admin_email = os.getenv("ADMIN_EMAIL", "admin@recon.local")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        return
    if not User.query.filter_by(email=admin_email).first():
        admin = User(username="admin", email=admin_email, full_name="System Administrator", role="superadmin", plan="enterprise", is_verified=True, is_active=True)
        admin.set_password(admin_password)
        admin.generate_api_key()
        db.session.add(admin)
        db.session.commit()
        logger.info(f"Default admin created: {admin_email}")
