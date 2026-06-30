"""iSpeak konfiguratsiya fayli."""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Asosiy sozlamalar."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'ispeak-dev-secret-change-in-prod')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'ispeak-jwt-secret-change')
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 7  # 7 kun

    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'ispeak.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Groq API
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    GROQ_BASE_URL = 'https://api.groq.com/openai/v1'
    GROQ_CHAT_MODEL = 'llama-3.3-70b-versatile'  # yoki 'llama-3.1-8b-instant'
    GROQ_WHISPER_MODEL = 'whisper-large-v3'  # audio uchun

    # Til sozlamalari
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'uz': 'Uzbek',
        'ru': 'Russian',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'tr': 'Turkish',
        'ar': 'Arabic',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ko': 'Korean',
    }

    # CEFR darajalari
    LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

    # Limitlar
    FREE_DAILY_MESSAGES = 10
    FREE_DAILY_PRONUNCIATION = 5