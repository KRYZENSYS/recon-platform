"""iSpeak ma'lumotlar bazasi modellari."""
from datetime import datetime, date

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """Foydalanuvchi."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    avatar_url = db.Column(db.String(512), nullable=True)

    # Til sozlamalari
    native_language = db.Column(db.String(8), default='uz', nullable=False)
    target_language = db.Column(db.String(8), default='en', nullable=False)
    level = db.Column(db.String(8), default='A1', nullable=False)

    # Gamification
    xp = db.Column(db.Integer, default=0, nullable=False)
    streak_days = db.Column(db.Integer, default=0, nullable=False)
    last_active_date = db.Column(db.Date, nullable=True)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)

    # Vaqt
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Aloqalar
    progress = db.relationship('UserProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True, cascade='all, delete-orphan')
    pronunciation_attempts = db.relationship('PronunciationAttempt', backref='user', lazy=True, cascade='all, delete-orphan')
    achievements = db.relationship('Achievement', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'avatar_url': self.avatar_url,
            'native_language': self.native_language,
            'target_language': self.target_language,
            'level': self.level,
            'xp': self.xp,
            'streak_days': self.streak_days,
            'is_premium': self.is_premium,
            'level_progress': self.get_level_progress(),
            'created_at': self.created_at.isoformat(),
        }

    def get_level_progress(self):
        """Level ichida qancha foiz o'tilganini hisoblash."""
        levels_xp = {'A1': 0, 'A2': 500, 'B1': 1500, 'B2': 3500, 'C1': 7000, 'C2': 12000}
        current_xp = levels_xp.get(self.level, 0)
        next_level_xp = list(levels_xp.values())[list(levels_xp.keys()).index(self.level) + 1] if self.level != 'C2' else 12000
        progress = ((self.xp - current_xp) / (next_level_xp - current_xp)) * 100 if next_level_xp > current_xp else 100
        return min(max(progress, 0), 100)

    def update_streak(self):
        """Streakni yangilash."""
        today = date.today()
        if self.last_active_date == today:
            return
        if self.last_active_date == today - __import__('datetime').timedelta(days=1):
            self.streak_days += 1
        else:
            self.streak_days = 1
        self.last_active_date = today


class Lesson(db.Model):
    """Dars."""
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(8), nullable=False, index=True)
    level = db.Column(db.String(8), nullable=False, index=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    topic = db.Column(db.String(64), nullable=False)  # travel, food, business, daily
    order_index = db.Column(db.Integer, default=0)
    duration_minutes = db.Column(db.Integer, default=15)
    is_premium = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contents = db.relationship('LessonContent', backref='lesson', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'language': self.language,
            'level': self.level,
            'title': self.title,
            'description': self.description,
            'topic': self.topic,
            'duration_minutes': self.duration_minutes,
            'is_premium': self.is_premium,
            'contents_count': len(self.contents),
        }


class LessonContent(db.Model):
    """Dars kontenti."""
    __tablename__ = 'lesson_contents'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    type = db.Column(db.String(32), nullable=False)  # vocabulary, dialogue, grammar, quiz
    order_index = db.Column(db.Integer, default=0)
    content_json = db.Column(db.Text, nullable=False)  # JSON formatida saqlanadi


class UserProgress(db.Model):
    """Foydalanuvchi darslardagi progressi."""
    __tablename__ = 'user_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer, default=0)  # 0-100
    time_spent_seconds = db.Column(db.Integer, default=0)
    last_attempt_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    lesson = db.relationship('Lesson', backref='progress_entries')


class ChatSession(db.Model):
    """AI chatbot suhbat sessiyasi."""
    __tablename__ = 'chat_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    scenario = db.Column(db.String(64), nullable=False)  # restaurant, airport, job_interview
    language = db.Column(db.String(8), nullable=False)
    messages_json = db.Column(db.Text, default='[]')  # JSON array of {role, content, corrections}
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)


class PronunciationAttempt(db.Model):
    """Talaffuz urinishlari."""
    __tablename__ = 'pronunciation_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    phrase_text = db.Column(db.String(512), nullable=False)
    recognized_text = db.Column(db.String(512), nullable=True)
    accuracy_score = db.Column(db.Integer, default=0)  # 0-100
    feedback = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(8), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Achievement(db.Model):
    """Yutuq (badge)."""
    __tablename__ = 'achievements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    badge_type = db.Column(db.String(64), nullable=False)  # first_lesson, streak_7, level_up, ...
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(512), nullable=True)
    icon = db.Column(db.String(32), default='🏆')
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)


class DailyUsage(db.Model):
    """Kunlik foydalanish statistikasi (free limit uchun)."""
    __tablename__ = 'daily_usage'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    messages_count = db.Column(db.Integer, default=0)
    pronunciation_count = db.Column(db.Integer, default=0)