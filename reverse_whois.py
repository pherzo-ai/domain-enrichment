#!/usr/bin/env python3
"""
Reverse WHOIS lookup via WhoisXMLAPI.
Usage: python reverse_whois.py "<organization name>" [--preview]
"""
import json
import sys
import argparse
import urllib.request

API_URL = "https://reverse-whois.whoisxmlapi.com/api/v2"
API_KEY = "at_AqNT93oHzOA9awbHMCfqqE0jUjdjh"

def query(org_name: str, preview: bool = False) -> dict:
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
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("org_name", help='Registrant org name, e.g. "Amazon Technologies, Inc."')
    ap.add_argument("--preview", action="store_true", help="Preview count, no credit charge")
    ap.add_argument("--output", help="Base filename for output (without extension)")
    args = ap.parse_args()
    
    result = query(args.org_name, preview=args.preview)
    
    if args.preview:
        print(f"Domains matching: {result.get('domainsCount', 0)}")
        print("Re-run without --preview to fetch the list (costs 1 credit)")
        return
    
    domains = result.get("domainsList", [])
    print(f"# {len(domains)} apex domains found for: {args.org_name}", file=sys.stderr)
    
    if args.output:
        # Write to txt file
        with open(f"{args.output}.txt", "w") as f:
            for d in domains:
                f.write(d + "\n")
        
        # Write to csv file
        with open(f"{args.output}.csv", "w") as f:
            f.write("domain\n")
            for d in domains:
                f.write(d + "\n")
        
        print(f"Saved {len(domains)} domains to {args.output}.txt and {args.output}.csv", file=sys.stderr)
    else:
        for d in domains:
            print(d)

if __name__ == "__main__":
    main()
