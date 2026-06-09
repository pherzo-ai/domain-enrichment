#!/usr/bin/env python3
"""
Expand each account's apex-domain list with alternate legal entities and
subsidiaries, then merge everything into the parent account's folder.

Workflow:
    python3 expand_accounts.py --preview     # FREE: show counts for every extra term
    python3 expand_accounts.py               # fetch valid terms + merge into parents

For each account we keep the domains already fetched (loaded from the existing
accounts/<slug>/<slug>.txt) and add domains from the extra terms below. Output
per account folder is rewritten in a unified format:
    <slug>.csv   -> columns: domain, sources   (sources = ; separated org terms)
    <slug>.txt   -> one apex domain per line
    <slug>.json  -> primary response (unchanged, kept as-is if present)
    <slug>_expanded.json -> combined per-term responses for the extra entities

Terms are (term, exact) tuples. Terms whose preview count is >= SKIP_ABOVE are
treated as registrar/registry "customer" noise and are skipped during fetch
(still reported), since no single company in this list legitimately owns that
many apex domains.
"""
import argparse
import csv
import json
import time
from pathlib import Path

from apex_domain_search import query, apex_domains, slugify, OUTPUT_ROOT

SKIP_ABOVE = 9999  # the API caps preview at 10000; a capped count is always registry noise

# Explicit (account, term) pairs to exclude:
#  - registrar/registry "customer" noise (entity appears as registrant on others' domains)
#  - parent conglomerates that should NOT be merged into a child-brand sub-account
EXCLUDE = {
    ("Amazon", "Amazon.com, Inc."),                                  # registry/customer noise
    ("Universal Parks & Resorts", "NBCUniversal Media, LLC"),        # capped noise
    ("NBCUniversal Media, Inc.", "NBCUniversal Media, LLC"),         # capped noise
    ("NBCUniversal Media, Inc.", "NBCUniversal"),                    # capped noise
    ("Car and Driver", "Hearst Communications, Inc."),               # parent conglomerate
    ("Car and Driver", "Hearst Magazines"),                          # sibling-brand portfolio
    ("SoulCycle", "Equinox Holdings, Inc."),                         # parent of SoulCycle
    ("Spoonflower", "Shutterfly, LLC"),                              # parent of Spoonflower
    ("C3 Presents, LLC", "Live Nation Entertainment, Inc."),         # parent conglomerate
    ("McGraw Hill", "McGraw-Hill"),                                  # broad match -> S&P noise
}

