"""Shodan & Censys full integration"""
import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import requests
import redis
from models import db, Scan, Finding, ScanType

logger = logging.getLogger(__name__)
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


class ShodanIntegration:
    """Shodan API integration - full version"""
    BASE_URL = "https://api.shodan.io"
    CACHE_TTL = 86400  # 24h

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SHODAN_API_KEY", "")
        if not self.api_key:
            logger.warning("Shodan API key not set - functionality limited")

    def _cache_key(self, key: str) -> str: return f"shodan:{key}"

    def _request(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        if not self.api_key: return None
        cache_key = self._cache_key(f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}")
        cached = redis_client.get(cache_key)
        if cached: return json.loads(cached)
        try:
            params = params or {}
            params["key"] = self.api_key
            res = requests.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=30)
            if res.status_code == 200:
                data = res.json()
                redis_client.setex(cache_key, self.CACHE_TTL, json.dumps(data))
                return data
            elif res.status_code == 401: logger.error("Shodan: Invalid API key")
            elif res.status_code == 429: logger.warning("Shodan: Rate limit")
            else: logger.error(f"Shodan API error: {res.status_code} - {res.text}")
        except Exception as e: logger.error(f"Shodan request failed: {e}")
        return None

    def host_lookup(self, ip: str) -> Dict:
        """Get detailed host information"""
        data = self._request(f"/shodan/host/{ip}")
        if not data: return {"ip": ip, "error": "No data available"}
        ports = data.get("ports", [])
        vulns = data.get("vulns", []) or []
        services = []
        for item in data.get("data", []):
            services.append({
                "port": item.get("port"),
                "protocol": item.get("transport", "tcp"),
                "service": item.get("product", "unknown"),
                "version": item.get("version", ""),
                "banner": (item.get("data", "") or "")[:500],
                "cpe": item.get("cpe", ""),
            })
        return {
            "ip": data.get("ip_str"),
            "organization": data.get("org", "N/A"),
            "isp": data.get("isp", "N/A"),
            "country": data.get("country_name", "N/A"),
            "city": data.get("city", "N/A"),
            "asn": data.get("asn", "N/A"),
            "os": data.get("os", "N/A"),
            "ports": ports,
            "vulns": vulns,
            "services": services,
            "hostnames": data.get("hostnames", []),
            "domains": data.get("domains", []),
            "last_update": data.get("last_update", ""),
        }

    def search(self, query: str, page: int = 1, limit: int = 100) -> Dict:
        """Search Shodan"""
        data = self._request("/shodan/host/search", {"query": query, "page": page, "minify": False})
        if not data: return {"total": 0, "matches": []}
        matches = []
        for m in data.get("matches", [])[:limit]:
            matches.append({
                "ip": m.get("ip_str"),
                "port": m.get("port"),
                "org": m.get("org", "N/A"),
                "hostnames": m.get("hostnames", []),
                "domains": m.get("domains", []),
                "product": m.get("product", ""),
                "version": m.get("version", ""),
                "os": m.get("os", ""),
            })
        return {"total": data.get("total", 0), "matches": matches, "query": query}

    def dns_domain(self, domain: str) -> Dict:
        """Get DNS information for domain"""
        data = self._request(f"/dns/domain/{domain}")
        if not data: return {"domain": domain, "subdomains": [], "records": {}}
        return {
            "domain": domain,
            "subdomains": data.get("subdomains", []),
            "records": {
                "A": data.get("data", []),
                "tags": data.get("tags", []),
            },
        }

    def exploits_search(self, query: str) -> List[Dict]:
        """Search exploits database"""
        data = self._request("/exploits/search", {"query": query})
        if not data: return []
        return [{
            "id": e.get("id"),
            "description": e.get("description", "")[:500],
            "type": e.get("type"),
            "platform": e.get("platform"),
            "source": e.get("source"),
            "cve": [c for c in (e.get("cve") or [])],
        } for e in data.get("matches", [])]

    def api_info(self) -> Dict:
        """Get API plan info"""
        return self._request("/api-info") or {}

    def create_finding_from_host(self, scan_id: int, host_data: Dict) -> List[Finding]:
        """Create findings from Shodan host data"""
        findings = []
        if host_data.get("vulns"):
            for cve in host_data["vulns"]:
                findings.append(Finding(scan_id=scan_id, title=f"Vulnerable to {cve}", description=f"Shodan reports this host is vulnerable to {cve}. CVSS analysis recommended.", severity=4, category="vulnerability", source="shodan", url=f"{host_data.get('ip')}", metadata={"cve": cve, "source": "shodan"}))
        for port in host_data.get("ports", []):
            if port in [21, 23, 135, 139, 445, 3389, 5900]:
                findings.append(Finding(scan_id=scan_id, title=f"Risky port {port} open", description=f"Port {port} is open and is known to be high-risk for attacks.", severity=3, category="network", source="shodan", url=f"{host_data.get('ip')}:{port}"))
        return findings


