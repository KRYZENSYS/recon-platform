"""Auth blueprint: login, register, 2FA, password reset, email verification"""
import os
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
import pyotp
import qrcode
import io
import base64

from models import db, User, Organization, Invitation, AuditLog
from modules.security import (
    validate_password, validate_email, get_client_ip, get_device_info,
    audit_log, check_account_lockout, record_failed_login, reset_failed_login,
    create_session, generate_secure_token, sanitize_input,
)

auth_bp = Blueprint("auth", __name__, template_folder="templates")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        data = request.form if request.form else request.get_json()
        login_id = sanitize_input(data.get("username") or data.get("email", ""))
        password = data.get("password", "")
        remember = data.get("remember", False)
        two_factor_code = data.get("two_factor_code")
        if not login_id or not password:
            flash("Username and password required", "error")
            return render_template("auth/login.html"), 400
        # Find user
        user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()
        if not user:
            audit_log("auth.login_failed", details={"reason": "user_not_found", "login_id": login_id}, status="failure")
            flash("Invalid credentials", "error")
            return render_template("auth/login.html"), 401
        if not user.is_active:
            audit_log("auth.login_blocked", "user", user.id, {"reason": "inactive"}, status="failure")
            flash("Account disabled", "error")
            return render_template("auth/login.html"), 403
        if check_account_lockout(user):
            flash(f"Account locked. Try again later.", "error")
            return render_template("auth/login.html"), 423
        if not user.check_password(password):
            record_failed_login(user)
            audit_log("auth.login_failed", "user", user.id, {"reason": "wrong_password"}, status="failure")
            flash("Invalid credentials", "error")
            return render_template("auth/login.html"), 401
        # Check 2FA
        if user.two_factor_enabled:
            if not two_factor_code:
                return render_template("auth/login_2fa.html", user_id=user.id), 200
            if not user.verify_2fa(two_factor_code):
                record_failed_login(user)
                audit_log("auth.2fa_failed", "user", user.id, status="failure")
                flash("Invalid 2FA code", "error")
                return render_template("auth/login_2fa.html", user_id=user.id), 401
        # Success
        reset_failed_login(user)
        login_user(user, remember=remember)
        create_session(user)
        audit_log("auth.login_success", "user", user.id, get_device_info())
        next_page = request.args.get("next")
        if not next_page or not next_page.startswith("/"):
            next_page = url_for("dashboard.index")
        return redirect(next_page) if not request.is_json else jsonify({"success": True, "redirect": next_page}), 200
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if not current_app.config.get("ENABLE_REGISTRATION", True):
        flash("Registration is disabled", "error")
        return redirect(url_for("auth.login"))
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        data = request.form if request.form else request.get_json()
        username = sanitize_input(data.get("username", ""))
        email = sanitize_input(data.get("email", ""))
        password = data.get("password", "")
        full_name = sanitize_input(data.get("full_name", ""))
        invitation_token = data.get("invitation_token")
        # Validate
        if not username or len(username) < 3:
            flash("Username must be at least 3 characters", "error")
            return render_template("auth/register.html"), 400
        if not validate_email(email):
            flash("Invalid email", "error")
            return render_template("auth/register.html"), 400
        valid, msg = validate_password(password)
        if not valid:
            flash(msg, "error")
            return render_template("auth/register.html"), 400
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already taken", "error")
            return render_template("auth/register.html"), 409
        # Invitation check
        invitation = None
        organization_id = None
        role = "user"
        if invitation_token:
            invitation = Invitation.query.filter_by(token=invitation_token, accepted_at=None).first()
            if not invitation or invitation.expires_at < datetime.utcnow():
                flash("Invalid or expired invitation", "error")
                return render_template("auth/register.html"), 400
            organization_id = invitation.organization_id
            role = invitation.role
        # Create user
        user = User(username=username, email=email, full_name=full_name, role=role, organization_id=organization_id)
        user.set_password(password)
        user.generate_api_key()
        # Email verification token
        if current_app.config.get("REQUIRE_EMAIL_VERIFICATION", True):
            from models import Settings
            user._verification_token = generate_secure_token(32)
        db.session.add(user)
        if invitation:
            invitation.accepted_at = datetime.utcnow()
        db.session.commit()
        # Send verification email (stub)
        audit_log("auth.register", "user", user.id, {"method": "invite" if invitation else "open"})
        flash("Account created! Please log in.", "success")
        if current_app.config.get("REQUIRE_EMAIL_VERIFICATION", True) and not invitation:
            flash("Check your email to verify your account", "info")
        return redirect(url_for("auth.login"))
    invitation_token = request.args.get("invite")
    return render_template("auth/register.html", invitation_token=invitation_token)


