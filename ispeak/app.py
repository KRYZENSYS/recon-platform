"""iSpeak — Asosiy Flask ilovasi (Groq AI bilan)."""
import os
import json
import uuid
from datetime import datetime, date, timedelta

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import Config
from models import db, User, Lesson, LessonContent, UserProgress, ChatSession, PronunciationAttempt, Achievement, DailyUsage
from services.groq_service import groq_service


def create_app():
    """Flask ilovasini yaratish."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Kengaytmalar
    db.init_app(app)
    jwt = JWTManager(app)
    CORS(app, origins='*')

    # Upload sozlamalari
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

    with app.app_context():
        db.create_all()

    # =========================================
    # HELPER FUNKSIYALAR
    # =========================================

    def get_today_usage(user_id):
        """Bugungi foydalanish statistikasi."""
        today = date.today()
        usage = DailyUsage.query.filter_by(user_id=user_id, date=today).first()
        if not usage:
            usage = DailyUsage(user_id=user_id, date=today)
            db.session.add(usage)
            db.session.commit()
        return usage

    def check_message_limit(user_id):
        """Free user limitini tekshirish."""
        user = User.query.get(user_id)
        if user.is_premium:
            return True
        usage = get_today_usage(user_id)
        return usage.messages_count < Config.FREE_DAILY_MESSAGES

    def add_xp(user_id, xp_amount):
        """XP qo'shish va level oshirish."""
        user = User.query.get(user_id)
        if not user:
            return
        user.xp += xp_amount
        # Level avtomatik oshirish
        levels_xp = {'A1': 0, 'A2': 500, 'B1': 1500, 'B2': 3500, 'C1': 7000, 'C2': 12000}
        for level, required_xp in levels_xp.items():
            if user.xp >= required_xp and level > user.level:
                user.level = level
                # Yangi badge berish
                achievement = Achievement(
                    user_id=user_id,
                    badge_type=f'level_{level.lower()}',
                    title=f'{level} darajaga yetdingiz!',
                    description=f'Tabriklayman! Siz {level} darajasini zabt etdingiz.',
                    icon='🎉'
                )
                db.session.add(achievement)
        user.update_streak()
        db.session.commit()

    # =========================================
    # AUTH ROUTES
    # =========================================

    @app.route('/api/auth/register', methods=['POST'])
    def register():
        """Ro'yxatdan o'tish."""
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        native_language = data.get('native_language', 'uz')
        target_language = data.get('target_language', 'en')

        if not email or not password or not name:
            return jsonify({'error': 'Email, parol va ism talab qilinadi'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Parol kamida 6 ta belgidan iborat bo\'lishi kerak'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Bu email allaqachon ro\'yxatdan o\'tgan'}), 400

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            name=name,
            native_language=native_language,
            target_language=target_language,
        )
        db.session.add(user)
        db.session.commit()

        # Birinchi dars uchun rag'bat
        first_lesson = Achievement(
            user_id=user.id,
            badge_type='welcome',
            title='iSpeak oilasiga xush kelibsiz!',
            description='Til o\'rganish sayohatingiz boshlandi',
            icon='🎤'
        )
        db.session.add(first_lesson)
        db.session.commit()

        token = create_access_token(identity=str(user.id))

        return jsonify({
            'token': token,
            'user': user.to_dict(),
            'message': 'Muvaffaqiyatli ro\'yxatdan o\'tdingiz!'
        }), 201

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """Tizimga kirish."""
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Email yoki parol noto\'g\'ri'}), 401

        token = create_access_token(identity=str(user.id))

        return jsonify({
            'token': token,
            'user': user.to_dict(),
        })

    @app.route('/api/auth/me', methods=['GET'])
    @jwt_required()
    def get_me():
        """Joriy foydalanuvchi ma'lumotlari."""
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404
        return jsonify(user.to_dict())

    # =========================================
    # CHAT ROUTES (AI BILAN SUHBAT)
    # =========================================

    @app.route('/api/chat/start', methods=['POST'])
    @jwt_required()
    def start_chat():
        """Yangi chat sessiyasini boshlash."""
        user_id = int(get_jwt_identity())
        data = request.get_json()
        scenario = data.get('scenario', 'small_talk')

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

        if not check_message_limit(user_id):
            return jsonify({
                'error': f'Kunlik limit tugadi. Premium obuna bo\'ling yoki ertaga qaytib keling!',
                'limit_reached': True
            }), 429

        session = ChatSession(
            user_id=user_id,
            scenario=scenario,
            language=user.target_language,
        )
        db.session.add(session)
        db.session.commit()

        return jsonify({
            'session_id': session.id,
            'scenario': scenario,
            'language': user.target_language,
            'user_level': user.level,
        })

    @app.route('/api/chat/message', methods=['POST'])
    @jwt_required()
    def send_chat_message():
        """AI chatbotga xabar yuborish."""
        user_id = int(get_jwt_identity())
        data = request.get_json()
        session_id = data.get('session_id')
        message = data.get('message', '').strip()

        if not message:
            return jsonify({'error': 'Xabar bo\'sh bo\'lmasligi kerak'}), 400

        # Limit tekshirish
        if not check_message_limit(user_id):
            return jsonify({
                'error': 'Kunlik limit tugadi!',
                'limit_reached': True
            }), 429

        session = ChatSession.query.get(session_id)
        if not session or session.user_id != user_id:
            return jsonify({'error': 'Sessiya topilmadi'}), 404

        user = User.query.get(user_id)

        # History parse qilish
        try:
            history = json.loads(session.messages_json or '[]')
        except json.JSONDecodeError:
            history = []

        # AI dan javob olish
        result = groq_service.get_chat_response(
            user_message=message,
            scenario=session.scenario,
            language=session.language,
            user_level=user.level,
            history=history,
            native_language=user.native_language
        )

        # History yangilash
        history.append({'role': 'user', 'content': message})
        history.append({'role': 'assistant', 'content': result['reply']})
        session.messages_json = json.dumps(history)

        # Statistika yangilash
        usage = get_today_usage(user_id)
        usage.messages_count += 1

        # XP qo'shish
        xp_gained = 10
        if result['corrections']:
            xp_gained += 5  # Xatolar tuzatilganda qo'shimcha XP

        db.session.commit()
        add_xp(user_id, xp_gained)

        return jsonify({
            'reply': result['reply'],
            'corrections': result['corrections'],
            'translation': result['translation'],
            'suggestions': result['suggestions'],
            'xp_gained': xp_gained,
            'total_xp': user.xp,
            'messages_remaining': (Config.FREE_DAILY_MESSAGES - usage.messages_count) if not user.is_premium else -1,
        })

    # =========================================
    # PRONUNCIATION ROUTES (TALAFUZ)
    # =========================================

    @app.route('/api/pronunciation/phrases', methods=['GET'])
    @jwt_required()
    def get_practice_phrases():
        """Talaffuz mashqi uchun iboralar."""
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        # So'nggi urinishlardan iboralar olmaslik uchun har safar yangi generatsiya
        phrases = groq_service.generate_practice_phrases(
            language=user.target_language,
            level=user.level,
            count=5
        )

        return jsonify({'phrases': phrases})

    @app.route('/api/pronunciation/evaluate', methods=['POST'])
    @jwt_required()
    def evaluate_pronunciation():
        """Audio faylni talaffuzini baholash."""
        user_id = int(get_jwt_identity())

        # Free limit
        usage = get_today_usage(user_id)
        user = User.query.get(user_id)
        if not user.is_premium and usage.pronunciation_count >= Config.FREE_DAILY_PRONUNCIATION:
            return jsonify({
                'error': 'Kunlik talaffuz limiti tugadi!',
                'limit_reached': True
            }), 429

        # Audio faylni olish
        if 'audio' not in request.files:
            return jsonify({'error': 'Audio fayl yuborilmagan'}), 400

        audio_file = request.files['audio']
        expected_text = request.form.get('expected_text', '').strip()

        if not expected_text:
            return jsonify({'error': 'expected_text talab qilinadi'}), 400

        if audio_file.filename == '':
            return jsonify({'error': 'Fayl tanlanmagan'}), 400

        # Faylni saqlash
        filename = secure_filename(f'{uuid.uuid4()}_{audio_file.filename}')
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(filepath)

        try:
            # Whisper bilan transkripsiya
            recognized_text = groq_service.transcribe_audio(
                filepath,
                language=user.target_language
            )

            # Baholash
            evaluation = groq_service.evaluate_pronunciation(
                expected_text=expected_text,
                recognized_text=recognized_text,
                language=user.target_language,
                native_language=user.native_language
            )

            # Saqlash
            attempt = PronunciationAttempt(
                user_id=user_id,
                phrase_text=expected_text,
                recognized_text=recognized_text,
                accuracy_score=evaluation['accuracy'],
                feedback=evaluation['feedback'],
                language=user.target_language
            )
            db.session.add(attempt)

            usage.pronunciation_count += 1
            db.session.commit()

            # XP qo'shish
            xp_gained = max(5, evaluation['accuracy'] // 10)
            add_xp(user_id, xp_gained)

            return jsonify({
                'evaluation': evaluation,
                'xp_gained': xp_gained,
                'attempts_remaining': (Config.FREE_DAILY_PRONUNCIATION - usage.pronunciation_count) if not user.is_premium else -1,
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            # Audio faylni o'chirish (xotirani tejash)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass

    @app.route('/api/pronunciation/history', methods=['GET'])
    @jwt_required()
    def pronunciation_history():
        """Talaffuz tarixi."""
        user_id = int(get_jwt_identity())
        attempts = PronunciationAttempt.query.filter_by(user_id=user_id)\
            .order_by(PronunciationAttempt.created_at.desc())\
            .limit(50).all()

        return jsonify({
            'attempts': [{
                'id': a.id,
                'phrase': a.phrase_text,
                'recognized': a.recognized_text,
                'score': a.accuracy_score,
                'feedback': a.feedback,
                'language': a.language,
                'created_at': a.created_at.isoformat(),
            } for a in attempts]
        })

    # =========================================
    # LESSON ROUTES
    # =========================================

    @app.route('/api/lessons', methods=['GET'])
    @jwt_required()
    def list_lessons():
        """Darslar ro'yxati."""
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        language = request.args.get('language', user.target_language)
        level = request.args.get('level', user.level)
        topic = request.args.get('topic', None)

        query = Lesson.query.filter_by(language=language, level=level)
        if topic:
            query = query.filter_by(topic=topic)

        lessons = query.order_by(Lesson.order_index).all()

        # User progress bilan birlashtirish
        result = []
        for lesson in lessons:
            progress = UserProgress.query.filter_by(
                user_id=user_id, lesson_id=lesson.id
            ).first()

            data = lesson.to_dict()
            data['progress'] = {
                'completed': progress.completed if progress else False,
                'score': progress.score if progress else 0,
            }
            result.append(data)

        return jsonify({'lessons': result})

    @app.route('/api/lessons/<int:lesson_id>', methods=['GET'])
    @jwt_required()
    def get_lesson(lesson_id):
        """Bitta darsning to'liq ma'lumotlari."""
        lesson = Lesson.query.get_or_404(lesson_id)

        contents = []
        for c in sorted(lesson.contents, key=lambda x: x.order_index):
            try:
                content_data = json.loads(c.content_json)
            except json.JSONDecodeError:
                content_data = {}
            contents.append({
                'id': c.id,
                'type': c.type,
                'order': c.order_index,
                'data': content_data
            })

        return jsonify({
            'lesson': lesson.to_dict(),
            'contents': contents,
        })

    @app.route('/api/lessons/<int:lesson_id>/complete', methods=['POST'])
    @jwt_required()
    def complete_lesson(lesson_id):
        """Darsni tugatish."""
        user_id = int(get_jwt_identity())
        data = request.get_json()
        score = data.get('score', 0)
        time_spent = data.get('time_spent', 0)

        lesson = Lesson.query.get_or_404(lesson_id)

        progress = UserProgress.query.filter_by(
            user_id=user_id, lesson_id=lesson_id
        ).first()

        if not progress:
            progress = UserProgress(user_id=user_id, lesson_id=lesson_id)
            db.session.add(progress)

        progress.completed = True
        progress.score = max(progress.score, score)
        progress.time_spent_seconds = time_spent
        progress.completed_at = datetime.utcnow()
        progress.last_attempt_at = datetime.utcnow()

        db.session.commit()

        # XP qo'shish
        xp_gained = max(20, score)
        add_xp(user_id, xp_gained)

        return jsonify({
            'success': True,
            'xp_gained': xp_gained,
            'total_xp': User.query.get(user_id).xp
        })

    # =========================================
    # PROGRESS & STATS
    # =========================================

    @app.route('/api/progress/dashboard', methods=['GET'])
    @jwt_required()
    def dashboard():
        """Dashboard statistikasi."""
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        usage = get_today_usage(user_id)
        completed_lessons = UserProgress.query.filter_by(user_id=user_id, completed=True).count()
        chat_sessions = ChatSession.query.filter_by(user_id=user_id).count()
        pronunciation_attempts = PronunciationAttempt.query.filter_by(user_id=user_id).count()
        avg_pronunciation = db.session.query(db.func.avg(PronunciationAttempt.accuracy_score))\
            .filter_by(user_id=user_id).scalar() or 0

        achievements = Achievement.query.filter_by(user_id=user_id)\
            .order_by(Achievement.earned_at.desc()).limit(5).all()

        return jsonify({
            'user': user.to_dict(),
            'today': {
                'messages_used': usage.messages_count,
                'pronunciation_used': usage.pronunciation_count,
                'messages_limit': Config.FREE_DAILY_MESSAGES,
                'pronunciation_limit': Config.FREE_DAILY_PRONUNCIATION,
            },
            'stats': {
                'completed_lessons': completed_lessons,
                'chat_sessions': chat_sessions,
                'pronunciation_attempts': pronunciation_attempts,
                'avg_pronunciation_score': round(float(avg_pronunciation), 1),
                'current_streak': user.streak_days,
                'total_xp': user.xp,
                'current_level': user.level,
            },
            'achievements': [{
                'title': a.title,
                'description': a.description,
                'icon': a.icon,
                'earned_at': a.earned_at.isoformat(),
            } for a in achievements],
        })

    # =========================================
    # SCENARIOS
    # =========================================

    @app.route('/api/scenarios', methods=['GET'])
    def list_scenarios():
        """Mavjud chat stsenariylari."""
        return jsonify({
            'scenarios': [
                {'id': 'restaurant', 'name': 'Restoran', 'icon': '🍽️', 'description': 'Ovqat buyurtma qilish'},
                {'id': 'airport', 'name': 'Aeroport', 'icon': '✈️', 'description': 'Ro\'yxatdan o\'tish va savollar'},
                {'id': 'hotel', 'name': 'Mehmахона', 'icon': '🏨', 'description': 'Xona bron qilish'},
                {'id': 'shopping', 'name': 'Xarid', 'icon': '🛍️', 'description': 'Do\'konda narsa so\'rash'},
                {'id': 'job_interview', 'name': 'Ish suhbati', 'icon': '💼', 'description': 'Ishga kirish suhbati'},
                {'id': 'doctor', 'name': 'Shifokor', 'icon': '⚕️', 'description': 'Tibbiy ko\'rik'},
                {'id': 'directions', 'name': 'Yo\'l', 'icon': '🗺️', 'description': 'Yo\'l so\'rash'},
                {'id': 'small_talk', 'name': 'Kundalik suhbat', 'icon': '💬', 'description': 'Salomlashish va gaplashish'},
                {'id': 'business_meeting', 'name': 'Biznes', 'icon': '📊', 'description': 'Biznes uchrashuv'},
                {'id': 'phone_call', 'name': 'Telefon', 'icon': '📞', 'description': 'Telefonda gaplashish'},
            ]
        })

    # =========================================
    # HEALTH
    # =========================================

    @app.route('/health')
    def health():
        return jsonify({
            'status': 'ok',
            'service': 'iSpeak API',
            'groq_configured': bool(Config.GROQ_API_KEY),
        })

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)