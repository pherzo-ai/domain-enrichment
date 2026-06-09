#!/usr/bin/env python3
"""
Visit every apex domain in master_apex_domains.csv and record whether a page
with real HTML content loads.

For each domain we try https:// first, then http://, follow redirects, and read
up to ~60KB of the body to detect HTML and a <title>. Results are written
incrementally to site_check_results.csv so the run is resumable (re-running
skips domains already recorded).

Usage:
    python3 check_sites.py [--workers N] [--timeout S]

Output columns:
    account, domain, scheme_used, status, final_url, content_bytes,
    has_html, title, content_loaded, error
"""
import argparse
import csv
import re
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings("ignore")
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Shared session: no retries, large connection pool (much faster on dead hosts).
SESSION = requests.Session()
_adapter = HTTPAdapter(pool_connections=256, pool_maxsize=256, max_retries=0)
SESSION.mount("http://", _adapter)
SESSION.mount("https://", _adapter)

INPUT = "master_apex_domains.csv"
OUTPUT = "site_check_results.csv"
MAX_BYTES = 60000
TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
HTML_RE = re.compile(rb"<html|<!doctype html|<body|<head", re.IGNORECASE)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

write_lock = threading.Lock()
counter_lock = threading.Lock()
done_count = 0


def fetch(domain, timeout):
    last_err = ""
    connect_to = min(timeout, 5.0)
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        try:
            with SESSION.get(url, headers=HEADERS, timeout=(connect_to, timeout),
                             stream=True, allow_redirects=True, verify=False) as r:
                chunk = b""
                for part in r.iter_content(chunk_size=8192):
                    chunk += part
                    if len(chunk) >= MAX_BYTES:
                        break
                title = ""
                m = TITLE_RE.search(chunk)
                if m:
                    title = m.group(1).decode("utf-8", "ignore")
                    title = re.sub(r"\s+", " ", title).strip()[:200]
                has_html = bool(HTML_RE.search(chunk))
                clen = len(chunk)
                loaded = (r.status_code < 400) and (clen > 0)
                return {
                    "scheme_used": scheme, "status": r.status_code,
                    "final_url": r.url, "content_bytes": clen,
                    "has_html": has_html, "title": title,
                    "content_loaded": loaded, "error": "",
                }
        except requests.exceptions.SSLError as e:
            last_err = f"SSL:{type(e).__name__}"
            continue
        except requests.exceptions.ConnectTimeout:
            last_err = "ConnectTimeout"
        except requests.exceptions.ReadTimeout:
            last_err = "ReadTimeout"
        except requests.exceptions.ConnectionError as e:
            last_err = f"ConnError:{type(e.args[0]).__name__ if e.args else 'x'}"
        except requests.exceptions.TooManyRedirects:
            last_err = "TooManyRedirects"
        except Exception as e:
            last_err = f"{type(e).__name__}"
    return {
        "scheme_used": "", "status": "", "final_url": "", "content_bytes": 0,
        "has_html": False, "title": "", "content_loaded": False, "error": last_err,
    }


def worker(account, domain, timeout, total):
    global done_count
    res = fetch(domain, timeout)
    row = [account, domain, res["scheme_used"], res["status"], res["final_url"],
           res["content_bytes"], res["has_html"], res["title"],
           res["content_loaded"], res["error"]]
    with write_lock:
        with open(OUTPUT, "a", newline="") as f:
            csv.writer(f).writerow(row)
    with counter_lock:
        done_count += 1
        if done_count % 250 == 0:
            print(f"  ...{done_count}/{total} checked", flush=True)
    return res["content_loaded"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=80)
    ap.add_argument("--timeout", type=float, default=12.0)
    args = ap.parse_args()

    with open(INPUT, newline="") as f:
        tasks = [(r["account"], r["domain"]) for r in csv.DictReader(f) if r.get("domain")]

    done = set()
    try:
        with open(OUTPUT, newline="") as f:
            for r in csv.DictReader(f):
                if r.get("domain"):
                    done.add(r["domain"])
    except FileNotFoundError:
        with open(OUTPUT, "w", newline="") as f:
            csv.writer(f).writerow(["account", "domain", "scheme_used", "status",
                                    "final_url", "content_bytes", "has_html",
                                    "title", "content_loaded", "error"])

    todo = [(a, d) for a, d in tasks if d not in done]
    total = len(todo)
    print(f"Total domains: {len(tasks)} | already done: {len(done)} | to check: {total}")
    if not total:
        print("Nothing to do.")
        return

    loaded = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(worker, a, d, args.timeout, total) for a, d in todo]
        for fut in as_completed(futures):
            try:
                if fut.result():
                    loaded += 1
            except Exception:
                pass

    print(f"\nDONE. {loaded}/{total} loaded content this run. Results in {OUTPUT}")


if __name__ == "__main__":
    main()
