"""🔬 Tech Detection moduli — sayt ishlatayotgan texnologiyalarni aniqlash."""
import re

import requests


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Recon Platform; Security Testing)'
}


TECH_SIGNATURES = {
    'Web Server': {
        'nginx': ['nginx', 'Server: nginx'],
        'Apache': ['Apache', 'Server: Apache'],
        'IIS': ['IIS', 'Microsoft-IIS'],
        'Cloudflare': ['cloudflare', 'cf-ray'],
        'LiteSpeed': ['LiteSpeed'],
        'Caddy': ['Caddy'],
    },
    'Programming Language': {
        'PHP': ['X-Powered-By: PHP', '.php'],
        'Python': ['X-Powered-By: Python', 'Werkzeug'],
        'Node.js': ['X-Powered-By: Express', 'node.js'],
        'Ruby': ['X-Powered-By: Phusion', 'Ruby'],
        'Java': ['JSESSIONID', 'X-Powered-By: JSP'],
    },
    'CMS': {
        'WordPress': ['wp-content', 'wp-includes', '/wp-json/'],
        'Joomla': ['Joomla', '/media/jui/'],
        'Drupal': ['Drupal', 'sites/default/files'],
        'Magento': ['Magento', 'mage/'],
        'Shopify': ['Shopify', 'shopify'],
        'Blogger': ['blogspot.com'],
    },
    'JavaScript Framework': {
        'React': ['react', '__react', 'data-reactroot'],
        'Vue.js': ['vue', '__vue', 'data-v-'],
        'Angular': ['ng-version', 'angular'],
        'jQuery': ['jquery', 'jQuery'],
        'Next.js': ['__NEXT_DATA__', '_next/'],
        'Nuxt.js': ['__NUXT__', '_nuxt/'],
    },
    'Analytics': {
        'Google Analytics': ['google-analytics.com', 'ga.js', 'gtag'],
        'Yandex.Metrica': ['mc.yandex.ru', 'Ya.Metrika'],
        'Facebook Pixel': ['connect.facebook.net'],
    },
    'CDN': {
        'Cloudflare': ['cf-ray', '__cfduid'],
        'Akamai': ['akamai', 'akamaiedge'],
        'Fastly': ['fastly'],
        'AWS CloudFront': ['cloudfront'],
    },
}


def detect(url):
    """Berilgan URL uchun texnologiyalarni aniqlash."""
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    results = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True, verify=False)

        # Header va HTML kontentini birlashtirish
        headers_text = '\n'.join([f'{k}: {v}' for k, v in resp.headers.items()])
        full_content = headers_text + '\n' + resp.text

        for category, techs in TECH_SIGNATURES.items():
            for tech_name, signatures in techs.items():
                confidence = 0
                for sig in signatures:
                    if sig.lower() in full_content.lower():
                        confidence += 50

                if confidence > 0:
                    results.append({
                        'category': category,
                        'name': tech_name,
                        'version': None,
                        'confidence': min(confidence, 100),
                    })

    except Exception as e:
        results.append({
            'category': 'Error',
            'name': f'Failed to detect: {str(e)[:64]}',
            'version': None,
            'confidence': 0,
        })

    return results