#!/usr/bin/env python3
"""
Comprehensive filter to remove typosquats and Amazon property redirects.
"""
import csv
import re

# Any redirect containing these is filtered (Amazon + all subsidiaries)
AMAZON_REDIRECT_DOMAINS = [
    'amazon.com', 'amazon.co.', 'amazon.de', 'amazon.fr', 'amazon.es',
    'amazon.it', 'amazon.nl', 'amazon.in', 'amazon.ca', 'amazon.com.au',
    'amazon.com.br', 'amazon.com.mx', 'amazon.co.jp', 'amazon.cn',
    'aws.amazon.com', 'amazonaws.com', 'amzn.to', 'amzn.com', 'a.co',
    # Amazon subsidiaries
    'audible.com', 'audible.co.',
    'eero.com',
    'ring.com',
    'blink', 'blinkforhome.com',
    'wholefoodsmarket.com', 'wholefoods.com',
    'zappos.com',
    'twitch.tv', 'twitch.com',
    'imdb.com',
    'goodreads.com',
    'shopbop.com',
    'mturk.com',
    'primevideo.com',
    'mgm.com',  # Amazon-owned studio
    'amazon.jobs', 'amazon.science',
    'theclimatepledge.com',
    'gangsoflagosonprime.com',
    'mxplayer.in',
    'veeqo.com',
    'wondery.com',
    'brilliancepublishing.com',
    'reinvent.awsevents',
    'cloudfront.net',  # AWS CDN
    'newworld.com',  # Amazon Games
    'ignitecommunity.com',
    'hvh-recruiter',  # Amazon hiring
    'youtube.com/containersfromthecouch',  # AWS YouTube
    'aws-samples',  # GitHub AWS
    'github.com/aws',
    'seattlespheres.com',
    'asvf.in',  # Amazon Smbhav Venture Fund
]

# Additional typosquat patterns
TYPOSQUAT_PATTERNS = [
    # Amazon variations
    r'^[0-9]*a+m+[aeoiu]*z+[oea]*n',  # catches amazon misspellings
    r'^[a-z]?amazon',  # anything + amazon
    r'^amazon[a-z0-9]',  # amazon + anything
    r'^maazon', r'^mazon', r'^aazon', r'^azn\.',
    r'^amajon', r'^amajun', r'^amaon', r'^amaozn', r'^amaxzon',
    r'^amazaon', r'^amazin\.', r'^amosun', r'^amozin', r'^amozon',
    r'^amxzon', r'^anazon', r'^zamazon',
    
    # AWS variations  
    r'^aws', r'aws\.', r'onaws\.', r'^awz', r'^asw\.', r'^aaws',
    
    # Alexa
    r'^alexa', r'^al[ea]x[ae]',
    
    # Echo 
    r'^echo',
    
    # Kindle
    r'^kindle', r'^kfb', r'^k[il]nd[el]e', r'kindle',  # any mention of kindle
    r'^kdp',  # Kindle Direct Publishing
    
    # Fire products
    r'^fire',
    
    # Prime
    r'^prime', r'^rpime',
    
    # Audible
    r'^audible', r'^brillianc[eu]a?udio',
    
    # IMDB
    r'^imdb',
    
    # Zappos
    r'^zappos',
    
    # Whole Foods
    r'^wholefoods?', r'^wfm\.',
    
    # Ring
    r'^ring', r'ring\.com',
    
    # Blink
    r'^blink',
    
    # Souq
    r'^souq',
    
    # Twitch  
    r'^twitch',
    
    # Goodreads
    r'^goodreads',
    
    # Box Office Mojo
    r'^boxoffice',
    
    # AWS/Eero
    r'^eero',
    
    # Vega (Amazon product)
    r'^vega',
    
    # A9 (Amazon search)
    r'^a9',
    
    # Generic defensive
    r'^(get|buy|shop|my|the|www|new|free|best|about)[_-]?amazon',
    r'^pay.*amazon', r'^review.*amazon', r'^order.*amazon',
    
    # Health AI / One Medical (Amazon Health)
    r'^(health|medical|ai).*(alexa|prime|amazon|onemedical)',
    r'^onemedical',
    r'^aicare',
    
    # Climate Pledge
    r'^climate',
    
    # Shipment Zero
    r'^shipment',
    
    # Just Walk Out (Amazon Go)
    r'^justwalkout',
    
    # MX Player (Amazon India)
    r'^mxplay', r'^mxplayer',
    
    # Vega (Amazon devices)
    r'vega',
    
    # God of War Prime (Amazon gaming promo)
    r'godofwar.*prime', r'onprime',
    
    # Wondery (Amazon podcast)
    r'^wondery',
    
    # Veeqo (Amazon subsidiary)
    r'^veeqo',
    
    # Containers from the couch (AWS)
    r'^containers',
    
    # Well Architected (AWS)
    r'architected',
    
    # Unified Hiring Portal (Amazon)
    r'^unifiedhiring',
]

