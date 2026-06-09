# WhoisXML Apex Domain Search

Tooling to discover, enrich, and validate the **apex (root) domains** owned by a
list of companies, using the [WhoisXMLAPI Reverse WHOIS](https://reverse-whois.whoisxmlapi.com/api)
service. It produces a tidy per-account folder structure (CSV / TXT / raw JSON),
a combined master CSV, and an optional "is the site live?" content check.

> This started as an Amazon-only experiment and grew into a general, reusable
> apex-domain research pipeline for an arbitrary list of accounts.

---

## Table of Contents

- [What this does](#what-this-does)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [The core workflow](#the-core-workflow)
  - [1. Single-account lookup](#1-single-account-lookup-reverse_whoispy)
  - [2. Bulk apex search for many accounts](#2-bulk-apex-search-for-many-accounts-apex_domain_searchpy)
  - [3. Expand with subsidiaries & alternate entities](#3-expand-with-subsidiaries--alternate-entities-expand_accountspy)
  - [4. Broaden empty accounts](#4-broaden-empty-accounts-broaden_emptypy)
  - [5. Combine into a master CSV](#5-combine-into-a-master-csv)
  - [6. Check which sites are live](#6-check-which-sites-are-live-check_sitespy)
- [Output files](#output-files)
- [How matching works (and its limits)](#how-matching-works-and-its-limits)
- [Credits & cost](#credits--cost)
- [Security note about the API key](#security-note-about-the-api-key)
- [Repository layout](#repository-layout)

---

## What this does

Given a list of company names, the pipeline:

1. Queries Reverse WHOIS by **registrant organization** to find apex domains.
2. **Expands** each account with known subsidiaries and alternate legal entity
   names (e.g. Amazon → Audible, Twitch, IMDb, Zappos, ...).
3. **Broadens** accounts that returned nothing by trying registrant email-domain,
   registrant name, and full-text search.
4. Merges everything into per-account folders plus one **master CSV**.
5. Optionally **visits every domain** to record whether real HTML content loads.

---

## Requirements

- **Python 3.9+** (no virtualenv required; only the standard library is needed
  for the WHOIS scripts).
- **`requests`** — only needed for the live-site checker (`check_sites.py`):

```bash
python3 -m pip install requests
```

- A **WhoisXMLAPI** account with **DRS (Domain Research Suite) credits**. The API
  key is read from the `WHOISXML_API_KEY` environment variable
  (see [Security note](#security-note-about-the-api-key)).

Set the key before running any of the WHOIS scripts:

```bash
export WHOISXML_API_KEY="your-whoisxmlapi-key"
```

To persist it across terminal sessions, add that line to your `~/.zshrc` (or
`~/.bashrc`). The scripts exit with a clear error if the variable is not set.

---

## Quick start

```bash
# 1. Preview counts for every account (FREE — uses no credits)
python3 apex_domain_search.py --preview

# 2. Fetch all apex domains (uses ~1 credit per account that has results)
python3 apex_domain_search.py

# 3. (optional) Add subsidiaries + alternate legal entities
python3 expand_accounts.py --preview     # free
python3 expand_accounts.py               # fetch + merge

# 4. (optional) Try harder for accounts that came back empty
python3 broaden_empty.py --preview       # free
#    then edit SELECTED in broaden_empty.py and run:
python3 broaden_empty.py --fetch

# 5. Build the combined master CSV
#    (see "Combine into a master CSV" below)

# 6. (optional) Check which domains actually serve a page
python3 -m pip install requests
python3 check_sites.py --workers 200 --timeout 8
```

> **Always run `--preview` first.** Preview mode is free and shows you the domain
> counts and which org-name spellings actually match before you spend any credits.

---

## The core workflow

### 1. Single-account lookup (`reverse_whois.py`)

The simplest tool — look up one organization.

```bash
# Just the count (free)
python3 reverse_whois.py "Amazon Technologies, Inc." --preview

# Fetch the list and print to stdout (costs 1 credit)
python3 reverse_whois.py "Amazon Technologies, Inc."

# Fetch and save to <name>.txt and <name>.csv
python3 reverse_whois.py "Amazon Technologies, Inc." --output amazon_tech
```

### 2. Bulk apex search for many accounts (`apex_domain_search.py`)

This is the main entry point. The list of accounts lives in the `ACCOUNTS`
array near the top of the file — **edit that list to change who you search for.**

```bash
# FREE preview of counts for every account in ACCOUNTS
python3 apex_domain_search.py --preview

# Full fetch -> writes accounts/<slug>/ with .csv, .txt, .json
python3 apex_domain_search.py

# Run a single account from the list
python3 apex_domain_search.py --only "Turo"

# Use a broad "contains" match instead of exact org match
python3 apex_domain_search.py --nonexact
```

For each account it creates:

```
accounts/<slug>/
├── <slug>.csv     # "domain" column, one apex per row
├── <slug>.txt     # one apex per line
└── <slug>.json    # raw API response
```

By default it uses **exact** registrant-organization matching and automatically
falls back to a **contains** match for accounts that return zero (previews are
free, so the fallback costs nothing extra).

### 3. Expand with subsidiaries & alternate entities (`expand_accounts.py`)

Many companies register domains under subsidiaries or slightly different legal
names. This script merges those into the parent account.

The `EXTRA_TERMS` dict maps each parent account to a list of
`(term, exact)` entities to add (e.g. `"Amazon"` → `Audible, Inc.`,
`Twitch Interactive, Inc.`, `IMDb.com, Inc.`, ...).

```bash
python3 expand_accounts.py --preview     # free: counts for every extra term
python3 expand_accounts.py               # fetch valid terms + merge into parents
```

After expansion, each account CSV gains a **`sources`** column showing which
entity each domain came from (`primary`, or the subsidiary/entity name), and a
`<slug>_expanded.json` with the combined raw responses.

Two safety mechanisms:

- **`SKIP_ABOVE`** — terms whose preview count hits the API's 10,000 cap are
  treated as registrar/registry "customer" noise and skipped.
- **`EXCLUDE`** — an explicit set of `(account, term)` pairs that should *not* be
  merged (e.g. don't dump a parent conglomerate like `Hearst Communications`
  into the child-brand `Car and Driver` account).

### 4. Broaden empty accounts (`broaden_empty.py`)

For accounts that still return nothing, this tries alternative WHOIS signals:

- `RegistrantContact.Email` contains `@<corp-domain>` (high precision)
- `RegistrantContact.Name` contains the brand
- `basicSearchTerms` full-text include
- looser `RegistrantContact.Organization` contains

```bash
python3 broaden_empty.py --preview       # free: counts for every strategy
```

Review the preview, then list the strategies worth buying in the `SELECTED`
dict at the bottom of the file and run:

```bash
python3 broaden_empty.py --fetch
```

> **Always inspect broad results before merging.** Generic words ("Qualified",
> "Nucleus", "On Location") pull in unrelated companies. Purchase the list, look
> at the actual domains, and keep only the ones you can verify are owned by the
> target. Recovered domains are written with a `<slug>_broadened.json` audit file.

### 5. Combine into a master CSV

Combine every per-account CSV into one navigable file with an `account` column.
Run this one-off snippet from the project root:

```bash
python3 - <<'PY'
import csv
from pathlib import Path
from apex_domain_search import ACCOUNTS, slugify

root = Path("accounts")
rows, summary = [], []
for account in ACCOUNTS:
    slug = slugify(account)
    p = root / slug / f"{slug}.csv"
    n = 0
    if p.exists():
        for r in csv.DictReader(open(p, newline="")):
            d = (r.get("domain") or "").strip()
            if d:
                rows.append((account, d, (r.get("sources") or "primary").strip()))
                n += 1
    summary.append((account, n))

rows.sort(key=lambda x: (x[0].lower(), x[1]))
with open("master_apex_domains.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["account", "domain", "sources"]); w.writerows(rows)
with open("master_summary.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["account", "apex_domain_count"]); w.writerows(summary)
print(f"{len(rows)} rows across {len(ACCOUNTS)} accounts")
PY
```

Produces:

- **`master_apex_domains.csv`** — `account, domain, sources` for every domain.
- **`master_summary.csv`** — `account, apex_domain_count`.

### 6. Check which sites are live (`check_sites.py`)

Visits every domain in `master_apex_domains.csv`, follows redirects, and records
whether a real page loaded (HTTP < 400 with a body), the page title, byte size,
and any error.

```bash
python3 -m pip install requests
python3 check_sites.py --workers 200 --timeout 8
```

- **Resumable** — results are written incrementally to `site_check_results.csv`;
  re-running skips domains already checked.
- Tune `--workers` (concurrency) and `--timeout` (seconds) to taste.

Then build a filtered "live only" list:

```bash
python3 - <<'PY'
import csv
truthy = lambda v: str(v).strip().lower() == "true"
live = [r for r in csv.DictReader(open("site_check_results.csv", newline="")) if truthy(r["content_loaded"])]
live.sort(key=lambda r: (r["account"].lower(), r["domain"]))
with open("live_domains.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["account","domain","status","final_url","title","content_bytes","has_html"])
    for r in live:
        w.writerow([r["account"], r["domain"], r["status"], r["final_url"], r["title"], r["content_bytes"], r["has_html"]])
print(f"{len(live)} live domains")
PY
```

---

## Output files

| File / folder | Description |
|---|---|
| `accounts/<slug>/<slug>.csv` | Apex domains for one account (`domain`, `sources`). |
| `accounts/<slug>/<slug>.txt` | Same domains, one per line. |
| `accounts/<slug>/<slug>.json` | Raw primary API response. |
| `accounts/<slug>/<slug>_expanded.json` | Raw responses for subsidiary/alt-entity terms. |
| `accounts/<slug>/<slug>_broadened.json` | Audit of broadened-search recoveries. |
| `accounts/<slug>/<slug>_related.json` | Forward-WHOIS / cert-transparency findings. |
| `master_apex_domains.csv` | All accounts combined (`account`, `domain`, `sources`). |
| `master_summary.csv` | Per-account apex counts. |
| `site_check_results.csv` | Per-domain live-site check results. |
| `site_check_summary.csv` | Per-account live-site counts. |
| `live_domains.csv` | Filtered list of only the domains that served content. |

---

## How matching works (and its limits)

The search matches on the **registrant organization** field in WHOIS records.
That means results depend on how a company filled in its WHOIS registrant data:

- **Exact match** (default) is precise but misses records under slightly
  different legal-entity spellings.
- **Contains match** is broader but pulls in unrelated companies that share a
  generic word — always verify.
- **Privacy/proxy protected** domains (Domains By Proxy, Withheld for Privacy,
  Squarespace/GoDaddy privacy, etc.) hide the registrant org, so they won't be
  found by org search at all. For these, `broaden_empty.py` plus forward-WHOIS /
  certificate-transparency (`crt.sh`) lookups are the fallback.
- The API caps a single query at **10,000** domains; a capped result almost
  always means the entity is a registrar/registry appearing on other people's
  domains, not a brand portfolio.

---

## Credits & cost

- **Preview mode (`--preview`) is always free** and does not consume credits.
- A **fetch/purchase consumes ~1 DRS credit per query that returns results.**
- The bulk and expand scripts preview first and only purchase when a preview
  shows matches, so empty queries cost nothing.

---

## Security note about the API key

The WhoisXMLAPI key is **not stored in the code**. Every script reads it from the
`WHOISXML_API_KEY` environment variable at runtime, so no secret is committed to
this repository.

```bash
export WHOISXML_API_KEY="your-whoisxmlapi-key"
```

Tips:

- Keep the key in your shell profile (`~/.zshrc`) or a local `.env` file that is
  git-ignored — never commit real values.
- If the key was ever exposed (e.g. in earlier git history), rotate it in your
  WhoisXMLAPI dashboard.

---

## Repository layout

```
.
├── README.md
├── reverse_whois.py          # single-account lookup
├── apex_domain_search.py     # bulk apex search (main entry point; edit ACCOUNTS)
├── expand_accounts.py        # merge subsidiaries / alternate legal entities
├── broaden_empty.py          # broaden search for empty accounts
├── check_sites.py            # visit domains, detect live HTML content
├── bulk_reverse_whois.py     # (legacy) Amazon-org bulk fetch
├── bulk_reverse_whois_core.py# (legacy) core-Amazon-org bulk fetch
├── filter_*.py               # (legacy) Amazon typosquat/redirect filters
├── accounts/                 # generated: per-account CSV/TXT/JSON
├── master_apex_domains.csv   # generated: combined master list
├── master_summary.csv        # generated: per-account counts
├── site_check_results.csv    # generated: live-site results
└── live_domains.csv          # generated: live-only filtered list
```
