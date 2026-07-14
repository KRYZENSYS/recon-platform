"""Subdomain enumeration - DNS, certificate transparency, wordlist brute-force"""
import asyncio
import aiohttp
import dns.resolver
import dns.asyncresolver
from typing import List, Set
from datetime import datetime


# Top 5000 subdomains (subset for performance)
COMMON_SUBDOMAINS = [
    "www", "mail", "ftp", "smtp", "pop", "pop3", "imap", "webmail",
    "email", "mx", "mx1", "mx2", "ns", "ns1", "ns2", "ns3", "ns4",
    "dns", "dns1", "dns2", "vpn", "remote", "gateway", "gw", "router",
    "admin", "administrator", "panel", "cpanel", "whm", "plesk", "webmin",
    "blog", "wp", "wordpress", "joomla", "drupal", "cms",
    "dev", "development", "stage", "staging", "test", "testing", "qa", "uat",
    "demo", "trial", "sandbox", "lab",
    "api", "api1", "api2", "api-dev", "api-staging", "api-prod", "rest", "graphql",
    "cdn", "cdn1", "cdn2", "static", "assets", "media", "images", "img", "files",
    "cloud", "aws", "azure", "gcp", "heroku", "digitalocean", "linode",
    "db", "database", "mysql", "postgres", "mongo", "redis", "elastic", "es",
    "backup", "backups", "bak", "old", "new", "legacy", "archive", "archives",
    "shop", "store", "cart", "pay", "payment", "billing", "invoice",
    "secure", "ssl", "tls", "https", "cert", "pki",
    "login", "signin", "auth", "sso", "oauth", "ldap", "ad",
    "portal", "intranet", "internal", "private", "corp", "corporate",
    "git", "github", "gitlab", "bitbucket", "svn", "gitolite",
    "ci", "cd", "jenkins", "travis", "circle", "bamboo", "gitlab-ci", "github-actions",
    "docker", "k8s", "kubernetes", "rancher", "openshift",
    "monitor", "monitoring", "nagios", "zabbix", "prometheus", "grafana", "kibana",
    "log", "logs", "logging", "elk", "splunk", "sentry",
    "help", "support", "ticket", "tickets", "jira", "confluence", "servicedesk",
    "wiki", "kb", "knowledge", "docs", "documentation", "manual",
    "forum", "community", "social", "chat", "slack", "discord", "teams",
    "video", "stream", "live", "broadcast", "youtube", "vimeo", "twitch",
    "mobile", "m", "ios", "android", "app", "apps",
    "minecraft", "game", "games", "play", "steam",
    "learn", "education", "school", "university", "academy", "training",
    "mail2", "webmail2", "exchange", "owa", "autodiscover",
    "search", "solr", "sphinx", "elasticsearch", "opensearch",
    "proxy", "proxies", "squid", "nginx", "haproxy", "varnish",
    "status", "health", "ping", "uptime", "monitor",
    "upload", "uploads", "download", "downloads", "transfer", "share", "files",
    "user", "users", "account", "accounts", "profile", "profiles", "me", "my",
    "crm", "erp", "hr", "finance", "accounting", "sales",
    "analytics", "stats", "statistics", "tracking", "tracking", "ga", "matomo",
    "marketing", "campaign", "ads", "ad", "adserver", "banner", "promo",
    "newsletter", "mailing", "email", "campaigns",
    "web1", "web2", "web3", "web4", "web01", "web02", "host", "host1",
    "node1", "node2", "server1", "server2", "srv", "srv1", "srv2",
    "lb", "lb1", "lb2", "loadbalancer", "elb", "alb", "nlb",
    "cache", "memcached", "varnish", "redis", "squid",
    "queue", "mq", "rabbitmq", "kafka", "activemq",
    "ws", "websocket", "wss", "socket",
    "sip", "voip", "pbx", "asterisk", "freeswitch",
    "git", "repo", "repos", "repository", "code", "source",
    "design", "ui", "ux", "figma", "sketch", "zeplin",
    "office", "office365", "sharepoint", "onedrive",
    "vps", "vm", "vagrant", "docker", "kubernetes",
    "ai", "ml", "data", "datalake", "warehouse", "bi", "tableau", "powerbi",
    "iot", "device", "devices", "sensor", "sensors",
    "vpn1", "vpn2", "wireguard", "openvpn", "ipsec",
    "remote", "ssh", "sftp", "scp", "rsync",
    "ftp1", "ftp2", "sftp1", "sftp2", "ftps",
    "ldap", "ldaps", "radius", "tacacs",
    "dns1", "dns2", "ns1", "ns2", "ns3", "ns4",
    "speed", "speedtest", "iperf", "test",
    "ex", "example", "demo", "sample", "tmp", "temp", "dev1", "dev2",
    "saas", "platform", "console", "dashboard", "portal",
    "billing", "invoice", "payment", "pay", "checkout", "cart", "shop",
    "meet", "zoom", "webex", "gotomeeting",
    "translate", "trans", "i18n", "l10n",
    "staging", "preprod", "pre-prod", "prod", "production",
    "beta", "alpha", "v1", "v2", "api-v1", "api-v2", "v3",
    "next", "nextcloud", "owncloud", "cloud",
    "grafana", "prometheus", "kibana", "elastic", "elasticsearch",
    "rabbit", "kafka", "mq", "activemq", "sqs", "sns",
    "argo", "argocd", "jenkins", "drone", "spinnaker",
    "wp-admin", "wp-content", "wp-includes", "wp-login",
    "joomla", "drupal", "magento", "shopify", "woocommerce",
    "prestashop", "opencart", "oscommerce", "zencart",
    "tomcat", "weblogic", "websphere", "jboss", "wildfly",
    "glassfish", "jetty", "nginx", "apache", "iis",
    "node", "nodejs", "express", "react", "vue", "angular",
    "python", "django", "flask", "fastapi", "rails", "ruby",
    "php", "laravel", "symfony", "codeigniter", "yii", "cakephp",
    "java", "spring", "springboot", "kotlin", "scala", "groovy",
    "go", "golang", "rust", "elixir", "erlang", "haskell", "clojure",
    "blockchain", "bitcoin", "ethereum", "crypto", "nft", "web3",
    "chatbot", "bot", "ai", "ml", "nlp", "computer-vision", "cv",
    "telegram", "whatsapp", "viber", "signal",
    "sms", "mms", "push", "notification",
]


