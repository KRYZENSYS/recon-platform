"""WHOIS Lookup + Email Harvester + Wayback Machine"""
import asyncio
import aiohttp
import re
import json
from datetime import datetime
from typing import Dict, List, Set


class WhoisLookup:
    """WHOIS information"""

    @staticmethod
    def lookup(domain: str) -> Dict:
        try:
            import whois
            w = whois.whois(domain)
            return {
                "domain": domain,
                "registrar": w.registrar,
                "whois_server": w.whois_server,
                "creation_date": str(w.creation_date) if w.creation_date else None,
                "expiration_date": str(w.expiration_date) if w.expiration_date else None,
                "updated_date": str(w.updated_date) if w.updated_date else None,
                "name_servers": w.name_servers if isinstance(w.name_servers, list) else [w.name_servers] if w.name_servers else [],
                "status": w.status,
                "emails": w.emails if isinstance(w.emails, list) else [w.emails] if w.emails else [],
                "org": w.org,
                "country": w.country,
                "state": w.state,
                "city": w.city,
                "address": w.address,
                "zipcode": w.zipcode,
                "dnssec": w.dnssec,
            }
        except Exception as e:
            return {"domain": domain, "error": str(e)}


class EmailHarvester:
    """Find emails from various sources"""

    @staticmethod
    async def from_google(domain: str) -> Set[str]:
        """Search Google for emails (via public search)"""
        emails = set()
        try:
            async with aiohttp.ClientSession() as session:
                queries = [
                    f'"{domain}" "@{domain}"',
                    f'site:linkedin.com "{domain}"',
                    f'site:facebook.com "{domain}"',
                ]
                for q in queries:
                    url = f"https://www.google.com/search?q={q}&num=100"
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            pattern = rf"[a-zA-Z0-9._%+-]+@{re.escape(domain)}"
                            matches = re.findall(pattern, text)
                            emails.update(matches)
        except Exception:
            pass
        return emails

    @staticmethod
    async def from_hunter(domain: str, api_key: str = None) -> Set[str]:
        """Hunter.io API"""
        emails = set()
        if not api_key:
            return emails
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for e in data.get("data", {}).get("emails", []):
                            emails.add(e.get("value", ""))
        except Exception:
            pass
        return emails

    @staticmethod
    async def from_github(domain: str) -> Set[str]:
        """GitHub code search"""
        emails = set()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.github.com/search/code?q=%40{domain}"
                headers = {"Accept": "application/vnd.github.v3+json"}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data.get("items", []):
                            # Search in repo for emails
                            repo_url = item.get("repository", {}).get("url")
                            if repo_url:
                                emails.update(await EmailHarvester._scrape_repo_for_emails(session, repo_url, domain))
        except Exception:
            pass
        return emails

    @staticmethod
    async def _scrape_repo_for_emails(session, repo_url, domain):
        emails = set()
        try:
            async with session.get(f"{repo_url}/contents/", timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data[:10]:
                        if item.get("type") == "file" and item.get("download_url"):
                            async with session.get(item["download_url"], timeout=aiohttp.ClientTimeout(total=10)) as fr:
                                if fr.status == 200:
                                    text = await fr.text()
                                    pattern = rf"[a-zA-Z0-9._%+-]+@{re.escape(domain)}"
                                    emails.update(re.findall(pattern, text))
        except Exception:
            pass
        return emails

    @staticmethod
    async def from_pgp(domain: str) -> Set[str]:
        """PGP key servers"""
        emails = set()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://keys.openpgp.org/vks/v1/by-email/{domain}"
                # Search keys for domain
                search_url = f"https://keys.openpgp.org/vks/v1/search?q={domain}"
                async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        pattern = rf"[a-zA-Z0-9._%+-]+@{re.escape(domain)}"
                        emails.update(re.findall(pattern, text))
        except Exception:
            pass
        return emails

    @staticmethod
    async def harvest(domain: str, sources: List[str] = None) -> Dict:
        """Full email harvest"""
        if sources is None:
            sources = ["google", "github", "pgp"]
        all_emails = set()
        tasks = []
        if "google" in sources:
            tasks.append(EmailHarvester.from_google(domain))
        if "github" in sources:
            tasks.append(EmailHarvester.from_github(domain))
        if "pgp" in sources:
            tasks.append(EmailHarvester.from_pgp(domain))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, set):
                all_emails.update(r)
        return {"domain": domain, "emails": sorted(list(all_emails)), "count": len(all_emails)}


class WaybackMachine:
    """Wayback Machine historical data"""

    @staticmethod
    async def get_snapshots(domain: str, limit: int = 100) -> List[Dict]:
        """Get all snapshots"""
        snapshots = []
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&limit={limit}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if len(data) > 1:
                            headers = data[0]
                            for row in data[1:]:
                                snap = dict(zip(headers, row))
                                snapshots.append({
                                    "url": f"http://web.archive.org/web/{snap.get('timestamp')}/{snap.get('original')}",
                                    "timestamp": snap.get("timestamp"),
                                    "status": snap.get("statuscode"),
                                    "mime": snap.get("mimetype"),
                                    "length": int(snap.get("length", 0)) if snap.get("length", "").isdigit() else 0,
                                })
        except Exception:
            pass
        return snapshots

    @staticmethod
    async def get_subdomains_from_history(domain: str) -> Set[str]:
        """Find subdomains from historical data"""
        subs = set()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://web.archive.org/cdx/search/cdx?url=*.{domain}&output=json&fl=original&collapse=urlkey&limit=10000"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for row in data[1:]:
                            url_str = row[0] if row else ""
                            match = re.match(rf"https?://([^/]+\.{re.escape(domain)})", url_str)
                            if match:
                                subs.add(match.group(1).lower())
        except Exception:
            pass
        return subs

    @staticmethod
    async def full_check(domain: str) -> Dict:
        """Full Wayback analysis"""
        start = datetime.utcnow()
        snapshots = await WaybackMachine.get_snapshots(domain, limit=500)
        subdomains = await WaybackMachine.get_subdomains_from_history(domain)
        return {
            "domain": domain, "snapshots": snapshots, "snapshot_count": len(snapshots),
            "subdomains": sorted(list(subdomains)), "subdomain_count": len(subdomains),
            "duration": (datetime.utcnow() - start).total_seconds(),
        }


# === Run functions ===
def run_whois(target: str, options: dict = None) -> dict:
    return WhoisLookup.lookup(target)


def run_emails(target: str, options: dict = None) -> dict:
    options = options or {}
    return asyncio.run(EmailHarvester.harvest(target, options.get("sources")))


def run_wayback(target: str, options: dict = None) -> dict:
    return asyncio.run(WaybackMachine.full_check(target))


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "example.com"
    print(json.dumps(run_whois(target), indent=2, default=str))
