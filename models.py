"""SQLAlchemy ma'lumotlar bazasi modellari."""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Scan(db.Model):
    """Tekshirish (scan) yozuvi."""
    __tablename__ = 'scans'

    id = db.Column(db.Integer, primary_key=True)
    target = db.Column(db.String(512), nullable=False, index=True)
    modules = db.Column(db.String(256), nullable=False)  # "spider,dns,user_enum,tech_detect"
    status = db.Column(db.String(32), nullable=False, default='pending', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Float, nullable=True)  # sekundlarda

    # Aloqalar
    spider_results = db.relationship('SpiderResult', backref='scan', lazy=True, cascade='all, delete-orphan')
    dns_results = db.relationship('DNSResult', backref='scan', lazy=True, cascade='all, delete-orphan')
    user_enum_results = db.relationship('UserEnumResult', backref='scan', lazy=True, cascade='all, delete-orphan')
    tech_results = db.relationship('TechResult', backref='scan', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'target': self.target,
            'modules': self.modules.split(',') if self.modules else [],
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'duration': self.duration
        }


class SpiderResult(db.Model):
    """Spider (crawler) natijalari."""
    __tablename__ = 'spider_results'

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'), nullable=False, index=True)
    url = db.Column(db.String(2048), nullable=False)
    depth = db.Column(db.Integer, default=0)
    status_code = db.Column(db.Integer, nullable=True)
    content_type = db.Column(db.String(128), nullable=True)
    title = db.Column(db.String(512), nullable=True)


class DNSResult(db.Model):
    """DNS ma'lumotlari."""
    __tablename__ = 'dns_results'

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'), nullable=False, index=True)
    record_type = db.Column(db.String(16), nullable=False)  # A, AAAA, MX, NS, TXT, CNAME
    host = db.Column(db.String(512), nullable=False)
    value = db.Column(db.String(1024), nullable=False)
    ttl = db.Column(db.Integer, nullable=True)


class UserEnumResult(db.Model):
    """Foydalanuvchi aniqlash natijalari."""
    __tablename__ = 'user_enum_results'

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'), nullable=False, index=True)
    username = db.Column(db.String(128), nullable=False)
    platform = db.Column(db.String(64), nullable=False)  # github, twitter, instagram, etc.
    url = db.Column(db.String(512), nullable=False)
    found = db.Column(db.Boolean, default=False)
    status_code = db.Column(db.Integer, nullable=True)


class TechResult(db.Model):
    """Texnologiyalarni aniqlash natijalari."""
    __tablename__ = 'tech_results'

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'), nullable=False, index=True)
    category = db.Column(db.String(64), nullable=False)  # Web Server, CMS, Framework, etc.
    name = db.Column(db.String(128), nullable=False)
    version = db.Column(db.String(64), nullable=True)
    confidence = db.Column(db.Integer, default=100)  # 0-100