# Parent account -> list of EXTRA (term, exact) entities to merge in.
# These are alternate legal entity names and known subsidiaries (best effort).
EXTRA_TERMS = {
    "Egnyte, Inc": [("Egnyte, Inc.", True), ("Egnyte", False)],
    "LegalShield": [("Pre-Paid Legal Services, Inc.", True), ("PPLSI, LLC", True),
                    ("Pre-Paid Legal Services", False)],
    "Jitterbit": [("Jitterbit, Inc.", True), ("Jitterbit", False)],
    "ShipBob": [("ShipBob, Inc.", True), ("ShipBob", False)],
    "Symphony": [("Symphony Communication Services, LLC", True),
                 ("Symphony Communication Services Holdings LLC", True)],
    "Gainsight": [("Gainsight, Inc.", True), ("Gainsight", False)],
    "Integral Ad Science": [("Integral Ad Science, Inc.", True)],
    "Flywire Corporation": [("Flywire", False), ("peerTransfer Corporation", True)],
    "TaskRabbit, Inc.": [("TaskRabbit", False)],
    "Khoros": [("Khoros, LLC", True), ("Lithium Technologies, Inc.", True),
               ("Spredfast, Inc.", True)],
    "Weedmaps": [("Ghost Management Group, LLC", True), ("WM Technology, Inc.", True)],
    "Turo": [("Turo Inc.", True), ("RelayRides, Inc.", True)],
    "Salsify": [("Salsify, Inc.", True)],
    "GoodRx": [("GoodRx, Inc.", True), ("GoodRx Holdings, Inc.", True)],
    "LegalZoom": [("LegalZoom.com, Inc.", True)],
    "MSNBC": [("MSNBC Interactive News, LLC", True), ("MSNBC Cable, LLC", True)],
    "Car and Driver": [("Hearst Communications, Inc.", True), ("Hearst Magazines", False)],
    "Insurance Office of America Inc": [("Insurance Office of America", False)],
    "SoulCycle": [("SoulCycle Inc.", True), ("Equinox Holdings, Inc.", True)],
    "Universal Parks & Resorts": [("Universal City Studios LLC", True),
                                  ("Universal City Studios LLLP", True),
                                  ("NBCUniversal Media, LLC", True)],
    "Humana": [("Humana Inc.", True)],
    "American Express": [("American Express Company", True),
                         ("American Express Travel Related Services Company, Inc.", True)],
    "Southwest Airlines": [("Southwest Airlines Co.", True)],
    "ServiceTitan": [("ServiceTitan, Inc.", True)],
    "NBCUniversal Media, Inc.": [("NBCUniversal Media, LLC", True), ("NBCUniversal", False)],
    "Citi": [("Citigroup Inc.", True), ("Citibank, N.A.", True), ("Citigroup", False)],
    "AAA National": [("American Automobile Association, Inc.", True), ("AAA National", False)],
    "Moody's Corporation": [("Moody's Analytics, Inc.", True),
                            ("Moody's Investors Service, Inc.", True), ("Moody's", False)],
    "McGraw Hill": [("McGraw Hill LLC", True), ("McGraw-Hill", False),
                    ("McGraw Hill Education", False)],
    "Amazon": [("Amazon.com, Inc.", True), ("Amazon Web Services, Inc.", True),
               ("Audible, Inc.", True), ("Twitch Interactive, Inc.", True),
               ("IMDb.com, Inc.", True), ("A9.com, Inc.", True), ("Goodreads, Inc.", True),
               ("Zappos IP, Inc.", True), ("Whole Foods Market, Inc.", True),
               ("Ring LLC", True), ("eero LLC", True), ("Zoox, Inc.", True),
               ("PillPack LLC", True), ("Wondery, Inc.", True), ("One Medical", False),
               ("MGM Holdings Inc.", True), ("Kuiper Systems LLC", True)],
    "Anthropic, PBC": [("Anthropic", False)],
    "Confluent, Inc.": [("Confluent", False)],
    "On Location Experiences companies": [("On Location Experiences, Inc.", True),
                                          ("On Location Events, LLC", True),
                                          ("Endeavor Group Holdings, Inc.", True)],
    "UFC": [("Zuffa, LLC", True), ("Ultimate Fighting Championship", False)],
    "C3 Presents, LLC": [("C3 Presents", False), ("Live Nation Entertainment, Inc.", True)],
    "Front Gate Tickets": [("Front Gate Ticketing Solutions, LLC", True),
                           ("Front Gate Tickets", False)],
    "NVIDIA": [("NVIDIA Corporation", True)],
    "Poetic Digital, LLC": [("Poetic Digital", False)],
    "Procter & Gamble": [("The Procter & Gamble Company", True), ("Procter & Gamble", False)],
    "Rakuten Symphony Singapore Pte. Ltd.": [("Rakuten Symphony", False)],
    "Rakuten": [("Rakuten, Inc.", True), ("Rakuten Group, Inc.", True),
                ("Rakuten Rewards", False), ("Ebates Inc.", True)],
    "OwnData": [("OwnBackup, Inc.", True), ("Own Company", False)],
    "Salesforce Inc on behalf of Slack Technologies LLC": [("Slack Technologies, LLC", True),
                                                           ("Slack Technologies, Inc.", True),
                                                           ("Slack", False)],
    "Qualified.com, Inc.": [("Qualified.com", False)],
    "Salesforce": [("Salesforce.com, Inc.", True), ("salesforce.com, inc.", True),
                   ("Tableau Software, LLC", True), ("MuleSoft, LLC", True)],
    "Spin Master, Ltd.": [("Spin Master Ltd.", True), ("Spin Master Corp.", True)],
    "Starbucks": [("Starbucks Corporation", True), ("Starbucks Coffee Company", False)],
    "WayUp": [("WayUp, Inc.", True)],
    "Spoonflower": [("Spoonflower, Inc.", True), ("Shutterfly, LLC", True)],
    "LoanStream Mortgage": [("OCMBC, Inc.", True), ("LoanStream", False)],
    "ProShip Inc": [("ProShip, Inc.", True), ("ProShip", False)],
    "Expensify": [("Expensify, Inc.", True)],
    "Cube Software": [("Cube Planning, Inc.", True)],
    "Patient IQ": [("PatientIQ, Inc.", True), ("PatientIQ", False)],
    "Fiddler": [("Fiddler AI", False), ("Fiddler Labs, Inc.", True)],
    "Smartcar": [("Smartcar, Inc.", True)],
    "Nucleus Security": [("Nucleus Security, Inc.", True)],
    "Northern Bank & Trust Company": [("Northern Bank", False)],
    "Nirvana Insurance": [("Nirvana Technology, Inc.", True)],
    "iDrive Logistics": [("iDrive Logistics", False), ("ShipCaddie", False)],
    "Fireworks AI": [("Fireworks AI, Inc.", True)],
    "Coastal Debt": [("Coastal Debt Resolve", False), ("Coastal Debt Relief", False)],
    "The Sporting News": [("Sporting News Holdings", False), ("The Sporting News", False)],
}


