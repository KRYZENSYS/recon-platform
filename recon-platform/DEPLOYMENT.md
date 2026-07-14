# 🛡️ Recon Platform v2.0 - Production Deployment Guide

## 📋 Pre-requirements

- Linux server (Ubuntu 22.04+ recommended)
- Docker & Docker Compose
- Domain with DNS A record pointing to server
- 2GB+ RAM, 20GB+ disk

## 🚀 Quick Deploy

```bash
# 1. Clone
git clone https://github.com/KRYZENSYS/recon-platform.git
cd recon-platform

# 2. Configure
cp .env.example .env
nano .env  # Edit secrets

# 3. Deploy
docker-compose -f docker-compose.production.yml up -d

# 4. Check
docker-compose ps
curl https://yourdomain.com/api/v1/health
```

## 🔐 SSL Setup with Let's Encrypt

```bash
# Install certbot
apt install -y certbot

# Generate cert
certbot certonly --standalone -d yourdomain.com

# Copy to nginx
mkdir -p ssl
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem

# Restart
docker-compose -f docker-compose.production.yml restart nginx
```

## 📊 Monitoring

- **Grafana:** http://yourdomain.com:3000 (admin/your-grafana-password)
- **Prometheus:** http://yourdomain.com:9090
- **Flower (Celery):** http://yourdomain.com:5555

## 🔄 Updates

```bash
git pull
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

## 💾 Backup

```bash
# Automated daily backup
cat > /etc/cron.daily/recon-backup << 'EOF'
#!/bin/bash
docker exec recon-db pg_dump -U recon recon | gzip > /backups/recon_$(date +\%Y\%m\%d).sql.gz
find /backups -mtime +30 -delete
EOF
chmod +x /etc/cron.daily/recon-backup
```

## 🐛 Troubleshooting

```bash
# View logs
docker-compose -f docker-compose.production.yml logs -f api
docker-compose -f docker-compose.production.yml logs -f worker

# Reset database
docker-compose down -v
docker-compose up -d

# Scale workers
docker-compose up -d --scale worker=4
```

## 🔧 Custom Configuration

Edit `.env` and restart:
```bash
docker-compose -f docker-compose.production.yml restart
```

## 📈 Performance Tuning

- **Workers:** Increase `concurrency` in worker command
- **DB:** Tune `SQLALCHEMY_ENGINE_OPTIONS` in `config.py`
- **Redis:** Increase `maxmemory` in docker-compose
- **Nginx:** Adjust `worker_processes` in `nginx.conf`

## 🆘 Support

- Issues: https://github.com/KRYZENSYS/recon-platform/issues
- Email: support@recon.kryzensys.com
- Docs: https://docs.recon.kryzensys.com
