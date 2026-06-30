# 🎤 iSpeak — Til o'rganish platformasi (Groq AI bilan)

iSpeak — bu **AI bilan suhbat qilish** va **talaffuzni tekshirish** orqali til o'rganish platformasi. **Groq API** ishlatadi (tez va arzon).

## ✨ Imkoniyatlar

- 🤖 **AI chatbot** — realistik stsenariylarda suhbat (restoran, aeroport, ish suhbati...)
- 🎙️ **Talaffuz tekshirish** — Groq Whisper bilan audio→matn va AI baholash
- 📚 **Interaktiv darslar** — AI yordamida yaratilgan kontent
- 🏆 **Gamification** — XP, level, streak, achievement'lar
- 🌍 **Ko'p tilli** — 11+ til qo'llab-quvvatlanadi
- 💎 **Free/Premium** — kunlik limitlar bilan

## 🚀 O'rnatish

```bash
# 1. Repository'ni clone qilish
git clone https://github.com/KRYZENSYS/recon-platform.git
cd recon-platform/ispeak

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Dependencies
pip install -r requirements.txt

# 4. Environment sozlash
cp .env.example .env
# .env faylga GROQ_API_KEY kiriting

# 5. Ishga tushirish
python app.py
```

Brauzerda: **http://localhost:5000**

## 🔑 Groq API kalit olish

1. 🔗 https://console.groq.com/keys
2. **"Create API Key"** bosing
3. **API key** ni `.env` faylga qo'ying

## 📡 API Endpoints

### Auth
- `POST /api/auth/register` — ro'yxatdan o'tish
- `POST /api/auth/login` — kirish
- `GET /api/auth/me` — joriy user

### Chat (AI)
- `POST /api/chat/start` — yangi sessiya boshlash
- `POST /api/chat/message` — xabar yuborish + AI javob

### Pronunciation
- `GET /api/pronunciation/phrases` — mashq iboralari
- `POST /api/pronunciation/evaluate` — audio baholash
- `GET /api/pronunciation/history` — tarix

### Lessons
- `GET /api/lessons` — darslar ro'yxati
- `GET /api/lessons/<id>` — dars tafsilotlari
- `POST /api/lessons/<id>/complete` — darsni tugatish

### Progress
- `GET /api/progress/dashboard` — dashboard statistikasi

## 🎯 Groq modellari

`config.py`'da o'zgartirish mumkin:
- **Chat:** `llama-3.3-70b-versatile` (yoki `llama-3.1-8b-instant` tezroq)
- **Whisper:** `whisper-large-v3`

## 📦 Deploy

Render.com yoki Railway.app'ga oson deploy qilish mumkin — `render.yaml` va `Procfile` tayyor.

## 📄 Litsenziya

MIT