class CensysIntegration:
    """Censys API integration"""
    BASE_URL = "https://search.censys.io/api"
    HOSTS_URL = "https://search.censys.io/api/v2"

    def __init__(self, api_id: str = None, api_secret: str = None):
        self.api_id = api_id or os.getenv("CENSYS_API_ID", "")
        self.api_secret = api_secret or os.getenv("CENSYS_API_SECRET", "")

    def _request(self, method: str, endpoint: str, data: dict = None) -> Optional[Dict]:
        if not self.api_id or not self.api_secret: return None
        cache_key = f"censys:{method}:{endpoint}:{json.dumps(data or {}, sort_keys=True)}"
        cached = redis_client.get(cache_key)
        if cached: return json.loads(cached)
        try:
            res = requests.request(method, f"{self.HOSTS_URL}{endpoint}", auth=(self.api_id, self.api_secret), json=data, timeout=30)
            if res.status_code == 200:
                d = res.json()
                redis_client.setex(cache_key, 86400, json.dumps(d))
                return d
        except Exception as e: logger.error(f"Censys request failed: {e}")
        return None

    def view_host(self, ip: str) -> Dict:
        """View specific host by IP"""
        return self._request("GET", f"/hosts/{ip}") or {}

    def search_hosts(self, query: str, per_page: int = 50) -> List[Dict]:
        """Search hosts using Censys query language"""
        data = self._request("POST", "/hosts/search", {"q": query, "per_page": per_page})
        if not data: return []
        return [{
            "ip": h.get("ip"),
            "services": [s.get("port") for s in h.get("services", [])],
            "location": h.get("location", {}),
            "autonomous_system": h.get("autonomous_system", {}),
            "operating_system": h.get("operating_system", {}),
        } for h in data.get("result", {}).get("hits", [])]

    def view_certificate(self, fingerprint: str) -> Dict:
        """Get certificate details"""
        return self._request("GET", f"/certificates/{fingerprint}") or {}


def shodan_scan_target(target: str, scan_id: int) -> List[Dict]:
    """Run Shodan lookup for target"""
    shodan = ShodanIntegration()
    findings = []
    if not shodan.api_key: return [{"warning": "Shodan API key not configured"}]
    import socket
    try:
        ip = socket.gethostbyname(target)
    except: ip = target
    host_info = shodan.host_lookup(ip)
    new_findings = shodan.create_finding_from_host(scan_id, host_info)
    for f in new_findings:
        db.session.add(f)
    db.session.commit()
    findings.extend([{"id": f.id, "title": f.title, "severity": f.severity} for f in new_findings])
    sub_info = shodan.dns_domain(target)
    findings.append({"info": f"Found {len(sub_info.get('subdomains', []))} subdomains via Shodan", "subdomains": sub_info.get("subdomains", [])[:50]})
    return findings
