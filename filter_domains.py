#!/usr/bin/env python3
"""
Filter domains to find likely active ones.
1. Remove infrastructure patterns
2. DNS resolution check
3. HTTP/HTTPS response check
"""
import socket
import urllib.request
import ssl
import sys
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import NamedTuple, Optional

# Infrastructure patterns to filter out
INFRA_PATTERNS = [
    r'^awsdns-\d+\.',           # AWS DNS infrastructure
    r'^ns-\d+\.',               # Nameserver patterns
    r'^xn--',                   # Punycode/IDN domains
    r'^spclient\.',             # Internal service domains
    r'^ec2-\d+',                # EC2 patterns
    r'^ip-\d+',                 # IP-based names
]

class DomainStatus(NamedTuple):
    domain: str
    resolves: bool
    http_status: Optional[int]
    https_status: Optional[int]
    redirect_url: Optional[str]

def is_infrastructure(domain: str) -> bool:
    """Check if domain matches infrastructure patterns."""
    for pattern in INFRA_PATTERNS:
        if re.match(pattern, domain, re.IGNORECASE):
            return True
    return False

def check_dns(domain: str) -> bool:
    """Check if domain resolves via DNS."""
    try:
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False

def check_http(domain: str, use_https: bool = False):
    """Check HTTP/HTTPS response."""
    protocol = "https" if use_https else "http"
    url = f"{protocol}://{domain}/"
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0 (compatible; DomainChecker/1.0)")
        
        with urllib.request.urlopen(req, timeout=5, context=ctx if use_https else None) as resp:
            redirect_url = resp.geturl() if resp.geturl() != url else None
            return resp.status, redirect_url
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None

def check_domain(domain: str):
    """Full check for a single domain."""
    # Skip infrastructure domains
    if is_infrastructure(domain):
        return None
    
    # DNS check
    resolves = check_dns(domain)
    if not resolves:
        return DomainStatus(domain, False, None, None, None)
    
    # HTTP checks
    https_status, redirect = check_http(domain, use_https=True)
    http_status, http_redirect = check_http(domain, use_https=False)
    
    # Use redirect from whichever worked
    final_redirect = redirect or http_redirect
    
    return DomainStatus(domain, True, http_status, https_status, final_redirect)

def main():
    input_file = "amazon_all_orgs_raw.txt"
    
    # Load domains
    with open(input_file) as f:
        domains = [line.strip() for line in f if line.strip()]
    
    print(f"Loaded {len(domains)} domains", file=sys.stderr)
    
    # Filter infrastructure first
    non_infra = [d for d in domains if not is_infrastructure(d)]
    infra_count = len(domains) - len(non_infra)
    print(f"Filtered out {infra_count} infrastructure domains", file=sys.stderr)
    print(f"Checking {len(non_infra)} domains for DNS and HTTP...", file=sys.stderr)
    
    results = []
    checked = 0
    
    # Parallel checking
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_domain, d): d for d in non_infra}
        
        for future in as_completed(futures):
            checked += 1
            if checked % 500 == 0:
                print(f"  Progress: {checked}/{len(non_infra)} checked...", file=sys.stderr)
            
            result = future.result()
            if result:
                results.append(result)
    
    # Categorize results
    resolving = [r for r in results if r.resolves]
    has_http = [r for r in resolving if r.http_status or r.https_status]
    has_website = [r for r in has_http if (r.http_status and r.http_status < 400) or (r.https_status and r.https_status < 400)]
    
    print(f"\n=== RESULTS ===", file=sys.stderr)
    print(f"Total domains: {len(domains)}", file=sys.stderr)
    print(f"Infrastructure filtered: {infra_count}", file=sys.stderr)
    print(f"DNS resolves: {len(resolving)}", file=sys.stderr)
    print(f"Has HTTP response: {len(has_http)}", file=sys.stderr)
    print(f"Active websites (2xx/3xx): {len(has_website)}", file=sys.stderr)
    
    # Save results
    # All resolving domains
    with open("amazon_domains_resolving.txt", "w") as f:
        for r in sorted(resolving, key=lambda x: x.domain):
            f.write(f"{r.domain}\n")
    
    # Active websites only
    with open("amazon_domains_active.txt", "w") as f:
        for r in sorted(has_website, key=lambda x: x.domain):
            f.write(f"{r.domain}\n")
    
    # Detailed CSV with all info
    with open("amazon_domains_detailed.csv", "w") as f:
        f.write("domain,resolves,http_status,https_status,redirect_url\n")
        for r in sorted(resolving, key=lambda x: x.domain):
            redirect = r.redirect_url.replace(",", ";") if r.redirect_url else ""
            f.write(f"{r.domain},{r.resolves},{r.http_status or ''},{r.https_status or ''},{redirect}\n")
    
    print(f"\nFiles saved:", file=sys.stderr)
    print(f"  amazon_domains_resolving.txt - All domains that resolve via DNS", file=sys.stderr)
    print(f"  amazon_domains_active.txt - Domains with active websites", file=sys.stderr)
    print(f"  amazon_domains_detailed.csv - Full details with HTTP status codes", file=sys.stderr)

if __name__ == "__main__":
    main()
