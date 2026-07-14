"""Production configuration with multi-environment support"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(64).hex())
    WTF_CSRF_TIME_LIMIT = 3600
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///recon.db").replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 300, "pool_size": 10, "max_overflow": 20}

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Celery
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/3")
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TIMEZONE = "UTC"
    CELERY_TASK_TIME_LIMIT = 600
    CELERY_TASK_SOFT_TIME_LIMIT = 540

    # Security
    BCRYPT_ROUNDS = 14
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.urandom(64).hex())
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() == "true"
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

    # Rate limiting
    RATELIMIT_STORAGE_URL = os.getenv("REDIS_URL", "redis://localhost:6379/4")
    RATELIMIT_STRATEGY = "fixed-window-elastic-expiry"
    RATELIMIT_HEADERS_ENABLED = True

    # Mail
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

    # Scan limits per plan
    PLAN_LIMITS = {
        "free": {"scans_per_month": 10, "concurrent_scans": 1, "team_members": 1, "api_calls_per_day": 100},
        "pro": {"scans_per_month": 100, "concurrent_scans": 5, "team_members": 5, "api_calls_per_day": 1000},
        "business": {"scans_per_month": 1000, "concurrent_scans": 20, "team_members": 50, "api_calls_per_day": 10000},
        "enterprise": {"scans_per_month": -1, "concurrent_scans": 100, "team_members": -1, "api_calls_per_day": -1},
    }

    # Recon settings
    RECON_USER_AGENT = "Mozilla/5.0 (compatible; ReconPlatform/2.0; +https://recon.kryzensys.com)"
    RECON_TIMEOUT = 30
    RECON_MAX_CONCURRENT = 50
    RECON_CACHE_TTL = 86400  # 24h

    # External APIs
    SHODAN_API_KEY = os.getenv("SHODAN_API_KEY")
    CENSYS_API_ID = os.getenv("CENSYS_API_ID")
    CENSYS_API_SECRET = os.getenv("CENSYS_API_SECRET")
    VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")

    # AI
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # Webhook
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", os.urandom(32).hex())

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

    # Sentry
    SENTRY_DSN = os.getenv("SENTRY_DSN")

    # Feature flags
    ENABLE_REGISTRATION = os.getenv("ENABLE_REGISTRATION", "true").lower() == "true"
    ENABLE_API_SIGNUP = os.getenv("ENABLE_API_SIGNUP", "true").lower() == "true"
    REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "true").lower() == "true"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False
    FORCE_HTTPS = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DEV_DATABASE_URL", "sqlite:///recon_dev.db")
    LOG_LEVEL = "DEBUG"
    BCRYPT_ROUNDS = 4


class TestingConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    BCRYPT_ROUNDS = 4
    WTF_CSRF_ENABLED = False
    ENABLE_REGISTRATION = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    FORCE_HTTPS = True
    LOG_LEVEL = "WARNING"


class StagingConfig(ProductionConfig):
    DEBUG = True
    FORCE_HTTPS = False


config = {"development": DevelopmentConfig, "production": ProductionConfig, "staging": StagingConfig, "testing": TestingConfig, "default": ProductionConfig}
