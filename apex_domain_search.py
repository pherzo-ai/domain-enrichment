#!/usr/bin/env python3
"""
Apex domain reverse-WHOIS search for a list of accounts.

For each account this script queries the WhoisXMLAPI Reverse WHOIS endpoint
(matching on the registrant organization) and writes a per-account folder
containing:
    - <slug>.json : the raw API response
    - <slug>.txt  : one apex domain per line
    - <slug>.csv  : a "domain" column with one apex domain per line

Usage:
    python3 apex_domain_search.py --preview      # free, just counts
    python3 apex_domain_search.py                # full fetch (1 credit / account)
    python3 apex_domain_search.py --only "Turo"  # run a single account
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

API_URL = "https://reverse-whois.whoisxmlapi.com/api/v2"
API_KEY = os.environ.get("WHOISXML_API_KEY")
if not API_KEY:
    sys.exit("Error: set the WHOISXML_API_KEY environment variable "
             "(e.g. export WHOISXML_API_KEY='your-key').")
OUTPUT_ROOT = Path("accounts")

ACCOUNTS = [
    "Egnyte, Inc",
    "LegalShield",
    "Jitterbit",
    "ShipBob",
    "Symphony",
    "Gainsight",
    "Integral Ad Science",
    "Flywire Corporation",
    "TaskRabbit, Inc.",
    "Khoros",
    "Weedmaps",
    "Turo",
    "Salsify",
    "GoodRx",
    "LegalZoom",
    "Alliant Credit Union",
    "MSNBC",
    "Car and Driver",
    "Insurance Office of America Inc",
    "SoulCycle",
    "Universal Parks & Resorts",
    "Humana",
    "American Express",
    "Southwest Airlines",
    "ServiceTitan",
    "NBCUniversal Media, Inc.",
    "Heartland Dental",
    "Citi",
    "AAA National",
    "Moody's Corporation",
    "McGraw Hill",
    "Amazon",
    "Anthropic, PBC",
    "Confluent, Inc.",
    "On Location Experiences companies",
    "UFC",
    "Cloud Cover Media, Inc.",
    "C3 Presents, LLC",
    "Front Gate Tickets",
    "NVIDIA",
    "Poetic Digital, LLC",
    "Procter & Gamble",
    "Rakuten Symphony Singapore Pte. Ltd.",
    "Rakuten",
    "OwnData",
    "Salesforce Inc on behalf of Slack Technologies LLC",
    "Qualified.com, Inc.",
    "Salesforce",
    "Spin Master, Ltd.",
    "Starbucks",
    "WayUp",
    "Spoonflower",
    "LoanStream Mortgage",
    "ProShip Inc",
    "Expensify",
    "Cube Software",
    "Patient IQ",
    "Klover",
    "Fiddler",
    "Smartcar",
    "Nucleus Security",
    "Northern Bank & Trust Company",
    "Nirvana Insurance",
    "Skyhawk Therapeutics",
    "iDrive Logistics",
    "AirOps",
    "Fireworks AI",
    "Coastal Debt",
    "Caribou",
    "The Sporting News",
]


# Accounts that returned 0 under strict exact registrant-org match
ZERO_ACCOUNTS = [
    "Egnyte, Inc",
    "Jitterbit",
    "ShipBob",
    "Integral Ad Science",
    "Car and Driver",
    "Insurance Office of America Inc",
    "Universal Parks & Resorts",
    "NBCUniversal Media, Inc.",
    "Heartland Dental",
    "AAA National",
    "Moody's Corporation",
    "Anthropic, PBC",
    "On Location Experiences companies",
    "Cloud Cover Media, Inc.",
    "C3 Presents, LLC",
    "Front Gate Tickets",
    "Poetic Digital, LLC",
    "Rakuten Symphony Singapore Pte. Ltd.",
    "OwnData",
    "Salesforce Inc on behalf of Slack Technologies LLC",
    "Qualified.com, Inc.",
    "LoanStream Mortgage",
    "ProShip Inc",
    "Cube Software",
    "Patient IQ",
    "Fiddler",
    "Nucleus Security",
    "Northern Bank & Trust Company",
    "Nirvana Insurance",
    "iDrive Logistics",
    "Coastal Debt",
    "The Sporting News",
]


def slugify(name: str) -> str:
    """Filesystem-safe slug for folder/file names."""
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def query(org_name: str, preview: bool = False, exact: bool = True) -> dict:
    payload = {
        "apiKey": API_KEY,
        "searchType": "current",
        "mode": "preview" if preview else "purchase",
        "punycode": True,
        "advancedSearchTerms": [{
            "field": "RegistrantContact.Organization",
            "term": org_name,
            "exactMatch": exact,
        }],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def apex_domains(result: dict) -> list:
    """Return a sorted, de-duplicated list of apex domains from the response."""
    raw = result.get("domainsList", []) or []
    seen = set()
    out = []
    for item in raw:
        domain = item.get("domainName") if isinstance(item, dict) else item
        if not domain:
            continue
        domain = domain.strip().lower().rstrip(".")
        if domain and domain not in seen:
            seen.add(domain)
            out.append(domain)
    return sorted(out)


def write_outputs(account: str, result: dict, domains: list) -> Path:
    slug = slugify(account)
    folder = OUTPUT_ROOT / slug
    folder.mkdir(parents=True, exist_ok=True)

    with open(folder / f"{slug}.json", "w") as f:
        json.dump(result, f, indent=2)

    with open(folder / f"{slug}.txt", "w") as f:
        for d in domains:
            f.write(d + "\n")

    with open(folder / f"{slug}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["domain"])
        for d in domains:
            writer.writerow([d])

    return folder


def run_preview(accounts, exact=True):
    print("=== PREVIEW MODE (no credits used) ===\n")
    print(f"{'COUNT':>8}  ACCOUNT")
    print(f"{'-----':>8}  -------")
    total = 0
    rows = []
    for acct in accounts:
        try:
            res = query(acct, preview=True, exact=exact)
            count = res.get("domainsCount", 0)
            total += count
            rows.append((acct, count))
            print(f"{count:>8}  {acct}")
        except Exception as e:
            rows.append((acct, None))
            print(f"{'ERR':>8}  {acct}  ({e})")
        time.sleep(0.4)
    print(f"\n{'='*40}")
    print(f"Accounts: {len(accounts)}")
    print(f"Total domains (capped at 10k each): {total:,}")
    zeros = [a for a, c in rows if c == 0]
    if zeros:
        print(f"\n{len(zeros)} account(s) returned 0 (org name may differ from registrant org):")
        for a in zeros:
            print(f"  - {a}")
    return rows


def run_fetch(accounts, exact=True, fallback=True):
    """Fetch domains for each account.

    With fallback=True we first preview using exact registrant-org match; if
    that returns 0 we retry the preview with a contains (non-exact) match. We
    only spend a credit (purchase) when a preview shows results, and we always
    write a folder for every account (empty files when there are no matches).
    """
    print("=== FULL FETCH (1 credit per account with results) ===\n")
    summary = []
    for acct in accounts:
        try:
            use_exact = exact
            count = query(acct, preview=True, exact=use_exact).get("domainsCount", 0)

            if count == 0 and fallback and exact:
                use_exact = False
                count = query(acct, preview=True, exact=use_exact).get("domainsCount", 0)

            if count == 0:
                res = {"domainsCount": 0, "domainsList": []}
                domains = []
                folder = write_outputs(acct, res, domains)
                print(f"{0:>6} domains  ->  {folder}  (no match)")
                summary.append((acct, 0, "none"))
                time.sleep(0.4)
                continue

            res = query(acct, preview=False, exact=use_exact)
            domains = apex_domains(res)
            folder = write_outputs(acct, res, domains)
            mode = "exact" if use_exact else "contains"
            print(f"{len(domains):>6} domains  ->  {folder}  ({mode})")
            summary.append((acct, len(domains), mode))
        except Exception as e:
            print(f"   ERROR  {acct}: {e}")
            summary.append((acct, None, "error"))
        time.sleep(1)

    print(f"\n{'='*50}\nSUMMARY")
    total = 0
    for acct, n, mode in summary:
        if n is None:
            print(f"  ERROR     {acct}")
        else:
            total += n
            print(f"  {n:>5}  [{mode:>8}]  {acct}")
    print(f"\nTotal apex domains written: {total:,}")
    print(f"Output root: {OUTPUT_ROOT.resolve()}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="Preview counts only (free)")
    ap.add_argument("--only", help="Run a single account by exact name from the list")
    ap.add_argument("--nonexact", action="store_true", help="Use contains (non-exact) org match")
    ap.add_argument("--zeros-only", action="store_true", help="Only the accounts that returned 0 under exact match")
    args = ap.parse_args()

    accounts = ACCOUNTS
    if args.only:
        accounts = [a for a in ACCOUNTS if a == args.only]
        if not accounts:
            print(f"No account matching: {args.only}")
            sys.exit(1)
    if args.zeros_only:
        accounts = [a for a in accounts if a in ZERO_ACCOUNTS]

    exact = not args.nonexact
    if args.preview:
        run_preview(accounts, exact=exact)
    else:
        run_fetch(accounts, exact=exact)


if __name__ == "__main__":
    main()
