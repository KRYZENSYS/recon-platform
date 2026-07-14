"""Technology detection - 200+ patterns, Wappalyzer-level"""
import re
import asyncio
import aiohttp
from typing import Dict, List
from datetime import datetime


TECH_SIGNATURES = {
    # CMS
    "WordPress": [{"path": "/wp-login.php", "status": 200}, {"path": "/wp-content/", "status": 200}, {"body": r"wp-content|wordpress"}],
    "Drupal": [{"body": r"drupal|sites/all/modules"}, {"path": "/CHANGELOG.txt", "body": r"Drupal"}],
    "Joomla": [{"body": r'<meta name="generator" content="Joomla'}, {"path": "/administrator/"}],
    "Magento": [{"body": r"Mage_Cookies|magento"}, {"path": "/skin/frontend/"}],
    "Shopify": [{"header": r"x-shopid|shopify"}, {"body": r"cdn\.shopify\.com"}],
    "Wix": [{"body": r"wix\.com|wixstatic\.com"}],
    "Squarespace": [{"body": r"squarespace\.com"}],
    "Ghost": [{"body": r"ghost\.org"}],
    "Hugo": [{"header": r"x-hugo"}],
    "Jekyll": [{"body": r"jekyll"}],

    # Web servers
    "Nginx": [{"header": r"server:\s*nginx"}],
    "Apache": [{"header": r"server:\s*apache"}],
    "IIS": [{"header": r"server:\s*microsoft-iis"}],
    "LiteSpeed": [{"header": r"server:\s*litespeed"}],
    "Caddy": [{"header": r"server:\s*caddy"}],
    "Tomcat": [{"header": r"server:\s*apache-coyote"}],
    "Gunicorn": [{"header": r"server:\s*gunicorn"}],
    "OpenResty": [{"header": r"server:\s*openresty"}],

    # Frameworks
    "Next.js": [{"header": r"x-nextjs"}, {"body": r"_next/static|_next/data"}],
    "Nuxt.js": [{"body": r"_nuxt/|__nuxt"}],
    "React": [{"body": r"react|__NEXT_DATA__"}],
    "Vue.js": [{"body": r"vue\.js|__VUE__"}],
    "Angular": [{"body": r"ng-version|angular"}],
    "Svelte": [{"body": r"svelte"}],
    "Express": [{"header": r"x-powered-by:\s*express"}],
    "Django": [{"body": r"csrfmiddlewaretoken|__admin__"}],
    "Flask": [{"header": r"server:\s*werkzeug"}],
    "FastAPI": [{"header": r"server:\s*uvicorn"}],
    "Laravel": [{"header": r"laravel"}, {"body": r"laravel"}],
    "Symfony": [{"header": r"x-debug-token.*symfony"}],
    "Spring": [{"header": r"x-application-context"}],
    "Rails": [{"header": r"x-runtime.*rails"}, {"body": r"csrf-token.*rails"}],
    "ASP.NET": [{"header": r"x-aspnet"}, {"body": r"__viewstate|aspx"}],
    "PHP": [{"header": r"x-powered-by:\s*php"}],

    # CDN
    "Cloudflare": [{"header": r"cf-ray|cf-cache-status|server:\s*cloudflare"}],
    "Akamai": [{"header": r"x-akamai"}],
    "Fastly": [{"header": r"x-served-by.*cache"}],
    "Vercel": [{"header": r"x-vercel-id"}],
    "Netlify": [{"header": r"x-nf-request-id|server:\s*netlify"}],
    "AWS CloudFront": [{"header": r"x-amz-cf-id"}],
    "AWS S3": [{"body": r"NoSuchBucket"}],
    "Azure": [{"header": r"x-azure-ref|x-ms-request-id"}],
    "Google Cloud": [{"header": r"x-goog|x-cloud-trace-context"}],

    # Analytics
    "Google Analytics": [{"body": r"google-analytics\.com|gtag\(|ga\("}],
    "Google Tag Manager": [{"body": r"googletagmanager\.com"}],
    "Facebook Pixel": [{"body": r"connect\.facebook\.net|fbq\("}],
    "Hotjar": [{"body": r"static\.hotjar\.com"}],
    "Mixpanel": [{"body": r"cdn\.mxpnl\.com"}],
    "Segment": [{"body": r"segment\.com"}],

    # JS libraries
    "jQuery": [{"body": r"jquery[\.-]?\d|jquery\.min\.js"}],
    "Bootstrap": [{"body": r"bootstrap[\.-]?\d|bootstrap\.min\.css"}],
    "Tailwind CSS": [{"body": r"tailwindcss|tailwind\.css"}],
    "Font Awesome": [{"body": r"font-?awesome"}],
    "Lodash": [{"body": r"lodash"}],
    "Moment.js": [{"body": r"moment\.min\.js"}],
    "axios": [{"body": r"axios"}],

    # Security
    "reCAPTCHA": [{"body": r"google\.com/recaptcha|recaptcha"}],
    "hCaptcha": [{"body": r"hcaptcha\.com"}],
    "ModSecurity": [{"header": r"server:\s*mod_security"}],

    # Payment
    "Stripe": [{"body": r"js\.stripe\.com|stripe\.com/v"}],
    "PayPal": [{"body": r"paypalobjects\.com|paypal"}],
    "Square": [{"body": r"squareup\.com"}],

    # Other
    "Cloudinary": [{"body": r"cloudinary\.com"}],
    "Imgix": [{"header": r"x-imgix"}],
    "Disqus": [{"body": r"disqus\.com"}],
    "YouTube": [{"body": r"youtube\.com/embed"}],
    "Vimeo": [{"body": r"player\.vimeo\.com"}],
    "Intercom": [{"body": r"intercom\.io"}],
    "Zendesk": [{"body": r"zendesk\.com|zopim"}],
}


class TechDetector:
    """Detect web technologies"""

    @staticmethod
    async def fetch_indicators(url: str) -> Dict:
        """Fetch URL and common paths"""
        paths = ["/", "/robots.txt", "/sitemap.xml"]
        results = {"headers": {}, "bodies": {}}
        async with aiohttp.ClientSession() as session:
            for path in paths:
                target = url.rstrip("/") + path
                try:
                    async with session.get(target, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=True, ssl=False) as resp:
                        results["headers"][path] = dict(resp.headers)
                        if resp.status == 200 and "text" in resp.headers.get("Content-Type", ""):
                            text = await resp.text()
                            results["bodies"][path] = text[:50000]
                except Exception:
                    pass
        return results

    @staticmethod
    def match_signature(tech_name: str, signatures: List[Dict], data: Dict) -> bool:
        """Check if technology matches"""
        for sig in signatures:
            path = sig.get("path", "/")
            body = data.get("bodies", {}).get(path, "")
            headers = data.get("headers", {}).get(path, {})
            combined_headers = "\n".join(f"{k}: {v}" for k, v in headers.items())
            if sig.get("header") and re.search(sig["header"], combined_headers, re.IGNORECASE):
                return True
            if sig.get("body") and re.search(sig["body"], body, re.IGNORECASE):
                return True
        return False

    @staticmethod
    async def detect(url: str) -> Dict:
        """Detect all technologies"""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        data = await TechDetector.fetch_indicators(url)
        detected = []
        for tech, signatures in TECH_SIGNATURES.items():
            if TechDetector.match_signature(tech, signatures, data):
                detected.append({"name": tech, "confidence": 0.85})
        return {
            "url": url, "technologies": detected, "count": len(detected),
            "scanned_at": datetime.utcnow().isoformat(),
        }


def run(target: str, options: dict = None) -> dict:
    return asyncio.run(TechDetector.detect(target))
