# 🚀 Deployment Guide

Bu qo'llanma **recon-platform** ilovasini bepul deploy qilishning turli usullarini ko'rsatadi.

---

## ⭐ Variant 1: Render.com (ENG OSON — tavsiya etiladi)

Render.com **bepul tier** bilan Flask ilovalarini qo'llab-quvvatlaydi.

### 1-Qadam: Render.com'ga kirish
1. 🔗 **https://render.com** saytiga kiring
2. **GitHub** orqali ro'yxatdan o'ting
3. **Dashboard** ga o'ting

### 2-Qadam: Yangi Web Service yaratish
1. **"New +"** → **"Web Service"** tugmasini bosing
2. **"Connect GitHub"** — `KRYZENSYS/recon-platform` ni tanlang
3. Sozlamalar:
   - **Name:** `recon-platform`
   - **Region:** Frankfurt (Yevropa uchun tez)
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:create_app() --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`
   - **Instance Type:** Free
4. **"Create Web Service"** tugmasini bosing

### 3-Qadam: Kutish ⏳
- **5-10 daqiqa** kuting — birinchi build tugaguncha
- Log'larni kuzatib turing
- ✅ **Deploy successful** ko'ringach, **URL** olasiz:

```
https://recon-platform.onrender.com
```

🎉 **Tayyor!** Saytingiz ishlayapti.

---

## 🔵 Variant 2: Railway.app

1. 🔗 https://railway.app ga kiring
2. **"Login with GitHub"** qiling
3. **"New Project"** → **"Deploy from GitHub repo"**
4. `KRYZENSYS/recon-platform` ni tanlang
5. Railway avtomatik aniqlaydi va deploy qiladi
6. **Variables** bo'limiga `PORT=5000` qo'shing

---

## 🟣 Variant 3: PythonAnywhere (faqat Python uchun)

1. 🔗 https://www.pythonanywhere.com ga kiring
2. **Beginner Account** yarating (bepul)
3. **Web** → **Add a new web app**
4. **Manual configuration** → **Python 3.11**
5. Quyidagilarni kiriting:
   - **Source code:** `/home/USERNAME/recon-platform`
   - **WSGI file:** `/var/www/USERNAME_pythonanywhere_com_wsgi.py`
6. **Bash console** oching va:
   ```bash
   git clone https://github.com/KRYZENSYS/recon-platform.git
   cd recon-platform
   mkvirtualenv --python=/usr/bin/python3.11 recon
   pip install -r requirements.txt
   ```
7. WSGI faylga quyidagilarni yozing:
   ```python
   import sys
   path = '/home/USERNAME/recon-platform'
   if path not in sys.path:
       sys.path.insert(0, path)
   from app import create_app
   application = create_app()
   ```
8. **Reload** tugmasini bosing

---

## 🐳 Variant 4: Docker (o'z serveringizda)

```bash
# Image yaratish
docker build -t recon-platform .

# Konteyner ishga tushirish
docker run -d \
  -p 5000:5000 \
  -v recon_data:/app/data \
  --name recon \
  recon-platform
```

Brauzerda oching: **http://localhost:5000**

---

## ⚙️ GitHub Actions bilan avtomatik deploy

GitHub'ga har bir push qilganingizda Render avtomatik deploy qilishi uchun:

1. **Render Dashboard** → **recon-platform** → **Settings**
2. **"Deploy Hook"** ni nusxa oling
3. **GitHub** → **recon-platform** → **Settings** → **Secrets and variables** → **Actions**
4. **New repository secret:**
   - **Name:** `RENDER_DEPLOY_HOOK`
   - **Value:** (Render'dan olgan URL)
5. **Save**

Endi har safar `main` branch'ga push qilganingizda avtomatik deploy bo'ladi! 🚀

---

## ⚠️ Muhim eslatmalar

1. **Free tier** da ilova **15 daqiqa davomatsiz bo'lsa uxlab qoladi** (Render)
   - Birinchi tashrif sekin bo'lishi mumkin (cold start ~30s)

2. **SQLite** oddiy holatlar uchun yetarli, lekin ko'p ma'lumot uchun **PostgreSQL** tavsiya etiladi

3. **Background scans** — `threading` ishlatadi, lekin production'da **Celery + Redis** ko'proq mos keladi

4. **Xavfsizlik** — production'da:
   - `SECRET_KEY` ni environment variable'ga o'tkazing
   - HTTPS yoqing (Render avtomatik qiladi)
   - Rate limiting qo'shing

---

## 🆘 Muammolar

**Build xatosi?**
- `requirements.txt` da versiyalar mos kelishi kerak
- Log'larda batafsil ma'lumot bo'ladi

**Port xatosi?**
- `$PORT` environment variable'ni ishlating (Render avtomatik beradi)

**Database yo'qoldimi?**
- Render'da doimiy disk yo'q — har deploy'da o'chiriladi
- **Disk qo'shing:** Settings → Disks → Add Disk (Free tier'da bepul)

---

**Muvaffaqiyatli deploy!** 🎉