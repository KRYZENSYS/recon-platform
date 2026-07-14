"""Email service - SendGrid, SMTP, AWS SES, Mailgun support"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailService:
    PROVIDERS = ["sendgrid", "smtp", "aws_ses", "mailgun"]

    def __init__(self, provider: str = None):
        self.provider = provider or os.getenv("EMAIL_PROVIDER", "smtp")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@recon.kryzensys.com")
        self.from_name = os.getenv("FROM_NAME", "Recon Platform")

    def send(self, to: str, subject: str, html: str, text: str = None, attachments: List[Dict] = None) -> Dict:
        try:
            if self.provider == "sendgrid": return self._send_sendgrid(to, subject, html, text, attachments)
            if self.provider == "aws_ses": return self._send_aws_ses(to, subject, html, text)
            if self.provider == "mailgun": return self._send_mailgun(to, subject, html, text)
            return self._send_smtp(to, subject, html, text, attachments)
        except Exception as e:
            logger.error(f"Email failed: {e}")
            return {"success": False, "error": str(e)}

    def _send_smtp(self, to, subject, html, text, attachments=None) -> Dict:
        host, port = os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587"))
        user, password = os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", "")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to
        if text: msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        if attachments:
            for att in attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(att["content"])
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={att['filename']}")
                msg.attach(part)
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            if user and password: server.login(user, password)
            server.sendmail(self.from_email, [to], msg.as_string())
        return {"success": True, "provider": "smtp"}

    def _send_sendgrid(self, to, subject, html, text, attachments=None) -> Dict:
        import requests
        api_key = os.getenv("SENDGRID_API_KEY", "")
        if not api_key: return {"success": False, "error": "SENDGRID_API_KEY not set"}
        data = {"personalizations": [{"to": [{"email": to}], "subject": subject}], "from": {"email": self.from_email, "name": self.from_name}, "content": [{"type": "text/plain", "value": text or ""}, {"type": "text/html", "value": html}]}
        res = requests.post("https://api.sendgrid.com/v3/mail/send", json=data, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, timeout=10)
        return {"success": res.status_code in [200, 202], "provider": "sendgrid"}

    def _send_aws_ses(self, to, subject, html, text) -> Dict:
        try:
            import boto3
            client = boto3.client("ses", region_name=os.getenv("AWS_REGION", "us-east-1"))
            response = client.send_email(Source=f"{self.from_name} <{self.from_email}>", Destination={"ToAddresses": [to] if isinstance(to, str) else to}, Message={"Subject": {"Data": subject, "Charset": "UTF-8"}, "Body": {"Html": {"Data": html, "Charset": "UTF-8"}, "Text": {"Data": text or "", "Charset": "UTF-8"}}})
            return {"success": True, "provider": "aws_ses", "message_id": response["MessageId"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _send_mailgun(self, to, subject, html, text) -> Dict:
        import requests
        api_key, domain = os.getenv("MAILGUN_API_KEY", ""), os.getenv("MAILGUN_DOMAIN", "")
        if not api_key or not domain: return {"success": False, "error": "Mailgun not configured"}
        res = requests.post(f"https://api.mailgun.net/v3/{domain}/messages", auth=("api", api_key), data={"from": f"{self.from_name} <{self.from_email}>", "to": to, "subject": subject, "html": html, "text": text or ""}, timeout=10)
        return {"success": res.status_code == 200, "provider": "mailgun"}


class EmailTemplates:
    @staticmethod
    def welcome(username: str, login_url: str = "https://recon.kryzensys.com/login") -> Dict:
        html = f"""<html><body style="font-family:Arial;background:#0f172a;color:#e2e8f0;padding:40px"><div style="max-width:600px;margin:0 auto;background:#1e293b;border-radius:16px;padding:40px"><div style="text-align:center;margin-bottom:30px"><div style="display:inline-block;width:60px;height:60px;background:linear-gradient(135deg,#6366f1,#a855f7);border-radius:16px;line-height:60px;font-size:30px">🛡️</div></div><h1 style="color:#fff;text-align:center">Welcome, {username}!</h1><p style="text-align:center;color:#94a3b8">Your account is ready</p><div style="text-align:center;margin:30px 0"><a href="{login_url}" style="display:inline-block;background:linear-gradient(90deg,#6366f1,#a855f7);color:#fff;padding:14px 40px;border-radius:8px;text-decoration:none;font-weight:600">Login Now →</a></div></div></body></html>"""
        return {"subject": f"Welcome to Recon Platform, {username}! 🛡️", "html": html, "text": f"Welcome {username}! Login: {login_url}"}

    @staticmethod
    def password_reset(username: str, reset_url: str) -> Dict:
        html = f"""<html><body style="font-family:Arial;background:#0f172a;color:#e2e8f0;padding:40px"><div style="max-width:600px;margin:0 auto;background:#1e293b;border-radius:16px;padding:40px"><h1 style="color:#fff">🔐 Password Reset</h1><p>Hi {username},</p><p>Click the button to reset your password:</p><div style="text-align:center;margin:30px 0"><a href="{reset_url}" style="display:inline-block;background:linear-gradient(90deg,#6366f1,#a855f7);color:#fff;padding:14px 40px;border-radius:8px;text-decoration:none;font-weight:600">Reset Password</a></div><p style="color:#f87171">⚠️ If you didn't request this, ignore this email.</p></div></body></html>"""
        return {"subject": "🔐 Password Reset", "html": html, "text": f"Reset: {reset_url}"}

    @staticmethod
    def email_verification(username: str, verify_url: str) -> Dict:
        html = f"""<html><body style="font-family:Arial;background:#0f172a;color:#e2e8f0;padding:40px"><div style="max-width:600px;margin:0 auto;background:#1e293b;border-radius:16px;padding:40px"><h1 style="color:#fff">✉️ Verify Email</h1><p>Hi {username}, verify your email:</p><div style="text-align:center;margin:30px 0"><a href="{verify_url}" style="display:inline-block;background:linear-gradient(90deg,#10b981,#059669);color:#fff;padding:14px 40px;border-radius:8px;text-decoration:none;font-weight:600">Verify</a></div></div></body></html>"""
        return {"subject": "✉️ Verify Email", "html": html, "text": f"Verify: {verify_url}"}

    @staticmethod
    def scan_complete(username: str, target: str, findings_count: int, severity_high: int, report_url: str) -> Dict:
        c = "#ef4444" if severity_high > 0 else "#10b981"
        html = f"""<html><body style="font-family:Arial;background:#0f172a;color:#e2e8f0;padding:40px"><div style="max-width:600px;margin:0 auto;background:#1e293b;border-radius:16px;padding:40px"><h1 style="color:#fff">🔍 Scan Complete</h1><p>Hi {username},</p><div style="background:#334155;border-radius:12px;padding:24px;margin:20px 0"><p><strong>Target:</strong> <code style="background:#0f172a;padding:4px 8px;border-radius:4px">{target}</code></p><p><strong>Findings:</strong> {findings_count}</p><p><strong>High Severity:</strong> <span style="color:{c};font-weight:600">{severity_high}</span></p></div><a href="{report_url}" style="display:inline-block;background:linear-gradient(90deg,#6366f1,#a855f7);color:#fff;padding:14px 40px;border-radius:8px;text-decoration:none;font-weight:600">View Report →</a></div></body></html>"""
        return {"subject": f"🔍 Scan complete: {target}", "html": html, "text": f"Scan done: {target} ({findings_count} findings)"}

    @staticmethod
    def admin_broadcast(message: str) -> Dict:
        html = f"""<html><body style="font-family:Arial;background:#0f172a;color:#e2e8f0;padding:40px"><div style="max-width:600px;margin:0 auto;background:#1e293b;border-radius:16px;padding:40px"><h1 style="color:#fff">📢 Announcement</h1><div style="background:#334155;border-radius:12px;padding:24px;margin:20px 0"><p style="white-space:pre-wrap">{message}</p></div></div></body></html>"""
        return {"subject": "📢 Announcement", "html": html, "text": message}

    @staticmethod
    def invoice(invoice_id: str, amount: float, plan: str) -> Dict:
        html = f"""<html><body style="font-family:Arial;background:#0f172a;color:#e2e8f0;padding:40px"><div style="max-width:600px;margin:0 auto;background:#1e293b;border-radius:16px;padding:40px"><h1 style="color:#fff">💰 Invoice</h1><p><strong>Invoice:</strong> {invoice_id}</p><p><strong>Plan:</strong> {plan}</p><p><strong>Amount:</strong> <span style="font-size:24px;color:#10b981;font-weight:600">${amount:.2f}</span></p></div></body></html>"""
        return {"subject": f"💰 Invoice #{invoice_id}", "html": html, "text": f"Invoice {invoice_id}: ${amount:.2f}"}


_email_service = None

def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None: _email_service = EmailService()
    return _email_service

def send_email(to: str, subject: str, html: str, text: str = None, **kwargs) -> Dict:
    return get_email_service().send(to, subject, html, text, **kwargs)

def send_welcome_email(user_email: str, username: str) -> Dict:
    t = EmailTemplates.welcome(username)
    return send_email(user_email, t["subject"], t["html"], t["text"])

def send_password_reset_email(user_email: str, username: str, reset_token: str) -> Dict:
    t = EmailTemplates.password_reset(username, f"https://recon.kryzensys.com/reset-password?token={reset_token}")
    return send_email(user_email, t["subject"], t["html"], t["text"])

def send_verification_email(user_email: str, username: str, verify_token: str) -> Dict:
    t = EmailTemplates.email_verification(username, f"https://recon.kryzensys.com/verify-email?token={verify_token}")
    return send_email(user_email, t["subject"], t["html"], t["text"])
