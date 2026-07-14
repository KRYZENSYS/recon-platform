"""Seed data - default settings, demo organization"""
from datetime import datetime, timedelta
from models import db, Settings, Organization, Subscription


DEFAULT_SETTINGS = {
    "site_name": {"value": "Recon Platform", "description": "Site display name"},
    "site_description": {"value": "Professional web reconnaissance and security testing", "description": "Site meta description"},
    "registration_enabled": {"value": True, "description": "Allow new user registration"},
    "email_verification_required": {"value": True, "description": "Require email verification"},
    "max_scan_targets_free": {"value": 10, "description": "Max scans/month for free"},
    "max_scan_targets_pro": {"value": 100, "description": "Max scans/month for pro"},
    "rate_limit_per_minute": {"value": 60, "description": "API rate limit"},
    "ai_reports_enabled": {"value": True, "description": "Enable AI reports"},
    "groq_model": {"value": "llama-3.3-70b-versatile", "description": "AI model"},
    "session_timeout_hours": {"value": 12, "description": "Session timeout"},
    "password_min_length": {"value": 12, "description": "Min password length"},
    "maintenance_mode": {"value": False, "description": "Maintenance mode"},
    "max_upload_size_mb": {"value": 50, "description": "Max upload size"},
    "webhook_timeout_seconds": {"value": 30, "description": "Webhook timeout"},
    "default_scan_timeout": {"value": 300, "description": "Default scan timeout"},
}


def seed_settings():
    """Seed default settings"""
    for key, data in DEFAULT_SETTINGS.items():
        if not Settings.query.filter_by(key=key).first():
            db.session.add(Settings(key=key, value=data["value"], description=data["description"]))
    db.session.commit()


def seed_demo_data():
    """Create demo organization"""
    if not Organization.query.filter_by(slug="demo").first():
        org = Organization(name="Demo Organization", slug="demo", plan="business", billing_email="demo@recon.local", max_seats=10)
        db.session.add(org)
        db.session.flush()
        sub = Subscription(user_id=1, organization_id=org.id, plan="business", status="active", started_at=datetime.utcnow(), expires_at=datetime.utcnow() + timedelta(days=30), payment_provider="system", external_id="demo")
        db.session.add(sub)
        db.session.commit()
        print(f"✅ Demo org: {org.name}")


def seed_all(app):
    """Run all seeds"""
    with app.app_context():
        seed_settings()
        seed_demo_data()
        print(f"✅ Seeded {len(DEFAULT_SETTINGS)} settings")
