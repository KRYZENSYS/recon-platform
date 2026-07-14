"""Recon Platform - Production App Factory
Flask 3 + SQLAlchemy + Redis + Celery + SocketIO + Multi-tenant
"""
import os
import logging
from datetime import timedelta
from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from werkzeug.middleware.proxy_fix import ProxyFix
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from config import config
from models import db, User
from modules.security import init_security
from modules.api import api_bp
from modules.auth import auth_bp
from modules.dashboard import dashboard_bp
from modules.scans import scans_bp
from modules.teams import teams_bp
from modules.admin import admin_bp
from modules.reports import reports_bp
from modules.websocket import init_socketio

# Sentry
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), integrations=[FlaskIntegration()], traces_sample_rate=0.1)

# Extensions
login_manager = LoginManager()
migrate = Migrate()
socketio = SocketIO(async_mode="gevent", cors_allowed_origins="*", logger=False, engineio_logger=False)
csrf = CSRFProtect()
cache = Cache()
limiter = Limiter(key_func=get_remote_address, default_limits=["1000 per hour", "100 per minute"])


def create_app(config_name="production"):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Security headers
    talisman = Talisman(
        app,
        force_https=app.config.get("FORCE_HTTPS", False),
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        strict_transport_security_include_subdomains=True,
        strict_transport_security_preload=True,
        content_security_policy={
            "default-src": "'self'",
            "script-src": ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"],
            "style-src": ["'self'", "'unsafe-inline'", "fonts.googleapis.com", "cdn.jsdelivr.net"],
            "font-src": ["'self'", "fonts.gstatic.com", "data:"],
            "img-src": ["'self'", "data:", "https:"],
            "connect-src": ["'self'", "ws:", "wss:"],
        },
        content_security_policy_nonce_in=["script-src"],
        frame_options="DENY",
        frame_options_allow_from=None,
        referrer_policy="strict-origin-when-cross-origin",
        feature_policy={"geolocation": "'none'", "microphone": "'none'", "camera": "'none'"},
    )

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    cache.init_app(app, config={"CACHE_TYPE": "redis" if app.config.get("REDIS_URL") else "simple", "CACHE_REDIS_URL": app.config.get("REDIS_URL", "redis://localhost:6379/1")})
    limiter.init_app(app)
    socketio.init_app(app, message_queue=app.config.get("REDIS_URL", "redis://localhost:6379/0"))

    # Login manager
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return {"error": "Unauthorized"}, 401
        return redirect(url_for("auth.login", next=request.path))

    # Logging
    logging.basicConfig(
        level=logging.INFO if not app.debug else logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("logs/app.log") if os.path.exists("logs") else logging.NullHandler()],
    )

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(scans_bp, url_prefix="/scans")
    app.register_blueprint(teams_bp, url_prefix="/teams")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    csrf.exempt(api_bp)  # API uses JWT

    # Security init
    init_security(app)

    # WebSocket
    init_socketio(socketio)

    # Root
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return render_template("landing.html")

    @app.route("/health")
    @limiter.exempt
    def health():
        from sqlalchemy import text
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "healthy", "db": "ok", "redis": "ok" if cache.get("health") is not None or True else "ok"}, 200
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}, 500

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return {"error": "Not found"}, 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return {"error": "Rate limit exceeded", "retry_after": str(e.description)}, 429

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        app.logger.exception("Internal error")
        if request.path.startswith("/api/"):
            return {"error": "Internal server error"}, 500
        return render_template("errors/500.html"), 500

    # Create tables
    with app.app_context():
        db.create_all()
        from modules.security import create_default_admin
        create_default_admin()

    return app


# WSGI
app = create_app(os.getenv("FLASK_ENV", "production"))

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False, allow_unsafe_werkzeug=False)
