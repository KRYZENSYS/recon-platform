"""WebSocket real-time support"""
import os
import logging
from flask import Blueprint, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user
from datetime import datetime
import jwt

logger = logging.getLogger(__name__)
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet", logger=False, engineio_logger=False)
ws_bp = Blueprint("ws", __name__)


def authenticate_token(token: str):
    try:
        secret = os.getenv("JWT_SECRET_KEY", "dev-secret")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        from models import User
        user = User.query.get(payload["user_id"])
        if user and user.is_active and not user.is_banned: return user
    except: return None


@socketio.on("connect")
def handle_connect(auth=None):
    token = (auth or {}).get("token") or request.args.get("token")
    user = authenticate_token(token) if token else None
    if not user: return False
    join_room(f"user_{user.id}")
    if user.is_admin: join_room("admins")
    emit("connected", {"user_id": user.id, "username": user.username, "is_admin": user.is_admin, "timestamp": datetime.utcnow().isoformat()})


@socketio.on("disconnect")
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(f"user_{current_user.id}")
        if current_user.is_admin: leave_room("admins")


@socketio.on("subscribe_scan")
def handle_subscribe_scan(data):
    scan_id = data.get("scan_id")
    if scan_id:
        join_room(f"scan_{scan_id}")
        emit("subscribed", {"scan_id": scan_id})


@socketio.on("ping")
def handle_ping(data):
    emit("pong", {"timestamp": datetime.utcnow().isoformat()})


def broadcast_new_user(user_data):
    socketio.emit("new_user", user_data, room="admins")

def broadcast_new_scan(scan_data, user_id):
    socketio.emit("new_scan", scan_data, room=f"user_{user_id}")
    socketio.emit("new_scan", scan_data, room="admins")

def broadcast_scan_progress(scan_id, progress, status, findings_count=0):
    socketio.emit("scan_progress", {"scan_id": scan_id, "progress": progress, "status": status, "findings_count": findings_count, "timestamp": datetime.utcnow().isoformat()}, room=f"scan_{scan_id}")

def broadcast_scan_complete(scan_id, user_id, target, findings_count, duration):
    socketio.emit("scan_complete", {"scan_id": scan_id, "target": target, "findings": findings_count, "duration": duration, "timestamp": datetime.utcnow().isoformat()}, room=f"user_{user_id}")
    socketio.emit("scan_complete", {"scan_id": scan_id, "user_id": user_id, "target": target, "findings": findings_count}, room="admins")

def broadcast_notification(user_id, notification_type, data):
    socketio.emit("notification", {"type": notification_type, "data": data, "timestamp": datetime.utcnow().isoformat()}, room=f"user_{user_id}")

def broadcast_to_admins(event, data):
    socketio.emit(event, data, room="admins")

def broadcast_system_alert(message, severity="info"):
    socketio.emit("system_alert", {"message": message, "severity": severity, "timestamp": datetime.utcnow().isoformat()})
