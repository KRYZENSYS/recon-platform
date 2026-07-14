"""SSL/TLS Checker - certificate, ciphers, vulnerabilities"""
import ssl
import socket
import json
from datetime import datetime, timezone
from typing import Dict, List
import asyncio
import hashlib


VULNERABLE_PROTOCOLS = ["SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1"]
STRONG_PROTOCOLS = ["TLSv1.2", "TLSv1.3"]

WEAK_CIPHERS = [
    "RC4", "DES", "3DES", "NULL", "EXPORT", "MD5", "aNULL", "eNULL",
    "ADH", "AECDH",
]


class SSLChecker:
    """Comprehensive SSL/TLS analyzer"""

    @staticmethod
    def get_certificate(host: str, port: int = 443, timeout: int = 10) -> Dict:
        """Get SSL certificate info"""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert_bin = ssock.getpeercert(binary_form=True)
                    cert = ssock.getpeercert()
                    # Parse certificate details
                    result = {
                        "subject": dict(x[0] for x in cert.get("subject", [])),
                        "issuer": dict(x[0] for x in cert.get("issuer", [])),
                        "version": cert.get("version"),
                        "serialNumber": cert.get("serialNumber"),
                        "notBefore": cert.get("notBefore"),
                        "notAfter": cert.get("notAfter"),
                        "subjectAltName": [x[1] for x in cert.get("subjectAltName", []) if x[0] == "DNS"],
                        "protocol": ssock.version(),
                        "cipher": ssock.cipher(),
                        "host": host,
                        "port": port,
                    }
                    # Calculate fingerprint
                    if cert_bin:
                        result["sha256_fingerprint"] = hashlib.sha256(cert_bin).hexdigest()
                        result["sha1_fingerprint"] = hashlib.sha1(cert_bin).hexdigest()
                        result["md5_fingerprint"] = hashlib.md5(cert_bin).hexdigest()
                    # Days until expiration
                    try:
                        expires = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                        now = datetime.now(timezone.utc)
                        result["days_until_expiry"] = (expires - now).days
                        result["is_expired"] = result["days_until_expiry"] < 0
                        result["expires_soon"] = 0 < result["days_until_expiry"] < 30
                    except Exception:
                        result["days_until_expiry"] = None
                    return result
        except (socket.timeout, ConnectionRefusedError, ssl.SSLError, OSError) as e:
            return {"host": host, "port": port, "error": str(e), "type": type(e).__name__}

    @staticmethod
    def check_protocols(host: str, port: int = 443) -> Dict:
        """Test which SSL/TLS versions are supported"""
        supported = {}
        for protocol_name, proto_const in [
            ("SSLv3", ssl.PROTOCOL_SSLv23 if hasattr(ssl, "PROTOCOL_SSLv23") else None),
            ("TLSv1.0", getattr(ssl, "PROTOCOL_TLSv1", None)),
            ("TLSv1.1", getattr(ssl, "PROTOCOL_TLSv1_1", None)),
            ("TLSv1.2", getattr(ssl, "PROTOCOL_TLSv1_2", None)),
            ("TLSv1.3", None),  # TLS 1.3 is default
        ]:
            if proto_const is None and protocol_name != "TLSv1.3":
                continue
            try:
                if protocol_name == "TLSv1.3":
                    ctx = ssl.create_default_context()
                else:
                    ctx = ssl.SSLContext(proto_const)
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                with socket.create_connection((host, port), timeout=5) as sock:
                    with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                        supported[protocol_name] = True
            except Exception:
                supported[protocol_name] = False
        return supported

    @staticmethod
    def check_ciphers(host: str, port: int = 443) -> Dict:
        """Test weak ciphers"""
        weak_ciphers_found = []
        for proto_name in ("TLSv1.0", "TLSv1.1", "TLSv1.2"):
            proto_const = getattr(ssl, f"PROTOCOL_{proto_name.replace('.', '_')}", None)
            if not proto_const:
                continue
            try:
                ctx = ssl.SSLContext(proto_const)
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                ctx.set_ciphers("ALL:@SECLEVEL=0")
                with socket.create_connection((host, port), timeout=5) as sock:
                    with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                        cipher = ssock.cipher()
                        if cipher and any(weak in cipher[0] for weak in WEAK_CIPHERS):
                            weak_ciphers_found.append({"protocol": proto_name, "cipher": cipher[0], "bits": cipher[2]})
            except Exception:
                pass
        return weak_ciphers_found

    @staticmethod
    def check_vulnerabilities(host: str, port: int = 443) -> List[Dict]:
        """Check for known SSL/TLS vulnerabilities"""
        vulns = []
        protocols = SSLChecker.check_protocols(host, port)
        # Check for POODLE (SSLv3)
        if protocols.get("SSLv3"):
            vulns.append({"name": "POODLE", "cve": "CVE-2014-3566", "severity": "high", "description": "SSLv3 enabled - vulnerable to POODLE attack"})
        # Check for BEAST (TLS 1.0)
        if protocols.get("TLSv1.0"):
            vulns.append({"name": "BEAST", "cve": "CVE-2011-3389", "severity": "medium", "description": "TLSv1.0 enabled - vulnerable to BEAST"})
        # Check for Heartbleed (would need actual test)
        # Check weak ciphers
        weak = SSLChecker.check_ciphers(host, port)
        if weak:
            vulns.append({"name": "Weak Ciphers", "severity": "high", "description": f"{len(weak)} weak ciphers found", "details": weak})
        # Check cert expiry
        cert = SSLChecker.get_certificate(host, port)
        if "days_until_expiry" in cert and cert["days_until_expiry"] is not None:
            if cert["days_until_expiry"] < 0:
                vulns.append({"name": "Expired Certificate", "severity": "critical", "description": f"Certificate expired {-cert['days_until_expiry']} days ago"})
            elif cert["days_until_expiry"] < 30:
                vulns.append({"name": "Certificate Expiring Soon", "severity": "medium", "description": f"Certificate expires in {cert['days_until_expiry']} days"})
        if "error" in cert:
            vulns.append({"name": "SSL Error", "severity": "high", "description": cert["error"]})
        return vulns

    @staticmethod
    def full_check(host: str, port: int = 443) -> Dict:
        """Complete SSL analysis"""
        cert = SSLChecker.get_certificate(host, port)
        protocols = SSLChecker.check_protocols(host, port)
        vulns = SSLChecker.check_vulnerabilities(host, port)
        # Calculate score
        score = 100
        score -= sum(20 for v in vulns if v["severity"] == "critical")
        score -= sum(10 for v in vulns if v["severity"] == "high")
        score -= sum(5 for v in vulns if v["severity"] == "medium")
        score = max(0, score)
        grade = "A+" if score >= 95 else "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "F"
        return {
            "host": host, "port": port,
            "certificate": cert, "protocols": protocols,
            "vulnerabilities": vulns, "score": score, "grade": grade,
            "scanned_at": datetime.utcnow().isoformat(),
        }


def run(target: str, options: dict = None) -> dict:
    options = options or {}
    port = options.get("port", 443)
    return SSLChecker.full_check(target, port)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "google.com"
    result = run(target)
    print(json.dumps(result, indent=2, default=str))