# Known Amazon subsidiaries/products to filter (even if not redirecting)
AMAZON_BRANDS = [
    'primevideo', 'primemusic', 'amazonmusic', 'amazonprime',
    'mturk', 'mechanicalturk', 'cloudendure', 'annapurna',
    'zooxamazon', 'awsamazon', 'amazaudible',
    'wholesaleamazon', 'zapposamazon',
    # AWS-related workshop/training domains
    'eksworkshop', 'awsworkshop', 'ec2mssql', 'containersonaws',
    'serverlesscoffee', 'wellarchitected', 'service-catalog-tools',
    # Captive portal domains
    'captiveportal',
    # S3 defensive domains
    's3-acronis', 's3-atlassian', 's3-blackberry', 's3-dk', 's3-fbi',
    's3-ida', 's3-iri', 's3-marcus', 's3-nsa', 's3-proofpoint',
    's3-spacex', 's3-ucia',
    # Amazon infrastructure/products
    'seattlespheres',  # Amazon HQ building
    'runfinch',  # AWS container tool
    'partiql',  # AWS query language
    'iotatlas',  # AWS IoT
    'bluage',  # AWS acquired company
    'swiship',  # Amazon shipping
    'apn-',  # Amazon Partner Network
    'saltburn',  # Amazon Studios film
    'bookstoredemo',  # AWS sample app
    'amz-kdp', 'kdppublishing',  # Kindle Direct Publishing
    'unicorndns', 'unicornpacket',  # AWS networking demos
    'blazegraph',  # Graph DB acquired by Amazon
    'sidewalk',  # Amazon Sidewalk IoT
    'amzpremium',  # amz = Amazon
    'whatiscitadel',  # AWS Citadel
    'theroutingloop',  # AWS networking
    'protozoa',  # AWS Lambda
]

def is_amazon_redirect(redirect_url):
    if not redirect_url:
        return False
    redirect_lower = redirect_url.lower()
    for domain in AMAZON_REDIRECT_DOMAINS:
        if domain in redirect_lower:
            return True
    return False

def is_typosquat_or_brand(domain):
    domain_lower = domain.lower()
    
    # Check brand names
    for brand in AMAZON_BRANDS:
        if brand in domain_lower:
            return True
    
    # Check patterns
    for pattern in TYPOSQUAT_PATTERNS:
        if re.search(pattern, domain_lower):
            return True
    
    return False

def main():
    input_file = "amazon_business_domains.csv"
    
    kept = []
    filtered = {'redirect': [], 'typosquat': []}
    
    with open(input_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row['domain']
            redirect = row.get('redirect_url', '')
            http_status = row.get('http_status', '')
            https_status = row.get('https_status', '')
            
            # Must have working response
            has_response = (http_status and http_status.isdigit() and int(http_status) < 400) or \
                          (https_status and https_status.isdigit() and int(https_status) < 400)
            if not has_response:
                continue
            
            # Filter Amazon redirects
            if is_amazon_redirect(redirect):
                filtered['redirect'].append(domain)
                continue
            
            # Filter typosquats and brands
            if is_typosquat_or_brand(domain):
                filtered['typosquat'].append(domain)
                continue
            
            kept.append({
                'domain': domain,
                'http_status': http_status,
                'https_status': https_status,
                'redirect_url': redirect
            })
    
    total_filtered = len(filtered['redirect']) + len(filtered['typosquat'])
    print(f"=== COMPREHENSIVE FILTERING ===")
    print(f"Filtered (Amazon redirects): {len(filtered['redirect'])}")
    print(f"Filtered (typosquats/brands): {len(filtered['typosquat'])}")
    print(f"Total filtered: {total_filtered}")
    print(f"Remaining unique domains: {len(kept)}")
    
    # Save clean list - txt
    with open("amazon_domains_unique.txt", "w") as f:
        for item in sorted(kept, key=lambda x: x['domain']):
            f.write(f"{item['domain']}\n")
    
    # Save clean list - csv
    with open("amazon_domains_unique.csv", "w") as f:
        f.write("domain,http_status,https_status,redirect_url\n")
        for item in sorted(kept, key=lambda x: x['domain']):
            redirect = item['redirect_url'].replace(",", ";") if item['redirect_url'] else ""
            f.write(f"{item['domain']},{item['http_status']},{item['https_status']},{redirect}\n")
    
    # Save what was filtered
    with open("amazon_filtered_comprehensive.txt", "w") as f:
        f.write(f"# Amazon redirects ({len(filtered['redirect'])}):\n")
        for d in sorted(filtered['redirect']):
            f.write(f"{d}\n")
        f.write(f"\n# Typosquats/Brand domains ({len(filtered['typosquat'])}):\n")
        for d in sorted(filtered['typosquat']):
            f.write(f"{d}\n")
    
    print(f"\nFiles saved:")
    print(f"  amazon_domains_unique.txt - {len(kept)} unique non-Amazon domains")
    print(f"  amazon_domains_unique.csv - Same with details")
    print(f"  amazon_filtered_comprehensive.txt - What was filtered")
    
    print(f"\n=== UNIQUE DOMAINS ({len(kept)}) ===")
    for item in sorted(kept, key=lambda x: x['domain']):
        redirect_info = f" -> {item['redirect_url'][:50]}..." if item['redirect_url'] and len(item['redirect_url']) > 50 else (f" -> {item['redirect_url']}" if item['redirect_url'] else "")
        print(f"  {item['domain']}{redirect_info}")

if __name__ == "__main__":
    main()
