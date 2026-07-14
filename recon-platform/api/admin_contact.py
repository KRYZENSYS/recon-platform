"""Admin contact API endpoints"""
import os
import json
import logging
from pathlib import Path
from flask import Blueprint, jsonify, request, send_from_directory

logger = logging.getLogger(__name__)

admin_contact_bp = Blueprint("admin_contact", __name__, url_prefix="/api/v1/admin")

CONFIG_PATH = Path(__file__).parent.parent / "config" / "admin_contact.json"


def _load_contact_config():
    """Load admin contact configuration"""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load contact config: {e}")
    return {
        "admin": {
            "name": "Firdavs (FirdavsVIP)",
            "role": "Founder & Lead Developer",
            "organization": "KRYZENSYS",
            "email": "f91186645@gmail.com",
            "telegram": {"username": "FirdavsVIP", "url": "https://t.me/FirdavsVIP", "display": "@FirdavsVIP"},
            "github": {"username": "KRYZENSYS", "url": "https://github.com/KRYZENSYS/", "display": "github.com/KRYZENSYS"}
        }
    }


@admin_contact_bp.route("/contact", methods=["GET"])
def get_admin_contact():
    """Get admin contact information"""
    config = _load_contact_config()
    return jsonify(config), 200


@admin_contact_bp.route("/contact/email", methods=["POST"])
def contact_via_email():
    """Submit a contact form message"""
    try:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        subject = data.get("subject", "").strip()
        message = data.get("message", "").strip()

        if not (name and email and subject and message):
            return jsonify({"error": "All fields are required"}), 400

        if "@" not in email or "." not in email:
            return jsonify({"error": "Invalid email"}), 400

        config = _load_contact_config()
        admin_email = config["admin"]["email"]

        try:
            from modules.email_service import send_email
            email_subject = f"[Recon Platform] {subject}"
            email_body = f"""
New contact form submission:

Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}

---
Sent from: Recon Platform Admin Contact Form
Timestamp: {request.headers.get('Date', 'N/A')}
IP: {request.remote_addr}
"""
            send_email(admin_email, email_subject, email_body)
        except Exception as e:
            logger.error(f"Email send failed: {e}")

        return jsonify({"success": True, "message": "Your message has been sent. We'll respond within 24 hours."}), 200

    except Exception as e:
        logger.error(f"Contact form error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@admin_contact_bp.route("/contact/info", methods=["GET"])
def contact_info_summary():
    """Get a short summary"""
    config = _load_contact_config()
    admin = config.get("admin", {})
    return jsonify({
        "name": admin.get("name"),
        "email": admin.get("email"),
        "telegram": admin.get("telegram", {}).get("display"),
        "github": admin.get("github", {}).get("display"),
        "organization": admin.get("organization"),
        "response_time": "24 hours",
    })