@auth_bp.route("/logout")
@login_required
def logout():
    audit_log("auth.logout", "user", current_user.id)
    logout_user()
    flash("Logged out successfully", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/2fa/setup", methods=["GET", "POST"])
@login_required
def setup_2fa():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if not current_user.two_factor_secret:
            current_user.generate_2fa_secret()
            db.session.commit()
        if current_user.verify_2fa(code):
            current_user.two_factor_enabled = True
            # Generate backup codes
            backup_codes = [secrets.token_hex(4) for _ in range(10)]
            current_user.backup_codes = backup_codes
            db.session.commit()
            audit_log("auth.2fa_enabled", "user", current_user.id)
            return render_template("auth/2fa_backup_codes.html", codes=backup_codes)
        flash("Invalid code", "error")
    if not current_user.two_factor_secret:
        current_user.generate_2fa_secret()
        db.session.commit()
    # Generate QR
    totp_uri = pyotp.TOTP(current_user.two_factor_secret).provisioning_uri(name=current_user.email, issuer_name="ReconPlatform")
    qr = qrcode.make(totp_uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template("auth/setup_2fa.html", secret=current_user.two_factor_secret, qr_code=qr_b64)


@auth_bp.route("/2fa/disable", methods=["POST"])
@login_required
def disable_2fa():
    code = request.form.get("code", "")
    if not current_user.verify_2fa(code):
        flash("Invalid code", "error")
        return redirect(url_for("auth.setup_2fa"))
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    current_user.backup_codes = None
    db.session.commit()
    audit_log("auth.2fa_disabled", "user", current_user.id)
    flash("2FA disabled", "success")
    return redirect(url_for("dashboard.settings"))


@auth_bp.route("/password/reset", methods=["GET", "POST"])
def password_reset_request():
    if request.method == "POST":
        email = sanitize_input(request.form.get("email", ""))
        user = User.query.filter_by(email=email).first()
        if user:
            from models import Settings
            token = generate_secure_token(32)
            user._reset_token = token
            user._reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            # Send email (stub)
            audit_log("auth.password_reset_requested", "user", user.id)
        flash("If email exists, reset link has been sent", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/password_reset.html")


@auth_bp.route("/password/reset/<token>", methods=["GET", "POST"])
def password_reset_confirm(token):
    user = User.query.filter_by(_reset_token=token).first()
    if not user or not user._reset_expires or user._reset_expires < datetime.utcnow():
        flash("Invalid or expired token", "error")
        return redirect(url_for("auth.password_reset_request"))
    if request.method == "POST":
        password = request.form.get("password", "")
        valid, msg = validate_password(password)
        if not valid:
            flash(msg, "error")
            return render_template("auth/password_reset_confirm.html", token=token)
        user.set_password(password)
        user._reset_token = None
        user._reset_expires = None
        user.failed_login_count = 0
        user.locked_until = None
        db.session.commit()
        audit_log("auth.password_reset_completed", "user", user.id)
        flash("Password updated. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/password_reset_confirm.html", token=token)


@auth_bp.route("/verify/<token>")
def verify_email(token):
    user = User.query.filter_by(_verification_token=token).first()
    if not user:
        flash("Invalid verification token", "error")
        return redirect(url_for("auth.login"))
    user.is_verified = True
    user._verification_token = None
    db.session.commit()
    audit_log("auth.email_verified", "user", user.id)
    flash("Email verified! You can now log in.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/sessions")
@login_required
def list_sessions():
    sessions = UserSession.query.filter_by(user_id=current_user.id).order_by(UserSession.last_seen.desc()).all()
    return render_template("auth/sessions.html", sessions=sessions)


@auth_bp.route("/sessions/<session_id>/revoke", methods=["POST"])
@login_required
def revoke_session(session_id):
    session = UserSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if session:
        session.is_active = False
        db.session.commit()
        audit_log("auth.session_revoked", "session", session_id)
        flash("Session revoked", "success")
    return redirect(url_for("auth.list_sessions"))


# Add fields to User model via Settings or dynamic
# (Patched at runtime)
def patch_user_model():
    from sqlalchemy import Column, String, DateTime
    User._verification_token = db.Column(db.String(64), index=True, nullable=True)
    User._reset_token = db.Column(db.String(64), index=True, nullable=True)
    User._reset_expires = db.Column(db.DateTime, nullable=True)
    User.backup_codes = db.Column(db.JSON, nullable=True)
