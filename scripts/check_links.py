"""
check_links.py — build the link-rot baseline for the repository.

Extracts every http(s) URL from the frozen corpus (paper links, data access
links, code access links — including URLs embedded in the free-text access
notes on "Raw Data" rows), resolves each one, and records the HTTP status and
the date checked.

Status codes are recorded as observed. Publisher domains commonly answer an
automated request with 403 even when the page is live in a browser; those are
labelled BLOCKED rather than DEAD, and are not evidence of link rot.

The recorded verdicts committed to this repository live in data/link_checks.csv,
one row per unique URL. This script merges those recorded verdicts with a fresh
probe, so a checkout can be re-verified with `make check-links` from an
unrestricted network and the diff shows what has decayed since the baseline.

Output: data/link_inventory.csv  (one row per paper x link, with verdicts)
"""

import concurrent.futures as cf
import csv
import datetime as dt
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

URL_RE = re.compile(r"https?://[^\s;,\)\]<>\"']+")
TIMEOUT = 25

# Domains whose automated 403/401 responses reflect bot protection, not rot.
PUBLISHER_HINTS = (
    "wiley.com", "sciencedirect.com", "academic.oup.com", "oup.com",
    "springer.com", "jstor.org", "tandfonline.com", "sagepub.com",
    "elsevier.com", "ssrn.com", "doi.org", "aeaweb.org",
)

# Hosts that serve a sign-in banner to every automated client, whatever the
# file's actual sharing settings. An automated probe cannot tell a genuinely
# restricted file from a publicly shared one here, so these are never labelled
# RESTRICTED on the strength of a probe — they are BLOCKED until a human looks.
# P80's sheet was mislabelled RESTRICTED on 2026-08-21 for exactly this reason
# and is in fact publicly viewable.
MANUAL_ONLY_HOSTS = (
    "docs.google.com", "drive.google.com", "sheets.google.com",
    "onedrive.live.com", "sharepoint.com", "dropbox.com",
)


def clean(u):
    return u.rstrip(".,;:)]}'\"")


def extract(rows):
    """Return list of (paper_id, field, url, note)."""
    out = []
    for r in rows:
        for field in ("paper_link", "data_link", "code_link"):
            raw = (r[field] or "").strip()
            if not raw:
                continue
            urls = [clean(u) for u in URL_RE.findall(raw)]
            note = URL_RE.sub("", raw).strip(" ;:,-").strip()
            if not urls:
                out.append((r["paper_id"], field, "", raw))
                continue
            for u in urls:
                out.append((r["paper_id"], field, u, note if len(urls) > 1 or note else ""))
    return out


def probe(url):
    """HEAD the URL; fall back to a range-limited GET when HEAD is unsupported.

    No page content is retrieved or stored — only the status line."""
    base = [
        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{url_effective}",
        "--max-time", str(TIMEOUT), "-L",
        "-A", "Mozilla/5.0 (compatible; sustfin-repo link checker)",
    ]
    try:
        p = subprocess.run(base + ["-I", url], capture_output=True, text=True, timeout=TIMEOUT + 10)
        code, _, eff = p.stdout.partition(" ")
        if code in ("000", "403", "405", "501"):
            p = subprocess.run(base + ["-r", "0-0", url], capture_output=True, text=True,
                               timeout=TIMEOUT + 10)
            code, _, eff = p.stdout.partition(" ")
        return code, eff.strip()
    except Exception:
        return "000", ""


def verdict(url, code):
    if any(h in url for h in MANUAL_ONLY_HOSTS):
        return "BLOCKED"
    if code in ("200", "206", "301", "302", "303", "307", "308"):
        return "LIVE"
    if code in ("401", "403"):
        return "BLOCKED" if any(h in url for h in PUBLISHER_HINTS) else "RESTRICTED"
    if code in ("404", "410"):
        return "DEAD"
    if code == "000":
        return "UNREACHABLE"
    return "OTHER"


def load_recorded():
    path = os.path.join(ROOT, "data", "link_checks.csv")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        return {r["url"]: r for r in csv.DictReader(fh)}


def main(probe_live=True):
    recs = json.load(open(os.path.join(ROOT, "data", "sustfin_datasets.json")))
    items = extract(recs)
    urls = sorted({u for _, _, u, _ in items if u})
    recorded = load_recorded()
    print(f"{len(items)} link entries, {len(urls)} unique URLs, "
          f"{len(recorded)} recorded verdicts")

    fresh = {}
    if probe_live:
        with cf.ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(probe, u): u for u in urls}
            for i, f in enumerate(cf.as_completed(futs), 1):
                fresh[futs[f]] = f.result()
                if i % 25 == 0:
                    print(f"  probed {i}/{len(urls)}")

    today = dt.date.today().isoformat()
    path = os.path.join(ROOT, "data", "link_inventory.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["paper_id", "link_type", "url", "access_note",
                    "verdict", "http_status", "check_note", "checked_on",
                    "reprobe_status", "reprobe_verdict", "reprobe_on"])
        for pid, field, url, note in items:
            if not url:
                w.writerow([pid, field, "", note, "NO URL", "", "", "", "", "", ""])
                continue
            rec = recorded.get(url, {})
            code, _eff = fresh.get(url, ("", ""))
            w.writerow([
                pid, field, url, note,
                rec.get("verdict", "NOT CHECKED"),
                rec.get("http_status", ""),
                rec.get("note", ""),
                rec.get("checked_on", ""),
                code,
                verdict(url, code) if code else "",
                today if probe_live else "",
            ])
    print("wrote", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    import sys
    main(probe_live="--no-probe" not in sys.argv)
