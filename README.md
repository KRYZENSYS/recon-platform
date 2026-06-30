# 🕷️ Recon Platform

> **Web Reconnaissance Platform** — Burp Suite-ga o'xshash veb-xavfsizlik tekshirish vositasi.

Bu platforma **passive va active reconnaissance** uchun mo'ljallangan bo'lib, quyidagi modullarni o'z ichiga oladi:

- 🕷️ **Spider** — saytning barcha havolalarini yig'ish
- 🌐 **DNS Recon** — domen, subdomain, MX, TXT yozuvlarini aniqlash
- 👤 **User Enumeration** — foydalanuvchi nomlarini aniqlash
- 🔬 **Tech Detection** — ishlatilayotgan texnologiyalarni aniqlash (CMS, server, framework)

---

## ⚠️ Muhim ogohlantirish

> Bu vosita **faqat sizga tegishli yoki ruxsat berilgan resurslarda** qo'llanilishi kerak.
> Boshqa shaxslar yoki tashkilotlarning ruxsatisiz tekshirish o'tkazish **qonunga zid** hisoblanadi.
> Loyiha **ta'lim va authorized penetration testing** maqsadida yaratilgan.

---

## 🏗️ Texnologiyalar

| Qatlam | Texnologiya |
|---|---|
| Backend | Python 3.11+, Flask 3.x |
| Database | SQLite (SQLAlchemy) |
| Frontend | HTML5, Bootstrap 5, Chart.js |
| Recon | requests, BeautifulSoup, dnspython |

---

## 📦 O'rnatish

```bash
# 1. Repository'ni clone qilish
git clone https://github.com/KRYZENSYS/recon-platform.git
cd recon-platform

# 2. Virtual environment yaratish
python3 -m venv venv
source venv/bin/activate      # Linux/Mac
# yoki: venv\Scripts\activate  # Windows

# 3. Kerakli kutubxonalarni o'rnatish
pip install -r requirements.txt

# 4. Serverni ishga tushirish
python app.py
```

Brauzerda oching: **http://127.0.0.1:5000**

---

## 📂 Loyiha strukturasi

```
recon-platform/
├── app.py                  # Flask ilovasi
├── config.py               # Konfiguratsiya
├── models.py               # SQLAlchemy modellari
├── requirements.txt        # Python dependencies
├── modules/
│   ├── __init__.py
│   ├── spider.py           # Web crawler
│   ├── dns_recon.py        # DNS ma'lumotlari
│   ├── user_enum.py        # Foydalanuvchi aniqlash
│   └── tech_detect.py      # Texnologiya aniqlash
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── new_scan.html
│   └── results.html
├── static/
│   ├── css/style.css
│   └── js/main.js
└── scans.db                # SQLite ma'lumotlar bazasi
```

---

## 🚀 Foydalanish

1. **Dashboard** sahifasida **"New Scan"** tugmasini bosing
2. Tekshiriladigan **URL yoki domen** kiriting
3. Kerakli **modullarni** tanlang (Spider, DNS, User Enum, Tech Detection)
4. **"Start Scan"** tugmasini bosing va natijalarni kuting
5. Natijalar real vaqtda ko'rsatiladi

---

## 📜 Litsenziya

MIT License — batafsil ma'lumot uchun [LICENSE](LICENSE) faylini ko'ring.

---

## 👨‍💻 Muallif

**KRYZENSYS** — [github.com/KRYZENSYS](https://github.com/KRYZENSYS)