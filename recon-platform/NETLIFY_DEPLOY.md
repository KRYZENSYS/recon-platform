# Netlify Deployment Guide - KRYZENSYS Recon Platform

## 🚀 Quick Deploy

### 1. Frontend Only Deploy (Tavsiya etiladi)

```toml
# netlify.toml (allaqachon mavjud)
[build]
  base = "recon-platform/frontend"
  publish = "."
  command = "echo 'Static frontend - ready'"
```

### 2. Netlify Dashboard sozlamalari

**Site settings → Build & deploy → Environment:**

| Variable | Value |
|----------|-------|
| `NODE_VERSION` | `20.11.0` |
| `PYTHON_VERSION` | `3.11` (faqat agar Python kerak bo'lsa) |
| `MISE_PYTHON_COMPILE` | `false` |
| `MISE_PYTHON_PRECOMPILED` | `true` |

### 3. Build settings (Netlify UI)

```
Base directory:    recon-platform/frontend
Build command:     echo "Static site - no build needed"
Publish directory: . (Base directory ichidagi)
```

## 🔧 Xatolarni tuzatish

### ❌ "python-build: definition not found: python-3.11.9"

**Sabab:** `mise` Python 3.11.9 ni topa olmayapti (eskirgan definition).

**Yechim:** `netlify.toml` ga qo'ying:

```toml
[build.environment]
  PYTHON_VERSION = "3.11"
  MISE_PYTHON_COMPILE = "false"
  MISE_PYTHON_PRECOMPILED = "true"
```

### ❌ "Failed to fetch cache"

**Yechim:** Cache tozalash:
1. Netlify Dashboard → Site settings → Build & deploy
2. "Clear cache" tugmasini bosing
3. Yangi deploy qiling

### ❌ "Python not found"

**Yechim:** Agar faqat frontend deploy qilayotgan bo'lsangiz, Python umuman kerak emas:
```toml
[build]
  command = "echo 'Static frontend - no build needed'"
```

## 📁 Struktura

```
recon-platform/
├── frontend/              # Netlify uchun (publish directory)
│   ├── index.html         # Asosiy sahifa
│   ├── admin/             # Admin panel
│   │   └── index.html
│   ├── pwa/               # PWA fayllar
│   │   ├── manifest.json
│   │   └── sw.js
│   ├── theme.js
│   ├── app.js
│   └── ...
├── api/                   # Backend (Netlify Functions yoki alohida server)
├── modules/               # Python modullar
└── netlify.toml           # Netlify konfiguratsiya
```

## 🌐 Custom Domain

1. Netlify Dashboard → Domain settings
2. "Add custom domain" → `recon.kryzensys.com`
3. DNS sozlang (CNAME yoki A record)
4. SSL avtomatik o'rnatiladi (Let's Encrypt)

## 🔐 Environment Variables

Netlify Dashboard → Site settings → Environment variables:

```
ADMIN_EMAIL=f91186645@gmail.com
ADMIN_GITHUB=https://github.com/KRYZENSYS/
ADMIN_TELEGRAM=https://t.me/FirdavsVIP
API_BASE_URL=https://recon-api.kryzensys.com
WS_URL=wss://recon-api.kryzensys.com
```

## 📞 Support

- 📧 f91186645@gmail.com
- 💻 https://github.com/KRYZENSYS/
- 📱 https://t.me/FirdavsVIP
