#!/usr/bin/env python3
"""
Broaden the reverse-WHOIS search for accounts that came back empty under
registrant-organization matching. We try several alternative signals:

  - RegistrantContact.Email  contains "@<corp email domain>"   (high precision)
  - RegistrantContact.Name   contains "<brand>"
  - DomainName               contains "<brand keyword>"        (broad, may include typosquats)
  - basic full-text include  ["<brand>"]                       (broadest)
  - RegistrantContact.Organization contains "<alt entity>"

Usage:
  python3 broaden_empty.py --preview      # FREE: counts for every strategy
  python3 broaden_empty.py --fetch        # purchase + merge selected strategies
"""
import argparse
import csv
import json
import time
import urllib.request
from pathlib import Path

from apex_domain_search import apex_domains, slugify, OUTPUT_ROOT

API_URL = "https://reverse-whois.whoisxmlapi.com/api/v2"
API_KEY = "at_AqNT93oHzOA9awbHMCfqqE0jUjdjh"
SKIP_ABOVE = 9999  # capped API result = registry/customer noise

# Per account: list of strategies. Each strategy is a dict:
#   {"label", "field", "term", "exact"}      -> advancedSearchTerms
#   {"label", "basic": ["a", "b"]}            -> basicSearchTerms include
STRATEGIES = {
    "Front Gate Tickets": [
        {"label": "email @frontgatetickets.com", "field": "RegistrantContact.Email", "term": "@frontgatetickets.com", "exact": False},
        {"label": "name Front Gate", "field": "RegistrantContact.Name", "term": "Front Gate", "exact": False},
        {"label": "domain 'frontgate'", "field": "DomainName", "term": "frontgate", "exact": False},
        {"label": "basic [Front Gate Tickets]", "basic": ["Front Gate Tickets"]},
    ],
    "NBCUniversal Media, Inc.": [
        {"label": "email @nbcuni.com", "field": "RegistrantContact.Email", "term": "@nbcuni.com", "exact": False},
        {"label": "email @nbcuniversal.com", "field": "RegistrantContact.Email", "term": "@nbcuniversal.com", "exact": False},
        {"label": "domain 'nbcuni'", "field": "DomainName", "term": "nbcuni", "exact": False},
    ],
    "Nirvana Insurance": [
        {"label": "email @nirvanatech.com", "field": "RegistrantContact.Email", "term": "@nirvanatech.com", "exact": False},
        {"label": "org Nirvana Tech", "field": "RegistrantContact.Organization", "term": "Nirvana Tech", "exact": False},
        {"label": "domain 'nirvanatech'", "field": "DomainName", "term": "nirvanatech", "exact": False},
        {"label": "domain 'nirvana-insurance'", "field": "DomainName", "term": "nirvana-insurance", "exact": False},
    ],
    "Nucleus Security": [
        {"label": "org Nucleus Security", "field": "RegistrantContact.Organization", "term": "Nucleus Security", "exact": False},
        {"label": "basic [Nucleus Security]", "basic": ["Nucleus Security"]},
    ],
    "On Location Experiences companies": [
        {"label": "org On Location Experiences", "field": "RegistrantContact.Organization", "term": "On Location Experiences", "exact": False},
        {"label": "basic [On Location Experiences]", "basic": ["On Location Experiences"]},
    ],
    "Poetic Digital, LLC": [
        {"label": "email @poetic.io", "field": "RegistrantContact.Email", "term": "@poetic.io", "exact": False},
        {"label": "email @poeticsystems.com", "field": "RegistrantContact.Email", "term": "@poeticsystems.com", "exact": False},
        {"label": "org Poetic Systems", "field": "RegistrantContact.Organization", "term": "Poetic Systems", "exact": False},
        {"label": "domain 'poeticsystems'", "field": "DomainName", "term": "poeticsystems", "exact": False},
    ],
    "Qualified.com, Inc.": [
        {"label": "basic [Qualified.com]", "basic": ["Qualified.com"]},
        {"label": "name Qualified", "field": "RegistrantContact.Name", "term": "Qualified", "exact": False},
        {"label": "org Qualified, Inc", "field": "RegistrantContact.Organization", "term": "Qualified, Inc", "exact": False},
    ],
}


def query(strategy: dict, preview: bool) -> dict:
    payload = {
        "apiKey": API_KEY,
        "searchType": "current",
        "mode": "preview" if preview else "purchase",
        "punycode": True,
    }
    if "basic" in strategy:
        payload["basicSearchTerms"] = {"include": strategy["basic"]}
    else:
        payload["advancedSearchTerms"] = [{
            "field": strategy["field"],
            "term": strategy["term"],
            "exactMatch": strategy.get("exact", False),
        }]
    req = urllib.request.Request(
        API_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def run_preview():
    print("=== BROADEN PREVIEW (no credits used) ===\n")
    for account, strats in STRATEGIES.items():
        print(f"# {account}")
        for s in strats:
            try:
                c = query(s, preview=True).get("domainsCount", 0)
                tag = "  <-- noise/capped" if c >= SKIP_ABOVE else ""
                print(f"    {c:>6}  {s['label']}{tag}")
            except Exception as e:
                print(f"    {'ERR':>6}  {s['label']}  ({e})")
            time.sleep(0.4)
        print()


def merge_into(account: str, new_domains_by_source: dict, responses: dict):
    slug = slugify(account)
    folder = OUTPUT_ROOT / slug
    folder.mkdir(parents=True, exist_ok=True)

    sources = {}
    txt = folder / f"{slug}.txt"
    if txt.exists():
        for ln in open(txt):
            d = ln.strip()
            if d:
                sources.setdefault(d, set()).add("primary")
    for src, domains in new_domains_by_source.items():
        for d in domains:
            sources.setdefault(d, set()).add(src)

    domains = sorted(sources)
    with open(folder / f"{slug}.txt", "w") as f:
        for d in domains:
            f.write(d + "\n")
    with open(folder / f"{slug}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["domain", "sources"])
        for d in domains:
            w.writerow([d, "; ".join(sorted(sources[d]))])
    if responses:
        with open(folder / f"{slug}_broadened.json", "w") as f:
            json.dump(responses, f, indent=2)
    return len(domains)


def run_fetch(selected: dict):
    """selected: {account: [strategy_label, ...]} -> purchase + merge those."""
    print("=== BROADEN FETCH (1 credit per strategy) ===\n")
    for account, labels in selected.items():
        strats = {s["label"]: s for s in STRATEGIES.get(account, [])}
        new_by_source = {}
        responses = {}
        for label in labels:
            s = strats.get(label)
            if not s:
                print(f"  ?? unknown strategy '{label}' for {account}")
                continue
            try:
                res = query(s, preview=False)
                responses[label] = res
                new_by_source[label] = apex_domains(res)
                print(f"  +{len(new_by_source[label]):>4}  {account} / {label}")
                time.sleep(0.8)
            except Exception as e:
                print(f"  ERROR {account} / {label}: {e}")
        total = merge_into(account, new_by_source, responses)
        print(f"  => {account}: {total} total apex domains\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    args = ap.parse_args()
    if args.preview:
        run_preview()
    elif args.fetch:
        # Filled in after reviewing preview (see SELECTED below).
        run_fetch(SELECTED)
    else:
        run_preview()


# Strategies chosen after reviewing the free preview (edited before --fetch).
SELECTED = {}


if __name__ == "__main__":
    main()
