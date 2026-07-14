"""SQLAlchemy models - multi-tenant, RBAC, audit"""
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import pyotp

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128))
    role = db.Column(db.String(32), default="user")  # user, premium, admin, superadmin
    plan = db.Column(db.String(32), default="free")
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="SET NULL"))
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    api_key = db.Column(db.String(64), unique=True, index=True)
    last_login = db.Column(db.DateTime)
    last_ip = db.Column(db.String(45))
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    avatar_url = db.Column(db.String(512))
    timezone = db.Column(db.String(64), default="UTC")
    locale = db.Column(db.String(8), default="en")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scans = db.relationship("Scan", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    api_keys = db.relationship("ApiKey", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    audit_logs = db.relationship("AuditLog", backref="user", lazy="dynamic")
    sessions = db.relationship("UserSession", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    organization = db.relationship("Organization", backref="users", foreign_keys=[organization_id])

    def set_password(self, password):
        from config import config
        rounds = config[os.getenv("FLASK_ENV", "production")].BCRYPT_ROUNDS
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_2fa_secret(self):
        self.two_factor_secret = pyotp.random_base32()
        return self.two_factor_secret

    def verify_2fa(self, token):
        if not self.two_factor_secret:
            return False
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(token, valid_window=1)

    def generate_api_key(self):
        self.api_key = f"rck_{secrets.token_urlsafe(40)}"
        return self.api_key

    @property
    def is_admin(self):
        return self.role in ("admin", "superadmin")

    @property
    def is_locked(self):
        return self.locked_until and self.locked_until > datetime.utcnow()

    def get_plan_limits(self):
        from config import config
        env = os.getenv("FLASK_ENV", "production")
        return config[env].PLAN_LIMITS.get(self.plan, {})

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email, "full_name": self.full_name, "role": self.role, "plan": self.plan, "is_verified": self.is_verified, "two_factor_enabled": self.two_factor_enabled, "created_at": self.created_at.isoformat() if self.created_at else None}


class Organization(db.Model):
    __tablename__ = "organizations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    plan = db.Column(db.String(32), default="business")
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    billing_email = db.Column(db.String(120))
    max_seats = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scans = db.relationship("Scan", backref="organization", lazy="dynamic")
    invitations = db.relationship("Invitation", backref="organization", lazy="dynamic", cascade="all, delete-orphan")


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    members = db.relationship("TeamMember", backref="team", lazy="dynamic", cascade="all, delete-orphan")


class TeamMember(db.Model):
    __tablename__ = "team_members"
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(32), default="member")  # owner, admin, member, viewer
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")


class Invitation(db.Model):
    __tablename__ = "invitations"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(32), default="member")
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    accepted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Scan(db.Model):
    __tablename__ = "scans"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"))
    target = db.Column(db.String(512), nullable=False, index=True)
    scan_type = db.Column(db.String(64), nullable=False)  # spider, dns, port, ssl, whois, subdomain, full
    status = db.Column(db.String(32), default="pending", index=True)  # pending, running, completed, failed, cancelled
    progress = db.Column(db.Integer, default=0)
    celery_task_id = db.Column(db.String(64), index=True)
    results = db.Column(db.JSON)
    summary = db.Column(db.JSON)
    risk_score = db.Column(db.Integer, default=0)  # 0-100
    duration = db.Column(db.Float)  # seconds
    error = db.Column(db.Text)
    is_scheduled = db.Column(db.Boolean, default=False)
    schedule_cron = db.Column(db.String(64))
    webhook_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    results_rel = db.relationship("ScanResult", backref="scan", lazy="dynamic", cascade="all, delete-orphan")
    vulnerabilities = db.relationship("Vulnerability", backref="scan", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "target": self.target, "scan_type": self.scan_type, "status": self.status, "progress": self.progress, "risk_score": self.risk_score, "duration": self.duration, "created_at": self.created_at.isoformat() if self.created_at else None, "completed_at": self.completed_at.isoformat() if self.completed_at else None}


class ScanResult(db.Model):
    __tablename__ = "scan_results"
    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    module = db.Column(db.String(64), nullable=False)
    type = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(db.String(16), default="info", index=True)  # critical, high, medium, low, info
    title = db.Column(db.String(256), nullable=False)
    data = db.Column(db.JSON)
    source = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Vulnerability(db.Model):
    __tablename__ = "vulnerabilities"
    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    cve_id = db.Column(db.String(32), index=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    severity = db.Column(db.String(16), nullable=False, index=True)
    cvss_score = db.Column(db.Float)
    cwe_id = db.Column(db.String(16))
    category = db.Column(db.String(64))
    affected_component = db.Column(db.String(256))
    proof_of_concept = db.Column(db.Text)
    remediation = db.Column(db.Text)
    references = db.Column(db.JSON)
    status = db.Column(db.String(32), default="open")  # open, in_progress, resolved, false_positive
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    comments = db.relationship("VulnComment", backref="vulnerability", lazy="dynamic", cascade="all, delete-orphan")


class VulnComment(db.Model):
    __tablename__ = "vuln_comments"
    id = db.Column(db.Integer, primary_key=True)
    vulnerability_id = db.Column(db.Integer, db.ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")


class ApiKey(db.Model):
    __tablename__ = "api_keys"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    secret_hash = db.Column(db.String(256), nullable=False)
    scopes = db.Column(db.JSON, default=list)
    last_used = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserSession(db.Model):
    __tablename__ = "user_sessions"
    id = db.Column(db.String(64), primary_key=True, default=lambda: secrets.token_urlsafe(32))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(512))
    device = db.Column(db.String(128))
    location = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=14))


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    resource_type = db.Column(db.String(64))
    resource_id = db.Column(db.String(64))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(512))
    details = db.Column(db.JSON)
    status = db.Column(db.String(16), default="success")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(512))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Subscription(db.Model):
    __tablename__ = "subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"))
    plan = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(32), default="active")  # active, cancelled, expired, past_due
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    auto_renew = db.Column(db.Boolean, default=True)
    payment_provider = db.Column(db.String(32))  # stripe, payme, click
    external_id = db.Column(db.String(128))


class Webhook(db.Model):
    __tablename__ = "webhooks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    secret = db.Column(db.String(64), nullable=False, default=lambda: secrets.token_urlsafe(32))
    events = db.Column(db.JSON, default=list)  # scan.completed, vulnerability.found, etc.
    is_active = db.Column(db.Boolean, default=True)
    last_triggered = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ScheduledScan(db.Model):
    __tablename__ = "scheduled_scans"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    target = db.Column(db.String(512), nullable=False)
    scan_type = db.Column(db.String(64), nullable=False)
    cron_expression = db.Column(db.String(64), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id", ondelete="CASCADE"))
    name = db.Column(db.String(256), nullable=False)
    format = db.Column(db.String(16), default="pdf")  # pdf, html, json, xml
    file_path = db.Column(db.String(512))
    ai_summary = db.Column(db.Text)
    executive_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Settings(db.Model):
    __tablename__ = "settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False)
    value = db.Column(db.JSON)
    description = db.Column(db.String(256))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))


import os
