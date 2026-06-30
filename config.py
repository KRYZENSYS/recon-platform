"""Recon Platform konfiguratsiya fayli."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Asosiy konfiguratsiya."""

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'recon-platform-secret-key-change-in-prod'

    # SQLite ma'lumotlar bazasi
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'scans.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # So'rov sozlamalari
    REQUEST_TIMEOUT = 10
    USER_AGENT = 'Recon-Platform/1.0 (Security Testing)'

    # Spider sozlamalari
    MAX_PAGES = 100
    MAX_DEPTH = 3

    # Scan sozlamalari
    SCAN_STATUS_PENDING = 'pending'
    SCAN_STATUS_RUNNING = 'running'
    SCAN_STATUS_COMPLETED = 'completed'
    SCAN_STATUS_FAILED = 'failed'