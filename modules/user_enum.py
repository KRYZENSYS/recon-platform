"""👤 User Enumeration moduli — foydalanuvchi nomlarini aniqlash."""
import re

import requests


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Recon Platform; Security Testing)'
}


def extract_username(target):
    """URL yoki domaindan username/identifikator ajratib olish."""
    if 'github.com/' in target:
        match = re.search(r'github\.com/([\w\-]+)', target)
        if match:
            return match.group(1)
    if 'twitter.com/' in target or 'x.com/' in target:
        match = re.search(r'(?:twitter|x)\.com/([\w\-]+)', target)
        if match:
            return match.group(1)
    if 'instagram.com/' in target:
        match = re.search(r'instagram\.com/([\w\-.]+)', target)
        if match:
            return match.group(1)

    # Faqat domen bo'lsa — name ajratib olish
    domain = target.replace('http://', '').replace('https://', '').split('/')[0]
    parts = domain.split('.')
    if len(parts) >= 2:
        return parts[-2]
    return domain


def check_github(username):
    """GitHub'da foydalanuvchi bor-yo'qligini tekshirish."""
    try:
        resp = requests.get(
            f'https://api.github.com/users/{username}',
            headers=HEADERS,
            timeout=8
        )
        return resp.status_code == 200, resp.status_code, f'https://github.com/{username}'
    except Exception:
        return False, None, f'https://github.com/{username}'


def check_twitter(username):
    """Twitter'da foydalanuvchi bor-yo'qligini tekshirish."""
    try:
        resp = requests.get(
            f'https://x.com/{username}',
            headers=HEADERS,
            timeout=8,
            allow_redirects=True
        )
        # Twitter sahifa mavjud bo'lsa, HTML'da "This account doesn't exist" bo'lmaydi
        exists = resp.status_code == 200 and "doesn't exist" not in resp.text.lower()
        return exists, resp.status_code, f'https://x.com/{username}'
    except Exception:
        return False, None, f'https://x.com/{username}'


def check_instagram(username):
    """Instagram'da foydalanuvchi bor-yo'qligini tekshirish."""
    try:
        resp = requests.get(
            f'https://www.instagram.com/{username}/',
            headers=HEADERS,
            timeout=8,
            allow_redirects=True
        )
        exists = resp.status_code == 200 and 'Sorry, this page' not in resp.text
        return exists, resp.status_code, f'https://instagram.com/{username}'
    except Exception:
        return False, None, f'https://instagram.com/{username}'


def check_gravatar(email_or_hash):
    """Gravatar'da profil bor-yo'qligini tekshirish."""
    try:
        resp = requests.get(
            f'https://www.gravatar.com/avatar/{email_or_hash}?d=404',
            headers=HEADERS,
            timeout=8
        )
        exists = resp.status_code == 200
        return exists, resp.status_code, f'https://www.gravatar.com/{email_or_hash}'
    except Exception:
        return False, None, f'https://www.gravatar.com/{email_or_hash}'


def enumerate(target):
    """Berilgan target uchun foydalanuvchini turli platformalarda qidirish."""
    username = extract_username(target)
    results = []

    checks = [
        ('GitHub', check_github),
        ('Twitter', check_twitter),
        ('Instagram', check_instagram),
    ]

    for platform, func in checks:
        try:
            found, status, url = func(username)
            results.append({
                'username': username,
                'platform': platform,
                'url': url,
                'found': found,
                'status_code': status,
            })
        except Exception:
            results.append({
                'username': username,
                'platform': platform,
                'url': '',
                'found': False,
                'status_code': None,
            })

    return results