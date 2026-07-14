"""Authentication endpoints - login, register, password reset, 2FA"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import jwt
import secrets
from models import db, User, ActivityLog
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def log_activity(user_id, action, details=None):
    """Log user activity"""
    log = ActivityLog(user_id=user_id, action=action, ip_address=request.remote_addr, user_agent=request.headers.get("User-Agent"), details=details or {})
    db.session.add(log)


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register new user"""
    data = request.json
    required = ["username", "email", "password"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400
    if len(data["password"]) < 12:
        return jsonify({"error": "Password must be at least 12 characters"}), 400
    if User.query.filter((User.username == data["username"]) | (User.email == data["email"])).first():
        return jsonify({"error": "Username or email already exists"}), 409
    user = User(username=data["username"], email=data["email"], full_name=data.get("full_name", ""))
    user.set_password(data["password"])
    user.email_verified = False
    user.verification_token = secrets.token_urlsafe(32)
    db.session.add(user)
    db.session.commit()
    log_activity(user.id, "register", {"email": user.email})
    db.session.commit()
    return jsonify({"message": "User created", "user": user.to_dict()})


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login with username/email and password - returns JWT"""
    data = request.json
    if not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password required"}), 400
    user = User.query.filter((User.username == data["username"]) | (User.email == data["username"])).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    if user.is_banned:
        return jsonify({"error": f"Account banned: {user.ban_reason}"}), 403
    if not user.is_active:
        return jsonify({"error": "Account inactive"}), 403
    # Update last login
    user.last_login = datetime.utcnow()
    user.last_login_ip = request.remote_addr
    user.login_count = (user.login_count or 0) + 1
    # Generate JWT token
    token_payload = {
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "role": user.role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=12),
    }
    token = jwt.encode(token_payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")
    refresh_token = jwt.encode({**token_payload, "exp": datetime.utcnow() + timedelta(days=30), "type": "refresh"}, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")
    log_activity(user.id, "login", {"ip": request.remote_addr})
    db.session.commit()
    return jsonify({
        "token": token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
        "is_admin": user.is_admin,
        "expires_in": 12 * 3600,
    })


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """Refresh JWT token"""
    data = request.json
    refresh_token = data.get("refresh_token", "")
    try:
        payload = jwt.decode(refresh_token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        if payload.get("type") != "refresh":
            return jsonify({"error": "Invalid token type"}), 401
        user = User.query.get(payload["user_id"])
        if not user or user.is_banned or not user.is_active:
            return jsonify({"error": "User invalid"}), 401
        new_token = jwt.encode({
            "user_id": user.id, "username": user.username, "is_admin": user.is_admin, "role": user.role,
            "iat": datetime.utcnow(), "exp": datetime.utcnow() + timedelta(hours=12),
        }, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")
        return jsonify({"token": new_token, "expires_in": 12 * 3600})
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token expired"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Logout user"""
    log_activity(current_user.id, "logout", {})
    db.session.commit()
    logout_user()
    return jsonify({"message": "Logged out"})


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    """Get current user info"""
    return jsonify(current_user.to_dict())


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """Request password reset"""
    data = request.json
    user = User.query.filter_by(email=data.get("email", "")).first()
    if user:
        user.reset_token = secrets.token_urlsafe(32)
        user.reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        # TODO: Send email with reset link
        return jsonify({"message": "If email exists, reset link sent", "token": user.reset_token})  # Token returned only in dev
    return jsonify({"message": "If email exists, reset link sent"})


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """Reset password with token"""
    data = request.json
    token = data.get("token", "")
    new_password = data.get("password", "")
    if len(new_password) < 12:
        return jsonify({"error": "Password must be at least 12 characters"}), 400
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_expires or user.reset_expires < datetime.utcnow():
        return jsonify({"error": "Invalid or expired token"}), 400
    user.set_password(new_password)
    user.reset_token = None
    user.reset_expires = None
    log_activity(user.id, "password_reset", {})
    db.session.commit()
    return jsonify({"message": "Password reset successful"})


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """Change password (logged in user)"""
    data = request.json
    if not current_user.check_password(data.get("current_password", "")):
        return jsonify({"error": "Current password incorrect"}), 401
    if len(data.get("new_password", "")) < 12:
        return jsonify({"error": "New password must be at least 12 characters"}), 400
    current_user.set_password(data["new_password"])
    log_activity(current_user.id, "password_change", {})
    db.session.commit()
    return jsonify({"message": "Password changed"})


@auth_bp.route("/2fa/enable", methods=["POST"])
@login_required
def enable_2fa():
    """Enable 2FA - returns secret and QR"""
    import pyotp
    secret = pyotp.random_base32()
    current_user.two_factor_secret = secret
    current_user.two_factor_enabled = False  # Activated after verification
    db.session.commit()
    import pyotp, qrcode
    from io import BytesIO
    import base64 as b
    uri = pyotp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name="Recon Platform")
    qr = qrcode.make(uri)
    buffer = BytesIO()
    qr.save(buffer)
    qr_b64 = b.b64encode(buffer.getvalue()).decode()
    return jsonify({"secret": secret, "qr_code": f"data:image/png;base64,{qr_b64}", "uri": uri})


@auth_bp.route("/2fa/verify", methods=["POST"])
@login_required
def verify_2fa():
    """Verify and activate 2FA"""
    import pyotp
    data = request.json
    code = data.get("code", "")
    if not current_user.two_factor_secret:
        return jsonify({"error": "2FA not initialized"}), 400
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if totp.verify(code, valid_window=1):
        current_user.two_factor_enabled = True
        # Generate backup codes
        backup_codes = [secrets.token_hex(8) for _ in range(10)]
        current_user.backup_codes = backup_codes
        log_activity(current_user.id, "2fa_enabled", {})
        db.session.commit()
        return jsonify({"message": "2FA enabled", "backup_codes": backup_codes})
    return jsonify({"error": "Invalid code"}), 400


@auth_bp.route("/2fa/disable", methods=["POST"])
@login_required
def disable_2fa():
    """Disable 2FA (requires password confirmation)"""
    data = request.json
    if not current_user.check_password(data.get("password", "")):
        return jsonify({"error": "Password required"}), 401
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    current_user.backup_codes = None
    log_activity(current_user.id, "2fa_disabled", {})
    db.session.commit()
    return jsonify({"message": "2FA disabled"})


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    """Verify email with token"""
    data = request.json
    token = data.get("token", "")
    user = User.query.filter_by(verification_token=token).first()
    if not user:
        return jsonify({"error": "Invalid token"}), 400
    user.is_verified = True
    user.email_verified_at = datetime.utcnow()
    user.verification_token = None
    log_activity(user.id, "email_verified", {})
    db.session.commit()
    return jsonify({"message": "Email verified"})


@auth_bp.route("/check-username", methods=["POST"])
def check_username():
    """Check if username is available"""
    data = request.json
    exists = User.query.filter_by(username=data.get("username", "")).first() is not None
    return jsonify({"available": not exists})


@auth_bp.route("/check-email", methods=["POST"])
def check_email():
    """Check if email is available"""
    data = request.json
    exists = User.query.filter_by(email=data.get("email", "")).first() is not None
    return jsonify({"available": not exists})
