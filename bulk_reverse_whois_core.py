#!/usr/bin/env python3
"""
Bulk reverse WHOIS lookup for CORE Amazon organizations only.
Excludes registrar/registry entities that show customer domains.
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

# CORE Amazon organizations (excludes registrar/registry services)
AMAZON_CORE_ORGS = [
    "Amazon Technologies, Inc.",
    "Amazon.com, Inc.",
    "Amazon Web Services, Inc.",
    "Amazon.com Services LLC",
    # Subsidiaries
    "Audible, Inc.",
    "Zappos IP, Inc.",
    "Twitch Interactive, Inc.",
    "IMDb.com, Inc.",
    "A9.com, Inc.",
    "Zoox, Inc.",
    "PillPack LLC",
    "Wondery LLC",
    "Whole Foods Market, Inc.",
    "One Medical",
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
        
        for org in AMAZON_CORE_ORGS:
            try:
                result = query_org(org, preview=True)
                count = result.get('domainsCount', 0)
                if count > 0:
                    print(f"{org}: {count:,} domains")
                    total_domains += count
                time.sleep(0.5)
            except Exception as e:
                print(f"{org}: ERROR - {e}")
        
        print(f"\n=== TOTAL (with duplicates): {total_domains:,} domains ===")
        return
    
    # Full mode
    print("=== FETCHING CORE AMAZON DOMAINS ===\n")
    all_domains = set()
    
    for org in AMAZON_CORE_ORGS:
        try:
            preview = query_org(org, preview=True)
            count = preview.get('domainsCount', 0)
            
            if count == 0:
                print(f"{org}: 0 domains (skipped)")
                continue
            
            print(f"{org}: {count:,} domains - fetching...", end=" ", flush=True)
            result = query_org(org, preview=False)
            domains = result.get('domainsList', [])
            
            before = len(all_domains)
            all_domains.update(domains)
            new = len(all_domains) - before
            print(f"got {len(domains)}, {new} new unique")
            
            time.sleep(1)
        except Exception as e:
            print(f"{org}: ERROR - {e}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Total unique domains: {len(all_domains):,}")
    
    with open("amazon_core_orgs_raw.txt", "w") as f:
        for d in sorted(all_domains):
            f.write(f"{d}\n")
    
    print(f"Saved to amazon_core_orgs_raw.txt")

if __name__ == "__main__":
    main()
