"""Web spider - async crawler with form detection, link extraction"""
import asyncio
import aiohttp
import re
from urllib.parse import urljoin, urlparse
from typing import Set, List, Dict
from datetime import datetime
from collections import deque


class WebSpider:
    """Async web crawler"""

    def __init__(self, max_pages: int = 100, max_depth: int = 5, concurrency: int = 10):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.concurrency = concurrency
        self.visited: Set[str] = set()
        self.queue: deque = deque()
        self.forms: List[Dict] = []
        self.endpoints: Set[str] = set()
        self.emails: Set[str] = set()
        self.comments: List[str] = []
        self.technologies: Set[str] = set()
        self.external_links: Set[str] = set()

    async def crawl(self, start_url: str) -> Dict:
        """Start crawling"""
        if not start_url.startswith(("http://", "https://")):
            start_url = "https://" + start_url
        base_domain = urlparse(start_url).netloc
        self.queue.append((start_url, 0))
        self.start_time = datetime.utcnow()
        sem = asyncio.Semaphore(self.concurrency)
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            tasks = []
            while self.queue and len(self.visited) < self.max_pages:
                url, depth = self.queue.popleft()
                if url in self.visited or depth > self.max_depth:
                    continue
                self.visited.add(url)
                tasks.append(self._process_url(sem, session, url, depth, base_domain))
                if len(tasks) >= self.concurrency:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks = []
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        return {
            "start_url": start_url, "pages_crawled": len(self.visited),
            "endpoints": sorted(list(self.endpoints))[:500],
            "forms": self.forms, "emails": sorted(list(self.emails)),
            "external_links": sorted(list(self.external_links))[:200],
            "technologies": sorted(list(self.technologies)),
            "duration": (datetime.utcnow() - self.start_time).total_seconds(),
        }

    async def _process_url(self, sem, session, url, depth, base_domain):
        async with sem:
            try:
                async with session.get(url, allow_redirects=True, ssl=False) as resp:
                    content_type = resp.headers.get("Content-Type", "")
                    if "text/html" not in content_type:
                        self.endpoints.add(url)
                        return
                    html = await resp.text()
                    self._analyze(url, html, depth, base_domain)
            except Exception:
                pass

    def _analyze(self, url, html, depth, base_domain):
        # Forms
        forms = re.findall(r"<form[^>]*>(.*?)</form>", html, re.DOTALL | re.IGNORECASE)
        for form in forms:
            action = re.search(r'action=["\']([^"\']*)["\']', form)
            method = re.search(r'method=["\']([^"\']*)["\']', form, re.IGNORECASE)
            inputs = re.findall(r'<input[^>]*>', form, re.IGNORECASE)
            input_details = [{"name": (re.search(r'name=["\']([^"\']*)', i) or [None, None]).group(1) if re.search(r'name=["\']([^"\']*)', i) else None, "type": (re.search(r'type=["\']([^"\']*)', i) or [None, "text"]).group(1) if re.search(r'type=["\']([^"\']*)', i) else "text"} for i in inputs]
            self.forms.append({"url": url, "action": action.group(1) if action else "", "method": (method.group(1) if method else "GET").upper(), "inputs": input_details})
        # Links
        links = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE) + re.findall(r'src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        for link in links:
            if not link or link.startswith(("javascript:", "mailto:", "tel:", "#", "data:")):
                if link.startswith("mailto:"):
                    email = link.replace("mailto:", "").split("?")[0]
                    if "@" in email:
                        self.emails.add(email)
                continue
            absolute = urljoin(url, link)
            parsed = urlparse(absolute)
            if parsed.netloc == base_domain:
                if absolute not in self.visited and depth < self.max_depth:
                    self.queue.append((absolute, depth + 1))
                self.endpoints.add(absolute.split("?")[0].split("#")[0])
            else:
                self.external_links.add(absolute)
        # Emails in body
        self.emails.update(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html))
        # Tech detection
        tech_map = {"wp-content": "WordPress", "drupal": "Drupal", "joomla": "Joomla", "react": "React", "vue.js": "Vue.js", "angular": "Angular", "jquery": "jQuery", "bootstrap": "Bootstrap", "cloudflare": "Cloudflare", "google-analytics": "Google Analytics", "stripe": "Stripe", "_next": "Next.js", "_nuxt": "Nuxt.js"}
        for marker, tech in tech_map.items():
            if marker in html.lower():
                self.technologies.add(tech)


def run(target: str, options: dict = None) -> dict:
    options = options or {}
    spider = WebSpider(max_pages=options.get("max_pages", 100), max_depth=options.get("max_depth", 5), concurrency=options.get("concurrency", 10))
    return asyncio.run(spider.crawl(target))