class SubdomainEnumerator:
    """Find subdomains via multiple methods"""

    @staticmethod
    async def dns_bruteforce(domain: str, wordlist: List[str] = None, concurrency: int = 50) -> Set[str]:
        """DNS brute-force with wordlist"""
        if wordlist is None:
            wordlist = COMMON_SUBDOMAINS
        found = set()
        sem = asyncio.Semaphore(concurrency)
        resolver = dns.asyncresolver.Resolver()
        resolver.timeout = 2
        resolver.lifetime = 2

        async def check_subdomain(word):
            async with sem:
                sub = f"{word}.{domain}"
                try:
                    answers = await resolver.resolve(sub, "A")
                    for rdata in answers:
                        found.add(sub)
                        break
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout, Exception):
                    pass

        await asyncio.gather(*[check_subdomain(w) for w in wordlist])
        return found

    @staticmethod
    async def crt_sh(domain: str) -> Set[str]:
        """Certificate Transparency via crt.sh"""
        found = set()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://crt.sh/?q=%.{domain}&output=json"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for entry in data:
                            name = entry.get("name_value", "")
                            for n in name.split("\n"):
                                n = n.strip().lower()
                                if n.endswith(domain) and "*" not in n:
                                    found.add(n)
        except Exception:
            pass
        return found

    @staticmethod
    async def hackertarget(domain: str) -> Set[str]:
        """HackerTarget API"""
        found = set()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        for line in text.split("\n"):
                            if "," in line:
                                host = line.split(",")[0].strip()
                                if host.endswith(domain):
                                    found.add(host.lower())
        except Exception:
            pass
        return found

    @staticmethod
    async def rapiddns(domain: str) -> Set[str]:
        """RapidDNS"""
        found = set()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://rapiddns.io/subdomain/{domain}?full=1"
                headers = {"User-Agent": "Mozilla/5.0"}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        import re
                        pattern = rf"((?:[a-z0-9-]+\.)+{re.escape(domain)})"
                        matches = re.findall(pattern, text)
                        for m in matches:
                            found.add(m.lower())
        except Exception:
            pass
        return found

    @staticmethod
    async def alienvault(domain: str) -> Set[str]:
        """AlienVault OTX"""
        found = set()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for entry in data.get("passive_dns", []):
                            hostname = entry.get("hostname", "").lower()
                            if hostname.endswith(domain):
                                found.add(hostname)
        except Exception:
            pass
        return found

    @staticmethod
    async def threatcrowd(domain: str) -> Set[str]:
        """ThreatCrowd"""
        found = set()
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://www.threatcrowd.org/searchApi/v2/api/domain/report/?domain={domain}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for sub in data.get("subdomains", []):
                            found.add(sub.lower())
        except Exception:
            pass
        return found

    @staticmethod
    async def full_enum(domain: str, methods: List[str] = None, wordlist: List[str] = None) -> dict:
        """Full subdomain enumeration"""
        if methods is None:
            methods = ["dns", "crt", "hackertarget", "rapiddns", "alienvault", "threatcrowd"]
        start = datetime.utcnow()
        all_found = set()
        source_count = {}
        tasks = []
        if "dns" in methods:
            tasks.append(("dns", SubdomainEnumerator.dns_bruteforce(domain, wordlist)))
        if "crt" in methods:
            tasks.append(("crt_sh", SubdomainEnumerator.crt_sh(domain)))
        if "hackertarget" in methods:
            tasks.append(("hackertarget", SubdomainEnumerator.hackertarget(domain)))
        if "rapiddns" in methods:
            tasks.append(("rapiddns", SubdomainEnumerator.rapiddns(domain)))
        if "alienvault" in methods:
            tasks.append(("alienvault", SubdomainEnumerator.alienvault(domain)))
        if "threatcrowd" in methods:
            tasks.append(("threatcrowd", SubdomainEnumerator.threatcrowd(domain)))
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        for (source, _), result in zip(tasks, results):
            if isinstance(result, set):
                all_found.update(result)
                source_count[source] = len(result)
        duration = (datetime.utcnow() - start).total_seconds()
        return {
            "domain": domain, "subdomains": sorted(list(all_found)),
            "count": len(all_found), "sources": source_count,
            "duration": duration, "scanned_at": start.isoformat(),
        }


def run(target: str, options: dict = None) -> dict:
    options = options or {}
    return asyncio.run(SubdomainEnumerator.full_enum(target, options.get("methods")))


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "example.com"
    result = run(target)
    print(f"Found {result['count']} subdomains in {result['duration']:.1f}s")
    for s in result["subdomains"][:20]:
        print(f"  - {s}")
