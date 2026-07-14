"""Port scanner - async, fast, with banner grabbing"""
import asyncio
import socket
from typing import List, Dict
from datetime import datetime

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
    111: "RPCBind", 135: "MSRPC", 139: "NetBIOS", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    465: "SMTPS", 587: "SMTP-TLS", 631: "IPP", 993: "IMAPS", 995: "POP3S", 1433: "MSSQL",
    1521: "Oracle", 1723: "PPTP", 2049: "NFS", 3306: "MySQL", 3389: "RDP", 3690: "SVN",
    4444: "Metasploit", 5000: "UPnP", 5432: "PostgreSQL", 5900: "VNC", 5984: "CouchDB",
    6379: "Redis", 7001: "WebLogic", 8000: "HTTP-Alt", 8008: "HTTP-Alt2", 8080: "HTTP-Proxy",
    8081: "HTTP-Alt3", 8443: "HTTPS-Alt", 8888: "HTTP-Alt4", 9000: "PHP-FPM", 9090: "Prometheus",
    9200: "Elasticsearch", 9300: "Elasticsearch", 11211: "Memcached", 27017: "MongoDB",
    50000: "SAP", 2701: "Radmin",
}

RISKY_PORTS = {
    21: ("high", "FTP - Unencrypted file transfer"),
    23: ("critical", "Telnet - Unencrypted remote access"),
    135: ("high", "MSRPC - Windows RPC"),
    139: ("high", "NetBIOS - Legacy file sharing"),
    445: ("critical", "SMB - Vulnerable to ransomware"),
    1433: ("high", "MSSQL exposed"),
    3389: ("high", "RDP - Brute-force target"),
    5900: ("high", "VNC - Remote desktop"),
    6379: ("critical", "Redis - Often unsecured"),
    9200: ("high", "Elasticsearch - Data exposure risk"),
    27017: ("high", "MongoDB - Often unsecured"),
    11211: ("high", "Memcached - DDoS amplification"),
}


class PortScanner:
    """Async port scanner with service detection"""

    @staticmethod
    async def scan_port(host: str, port: int, timeout: float = 2.0) -> Dict:
        """Scan single port"""
        try:
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            service = COMMON_PORTS.get(port, "Unknown")
            banner = ""
            try:
                banner_data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                banner = banner_data.decode("utf-8", errors="ignore").strip()[:256]
            except (asyncio.TimeoutError, Exception):
                pass
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            risk = RISKY_PORTS.get(port, ("info", ""))
            return {
                "port": port, "state": "open", "service": service,
                "banner": banner, "risk": risk[0], "risk_note": risk[1],
            }
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return {"port": port, "state": "closed"}
        except Exception as e:
            return {"port": port, "state": "filtered", "error": str(e)}

    @staticmethod
    async def scan_ports(host: str, ports: List[int] = None, max_concurrent: int = 100) -> List[Dict]:
        """Scan multiple ports"""
        if ports is None:
            ports = list(COMMON_PORTS.keys())
        sem = asyncio.Semaphore(max_concurrent)
        async def bounded_scan(port):
            async with sem:
                return await PortScanner.scan_port(host, port)
        tasks = [bounded_scan(p) for p in ports]
        return await asyncio.gather(*tasks)

    @staticmethod
    async def full_scan(host: str, port_range: tuple = (1, 1024)) -> Dict:
        """Full port range scan"""
        start_time = datetime.utcnow()
        ports = list(range(port_range[0], port_range[1] + 1))
        results = await PortScanner.scan_ports(host, ports, max_concurrent=200)
        open_ports = [r for r in results if r["state"] == "open"]
        risky = [r for r in open_ports if r.get("risk") in ("high", "critical")]
        duration = (datetime.utcnow() - start_time).total_seconds()
        return {
            "host": host, "scanned_ports": len(ports), "open_ports": len(open_ports),
            "risky_ports": len(risky), "results": open_ports, "duration": duration,
            "risk_score": min(100, len(risky) * 15 + len(open_ports) * 2),
            "timestamp": start_time.isoformat(),
        }

    @staticmethod
    def resolve_host(host: str) -> str:
        try:
            return socket.gethostbyname(host)
        except socket.gaierror:
            return host


async def run(target: str, options: dict = None) -> dict:
    options = options or {}
    host = PortScanner.resolve_host(target)
    port_range = options.get("port_range", (1, 1024))
    return await PortScanner.full_scan(host, port_range)


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "scanme.nmap.org"
    result = asyncio.run(run(target))
    print(f"Open ports: {result['open_ports']}")
    for p in result["results"][:10]:
        print(f"  {p['port']}/tcp {p['service']} {p.get('banner', '')[:50]}")
