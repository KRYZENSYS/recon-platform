"""DNS Reconnaissance - all record types, zone transfer, DNS security"""
import asyncio
import dns.resolver
import dns.asyncresolver
import dns.zone
import dns.query
import dns.exception
from typing import Dict, List
from datetime import datetime


class DNSRecon:
    """DNS information gathering"""

    RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME", "SRV", "CAA", "PTR"]

    @staticmethod
    async def resolve(domain: str, record_types: List[str] = None) -> Dict:
        """Resolve multiple record types"""
        if record_types is None:
            record_types = DNSRecon.RECORD_TYPES
        results = {"domain": domain, "records": {}, "errors": {}}
        resolver = dns.asyncresolver.Resolver()
        resolver.timeout = 3
        resolver.lifetime = 3
        for rtype in record_types:
            try:
                answers = await resolver.resolve(domain, rtype, raise_on_no_answer=False)
                results["records"][rtype] = [r.to_text() for r in answers]
            except dns.resolver.NXDOMAIN:
                results["errors"][rtype] = "Domain does not exist"
            except dns.resolver.NoAnswer:
                results["records"][rtype] = []
            except dns.resolver.Timeout:
                results["errors"][rtype] = "Timeout"
            except Exception as e:
                results["errors"][rtype] = str(e)
        return results

    @staticmethod
    async def zone_transfer(domain: str) -> Dict:
        """Attempt zone transfer (AXFR)"""
        results = {"domain": domain, "vulnerable": False, "nameservers": []}
        resolver = dns.asyncresolver.Resolver()
        try:
            ns_answers = await resolver.resolve(domain, "NS")
            for ns in ns_answers:
                ns_host = str(ns).rstrip(".")
                results["nameservers"].append(ns_host)
                try:
                    loop = asyncio.get_event_loop()
                    zone = await loop.run_in_executor(None, lambda: dns.query.xfr(ns_host, domain, timeout=5))
                    if zone:
                        results["vulnerable"] = True
                except Exception:
                    pass
        except Exception as e:
            results["error"] = str(e)
        return results

    @staticmethod
    async def dns_security_check(domain: str) -> Dict:
        """Check DNS security (SPF, DKIM, DMARC, DNSSEC, CAA)"""
        results = {"domain": domain, "checks": {}}
        resolver = dns.asyncresolver.Resolver()
        # SPF
        try:
            answers = await resolver.resolve(domain, "TXT")
            for r in answers:
                txt = r.to_text().strip('"')
                if txt.startswith("v=spf1"):
                    results["checks"]["spf"] = {"present": True, "value": txt[:200]}
                    break
        except Exception:
            pass
        if "spf" not in results["checks"]:
            results["checks"]["spf"] = {"present": False, "risk": "Email spoofing possible"}
        # DMARC
        try:
            answers = await resolver.resolve(f"_dmarc.{domain}", "TXT")
            for r in answers:
                txt = r.to_text().strip('"')
                if txt.startswith("v=DMARC1"):
                    results["checks"]["dmarc"] = {"present": True, "policy": "enforced" if "p=reject" in txt or "p=quarantine" in txt else "monitor"}
                    break
        except Exception:
            pass
        if "dmarc" not in results["checks"]:
            results["checks"]["dmarc"] = {"present": False, "risk": "Email spoofing not prevented"}
        # DNSSEC
        try:
            answers = await resolver.resolve(domain, "DNSKEY")
            if answers:
                results["checks"]["dnssec"] = {"present": True, "keys": len(answers)}
        except Exception:
            results["checks"]["dnssec"] = {"present": False, "risk": "DNS spoofing possible"}
        # CAA
        try:
            answers = await resolver.resolve(domain, "CAA")
            results["checks"]["caa"] = {"present": True, "records": [r.to_text() for r in answers]}
        except Exception:
            results["checks"]["caa"] = {"present": False, "risk": "Any CA can issue certs"}
        # Score
        score = 100
        if not results["checks"].get("spf", {}).get("present"): score -= 20
        if not results["checks"].get("dmarc", {}).get("present"): score -= 20
        if not results["checks"].get("dnssec", {}).get("present"): score -= 15
        if not results["checks"].get("caa", {}).get("present"): score -= 5
        results["security_score"] = max(0, score)
        return results

    @staticmethod
    async def full_recon(domain: str) -> Dict:
        """Full DNS recon"""
        start = datetime.utcnow()
        results = await DNSRecon.resolve(domain)
        results["zone_transfer"] = await DNSRecon.zone_transfer(domain)
        results["security"] = await DNSRecon.dns_security_check(domain)
        results["duration"] = (datetime.utcnow() - start).total_seconds()
        return results


def run(target: str, options: dict = None) -> dict:
    return asyncio.run(DNSRecon.full_recon(target))
