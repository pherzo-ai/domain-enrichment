#!/usr/bin/env python3
"""
Bulk reverse WHOIS lookup for multiple Amazon organization names.
Combines results and removes duplicates before filtering.
"""
import json
import os
import sys
import urllib.request
import time

API_URL = "https://reverse-whois.whoisxmlapi.com/api/v2"
API_KEY = os.environ.get("WHOISXML_API_KEY")
if not API_KEY:
    sys.exit("Error: set the WHOISXML_API_KEY environment variable "
             "(e.g. export WHOISXML_API_KEY='your-key').")

# Different Amazon organization names to query
AMAZON_ORGS = [
    "Amazon Technologies, Inc.",
    "Amazon.com, Inc.",
    "Amazon Web Services, Inc.",
    "Amazon.com Services LLC",
    "Amazon.com Services, Inc.",
    "Amazon Data Services, Inc.",
    "Amazon Registry Services, Inc.",
    "Audible, Inc.",
    "Whole Foods Market, Inc.",
    "Whole Foods Market IP, L.P.",
    "Ring LLC",
    "Blink Home, Inc.", 
    "Zappos.com, Inc.",
    "Zappos IP, Inc.",
    "Twitch Interactive, Inc.",
    "IMDb.com, Inc.",
    "Goodreads, Inc.",
    "A9.com, Inc.",
    "Amazon Instant Video, Inc.",
    "Amazon Digital Services LLC",
    "Amazon Digital Services, Inc.",
    "Amazon Content Services LLC",
    "Amazon Europe Core S.a.r.l.",
    "Amazon EU S.a.r.l.",
    "Amazon Fulfillment Services, Inc.",
    "Eero LLC",
    "Eero Inc.",
    "MGM Holdings Inc.",
    "Kuiper Systems LLC",
    "Zoox, Inc.",
    "One Medical",
    "1Life Healthcare, Inc.",
    "PillPack LLC",
    "PillPack, Inc.",
    "Wondery LLC",
    "Wondery, Inc.",
]

def query_org(org_name: str, preview: bool = False) -> dict:
    """Query a single organization."""
    payload = {
        "apiKey": API_KEY,
        "searchType": "current",
        "mode": "preview" if preview else "purchase",
        "punycode": True,
        "advancedSearchTerms": [{
            "field": "RegistrantContact.Organization",
            "term": org_name,
            "exactMatch": True
        }]
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())

def main():
    preview_mode = "--preview" in sys.argv
    
    if preview_mode:
        print("=== PREVIEW MODE (no credits used) ===\n")
        total_domains = 0
        
        for org in AMAZON_ORGS:
            try:
                result = query_org(org, preview=True)
                count = result.get('domainsCount', 0)
                if count > 0:
                    print(f"{org}: {count:,} domains")
                    total_domains += count
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"{org}: ERROR - {e}")
        
        print(f"\n=== TOTAL (with duplicates): {total_domains:,} domains ===")
        print("\nNote: Some domains may be registered under multiple orgs.")
        print("Run without --preview to fetch all domains (uses 1 credit per org with results).")
        return
    
    # Full mode - fetch all domains
    print("=== FETCHING ALL DOMAINS ===\n")
    all_domains = set()
    orgs_with_domains = []
    
    for org in AMAZON_ORGS:
        try:
            # First preview to check count
            preview = query_org(org, preview=True)
            count = preview.get('domainsCount', 0)
            
            if count == 0:
                print(f"{org}: 0 domains (skipped)")
                continue
            
            print(f"{org}: {count:,} domains - fetching...", end=" ", flush=True)
            
            # Fetch actual domains
            result = query_org(org, preview=False)
            domains = result.get('domainsList', [])
            
            before = len(all_domains)
            all_domains.update(domains)
            new = len(all_domains) - before
            
            print(f"got {len(domains)}, {new} new unique")
            orgs_with_domains.append((org, len(domains), new))
            
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"{org}: ERROR - {e}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Organizations queried: {len(AMAZON_ORGS)}")
    print(f"Organizations with domains: {len(orgs_with_domains)}")
    print(f"Total unique domains: {len(all_domains):,}")
    
    # Save raw combined list
    with open("amazon_all_orgs_raw.txt", "w") as f:
        for d in sorted(all_domains):
            f.write(f"{d}\n")
    
    print(f"\nSaved to amazon_all_orgs_raw.txt")
    print("Now run filter_comprehensive.py on this file to apply filters.")

if __name__ == "__main__":
    main()
