"""Patches and migrations for production deployment"""
from models import db
from sqlalchemy import inspect, text


def patch_user_columns(app):
    """Add missing columns to User model"""
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            if "users" in inspector.get_table_names():
                existing = {c["name"] for c in inspector.get_columns("users")}
                with db.engine.begin() as conn:
                    if "_verification_token" not in existing:
                        conn.execute(text("ALTER TABLE users ADD COLUMN _verification_token VARCHAR(64)"))
                    if "_reset_token" not in existing:
                        conn.execute(text("ALTER TABLE users ADD COLUMN _reset_token VARCHAR(64)"))
                    if "_reset_expires" not in existing:
                        conn.execute(text("ALTER TABLE users ADD COLUMN _reset_expires DATETIME"))
                    if "backup_codes" not in existing:
                        conn.execute(text("ALTER TABLE users ADD COLUMN backup_codes JSON"))
                    if "is_deleted" not in existing:
                        conn.execute(text("ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
                    if "avatar_url" not in existing:
                        conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512)"))
                    if "timezone" not in existing:
                        conn.execute(text("ALTER TABLE users ADD COLUMN timezone VARCHAR(64) DEFAULT 'UTC'"))
                    if "locale" not in existing:
                        conn.execute(text("ALTER TABLE users ADD COLUMN locale VARCHAR(8) DEFAULT 'en'"))
        except Exception as e:
            app.logger.warning(f"Column patch skipped: {e}")


def init_app(app):
    patch_user_columns(app)
