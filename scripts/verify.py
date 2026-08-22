"""
verify.py — independent check on the built repository.

Recomputes every headline figure straight from the frozen corpus, using its own
parsing rather than the derived table, and asserts that the derived table, the
generated documents and the README all agree with it. A disagreement means the
build is stale or a scoring key changed without the docs being regenerated.

Run with `make verify`. Exits non-zero on any failure.
"""

import collections
import csv
import json
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FAILS = []
CHECKS = [0]


def check(label, got, want):
    CHECKS[0] += 1
    ok = got == want
    if not ok:
        FAILS.append(f"{label}: got {got!r}, expected {want!r}")
    print(f"  [{'ok' if ok else 'FAIL'}] {label}: {got}")


def near(label, got, want, tol=0.005):
    CHECKS[0] += 1
    ok = abs(got - want) <= tol
    if not ok:
        FAILS.append(f"{label}: got {got!r}, expected ~{want!r}")
    print(f"  [{'ok' if ok else 'FAIL'}] {label}: {got:.4f}")


def frozen():
    p = os.path.join(ROOT, "data", "SustFin_Corpus_FINAL.csv")
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    raw = frozen()
    derived = json.load(open(os.path.join(ROOT, "data", "sustfin_datasets.json")))
    stats = json.load(open(os.path.join(ROOT, "data", "stats.json")))
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    catalogue = open(os.path.join(ROOT, "docs", "CATALOGUE.md"), encoding="utf-8").read()
    citations = open(os.path.join(ROOT, "docs", "CITATIONS.md"), encoding="utf-8").read()

    print("\n1. Corpus integrity")
    check("frozen corpus rows", len(raw), 109)
    check("derived table rows", len(derived), 109)
    ids_raw = [r["PAPER ID"].strip() for r in raw]
    ids_der = [r["paper_id"] for r in derived]
    check("paper ids unique in frozen", len(set(ids_raw)), 109)
    check("derived ids match frozen exactly", sorted(ids_der), sorted(ids_raw))
    check("every id appears in the catalogue",
          sum(1 for i in ids_raw if re.search(rf"\|\s*{re.escape(i)}\s*\|", catalogue)), 109)
    check("every id appears in citations",
          sum(1 for i in ids_raw if re.search(rf"\|\s*{re.escape(i)}\s*\|", citations)), 109)
    check("no derived row lost its citation",
          sum(1 for r in derived if not r["citation"]), 0)

    print("\n2. Scores, recomputed independently of derive.py")
    dmap = {"Y": 1.0, "Partial": 0.75, "Raw Data": 0.5, "On Demand": 0.25, "N": 0.0}
    cmap = {"Y": 1.0, "Partial": 0.5, "On Demand": 0.25, "N": 0.0}
    ds = [dmap[r["Data Publicly Available? (Y/N/Partial)"].strip()] for r in raw]
    cs = [cmap[r["Replication Code? (Y/N/Partial)"].strip()] for r in raw]
    os_ = [(a + b) / 2 for a, b in zip(ds, cs)]
    near("mean data score", sum(ds) / len(ds), stats["data_mean"])
    near("mean code score", sum(cs) / len(cs), stats["code_mean"])
    near("mean openness score", sum(os_) / len(os_), stats["open_mean"])
    check("derived scores identical row by row",
          [round(x, 4) for x in os_], [r["openness_score"] for r in derived])

    fully_open = sum(
        1 for r in raw
        if r["Data Publicly Available? (Y/N/Partial)"].strip() == "Y"
        and r["Replication Code? (Y/N/Partial)"].strip() == "Y"
    )
    fully_closed = sum(1 for x in os_ if x == 0.0)
    check("fully open", fully_open, stats["fully_open"])
    check("fully closed", fully_closed, stats["fully_closed"])
    check("fully open == count of Tier 1", fully_open,
          sum(1 for r in derived if r["curation_tier"] == "Tier 1"))

    print("\n3. The openness asymmetry")
    code_only = sum(
        1 for r in raw
        if r["Replication Code? (Y/N/Partial)"].strip() == "Y"
        and r["Data Publicly Available? (Y/N/Partial)"].strip() != "Y"
    )
    data_only = sum(
        1 for r in raw
        if r["Data Publicly Available? (Y/N/Partial)"].strip() == "Y"
        and r["Replication Code? (Y/N/Partial)"].strip() != "Y"
    )
    check("code released without data", code_only, stats["code_y_not_open"])
    check("data released without code", data_only, stats["data_y_not_open"])
    check("code released against no data at all",
          sum(1 for r in raw
              if r["Replication Code? (Y/N/Partial)"].strip() == "Y"
              and r["Data Publicly Available? (Y/N/Partial)"].strip() == "N"),
          stats["unrunnable_code"])

    print("\n4. Licensing exposure")
    LIC = {"Proprietary Database", "Market Data", "Earnings Call transcripts", "News & Media"}
    PUB = {"Official Statistics", "SEC Filings", "Weather & Hazard",
           "Satellite Imagery", "CDP Reports"}

    def cls(r):
        s = {r["Data Source (primary)"].strip(), r["Data Source (secondary)"].strip()} - {""}
        l, p = bool(s & LIC), bool(s & PUB)
        return ("licensed and public" if l and p else "licensed only" if l
                else "public only" if p else "neither")

    groups = collections.defaultdict(list)
    for r, o, d in zip(raw, os_, ds):
        groups[cls(r)].append((o, d))
    for k, v in stats["licensing"].items():
        check(f"n, {k}", len(groups[k]), v["n"])
        near(f"mean data score, {k}",
             sum(d for _, d in groups[k]) / len(groups[k]), v["data"])
    check("touch at least one licensed input",
          len(groups["licensed only"]) + len(groups["licensed and public"]),
          stats["any_licensed"])
    check("licensing classes partition the corpus",
          sum(len(v) for v in groups.values()), 109)

    print("\n5. Clusters")
    CL = {
        "Biodiversity & Nature": ["Topic: Biodiversity & Nature"],
        "Climate Physical Risk": ["Topic: Climate Physical Risk"],
        "Climate Transition Risk & Corporate Emissions":
            ["Topic: Climate Transition Risk", "Topic: Corporate Emissions (Scope 1/2/3)"],
        "Green Bonds & Sustainable Debt": ["Topic: Green Bonds & Sustainable Debt"],
        "Social & Governance": ["Topic: Social Factors", "Topic: Governance"],
        "ESG Disclosure & Ratings": ["Topic: ESG Disclosure", "Topic: ESG Ratings"],
    }
    for name, cols in CL.items():
        g = [i for i, r in enumerate(raw)
             if any(r[c].strip().upper().startswith("Y") for c in cols)]
        check(f"n, {name}", len(g), stats["clusters"][name]["n"])
        near(f"mean data score, {name}",
             sum(ds[i] for i in g) / len(g), stats["clusters"][name]["data"])

    print("\n6. Currency")
    def yrs(v):
        return [int(y) for y in re.findall(r"(?:1[89]|20)\d{2}", v or "")]

    multi = [r["PAPER ID"] for r in raw
             if len(yrs(r["Dataset End Year"])) > 1 or len(yrs(r["Dataset Start Year"])) > 1]
    check("papers listing several sample years (handled as min..max)", multi, ["P61"])
    lags = [max(yrs(r["Publication Year"])) - max(yrs(r["Dataset End Year"]))
            for r in raw if yrs(r["Dataset End Year"]) and yrs(r["Publication Year"])]
    check("lag computable for every paper", len(lags), 109)
    near("median lag", st.median(lags), stats["lag_median"], tol=0.001)
    check("max lag", max(lags), stats["lag_max"])
    check("no negative lag (data ending after publication)",
          sum(1 for x in lags if x < 0), 0)
    check("papers with data past 2023",
          sum(1 for r in raw if max(yrs(r["Dataset End Year"])) > 2023), stats["past_2023"])
    check("derived coverage windows are all positive",
          sorted(r["paper_id"] for r in derived
                 if r["coverage_window_years"] is not None
                 and r["coverage_window_years"] < 1), [])

    print("\n7. Links")
    inv = list(csv.DictReader(open(os.path.join(ROOT, "data", "link_inventory.csv"))))
    checks_file = list(csv.DictReader(open(os.path.join(ROOT, "data", "link_checks.csv"))))
    recorded = {x["url"] for x in checks_file}
    asset_urls = {x["url"] for x in inv
                  if x["url"] and x["link_type"] in ("data_link", "code_link")}
    check("every asset URL has a recorded verdict", sorted(asset_urls - recorded), [])
    check("no recorded verdict is orphaned",
          sorted(recorded - {x["url"] for x in inv if x["url"]}), [])
    check("every link row carries a known paper id",
          sorted({x["paper_id"] for x in inv} - set(ids_raw)), [])
    check("no asset link is DEAD",
          sorted(x["url"] for x in inv
                 if x["link_type"] != "paper_link" and x["verdict"] == "DEAD"), [])

    print("\n8. Data-quality warnings (reported, never auto-corrected)")
    warn = []
    for r in raw:
        blob = " ".join(r.values())
        if re.search(r"\[?VERIFY\]?|TBD|TODO", blob, re.I):
            warn.append(f"{r['PAPER ID']}: unresolved coder note in the frozen corpus")
    scope_note = [
        (r["PAPER ID"], r["Data Geographic Scope"].strip(), r["Geographic Notes"].strip())
        for r in raw if r["Geographic Notes"].strip()
    ]
    for pid, scope, note in scope_note:
        # Only flag notes that open by describing a global sample. "US (and
        # global)" and "US/global equities" are deliberate codings of a
        # primarily US sample and are not errors.
        if scope == "US" and note.strip().lower().startswith("global"):
            warn.append(f"{pid}: scope coded US but the note opens by describing a global sample")
    seen = {}
    for pid, _scope, note in scope_note:
        if len(note) > 60:
            seen.setdefault(note, []).append(pid)
    for note, pids in seen.items():
        if len(pids) > 1:
            warn.append(f"{'/'.join(pids)}: identical long geographic note — possible copy-paste")
    # Warnings that have been reviewed and either accepted or explained in the
    # README. Anything not in this set fails the build, so a new coding problem
    # cannot appear silently. Resolved on 2026-08-22 and deliberately removed
    # from this set: P66 and P105 (coder notes cleared), P81/P82 (P82 had been
    # coded from P81's paper and was fully recoded).
    #
    # P80 is accepted, not pending: it studies multinational firms operating
    # near protected areas that are all in the United States, so the note
    # describes the firms while the scope describes the phenomenon. The rule is
    # in CODEBOOK.md §6 under "Whose geography is coded". The check is left in
    # place rather than suppressed, because a scope disagreeing with its own
    # note is usually an error and a new instance should still be judged.
    known = {
        "P80: scope coded US but the note opens by describing a global sample",
    }
    for w in sorted(warn):
        print(f"  [{'known' if w in known else 'NEW'}] {w}")
    check("no unrecorded data-quality warning", sorted(set(warn) - known), [])
    check("no stale entry left in the known-warnings set",
          sorted(known - set(warn)), [])
    print("  known warnings are listed in README under 'Open items in the frozen corpus'.")

    print("\n9. README agrees with the build")
    for label, needle in (
        ("corpus size", f"| Papers coded | **{len(raw)}**"),
        ("fully open", f"| Fully open (data **and** code) | **{fully_open}**"),
        ("fully closed", f"| Fully closed (neither) | **{fully_closed}**"),
        ("licensed inputs", f"| Touch at least one licensed input | **{stats['any_licensed']}**"),
        ("code-without-data", f"| Code released without data | **{code_only}**"),
    ):
        check(f"README states the built {label}", needle in readme, True)
    check("README stats block was rendered",
          "<!-- STATS:BEGIN -->\n<!-- STATS:END -->" not in readme, True)
    check("README tiers block was rendered",
          "<!-- TIERS:BEGIN -->\n<!-- TIERS:END -->" not in readme, True)
    check("README badges block was rendered",
          "<!-- BADGES:BEGIN -->\n<!-- BADGES:END -->" not in readme, True)

    print(f"\n{CHECKS[0]} checks run.")
    if FAILS:
        print(f"\n{len(FAILS)} FAILED:")
        for f in FAILS:
            print("  -", f)
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
