# 🔐 ADMIN CREDENTIALS - SAQLANG!

```
╔══════════════════════════════════════════════════════════════╗
║                   KRYZENSYS ADMIN ACCESS                     ║
╠══════════════════════════════════════════════════════════════╣
║  Username:   admin                                           ║
║  Email:      admin@recon.kryzensys.com                       ║
║  Password:   KrysAdmin#2026!Secure#X9qP                      ║
║  Role:       superadmin                                      ║
║  Plan:       enterprise (10 years, unlimited)                ║
║  User ID:    1                                               ║
╚══════════════════════════════════════════════════════════════╝
```

## 🌐 Login URLs:

| Method | URL | Credentials |
|--------|-----|-------------|
| **Web UI** | `https://yourdomain.com/admin/login` | `admin` / `KrysAdmin#2026!Secure#X9qP` |
| **API** | `POST https://yourdomain.com/api/v1/auth/login` | JSON: `{"username":"admin","password":"KrysAdmin#2026!Secure#X9qP"}` |
| **cURL** | `curl -X POST https://yourdomain.com/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"KrysAdmin#2026!Secure#X9qP"}'` | — |

## 🔑 Admin Capabilities:

✅ Full dashboard access (`/admin/dashboard/stats`)
✅ User management (create, ban, delete, reset password)
✅ Scan management (view all, cancel, delete)
✅ Settings control (all platform settings)
✅ Activity logs viewer
✅ System health monitor
✅ Cache management
✅ Maintenance mode toggle
✅ Broadcast notifications to users
✅ Organization management
✅ Analytics & top targets
✅ All 102 lab functions

## 🔄 Password Reset:

```bash
# SSH into server
ssh root@yourdomain.com
cd /opt/recon-platform
docker-compose exec api python create_admin.py admin newPasswordHere admin@recon.kryzensys.com
```

## 🛡️ Security Notes:

- **2FA:** Enable immediately after first login
- **IP Whitelist:** Configure in admin settings
- **Backup Codes:** Generate and store safely
- **Session Timeout:** 12 hours (configurable)
- **Password Rotation:** Every 90 days recommended
- **File Storage:** Credentials file has 0600 permissions

## 📞 Recovery:

If you lose access:
1. SSH to server
2. Run: `docker-compose exec api python create_admin.py`
3. Follow interactive prompts
4. New credentials will be generated
