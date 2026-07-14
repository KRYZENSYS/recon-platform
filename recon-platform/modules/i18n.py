"""i18n - Internationalization (10+ languages)"""
import os
import json
import logging
from typing import Dict, Optional
from flask import Blueprint, request, session, g
from flask_babel import Babel, _, get_locale

logger = logging.getLogger(__name__)

TRANSLATIONS = {
    "en": {
        "app.name": "Recon Platform",
        "nav.dashboard": "Dashboard",
        "nav.scans": "Scans",
        "nav.lab": "Lab Tools",
        "nav.admin": "Admin",
        "nav.profile": "Profile",
        "auth.login": "Sign In",
        "auth.logout": "Sign Out",
        "auth.register": "Sign Up",
        "auth.username": "Username",
        "auth.password": "Password",
        "auth.email": "Email",
        "auth.forgot_password": "Forgot Password?",
        "scan.new": "New Scan",
        "scan.target": "Target",
        "scan.type": "Scan Type",
        "scan.status": "Status",
        "scan.running": "Running",
        "scan.completed": "Completed",
        "scan.failed": "Failed",
        "scan.start": "Start Scan",
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.delete": "Delete",
        "common.edit": "Edit",
        "common.search": "Search",
        "common.loading": "Loading...",
        "common.no_data": "No data available",
        "common.error": "An error occurred",
        "common.success": "Success",
        "admin.users": "Users",
        "admin.scans": "Scans",
        "admin.settings": "Settings",
        "admin.system": "System",
    },
    "ru": {
        "app.name": "Рекон Платформа",
        "nav.dashboard": "Панель управления",
        "nav.scans": "Сканирования",
        "nav.lab": "Инструменты",
        "nav.admin": "Админ",
        "nav.profile": "Профиль",
        "auth.login": "Войти",
        "auth.logout": "Выйти",
        "auth.register": "Регистрация",
        "auth.username": "Имя пользователя",
        "auth.password": "Пароль",
        "auth.email": "Электронная почта",
        "auth.forgot_password": "Забыли пароль?",
        "scan.new": "Новое сканирование",
        "scan.target": "Цель",
        "scan.type": "Тип сканирования",
        "scan.status": "Статус",
        "scan.running": "Выполняется",
        "scan.completed": "Завершено",
        "scan.failed": "Ошибка",
        "scan.start": "Начать сканирование",
        "common.save": "Сохранить",
        "common.cancel": "Отмена",
        "common.delete": "Удалить",
        "common.edit": "Редактировать",
        "common.search": "Поиск",
        "common.loading": "Загрузка...",
        "common.no_data": "Нет данных",
        "common.error": "Произошла ошибка",
        "common.success": "Успешно",
        "admin.users": "Пользователи",
        "admin.scans": "Сканирования",
        "admin.settings": "Настройки",
        "admin.system": "Система",
    },
    "uz": {
        "app.name": "Recon Platforma",
        "nav.dashboard": "Boshqaruv paneli",
        "nav.scans": "Skanerlashlar",
        "nav.lab": "Laboratoriya",
        "nav.admin": "Admin",
        "nav.profile": "Profil",
        "auth.login": "Kirish",
        "auth.logout": "Chiqish",
        "auth.register": "Ro'yxatdan o'tish",
        "auth.username": "Foydalanuvchi nomi",
        "auth.password": "Parol",
        "auth.email": "Elektron pochta",
        "auth.forgot_password": "Parolni unutdingizmi?",
        "scan.new": "Yangi skanerlash",
        "scan.target": "Maqsad",
        "scan.type": "Skanerlash turi",
        "scan.status": "Holat",
        "scan.running": "Bajarilmoqda",
        "scan.completed": "Tugatildi",
        "scan.failed": "Xatolik",
        "scan.start": "Skanerlashni boshlash",
        "common.save": "Saqlash",
        "common.cancel": "Bekor qilish",
        "common.delete": "O'chirish",
        "common.edit": "Tahrirlash",
        "common.search": "Qidirish",
        "common.loading": "Yuklanmoqda...",
        "common.no_data": "Ma'lumot yo'q",
        "common.error": "Xatolik yuz berdi",
        "common.success": "Muvaffaqiyat",
        "admin.users": "Foydalanuvchilar",
        "admin.scans": "Skanerlashlar",
        "admin.settings": "Sozlamalar",
        "admin.system": "Tizim",
    },
    "es": {
        "app.name": "Plataforma Recon", "nav.dashboard": "Panel", "nav.scans": "Escaneos", "nav.lab": "Herramientas",
        "auth.login": "Iniciar sesión", "auth.logout": "Cerrar sesión", "auth.register": "Registrarse",
        "auth.username": "Usuario", "auth.password": "Contraseña", "auth.email": "Correo",
        "scan.new": "Nuevo escaneo", "scan.target": "Objetivo", "scan.status": "Estado",
        "scan.running": "Ejecutando", "scan.completed": "Completado", "scan.failed": "Falló",
        "common.save": "Guardar", "common.cancel": "Cancelar", "common.delete": "Eliminar", "common.search": "Buscar",
    },
    "fr": {
        "app.name": "Plateforme Recon", "nav.dashboard": "Tableau de bord", "nav.scans": "Analyses", "nav.lab": "Outils",
        "auth.login": "Connexion", "auth.logout": "Déconnexion", "auth.register": "S'inscrire",
        "auth.username": "Nom d'utilisateur", "auth.password": "Mot de passe", "auth.email": "Email",
        "scan.new": "Nouvelle analyse", "scan.target": "Cible", "scan.status": "Statut",
        "scan.running": "En cours", "scan.completed": "Terminé", "scan.failed": "Échec",
        "common.save": "Enregistrer", "common.cancel": "Annuler", "common.delete": "Supprimer", "common.search": "Rechercher",
    },
    "de": {
        "app.name": "Recon-Plattform", "nav.dashboard": "Dashboard", "nav.scans": "Scans", "nav.lab": "Werkzeuge",
        "auth.login": "Anmelden", "auth.logout": "Abmelden", "auth.register": "Registrieren",
        "auth.username": "Benutzername", "auth.password": "Passwort", "auth.email": "E-Mail",
        "scan.new": "Neuer Scan", "scan.target": "Ziel", "scan.status": "Status",
        "scan.running": "Läuft", "scan.completed": "Abgeschlossen", "scan.failed": "Fehlgeschlagen",
        "common.save": "Speichern", "common.cancel": "Abbrechen", "common.delete": "Löschen", "common.search": "Suchen",
    },
    "zh": {
        "app.name": "侦察平台", "nav.dashboard": "仪表板", "nav.scans": "扫描", "nav.lab": "工具",
        "auth.login": "登录", "auth.logout": "退出", "auth.register": "注册",
        "auth.username": "用户名", "auth.password": "密码", "auth.email": "邮箱",
        "scan.new": "新扫描", "scan.target": "目标", "scan.status": "状态",
        "scan.running": "运行中", "scan.completed": "已完成", "scan.failed": "失败",
        "common.save": "保存", "common.cancel": "取消", "common.delete": "删除", "common.search": "搜索",
    },
    "ja": {
        "app.name": "偵察プラットフォーム", "nav.dashboard": "ダッシュボード", "nav.scans": "スキャン", "nav.lab": "ツール",
        "auth.login": "ログイン", "auth.logout": "ログアウト", "auth.register": "登録",
        "auth.username": "ユーザー名", "auth.password": "パスワード", "auth.email": "メール",
        "scan.new": "新規スキャン", "scan.target": "ターゲット", "scan.status": "ステータス",
        "scan.running": "実行中", "scan.completed": "完了", "scan.failed": "失敗",
        "common.save": "保存", "common.cancel": "キャンセル", "common.delete": "削除", "common.search": "検索",
    },
    "ar": {
        "app.name": "منصة الاستطلاع", "nav.dashboard": "لوحة التحكم", "nav.scans": "الفحوصات", "nav.lab": "الأدوات",
        "auth.login": "تسجيل الدخول", "auth.logout": "تسجيل الخروج", "auth.register": "تسجيل",
        "auth.username": "اسم المستخدم", "auth.password": "كلمة المرور", "auth.email": "البريد",
        "scan.new": "فحص جديد", "scan.target": "الهدف", "scan.status": "الحالة",
        "scan.running": "قيد التشغيل", "scan.completed": "مكتمل", "scan.failed": "فشل",
        "common.save": "حفظ", "common.cancel": "إلغاء", "common.delete": "حذف", "common.search": "بحث",
    },
    "tr": {
        "app.name": "Recon Platformu", "nav.dashboard": "Gösterge Paneli", "nav.scans": "Taramalar", "nav.lab": "Araçlar",
        "auth.login": "Giriş Yap", "auth.logout": "Çıkış Yap", "auth.register": "Kayıt Ol",
        "auth.username": "Kullanıcı Adı", "auth.password": "Şifre", "auth.email": "E-posta",
        "scan.new": "Yeni Tarama", "scan.target": "Hedef", "scan.status": "Durum",
        "scan.running": "Çalışıyor", "scan.completed": "Tamamlandı", "scan.failed": "Başarısız",
        "common.save": "Kaydet", "common.cancel": "İptal", "common.delete": "Sil", "common.search": "Ara",
    },
    "pt": {
        "app.name": "Plataforma Recon", "nav.dashboard": "Painel", "nav.scans": "Verificações", "nav.lab": "Ferramentas",
        "auth.login": "Entrar", "auth.logout": "Sair", "auth.register": "Registrar",
        "auth.username": "Usuário", "auth.password": "Senha", "auth.email": "E-mail",
        "scan.new": "Nova verificação", "scan.target": "Alvo", "scan.status": "Status",
        "scan.running": "Em execução", "scan.completed": "Concluído", "scan.failed": "Falhou",
        "common.save": "Salvar", "common.cancel": "Cancelar", "common.delete": "Excluir", "common.search": "Buscar",
    },
}

