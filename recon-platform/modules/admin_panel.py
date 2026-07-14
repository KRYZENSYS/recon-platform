"""Admin Panel - Full featured admin dashboard"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from models import db, User, Scan, Organization, Subscription, Settings, ActivityLog, Report
import json

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


# ============ DASHBOARD STATS ============
@admin_bp.route("/dashboard/stats", methods=["GET"])
@admin_required
def dashboard_stats():
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    stats = {
        "users": {
            "total": User.query.count(),
            "active_24h": User.query.filter(User.last_login >= last_24h).count(),
            "active_7d": User.query.filter(User.last_login >= last_7d).count(),
            "active_30d": User.query.filter(User.last_login >= last_30d).count(),
            "new_24h": User.query.filter(User.created_at >= last_24h).count(),
            "new_7d": User.query.filter(User.created_at >= last_7d).count(),
            "new_30d": User.query.filter(User.created_at >= last_30d).count(),
            "verified": User.query.filter_by(is_verified=True).count(),
            "admins": User.query.filter_by(is_admin=True).count(),
        },
        "scans": {
            "total": Scan.query.count(),
            "completed": Scan.query.filter_by(status="completed").count(),
            "running": Scan.query.filter_by(status="running").count(),
            "failed": Scan.query.filter_by(status="failed").count(),
            "last_24h": Scan.query.filter(Scan.created_at >= last_24h).count(),
            "last_7d": Scan.query.filter(Scan.created_at >= last_7d).count(),
        },
        "organizations": {
            "total": Organization.query.count(),
            "active": Organization.query.filter_by(is_active=True).count(),
        },
        "subscriptions": {
            "free": Subscription.query.filter_by(plan="free").count(),
            "pro": Subscription.query.filter_by(plan="pro").count(),
            "business": Subscription.query.filter_by(plan="business").count(),
            "enterprise": Subscription.query.filter_by(plan="enterprise").count(),
            "active": Subscription.query.filter_by(status="active").count(),
        },
        "revenue": {
            "total": db.session.query(func.sum(Subscription.amount)).scalar() or 0,
            "month_30d": db.session.query(func.sum(Subscription.amount)).filter(Subscription.created_at >= last_30d).scalar() or 0,
        },
    }
    return jsonify(stats)


@admin_bp.route("/dashboard/charts", methods=["GET"])
@admin_required
def dashboard_charts():
    days = int(request.args.get("days", 30))
    start = datetime.utcnow() - timedelta(days=days)
    user_growth = db.session.query(
        func.date(User.created_at).label("date"),
        func.count(User.id).label("count")
    ).filter(User.created_at >= start).group_by(func.date(User.created_at)).all()
    scan_growth = db.session.query(
        func.date(Scan.created_at).label("date"),
        func.count(Scan.id).label("count")
    ).filter(Scan.created_at >= start).group_by(func.date(Scan.created_at)).all()
    return jsonify({
        "user_growth": [{"date": str(d.date), "count": d.count} for d in user_growth],
        "scan_growth": [{"date": str(d.date), "count": d.count} for d in scan_growth],
    })


# ============ USER MANAGEMENT ============
@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)
    search = request.args.get("search", "")
    role = request.args.get("role")
    verified = request.args.get("verified")
    query = User.query
    if search:
        like = f"%{search}%"
        query = query.filter(or_(User.email.ilike(like), User.username.ilike(like), User.full_name.ilike(like)))
    if role:
        query = query.filter_by(role=role)
    if verified is not None:
        query = query.filter_by(is_verified=verified.lower() == "true")
    total = query.count()
    users = query.order_by(User.created_at.desc()).limit(per_page).offset((page - 1) * per_page).all()
    return jsonify({
        "total": total, "page": page, "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "users": [u.to_dict() for u in users],
    })


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_required
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    data = user.to_dict()
    data["recent_scans"] = [s.to_dict() for s in user.scans.order_by(Scan.created_at.desc()).limit(10).all()]
    data["subscriptions"] = [s.to_dict() for s in user.subscriptions.all()]
    return jsonify(data)


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    if "role" in data: user.role = data["role"]
    if "is_admin" in data: user.is_admin = bool(data["is_admin"])
    if "is_verified" in data: user.is_verified = bool(data["is_verified"])
    if "is_active" in data: user.is_active = bool(data["is_active"])
    if "plan" in data: user.plan = data["plan"]
    if "full_name" in data: user.full_name = data["full_name"]
    db.session.commit()
    return jsonify(user.to_dict())


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        return jsonify({"error": "Cannot delete yourself"}), 400
    user = User.query.get_or_404(user_id)
    user.is_deleted = True
    user.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "User soft-deleted"})


@admin_bp.route("/users/<int:user_id>/ban", methods=["POST"])
@admin_required
def ban_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    user.is_banned = True
    user.ban_reason = data.get("reason", "")
    user.banned_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "User banned"})


@admin_bp.route("/users/<int:user_id>/unban", methods=["POST"])
@admin_required
def unban_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_banned = False
    user.ban_reason = None
    user.banned_at = None
    db.session.commit()
    return jsonify({"message": "User unbanned"})


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def admin_reset_password(user_id):
    import secrets
    user = User.query.get_or_404(user_id)
    new_password = secrets.token_urlsafe(16)
    user.set_password(new_password)
    db.session.commit()
    return jsonify({"message": "Password reset", "new_password": new_password})


# ============ SCAN MANAGEMENT ============
@admin_bp.route("/scans", methods=["GET"])
@admin_required
def list_scans():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)
    status = request.args.get("status")
    user_id = request.args.get("user_id")
    query = Scan.query
    if status:
        query = query.filter_by(status=status)
    if user_id:
        query = query.filter_by(user_id=int(user_id))
    total = query.count()
    scans = query.order_by(Scan.created_at.desc()).limit(per_page).offset((page - 1) * per_page).all()
    return jsonify({
        "total": total, "page": page, "per_page": per_page,
        "scans": [s.to_dict() for s in scans],
    })


@admin_bp.route("/scans/<int:scan_id>", methods=["DELETE"])
@admin_required
def delete_scan(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    db.session.delete(scan)
    db.session.commit()
    return jsonify({"message": "Scan deleted"})


@admin_bp.route("/scans/<int:scan_id>/cancel", methods=["POST"])
@admin_required
def cancel_scan(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    if scan.status == "running":
        scan.status = "cancelled"
        scan.completed_at = datetime.utcnow()
        db.session.commit()
    return jsonify({"message": "Scan cancelled"})


# ============ SETTINGS ============
@admin_bp.route("/settings", methods=["GET"])
@admin_required
def get_settings():
    settings = Settings.query.all()
    return jsonify({s.key: s.value for s in settings})


@admin_bp.route("/settings", methods=["PUT"])
@admin_required
def update_settings():
    data = request.json
    for key, value in data.items():
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            setting.updated_at = datetime.utcnow()
            setting.updated_by = current_user.id
        else:
            setting = Settings(key=key, value=str(value), updated_by=current_user.id)
            db.session.add(setting)
    db.session.commit()
    return jsonify({"message": "Settings updated"})


# ============ ACTIVITY LOGS ============
@admin_bp.route("/logs", methods=["GET"])
@admin_required
def get_logs():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 100)), 500)
    action = request.args.get("action")
    user_id = request.args.get("user_id")
    query = ActivityLog.query
    if action:
        query = query.filter_by(action=action)
    if user_id:
        query = query.filter_by(user_id=int(user_id))
    total = query.count()
    logs = query.order_by(ActivityLog.created_at.desc()).limit(per_page).offset((page - 1) * per_page).all()
    return jsonify({
        "total": total, "page": page, "per_page": per_page,
        "logs": [l.to_dict() for l in logs],
    })


# ============ ORGANIZATIONS ============
@admin_bp.route("/organizations", methods=["GET"])
@admin_required
def list_organizations():
    orgs = Organization.query.order_by(Organization.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orgs])


@admin_bp.route("/organizations/<int:org_id>", methods=["PUT"])
@admin_required
def update_organization(org_id):
    org = Organization.query.get_or_404(org_id)
    data = request.json
    for field in ["name", "plan", "billing_email", "is_active", "max_seats"]:
        if field in data:
            setattr(org, field, data[field])
    db.session.commit()
    return jsonify(org.to_dict())


# ============ SYSTEM ============
@admin_bp.route("/system/health", methods=["GET"])
@admin_required
def system_health():
    import psutil
    return jsonify({
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total": psutil.virtual_memory().total,
            "used": psutil.virtual_memory().used,
            "percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total": psutil.disk_usage("/").total,
            "used": psutil.disk_usage("/").used,
            "percent": psutil.disk_usage("/").percent,
        },
        "uptime": (datetime.utcnow() - current_app.startup_time).total_seconds(),
    })


@admin_bp.route("/system/cache/clear", methods=["POST"])
@admin_required
def clear_cache():
    from extensions import cache
    cache.clear()
    return jsonify({"message": "Cache cleared"})


@admin_bp.route("/system/maintenance", methods=["POST"])
@admin_required
def toggle_maintenance():
    setting = Settings.query.filter_by(key="maintenance_mode").first()
    if setting:
        setting.value = str(not (setting.value.lower() == "true")).lower()
        db.session.commit()
    return jsonify({"maintenance": setting.value if setting else "false"})


# ============ BROADCAST ============
@admin_bp.route("/broadcast", methods=["POST"])
@admin_required
def broadcast():
    data = request.json
    message = data.get("message", "")
    user_ids = data.get("user_ids", [])
    target = data.get("target", "all")
    if target == "all":
        users = User.query.filter_by(is_active=True, is_banned=False).all()
    elif target == "verified":
        users = User.query.filter_by(is_active=True, is_verified=True).all()
    elif target == "selected" and user_ids:
        users = User.query.filter(User.id.in_(user_ids)).all()
    else:
        return jsonify({"error": "Invalid target"}), 400
    sent = 0
    for user in users:
        try:
            from modules.notifications import send_notification
            send_notification(user.id, "admin_broadcast", {"message": message})
            sent += 1
        except Exception:
            pass
    return jsonify({"message": f"Sent to {sent} users", "count": sent})


# ============ ANALYTICS ============
@admin_bp.route("/analytics/overview", methods=["GET"])
@admin_required
def analytics_overview():
    days = int(request.args.get("days", 30))
    start = datetime.utcnow() - timedelta(days=days)
    return jsonify({
        "new_users": User.query.filter(User.created_at >= start).count(),
        "total_scans": Scan.query.filter(Scan.created_at >= start).count(),
        "total_findings": db.session.query(func.sum(Scan.findings_count)).filter(Scan.created_at >= start).scalar() or 0,
        "avg_scan_duration": db.session.query(func.avg(Scan.duration)).filter(Scan.created_at >= start).scalar() or 0,
    })


@admin_bp.route("/analytics/top-targets", methods=["GET"])
@admin_required
def top_targets():
    limit = int(request.args.get("limit", 10))
    results = db.session.query(
        Scan.target, func.count(Scan.id).label("count")
    ).group_by(Scan.target).order_by(func.count(Scan.id).desc()).limit(limit).all()
    return jsonify([{"target": r.target, "scans": r.count} for r in results])
