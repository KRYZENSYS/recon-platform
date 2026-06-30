"""🌐 DNS Recon moduli — domen haqida ma'lumot yig'ish."""
import dns.resolver
import dns.zone
import dns.query
import dns.name


def recon(domain):
    """Berilgan domen uchun DNS ma'lumotlarini yig'ish."""
    results = []

    record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA']

    for rtype in record_types:
        try:
            answers = dns.resolver.resolve(domain, rtype, raise_on_no_answer=False)
            for rdata in answers:
                if rtype == 'MX':
                    value = f"{rdata.preference} {rdata.exchange}"
                elif rtype == 'SOA':
                    value = f"{rdata.mname} {rdata.rname} (serial: {rdata.serial})"
                elif rtype == 'TXT':
                    value = ' '.join([s.decode('utf-8', errors='ignore') if isinstance(s, bytes) else str(s) for s in rdata.strings])
                else:
                    value = str(rdata)

                results.append({
                    'type': rtype,
                    'host': domain,
                    'value': value[:1024],
                    'ttl': answers.rrset.ttl if answers.rrset else None,
                })
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.resolver.LifetimeTimeout, dns.exception.Timeout):
            continue
        except Exception:
            continue

    # Subdomain bruteforce (keng tarqalganlar)
    common_subs = ['www', 'mail', 'ftp', 'smtp', 'pop', 'ns1', 'ns2',
                   'webmail', 'login', 'admin', 'blog', 'dev', 'api',
                   'cdn', 'cloud', 'support', 'mail2', 'cpanel']

    for sub in common_subs:
        subdomain = f"{sub}.{domain}"
        try:
            answers = dns.resolver.resolve(subdomain, 'A', raise_on_no_answer=False)
            for rdata in answers:
                results.append({
                    'type': 'A',
                    'host': subdomain,
                    'value': str(rdata),
                    'ttl': answers.rrset.ttl if answers.rrset else None,
                })
        except Exception:
            continue

    return results