SUPPORTED_LANGUAGES = list(TRANSLATIONS.keys())


def t(key: str, lang: str = None) -> str:
    """Get translation for key"""
    if not lang:
        lang = session.get("language", "en")
        if hasattr(g, "lang"): lang = g.lang
    translations = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return translations.get(key, TRANSLATIONS["en"].get(key, key))


def set_language(lang: str) -> bool:
    """Set user's language"""
    if lang in SUPPORTED_LANGUAGES:
        session["language"] = lang
        return True
    return False


def get_user_language() -> str:
    """Get current user language"""
    if hasattr(g, "lang"): return g.lang
    return session.get("language", "en")


i18n_bp = Blueprint("i18n", __name__, url_prefix="/api/v1/i18n")


@i18n_bp.route("/languages", methods=["GET"])
def list_languages():
    return jsonify({"supported": SUPPORTED_LANGUAGES, "translations": TRANSLATIONS})


@i18n_bp.route("/set", methods=["POST"])
def set_user_language():
    lang = request.json.get("language", "en")
    if set_language(lang): return jsonify({"language": lang, "success": True})
    return jsonify({"error": "Unsupported language"}), 400


@i18n_bp.route("/translate", methods=["GET"])
def get_translations():
    lang = request.args.get("lang", "en")
    if lang not in TRANSLATIONS: lang = "en"
    return jsonify({"language": lang, "translations": TRANSLATIONS[lang]})
