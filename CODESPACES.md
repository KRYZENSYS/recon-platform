# 🚀 GitHub Codespaces bilan Deploy

GitHub Codespaces — bu sizning repo'ingizni **to'liq ishga tushiradigan** va **internetga ochadigan** bulutli muhit. **60 soat/oy** bepul!

---

## ⚡ Tezkor boshlash (30 soniya)

### 1-Qadam: Codespace yaratish

1. 🔗 **https://github.com/KRYZENSYS/recon-platform** sahifasiga kiring
2. 🟢 **Yashil "Code" tugmasini** bosing
3. **"Codespaces"** tabini tanlang
4. **"Create codespace on main"** tugmasini bosing

⏳ **Bir necha daqiqa kuting** — konteyner yaratiladi va Python o'rnatiladi.

### 2-Qadam: Ilovani ishga tushirish

Codespace ochilgach, terminalda quyidagilarni yozing:

```bash
python app.py
```

yoki **production mode** uchun:

```bash
gunicorn app:create_app() --bind 0.0.0.0:5000
```

### 3-Qadam: Port'ni ochish

1. **"Ports" tabini** bosing (pastdagi panelda)
2. **5000 portini** toping
3. **"Forward Port"** yoki **"Open in Browser"** qiling

🎉 **Tayyor!** Sizning ilova ishlayapti:
```
https://<codespace-name>-5000.app.github.dev
```

---

## 🎯 Avtomatik Port Forwarding

`.devcontainer/devcontainer.json` fayli **5000 portini avtomatik ochadi** — qo'lda hech narsa qilish shart emas!

---

## 📋 Foydali buyruqlar

```bash
# Virtual environment yaratish (ixtiyoriy)
python -m venv venv
source venv/bin/activate

# Dependencies o'rnatish
pip install -r requirements.txt

# Development mode
python app.py

# Production mode
gunicorn app:create_app() --bind 0.0.0.0:5000 --workers 2

# Ma'lumotlar bazasini tozalash
rm scans.db
```

---

## 💰 Bepul tarif

GitHub Codespaces **shaxsiy hisob** uchun **60 soat/oy** bepul. Bu oyiga ~2 soatlik ishlashga yetadi.

**Pro hisob** uchun **180 soat/oy** bepul.

---

## ⚠️ Muhim eslatmalar

1. **Codespace yopilganda ma'lumotlar saqlanmaydi** — agar kerak bo'lsa:
   ```bash
   git add . && git commit -m "Save progress" && git push
   ```

2. **SQLite fayli** (`scans.db`) **commit qilinmaydi** (`.gitignore`'da bor)

3. **Ports** tab'da **"Visibility: Public"** qiling — tashqi foydalanuvchilar kira olsin

4. **Secrets** — hech qachon tokenlar/parollarni commit qilmang!

---

## 🔧 Muammolarni hal qilish

**Port ko'rinmayaptimi?**
- Ports tab → "Add Port" → 5000

**Ilova ishlamayaptimi?**
- Terminal'da xatolarni ko'ring
- `pip install -r requirements.txt` qayta ishga tushiring

**Sekin ishlayaptimi?**
- 2-core machine type'ga o'ting (Settings → Machine type)

---

## 🎉 Muvaffaqiyatli deploy!

Endi sizning **recon-platform** ilovangiz butun dunyo uchun ochiq! 🌐