#!/usr/bin/env python3
"""
Filter out typosquat domains and those redirecting to Amazon properties.
"""
import csv
import re

# Amazon redirect patterns to filter out
AMAZON_REDIRECT_PATTERNS = [
    r'amazon\.com',
    r'amazon\.co\.',
    r'amazon\.[a-z]{2,3}$',
    r'aws\.amazon\.com',
    r'amazonaws\.com',
    r'amzn\.to',
    r'amzn\.com',
    r'a\.co',
]

# Typosquat patterns (misspellings and variations)
TYPOSQUAT_PATTERNS = [
    # Amazon misspellings
    r'^[0-9]*a{1,3}m{1,2}a{0,2}z{1,2}o{0,2}n',  # aamazon, amzon, amazzon, etc.
    r'^[0-9]*amzon',
    r'^[0-9]*amazn',
    r'^[0-9]*amaz0n',
    r'^[0-9]*amazon[0-9]',
    r'^[0-9]+amazon',
    r'^4mazon',
    r'^ad?mazon',
    r'^am[ae]zon',
    r'^ama[sz]on',
    r'^amaazon',
    r'^amazo[mn]',
    r'^anazon',
    r'^mazon',
    r'^qmazon',
    r'^smazon',
    r'^wmazon',
    r'^xmazon',
    r'^zamazon',
    
    # AWS misspellings
    r'^a{1,2}w{1,2}s{1,2}[^a-z]',  # aaws, awws, awss
    r'^[0-9]+aws',
    r'^aws[0-9]',
    r'^awz',
    r'^asw\.',
    r'^was\.',
    
    # Kindle misspellings
    r'^k[il]nd[el]e',
    r'^kindale',
    r'^kindel',
    r'^kindlle',
    
    # Echo misspellings
    r'^ech[o0][^a-z]',
    
    # Alexa misspellings  
    r'^al[ea]x[ae]',
    r'^alexaa',
    
    # Prime misspellings
    r'^prim[ea][^a-z]',
    r'^rpime',
    
    # Generic defensive patterns
    r'^(get|buy|shop|my|the|www|new|free|best)[_-]?amazon',
    r'^amazon[_-]?(shop|buy|deals|sale|store|prime|web|site|online)',
    r'^(signin|login|secure|account|verify|update|support)[_-]?amazon',
    r'^amazon[_-]?(signin|login|secure|account|verify|update|support)',
]

def is_amazon_redirect(redirect_url):
    """Check if URL redirects to an Amazon property."""
    if not redirect_url:
        return False
    for pattern in AMAZON_REDIRECT_PATTERNS:
        if re.search(pattern, redirect_url, re.IGNORECASE):
            return True
    return False

def is_typosquat(domain):
    """Check if domain matches typosquat patterns."""
    for pattern in TYPOSQUAT_PATTERNS:
        if re.search(pattern, domain, re.IGNORECASE):
            return True
    return False

def main():
    input_file = "amazon_domains_detailed.csv"
    
    kept = []
    filtered_redirects = []
    filtered_typosquats = []
    
    with open(input_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row['domain']
            redirect = row.get('redirect_url', '')
            http_status = row.get('http_status', '')
            https_status = row.get('https_status', '')
            
            # Check if it's an Amazon redirect
            if is_amazon_redirect(redirect):
                filtered_redirects.append(domain)
                continue
            
            # Check if it's a typosquat
            if is_typosquat(domain):
                filtered_typosquats.append(domain)
                continue
            
            # Keep domains that have a working response
            if (http_status and int(http_status) < 400) or (https_status and int(https_status) < 400):
                kept.append({
                    'domain': domain,
                    'http_status': http_status,
                    'https_status': https_status,
                    'redirect_url': redirect
                })
    
    print(f"=== FILTERING RESULTS ===")
    print(f"Original active domains: {len(kept) + len(filtered_redirects) + len(filtered_typosquats)}")
    print(f"Filtered (Amazon redirects): {len(filtered_redirects)}")
    print(f"Filtered (typosquats): {len(filtered_typosquats)}")
    print(f"Remaining real domains: {len(kept)}")
    
    # Save filtered domains list (for reference)
    with open("amazon_filtered_out.txt", "w") as f:
        f.write("# Domains filtered as Amazon redirects:\n")
        for d in sorted(filtered_redirects):
            f.write(f"{d}\n")
        f.write("\n# Domains filtered as typosquats:\n")
        for d in sorted(filtered_typosquats):
            f.write(f"{d}\n")
    
    # Save clean list - txt
    with open("amazon_domains_clean.txt", "w") as f:
        for item in sorted(kept, key=lambda x: x['domain']):
            f.write(f"{item['domain']}\n")
    
    # Save clean list - csv with details
    with open("amazon_domains_clean.csv", "w") as f:
        f.write("domain,http_status,https_status,redirect_url\n")
        for item in sorted(kept, key=lambda x: x['domain']):
            redirect = item['redirect_url'].replace(",", ";") if item['redirect_url'] else ""
            f.write(f"{item['domain']},{item['http_status']},{item['https_status']},{redirect}\n")
    
    print(f"\nFiles saved:")
    print(f"  amazon_domains_clean.txt - {len(kept)} real domains")
    print(f"  amazon_domains_clean.csv - Same with HTTP details")
    print(f"  amazon_filtered_out.txt - Domains that were filtered out")
    
    # Show sample of kept domains
    print(f"\nSample of kept domains:")
    for item in sorted(kept, key=lambda x: x['domain'])[:20]:
        print(f"  {item['domain']}")

if __name__ == "__main__":
    main()
