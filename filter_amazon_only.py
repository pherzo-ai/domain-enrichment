#!/usr/bin/env python3
"""
Filter to keep only domains that are LIKELY Amazon business domains.
This excludes customer domains registered through Amazon's registry services.
"""
import csv
import re

# Patterns that indicate an Amazon-related domain
AMAZON_RELATED_PATTERNS = [
    # Amazon brand patterns
    r'amazon', r'amzn', r'amz[^a-z]',
    r'aws', r'alexa', r'echo[^a-z]',
    r'kindle', r'fire[^a-z]', r'prime',
    r'audible', r'wholefoods', r'wholefood',
    r'zappos', r'twitch', r'imdb',
    r'goodreads', r'ring[^a-z]', r'blink',
    r'eero', r'zoox', r'kuiper',
    r'pillpack', r'onemedical', r'wondery',
    r'a9\.', r'lab126', r'annapurna',
    r'cloudendure', r'cloudfront',
    r'mgm[^a-z]', r'mgmplus',
    # AWS/Cloud patterns
    r'eksworkshop', r'serverless',
    r's3[^a-z]', r'ec2[^a-z]', r'lambda',
    r'dynamodb', r'redshift', r'athena',
    r'sagemaker', r'bedrock', r'lex[^a-z]',
    # Amazon products/services
    r'primevideo', r'primemusic', r'freevee',
    r'comixology', r'dpreview', r'woot',
    r'shopbop', r'souq', r'mturk',
    r'mechanical.?turk', r'abebooks',
    # Infrastructure
    r'awsdns', r'amazonaws',
]

# Known Amazon acquisitions and projects (not obvious from name)
KNOWN_AMAZON_DOMAINS = {
    'fauna.com', 'fauna.net',
    'umbra3d.com', 
    'inlt.com',
    'dbbest.com', 'dbbest.net',
    'viziotix.com',
    'newworld.com',
    'lostark.com',
    'seattlespheres.com',
    'blazegraph.com',
    'bluage.com',
    'partiql.org',
    'runfinch.com',
    'saltburnfilm.com',
}

def is_amazon_related(domain):
    """Check if domain is likely Amazon-related."""
    domain_lower = domain.lower()
    
    # Check if in known list
    if domain_lower in KNOWN_AMAZON_DOMAINS:
        return True
    
    # Check patterns
    for pattern in AMAZON_RELATED_PATTERNS:
        if re.search(pattern, domain_lower):
            return True
    
    return False

def main():
    input_file = "amazon_domains_detailed.csv"
    
    amazon_domains = []
    non_amazon_domains = []
    
    with open(input_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row['domain']
            http_status = row.get('http_status', '')
            https_status = row.get('https_status', '')
            redirect = row.get('redirect_url', '')
            
            # Must have working response
            has_response = (http_status and http_status.isdigit() and int(http_status) < 400) or \
                          (https_status and https_status.isdigit() and int(https_status) < 400)
            
            if not has_response:
                continue
            
            if is_amazon_related(domain):
                amazon_domains.append({
                    'domain': domain,
                    'http_status': http_status,
                    'https_status': https_status,
                    'redirect_url': redirect
                })
            else:
                non_amazon_domains.append(domain)
    
    print(f"=== AMAZON-RELATED FILTER ===")
    print(f"Total active domains checked: {len(amazon_domains) + len(non_amazon_domains)}")
    print(f"Amazon-related domains: {len(amazon_domains)}")
    print(f"Non-Amazon (customer) domains: {len(non_amazon_domains)}")
    
    # Save Amazon-related domains
    with open("amazon_business_domains.txt", "w") as f:
        for item in sorted(amazon_domains, key=lambda x: x['domain']):
            f.write(f"{item['domain']}\n")
    
    with open("amazon_business_domains.csv", "w") as f:
        f.write("domain,http_status,https_status,redirect_url\n")
        for item in sorted(amazon_domains, key=lambda x: x['domain']):
            redirect = item['redirect_url'].replace(",", ";") if item['redirect_url'] else ""
            f.write(f"{item['domain']},{item['http_status']},{item['https_status']},{redirect}\n")
    
    # Save non-Amazon for reference
    with open("amazon_registry_customer_domains.txt", "w") as f:
        f.write("# These appear to be customer domains registered through Amazon Route 53\n")
        for d in sorted(non_amazon_domains):
            f.write(f"{d}\n")
    
    print(f"\nFiles saved:")
    print(f"  amazon_business_domains.txt - {len(amazon_domains)} Amazon business domains")
    print(f"  amazon_business_domains.csv - Same with HTTP details")
    print(f"  amazon_registry_customer_domains.txt - {len(non_amazon_domains)} customer domains (excluded)")
    
    print(f"\nSample Amazon business domains:")
    for item in sorted(amazon_domains, key=lambda x: x['domain'])[:30]:
        redirect_info = f" -> {item['redirect_url'][:40]}..." if item['redirect_url'] and len(item['redirect_url']) > 40 else ""
        print(f"  {item['domain']}{redirect_info}")

if __name__ == "__main__":
    main()
