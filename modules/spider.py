"""🕷️ Spider moduli — web sahifalarni krawling qilish."""
from urllib.parse import urljoin, urlparse
from collections import deque

import requests
from bs4 import BeautifulSoup

from config import Config


HEADERS = {'User-Agent': Config.USER_AGENT}


def normalize_url(url):
    """URL'ga http:// prefiksi qo'shish."""
    if not url.startswith(('http://', 'https://')):
        return 'http://' + url
    return url


def is_same_domain(url, base):
    """URL boshqa domenmi yoki yo'qligini tekshirish."""
    p1 = urlparse(url)
    p2 = urlparse(base)
    return p1.netloc == p2.netloc


def crawl(start_url, max_pages=None, max_depth=None):
    """Berilgan URL'dan boshlab havolalarni yig'ish."""
    max_pages = max_pages or Config.MAX_PAGES
    max_depth = max_depth or Config.MAX_DEPTH

    start_url = normalize_url(start_url)
    visited = set()
    queue = deque([(start_url, 0)])
    results = []

    while queue and len(results) < max_pages:
        url, depth = queue.popleft()

        if url in visited or depth > max_depth:
            continue

        visited.add(url)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=Config.REQUEST_TIMEOUT, allow_redirects=True)

            result = {
                'url': url,
                'depth': depth,
                'status': resp.status_code,
                'content_type': resp.headers.get('Content-Type', '')[:128],
                'title': None,
            }

            # Sahifa sarlavhasini olish
            if 'text/html' in result['content_type']:
                try:
                    soup = BeautifulSoup(resp.text, 'lxml')
                    title_tag = soup.find('title')
                    if title_tag:
                        result['title'] = title_tag.get_text(strip=True)[:512]

                    # Yangi havolalarni topish
                    if depth < max_depth:
                        for link in soup.find_all('a', href=True):
                            absolute = urljoin(url, link['href'])
                            absolute = absolute.split('#')[0].split('?')[0]
                            if absolute and is_same_domain(absolute, start_url) and absolute not in visited:
                                queue.append((absolute, depth + 1))
                except Exception:
                    pass

            results.append(result)

        except requests.exceptions.RequestException:
            results.append({
                'url': url,
                'depth': depth,
                'status': None,
                'content_type': None,
                'title': None,
            })

    return results