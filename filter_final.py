#!/usr/bin/env python3
"""
Final filter to remove defensive registrations (lawsuits, protests, etc.)
"""
import csv
import re

# Patterns for defensive registrations to remove
DEFENSIVE_PATTERNS = [
    # Lawsuit/legal defensive
    r'lawsuit', r'classaction', r'legal[^a-z]', r'sue[^a-z]',
    r'breach', r'lawyer',
    
    # Anti-brand protest/negative domains
    r'against', r'hate', r'sucks', r'bad[^a-z]',
    r'notmy', r'sayno', r'wtfis', r'killer',
    r'nohere', r'ilove', r'iheart', r'welove',
    r'^moms', r'^dads', r'^cyclists', r'^bikes',
    r'crash', r'kills', r'sux', r'unsafe', r'dangerous',
    r'cantdrive', r'blocks', r'inthebikelane',
    r'insider', r'sweeps', r'giveaway', r'contest',
    
    # Internal/test domains
    r'internal', r'test[^a-z]', r'dev[^a-z]', r'staging',
    
    # Typosquats that slipped through
    r'^www[a-z]',  # wwwaudiblecom
    r'^[a-z]twitch',  # gtwitchcon, rtwitchcon
    r'^the[a-z]+con\.',  # thetwitchcon
    
    # More brand typosquats
    r'^[a-z]?imdb[^\.]*\.',  # 2imdb, actorsimdb
    r'prime\.tk',  # coinbaseprime.tk
    
    # Random defensive patterns
    r'career[s]?-',  # career-zoox
    
    # Zoox-specific defensive
    r'zoox(doox|soox|sux|com\.com)',
    r'zoox(bot|app|store|sf|sanfrancisco)',  # likely defensive
    r'zoox(airbot|cargobot|dropbot|exobot|mobot|solbot)',  # product speculative
    r'zooxbest',
    
    # False positives - customer domains with amazon-ish strings
    r'ring\.(ch|es|gr|it|fr)',  # compring.es contains "ring"
    r'spring',  # dorothyspring.es
    r'fire\.(ch|es|gr|it|fr|iq)',  # getfire.ch, mazaya-fire.iq
    r'prime\.(ch|es|gr|it|fr)',  # wpprime.es
    r'echo\.(ch|es|gr|it|fr)',  # luxecho.gr
    r'alex\.',  # infoalex, klimalex, bigalex
    r'lex[^a-z]',  # laborlex, lex-media
    r'paws',  # pawspaleochora
    r'catering',
    r'carsharing',
    r'engineering',
    r'darzalex',  # J&J drug
    r'gruering',
    r'promocatering',
    r'shahrzad',
    r'coredat',  # redirect destination
    r'assistonemedical',  # one medical defensive
    r'cloudfront\.(me)',  # defensive cloudfront
    r'nozooxhere',
    r'ridezoox',
    
    # More false positives
    r'badzoox',
    r'actorsimdb',
    r'cloudfrontstreaming',
    r'inglesprimero',  # "English first" Spanish site
    r'mzdyamazon',  # Czech site
    r'safebrowse\.io',  # warning page redirect
    
    # Zoox product speculative domains
    r'zoox(auto|car|data|labs|mobility|driverless|y)\.',
    r'zooxcandrive',
    r'zooxautomation',
]

# Patterns to KEEP (real products/acquisitions)
KEEP_PATTERNS = [
    r'^zoox\.com$',  # Main Zoox domain
    r'^fauna\.',
    r'^umbra3d\.',
    r'^inlt\.',
    r'^dbbest\.',
    r'^viziotix\.',
    r'^pillpack\.',
    r'^woot\.',
    r'^newworld\.',
    r'^blazegraph\.',
    r'^bluage\.',
    r'^partiql\.',
    r'^runfinch\.',
]

def is_defensive(domain):
    """Check if domain is a defensive registration."""
    domain_lower = domain.lower()
    
    # Check if it's a known good domain first
    for pattern in KEEP_PATTERNS:
        if re.search(pattern, domain_lower):
            return False
    
    # Check defensive patterns
    for pattern in DEFENSIVE_PATTERNS:
        if re.search(pattern, domain_lower):
            return True
    
    return False

def main():
    input_file = "amazon_domains_unique.csv"
    
    kept = []
    filtered = []
    
    with open(input_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row['domain']
            
            if is_defensive(domain):
                filtered.append(domain)
            else:
                kept.append(row)
    
    print(f"=== FINAL CLEANUP ===")
    print(f"Input domains: {len(kept) + len(filtered)}")
    print(f"Defensive registrations removed: {len(filtered)}")
    print(f"Final unique domains: {len(kept)}")
    
    # Save final list
    with open("amazon_acquisitions_final.txt", "w") as f:
        for item in sorted(kept, key=lambda x: x['domain']):
            f.write(f"{item['domain']}\n")
    
    with open("amazon_acquisitions_final.csv", "w") as f:
        f.write("domain,http_status,https_status,redirect_url\n")
        for item in sorted(kept, key=lambda x: x['domain']):
            redirect = item['redirect_url'].replace(",", ";") if item['redirect_url'] else ""
            f.write(f"{item['domain']},{item['http_status']},{item['https_status']},{redirect}\n")
    
    print(f"\nFiles saved:")
    print(f"  amazon_acquisitions_final.txt - {len(kept)} domains")
    print(f"  amazon_acquisitions_final.csv - Same with details")
    
    print(f"\n=== FINAL DOMAINS ({len(kept)}) ===")
    for item in sorted(kept, key=lambda x: x['domain']):
        redirect = f" -> {item['redirect_url'][:50]}..." if item['redirect_url'] and len(item['redirect_url']) > 50 else (f" -> {item['redirect_url']}" if item['redirect_url'] else "")
        print(f"  {item['domain']}{redirect}")
    
    print(f"\n=== REMOVED DEFENSIVE DOMAINS ({len(filtered)}) ===")
    for d in sorted(filtered):
        print(f"  {d}")

if __name__ == "__main__":
    main()