def existing_domains(account: str) -> list:
    slug = slugify(account)
    txt = OUTPUT_ROOT / slug / f"{slug}.txt"
    if not txt.exists():
        return []
    with open(txt) as f:
        return [ln.strip() for ln in f if ln.strip()]


def run_preview():
    print("=== EXPANSION PREVIEW (no credits used) ===\n")
    flagged = []
    for account, terms in EXTRA_TERMS.items():
        print(f"# {account}")
        for term, exact in terms:
            try:
                count = query(term, preview=True, exact=exact).get("domainsCount", 0)
                mode = "exact" if exact else "contains"
                tag = ""
                if count >= SKIP_ABOVE:
                    tag = "  <-- SKIP (registry/customer noise)"
                    flagged.append((account, term, count))
                print(f"    {count:>6}  [{mode:>8}]  {term}{tag}")
            except Exception as e:
                print(f"    {'ERR':>6}              {term}  ({e})")
            time.sleep(0.35)
        print()
    if flagged:
        print("=== Flagged (skipped on fetch) ===")
        for a, t, c in flagged:
            print(f"  {c:>6}  {t}  ({a})")


def write_merged(account: str, sources_by_domain: dict, expanded_responses: dict):
    slug = slugify(account)
    folder = OUTPUT_ROOT / slug
    folder.mkdir(parents=True, exist_ok=True)

    domains = sorted(sources_by_domain)

    with open(folder / f"{slug}.txt", "w") as f:
        for d in domains:
            f.write(d + "\n")

    with open(folder / f"{slug}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["domain", "sources"])
        for d in domains:
            w.writerow([d, "; ".join(sorted(sources_by_domain[d]))])

    if expanded_responses:
        with open(folder / f"{slug}_expanded.json", "w") as f:
            json.dump(expanded_responses, f, indent=2)

    return len(domains)


def run_fetch():
    print("=== EXPANSION FETCH (1 credit per new term with results) ===\n")
    summary = []
    for account, terms in EXTRA_TERMS.items():
        sources = {}
        for d in existing_domains(account):
            sources.setdefault(d, set()).add("primary")
        base = len(sources)

        expanded = {}
        added_terms = []
        for term, exact in terms:
            if (account, term) in EXCLUDE:
                print(f"  [excluded]   {account} / {term}")
                continue
            try:
                count = query(term, preview=True, exact=exact).get("domainsCount", 0)
                if count == 0:
                    continue
                if count >= SKIP_ABOVE:
                    print(f"  [skip noise] {term}: {count} (>= {SKIP_ABOVE})")
                    continue
                res = query(term, preview=False, exact=exact)
                expanded[term] = res
                for d in apex_domains(res):
                    sources.setdefault(d, set()).add(term)
                added_terms.append((term, count))
                time.sleep(0.8)
            except Exception as e:
                print(f"  ERROR {account} / {term}: {e}")

        total = write_merged(account, sources, expanded)
        gained = total - base
        note = ", ".join(t for t, _ in added_terms) if added_terms else "no new sources"
        print(f"{total:>6} total (+{gained:>4})  {account}   [{note}]")
        summary.append((account, base, total, gained))

    print(f"\n{'='*60}\nSUMMARY (base -> total, +gained)")
    grand = 0
    for account, base, total, gained in summary:
        grand += total
        print(f"  {base:>5} -> {total:>5}  (+{gained:>4})  {account}")
    print(f"\nGrand total apex domains across expanded accounts: {grand:,}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="Preview counts only (free)")
    args = ap.parse_args()
    if args.preview:
        run_preview()
    else:
        run_fetch()


if __name__ == "__main__":
    main()
