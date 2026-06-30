"""Recon Platform — Flask ilovasi."""
import threading
import time
from datetime import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for

from config import Config
from models import db, Scan, SpiderResult, DNSResult, UserEnumResult, TechResult


def create_app():
    """Flask ilovasini yaratish."""
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # Modullarni import qilish (app yaratilgandan keyin)
    from modules import spider, dns_recon, user_enum, tech_detect

    @app.route('/')
    def dashboard():
        """Asosiy dashboard sahifasi."""
        scans = Scan.query.order_by(Scan.created_at.desc()).limit(20).all()
        stats = {
            'total': Scan.query.count(),
            'running': Scan.query.filter_by(status='running').count(),
            'completed': Scan.query.filter_by(status='completed').count(),
            'failed': Scan.query.filter_by(status='failed').count(),
        }
        return render_template('dashboard.html', scans=scans, stats=stats)

    @app.route('/scan/new', methods=['GET', 'POST'])
    def new_scan():
        """Yangi scan yaratish."""
        if request.method == 'POST':
            target = request.form.get('target', '').strip()
            modules = request.form.getlist('modules')

            if not target:
                return render_template('new_scan.html', error='Target kiriting')

            if not modules:
                return render_template('new_scan.html', error='Kamida bitta modul tanlang')

            scan = Scan(
                target=target,
                modules=','.join(modules),
                status='pending'
            )
            db.session.add(scan)
            db.session.commit()

            # Background thread'da ishga tushirish
            thread = threading.Thread(target=run_scan, args=(app, scan.id))
            thread.daemon = True
            thread.start()

            return redirect(url_for('view_scan', scan_id=scan.id))

        return render_template('new_scan.html')

    @app.route('/scan/<int:scan_id>')
    def view_scan(scan_id):
        """Scan natijalarini ko'rish."""
        scan = Scan.query.get_or_404(scan_id)
        return render_template('results.html', scan=scan)

    @app.route('/api/scan/<int:scan_id>/status')
    def api_scan_status(scan_id):
        """Scan holatini JSON qaytarish."""
        scan = Scan.query.get_or_404(scan_id)
        return jsonify(scan.to_dict())

    @app.route('/api/scan/<int:scan_id>/delete', methods=['POST'])
    def api_scan_delete(scan_id):
        """Scan'ni o'chirish."""
        scan = Scan.query.get_or_404(scan_id)
        db.session.delete(scan)
        db.session.commit()
        return jsonify({'success': True})

    @app.route('/api/scan/<int:scan_id>/results')
    def api_scan_results(scan_id):
        """Barcha natijalarni JSON ko'rinishida qaytarish."""
        scan = Scan.query.get_or_404(scan_id)
        return jsonify({
            'scan': scan.to_dict(),
            'spider': [
                {'url': r.url, 'depth': r.depth, 'status': r.status_code,
                 'type': r.content_type, 'title': r.title}
                for r in scan.spider_results
            ],
            'dns': [
                {'type': r.record_type, 'host': r.host, 'value': r.value, 'ttl': r.ttl}
                for r in scan.dns_results
            ],
            'users': [
                {'username': r.username, 'platform': r.platform,
                 'url': r.url, 'found': r.found, 'status': r.status_code}
                for r in scan.user_enum_results
            ],
            'tech': [
                {'category': r.category, 'name': r.name, 'version': r.version,
                 'confidence': r.confidence}
                for r in scan.tech_results
            ],
        })

    @app.route('/health')
    def health():
        """Sog'liq tekshiruvi."""
        return jsonify({'status': 'ok'})

    return app


def run_scan(app, scan_id):
    """Background thread'da scan'ni ishga tushirish."""
    from modules import spider, dns_recon, user_enum, tech_detect

    with app.app_context():
        scan = Scan.query.get(scan_id)
        if not scan:
            return

        start_time = time.time()
        scan.status = 'running'
        db.session.commit()

        modules = scan.modules.split(',')
        target = scan.target

        try:
            if 'spider' in modules:
                results = spider.crawl(target)
                for r in results:
                    db.session.add(SpiderResult(
                        scan_id=scan.id, url=r['url'], depth=r['depth'],
                        status_code=r.get('status'), content_type=r.get('content_type'),
                        title=r.get('title')
                    ))

            if 'dns' in modules:
                domain = target.replace('http://', '').replace('https://', '').split('/')[0]
                results = dns_recon.recon(domain)
                for r in results:
                    db.session.add(DNSResult(
                        scan_id=scan.id, record_type=r['type'], host=r['host'],
                        value=r['value'], ttl=r.get('ttl')
                    ))

            if 'user_enum' in modules:
                results = user_enum.enumerate(target)
                for r in results:
                    db.session.add(UserEnumResult(
                        scan_id=scan.id, username=r['username'], platform=r['platform'],
                        url=r['url'], found=r['found'], status_code=r.get('status_code')
                    ))

            if 'tech_detect' in modules:
                results = tech_detect.detect(target)
                for r in results:
                    db.session.add(TechResult(
                        scan_id=scan.id, category=r['category'], name=r['name'],
                        version=r.get('version'), confidence=r.get('confidence', 100)
                    ))

            db.session.commit()
            scan.status = 'completed'

        except Exception as e:
            db.session.rollback()
            scan.status = 'failed'
            print(f'[ERROR] Scan {scan_id}: {e}')

        finally:
            scan.finished_at = datetime.utcnow()
            scan.duration = time.time() - start_time
            db.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)