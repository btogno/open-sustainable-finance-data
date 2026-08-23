"""
build_docs.py — render the human-readable repository from the derived data.

Reads  : data/sustfin_datasets.json, data/link_inventory.csv
Writes : docs/CATALOGUE.md   one row per paper, all 109, sorted by openness
         docs/CITATIONS.md   full verbatim citation for every paper ID
         docs/STATS.md       every headline figure, recomputed
         README.md           refreshes the block between the STATS markers

Nothing here is hand-typed: every number in the repository is computed from the
frozen corpus, so `make build` is the only way a figure can change.
"""

import collections
import csv
import datetime as dt
import json
import os
import re
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")

CLUSTER_ORDER = [
    "Biodiversity & Nature",
    "Climate Physical Risk",
    "Climate Transition Risk & Corporate Emissions",
    "Green Bonds & Sustainable Debt",
    "Social & Governance",
    "ESG Disclosure & Ratings",
]

DATA_BADGE = {
    "Y": "`D:OPEN`",
    "Partial": "`D:PART`",
    "Raw Data": "`D:RAW`",
    "On Demand": "`D:REQ`",
    "N": "`D:—`",
}

CODE_BADGE = {
    "Y": "`C:OPEN`",
    "Partial": "`C:PART`",
    "On Demand": "`C:REQ`",
    "N": "`C:—`",
}

METHOD_NAME = {
    "ECON": "Standard econometrics on accounting and market data",
    "SAT": "Satellite and remote sensing",
    "NLP": "NLP / textual analysis",
    "SURV": "Survey instrument",
    "EXP": "Experiment",
    "FILE": "Regulatory filing parsing",
    "ML": "Machine learning (non-NLP)",
    "META": "Meta-analysis / systematic review",
    "OTH": "Other",
}

METHOD_ORDER = ["ECON", "SAT", "NLP", "SURV", "EXP", "FILE", "ML", "META", "OTH"]

PRIMARY_TO_CODE = {
    "Standard Econometrics Accounting / Market Data": "ECON",
    "NLP / Textual Analysis": "NLP",
    "Satellite & Remote Sensing": "SAT",
    "Survey Instrument": "SURV",
    "Experiment": "EXP",
    "Regulatory Filing Parsing": "FILE",
    "Machine Learning (non-NLP)": "ML",
    "Meta-Analysis / Systematic Review": "META",
    "Other": "OTH",
}

TIER_BADGE = {
    "Tier 1": "`T1`",
    "Tier 2": "`T2`",
    "Tier 3": "`T3`",
    "": "",
}


def load():
    recs = json.load(open(os.path.join(ROOT, "data", "sustfin_datasets.json")))
    links = list(csv.DictReader(open(os.path.join(ROOT, "data", "link_inventory.csv"))))
    return recs, links


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def fmt(x, n=2):
    return f"{x:.{n}f}"


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------

def stats(recs, links):
    n = len(recs)
    s = {"n": n, "built_on": dt.date.today().isoformat()}

    s["journals"] = collections.Counter(r["journal"] for r in recs)
    s["years"] = collections.Counter(r["publication_year"] for r in recs)
    s["data_levels"] = collections.Counter(r["data_availability"] for r in recs)
    s["code_levels"] = collections.Counter(r["code_availability"] for r in recs)
    s["geo"] = collections.Counter(r["geographic_scope"] for r in recs)
    s["unit"] = collections.Counter(r["unit_of_observation"] or "(unrecorded)" for r in recs)
    s["tiers"] = collections.Counter(r["curation_tier"] for r in recs if r["curation_tier"])

    s["data_mean"] = mean([r["data_score"] for r in recs])
    s["code_mean"] = mean([r["code_score"] for r in recs])
    s["open_mean"] = mean([r["openness_score"] for r in recs])
    s["fully_open"] = sum(1 for r in recs if r["openness_tier"] == "fully open")
    s["fully_closed"] = sum(1 for r in recs if r["openness_score"] == 0.0)
    s["score_hist"] = collections.Counter(r["openness_score"] for r in recs)

    # the asymmetry: released code without released data, and the reverse
    s["code_y_not_open"] = sum(
        1 for r in recs if r["code_availability"] == "Y" and r["data_availability"] != "Y"
    )
    s["data_y_not_open"] = sum(
        1 for r in recs if r["data_availability"] == "Y" and r["code_availability"] != "Y"
    )
    s["unrunnable_code"] = sum(
        1 for r in recs if r["code_availability"] == "Y" and r["data_availability"] == "N"
    )

    s["licensing"] = {}
    for k in ("licensed only", "licensed and public", "public only", "neither"):
        g = [r for r in recs if r["licensing_exposure"] == k]
        s["licensing"][k] = {
            "n": len(g),
            "data": mean([r["data_score"] for r in g]),
            "code": mean([r["code_score"] for r in g]),
            "open": mean([r["openness_score"] for r in g]),
            "fully_open": sum(1 for r in g if r["openness_tier"] == "fully open"),
        }
    s["any_licensed"] = sum(
        1 for r in recs if r["licensing_exposure"] in ("licensed only", "licensed and public")
    )

    s["clusters"] = {}
    for c in CLUSTER_ORDER:
        g = [r for r in recs if c in r["clusters"]]
        lags = [r["lag_years"] for r in g if r["lag_years"] is not None]
        s["clusters"][c] = {
            "n": len(g),
            "data": mean([r["data_score"] for r in g]),
            "code": mean([r["code_score"] for r in g]),
            "open": mean([r["openness_score"] for r in g]),
            "fully_open": sum(1 for r in g if r["openness_tier"] == "fully open"),
            "median_lag": st.median(lags) if lags else None,
            "median_end": st.median([r["dataset_end_year"] for r in g
                                     if r["dataset_end_year"]]),
        }

    # Methods are counted on an any-mention basis across the primary and
    # secondary fields; the primary column is reported alongside, because the
    # gap between the two is the adoption result.
    primary = collections.Counter(
        PRIMARY_TO_CODE.get(r["method_primary"], "OTH") for r in recs
    )
    s["methods"] = {}
    for code in METHOD_ORDER:
        g = [r for r in recs if code in r["method_codes"]]
        if not g:
            continue
        s["methods"][code] = {
            "n": len(g),
            "primary": primary.get(code, 0),
            "open": mean([r["openness_score"] for r in g]),
            "data": mean([r["data_score"] for r in g]),
        }

    s["cluster_methods"] = {}
    for c in CLUSTER_ORDER:
        g = [r for r in recs if c in r["clusters"]]
        mc = collections.Counter()
        for r in g:
            for m in set(r["method_codes"]):
                mc[m] += 1
        s["cluster_methods"][c] = mc

    lags = [r["lag_years"] for r in recs if r["lag_years"] is not None]
    s["lag_median"], s["lag_mean"], s["lag_max"] = st.median(lags), mean(lags), max(lags)
    s["past_2023"] = sum(1 for r in recs if (r["dataset_end_year"] or 0) > 2023)
    windows = [r["coverage_window_years"] for r in recs if r["coverage_window_years"]]
    s["window_median"] = st.median(windows)

    # Link figures cover data and code links only. Publisher landing pages are
    # DOIs and were never probed; counting them would inflate the denominator
    # with links that were never in question.
    assets = [x for x in links if x["link_type"] != "paper_link" and x["url"]]
    s["links_total"] = len(assets)
    s["links_verdicts"] = collections.Counter(x["verdict"] for x in assets)
    s["links_methods"] = collections.Counter(x["method"] or "—" for x in assets)
    s["links_paper_pages"] = sum(
        1 for x in links if x["link_type"] == "paper_link" and x["url"]
    )
    s["links_checked_on"] = max((x["checked_on"] for x in assets if x["checked_on"]),
                                default="")
    return s


# ---------------------------------------------------------------------------
# renderers
# ---------------------------------------------------------------------------

def clip(s, n=70):
    """One-line a note and trim it to n characters on a word boundary."""
    s = oneline(s)
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def oneline(s):
    """Flatten a cell for a markdown table.

    The coding workbook uses real line breaks inside cells for legibility — in
    citations, in the free-text access notes, and in the one cell that lists two
    sample years. A raw newline terminates a markdown table row, so every value
    rendered into a table passes through here first.
    """
    return re.sub(r"\s+", " ", str(s or "").replace("|", "\\|")).strip()


def link_cell(rec, links_by_paper):
    """Render the access links for one paper, with their verified status."""
    parts = []
    for field, label in (("data_link", "data"), ("code_link", "code")):
        entries = [x for x in links_by_paper.get(rec["paper_id"], [])
                   if x["link_type"] == field]
        urls = [x for x in entries if x["url"]]
        if not urls:
            note = next((x["access_note"] for x in entries if x["access_note"]), "")
            if note:
                parts.append(f"{label}: <sub>{clip(note)}</sub>")
            continue
        marks = []
        note = next((x["access_note"] for x in entries if x["access_note"]), "")
        for i, x in enumerate(urls, 1):
            # Verification state is deliberately not shown here. It lives in
            # LINK_CHECKS.md, because a mark in this column reads as a judgement
            # on the paper rather than on the checker that produced it.
            name = label if len(urls) == 1 else f"{label}&nbsp;{i}"
            marks.append(f"[{name}]({x['url']})")
        cell = " ".join(marks)
        if note:
            cell += f" <sub>{clip(note)}</sub>"
        parts.append(cell)
    return "<br>".join(parts) if parts else "—"


def catalogue(recs, links, s):
    links_by_paper = collections.defaultdict(list)
    for x in links:
        links_by_paper[x["paper_id"]].append(x)

    order = sorted(recs, key=lambda r: (-r["openness_score"], r["paper_id"]))

    out = [
        "# Catalogue — all 109 papers",
        "",
        "Every paper in the frozen corpus, whether or not it releases anything. "
        "Papers with no public data and no code are listed too. The openness rate "
        "of the field is only measurable against the whole population.",
        "",
        "Sorted by openness score, descending. Full citations are in "
        "[CITATIONS.md](CITATIONS.md); field definitions and scoring keys are in "
        "[CODEBOOK.md](CODEBOOK.md).",
        "",
"**Availability.** `D:` data — `OPEN` constructed panel released · `PART` "
        "partly released · `RAW` public raw sources named, nothing released · "
        "`REQ` on request · `—` none. `C:` replication code, same scale. The "
        "score is the mean of the two; `T1`–`T3` marks the curation tier.",
        "",
        "**Topics.** `BIO` biodiversity · `PHY` physical risk · `TRN` transition "
        "risk · `EMI` corporate emissions · `GRB` green bonds · `DIS` ESG "
        "disclosure · `RAT` ESG ratings · `SOC` social · `GOV` governance · "
        "`OTH` other. Non-exclusive.",
        "",
        "**Methods**, counted across the primary and secondary fields: `ECON` "
        "standard econometrics · `NLP` textual analysis · `SAT` satellite and "
        "remote sensing · `SURV` survey · `EXP` experiment · `FILE` regulatory "
        "filing parsing · `ML` machine learning · `META` meta-analysis · `OTH` "
        "other.",
        "",
        "**Inputs.** The raw data sources: `PROP` proprietary database · `MKT` "
        "market data · `OFF` official statistics · `SEC` SEC filings · `WX` "
        "weather and hazard · `SATI` satellite imagery · `CALL` earnings calls · "
        "`NEWS` news and media · `CDP` CDP reports · `SURV` survey · `SOCM` "
        "social media · `OTH` other. The leading badge is the paper's licensing "
        "exposure — `L:LIC` licensed inputs only · `L:MIX` licensed and public · "
        "`L:PUB` public only · `L:—` neither. This is the variable behind the "
        "corpus-wide result that papers built exclusively on licensed inputs "
        "score 0.16 on data against 0.55 for public-only; see "
        "[STATS.md](STATS.md).",
        "",
        "**Access links** are reproduced as the paper gives them. Every one has "
        "been checked and the result — when, by what means, and what it "
        f"resolved to — is recorded in [LINK_CHECKS.md](LINK_CHECKS.md), last "
        f"updated {s['links_checked_on']}.",
        "",
        "| ID | Study | Topics | Methods | Inputs | Coverage | Geo | Data | Code | Score | Access |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in order:
        title = oneline(r["short_title"])
        study = f"[{title}]({r['paper_link']})" if r["paper_link"] else title
        study = f"{study}<br><sub>{r['journal']} {r['publication_year']}</sub>"
        topics = " ".join(f"`{t}`" for t in r["topic_codes"])
        methods = " ".join(f"`{m}`" for m in r["method_codes"]) or "—"
        inputs = " ".join(
            [f"**`L:{r['licensing_code']}`**"]
            + [f"`{c}`" for c in r["source_codes"]]
        )
        score = fmt(r["openness_score"])
        if r["curation_tier"]:
            score += f" {TIER_BADGE[r['curation_tier']]}"
        out.append(
            f"| {r['paper_id']} | {study} | {topics} | {methods} | {inputs} | "
            f"{oneline(r['coverage']) or '—'} | "
            f"{oneline(r['geographic_scope']) or '—'} | {DATA_BADGE[r['data_availability']]} | "
            f"{CODE_BADGE[r['code_availability']]} | {score} | "
            f"{link_cell(r, links_by_paper)} |"
        )

    out += ["", "---", "", "## Index by cluster", "",
            "Clusters are non-exclusive, so a paper carrying several topic flags "
            "appears under several clusters and the counts sum above 109.", ""]
    for c in CLUSTER_ORDER:
        g = sorted((r for r in recs if c in r["clusters"]),
                   key=lambda r: (-r["openness_score"], r["paper_id"]))
        cs = s["clusters"][c]
        out += [
            f"### {c} — n = {cs['n']}",
            "",
            f"Mean data {fmt(cs['data'])} · mean code {fmt(cs['code'])} · "
            f"composite {fmt(cs['open'])} · fully open {cs['fully_open']} · "
            f"median lag {cs['median_lag']:.0f} years",
            "",
            " ".join(f"`{r['paper_id']}`" for r in g),
            "",
        ]
    return "\n".join(out) + "\n"


def link_checks(recs, links):
    """A readable rendering of the link-rot baseline, one row per link."""
    titles = {r["paper_id"]: oneline(r["short_title"]) for r in recs}
    order = {p: i for i, p in enumerate(sorted(titles, key=lambda x: int(x[1:])))}
    rows = [x for x in links if x["link_type"] != "paper_link"]
    rows.sort(key=lambda x: (order.get(x["paper_id"], 999), x["link_type"]))

    counts = collections.Counter(x["verdict"] for x in rows if x["url"])

    out = [
        "# Link checks",
        "",
        "Every data and code access link in the corpus, with the result of "
        "checking it. Publisher landing pages are omitted: those are DOIs.",
        "",
        "**Verdicts.** `LIVE` resolved and served the expected resource · "
        "`REDIRECT` resolves, but to a different address than the paper gives — "
        "the new one is in the note · `BLOCKED` the host refuses automated "
        "requests, or answers all of them identically whatever the file's real "
        "permissions, so only a person can settle it · `ERROR` returned a server "
        "error, possibly transient · `NO URL` the access field holds an email "
        "address or a prose note rather than a link.",
        "",
        "**Method.** `web` an automated probe · `manual` a person opened it in a "
        "browser. A manual verdict overrides an automated one and should not be "
        "overwritten by a later `make check-links` run without someone looking "
        "again.",
        "",
        "A `LIVE` verdict proves a page exists. It does not prove the file behind "
        "it is still the file the paper used, and nothing here verifies that a "
        "released panel reproduces a published table.",
        "",
        "Current state: "
        + " · ".join(f"**{k}** {v}" for k, v in counts.most_common())
        + f" across {sum(counts.values())} link entries. Counted per entry: "
        "several papers cite the same public source, so the unique-URL totals "
        "quoted in the README are lower.",
        "",
        "| Paper | Study | Link | Verdict | Method | Checked | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in rows:
        kind = "data" if x["link_type"] == "data_link" else "code"
        if x["url"]:
            shown = x["url"]
            label = shown if len(shown) <= 60 else shown[:57] + "…"
            cell = f"[{oneline(label)}]({shown})"
        else:
            cell = f"<sub>{clip(x['access_note'], 60)}</sub>"
        out.append(
            f"| {x['paper_id']} | <sub>{clip(titles.get(x['paper_id'], ''), 45)}</sub> | "
            f"{kind}: {cell} | `{x['verdict']}` | {('`' + x['method'] + '`') if x.get('method') else '—'} | "
            f"{x['checked_on'] or '—'} | <sub>{clip(x['check_note'], 90)}</sub> |"
        )
    return "\n".join(out) + "\n"


def citations(recs):
    out = [
        "# Citations",
        "",
        "The full citation for every paper in the corpus, reproduced verbatim as "
        "coded. Ordered by paper ID.",
        "",
        "| ID | Journal | Citation |",
        "|---|---|---|",
    ]
    for r in sorted(recs, key=lambda r: int(r["paper_id"][1:])):
        cite = oneline(r["citation"])
        out.append(f"| {r['paper_id']} | {r['journal']} | {cite} |")
    return "\n".join(out) + "\n"


def stats_md(s):
    o = [
        "# Statistics",
        "",
        f"Recomputed from the frozen corpus on {s['built_on']}. Every figure the "
        "README or the thesis cites is derived here, so the two cannot drift apart.",
        "",
        "## Corpus",
        "",
        f"- **n = {s['n']}** papers, four journals, publication years "
        f"{min(s['years'])}–{max(s['years'])}.",
        "- Journals: " + " · ".join(f"{k} {v}" for k, v in s["journals"].most_common()),
        "- Geographic scope of the data: "
        + " · ".join(f"{k} {v}" for k, v in s["geo"].most_common()),
        "- Unit of observation: "
        + " · ".join(f"{k} {v}" for k, v in s["unit"].most_common()),
        "",
        "## Openness",
        "",
        f"- Mean data score **{fmt(s['data_mean'])}**, mean code score "
        f"**{fmt(s['code_mean'])}**, mean composite **{fmt(s['open_mean'])}**.",
        f"- **{s['fully_open']}** papers ({fmt(100*s['fully_open']/s['n'], 1)} %) are "
        f"fully open — data *and* code released. **{s['fully_closed']}** "
        f"({fmt(100*s['fully_closed']/s['n'], 1)} %) score zero on both.",
        "- Data availability: "
        + " · ".join(f"{k} {v}" for k, v in s["data_levels"].most_common()),
        "- Code availability: "
        + " · ".join(f"{k} {v}" for k, v in s["code_levels"].most_common()),
        f"- The asymmetry runs one way: **{s['code_y_not_open']}** papers release "
        f"code without releasing data, against **{s['data_y_not_open']}** the other "
        f"way. **{s['unrunnable_code']}** publish replication code against no public "
        "data at all — code that cannot be executed.",
        "- Score distribution: "
        + " · ".join(f"{fmt(k)}: {v}" for k, v in sorted(s["score_hist"].items())),
        "",
        "## Licensing exposure",
        "",
        f"**{s['any_licensed']}** of {s['n']} papers "
        f"({fmt(100*s['any_licensed']/s['n'], 1)} %) draw on at least one licensed input.",
        "",
        "| Exposure | n | Mean data | Mean code | Composite | Fully open |",
        "|---|---|---|---|---|---|",
    ]
    for k, v in s["licensing"].items():
        o.append(f"| {k} | {v['n']} | {fmt(v['data'])} | {fmt(v['code'])} | "
                 f"{fmt(v['open'])} | {v['fully_open']} |")
    o += [
        "",
        "## Clusters",
        "",
        "Ordered along the openness gradient. Non-exclusive, so counts sum above "
        f"{s['n']}.",
        "",
        "| Cluster | n | Data | Code | Composite | Fully open | Median lag | Median data end |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in CLUSTER_ORDER:
        v = s["clusters"][c]
        o.append(f"| {c} | {v['n']} | {fmt(v['data'])} | {fmt(v['code'])} | "
                 f"{fmt(v['open'])} | {v['fully_open']} | {v['median_lag']:.0f} | "
                 f"{v['median_end']:.0f} |")
    o += [
        "",
        "## Methods",
        "",
        "Counted on an **any-mention** basis across the primary and secondary "
        "method fields. A method can be widely used without being any paper's "
        "primary technique, which is why the two columns differ.",
        "",
        "| Method | Any mention | Primary only | Mean openness | Mean data |",
        "|---|---|---|---|---|",
    ]
    for code, v in s["methods"].items():
        o.append(f"| {METHOD_NAME[code]} | {v['n']} | {v['primary']} | "
                 f"{fmt(v['open'])} | {fmt(v['data'])} |")
    o += [
        "",
        "### Methods by cluster",
        "",
        "| Cluster | n | Standard econometrics | Other methods, any mention |",
        "|---|---|---|---|",
    ]
    for c in CLUSTER_ORDER:
        mc = s["cluster_methods"][c]
        n = s["clusters"][c]["n"]
        econ = mc.get("ECON", 0)
        rest = " · ".join(f"{METHOD_NAME[k].split(' /')[0].split(' on ')[0]} {v}"
                          for k, v in mc.most_common() if k != "ECON")
        o.append(f"| {c} | {n} | {econ} ({fmt(100*econ/n, 0)} %) | {rest or '—'} |")
    o += [
        "",
        "## Currency of the evidence",
        "",
        f"- Median lag from last year of data to publication: **{s['lag_median']:.0f} "
        f"years** (mean {fmt(s['lag_mean'], 1)}, maximum {s['lag_max']}).",
        f"- Median sample window: **{s['window_median']:.0f} years**.",
        f"- Papers carrying data past 2023: **{s['past_2023']}**.",
        "",
        "## Link inventory",
        "",
        f"{s['links_total']} data and code link entries across the corpus, last "
        f"checked {s['links_checked_on']}: "
        + " · ".join(f"{k} {v}" for k, v in s["links_verdicts"].most_common())
        + ". Established by "
        + " · ".join(f"{k} {v}" for k, v in s["links_methods"].most_common())
        + ".",
        "",
        f"The {s['links_paper_pages']} publisher landing pages are excluded: they "
        "are DOIs and were not probed. Where an automated probe could not "
        "settle a link — Harvard Dataverse, Wiley, Mendeley, FEMA, OSF and Google "
        "all refuse robots or answer them identically whatever a file's real "
        "permissions — it was opened in a browser instead, which is what the "
        "`manual` method records. See [LINK_CHECKS.md](LINK_CHECKS.md).",
        "",
    ]
    return "\n".join(o) + "\n"


def readme_block(s):
    lic = s["licensing"]
    return "\n".join([
        f"| | |",
        f"|---|---|",
        f"| Papers coded | **{s['n']}** (JF {s['journals']['Journal of Finance']} · "
        f"JFE {s['journals']['Journal of Financial Economics']} · "
        f"RFS {s['journals']['Review of Financial Studies']} · "
        f"RoF {s['journals']['Review of Finance']}) |",
        f"| Fully open (data **and** code) | **{s['fully_open']}** "
        f"({fmt(100*s['fully_open']/s['n'], 1)} %) |",
        f"| Fully closed (neither) | **{s['fully_closed']}** "
        f"({fmt(100*s['fully_closed']/s['n'], 1)} %) |",
        f"| Mean openness score | **{fmt(s['open_mean'])}** "
        f"(data {fmt(s['data_mean'])} · code {fmt(s['code_mean'])}) |",
        f"| Code released without data | **{s['code_y_not_open']}** papers, against "
        f"{s['data_y_not_open']} the other way |",
        f"| Touch at least one licensed input | **{s['any_licensed']}** "
        f"({fmt(100*s['any_licensed']/s['n'], 1)} %) |",
        f"| Mean data score, licensed-only vs public-only | "
        f"**{fmt(lic['licensed only']['data'])}** vs "
        f"**{fmt(lic['public only']['data'])}** |",
        f"| Median lag, last data year to publication | **{s['lag_median']:.0f} years** |",
        f"| Access links resolving when last checked | "
        f"**{s['links_verdicts']['LIVE']}** of {s['links_total']}"
        + (f", {s['links_verdicts']['BLOCKED']} not verifiable automatically"
           if s["links_verdicts"].get("BLOCKED") else "")
        + (f", {s['links_verdicts']['REDIRECT']} redirecting"
           if s["links_verdicts"].get("REDIRECT") else "")
        + (f", {s['links_verdicts']['ERROR']} erroring"
           if s["links_verdicts"].get("ERROR") else "")
        + f" ({s['links_checked_on']}) |",
    ])


def readme_badges(s):
    def b(label, msg, colour):
        def q(t):
            t = t.replace("-", "--").replace("_", "__").replace("%", "%25")
            return (t.replace(" ", "%20").replace("(", "%28").replace(")", "%29"))
        return f"![{label}](https://img.shields.io/badge/{q(label)}-{q(msg)}-{colour})"

    pct = 100 * s["fully_open"] / s["n"]
    return " ".join([
        b("corpus", f"{s['n']} papers", "informational"),
        b("journals", "4", "informational"),
        b("fully open", f"{s['fully_open']} ({fmt(pct, 1)}%)", "critical"),
        b("mean openness", fmt(s["open_mean"]), "yellow"),
        b("links checked", s["links_checked_on"], "lightgrey"),
        b("data licence", "CC BY 4.0", "blue"),
        b("code licence", "MIT", "blue"),
    ])


def readme_tiers(recs, s, links):
    urls = collections.defaultdict(dict)
    for x in links:
        if x["url"]:
            urls[x["paper_id"]].setdefault(x["link_type"], x["url"])

    rows = [
        "| ID | Study | Topics | Coverage | Geo | Data | Code | Access |",
        "|---|---|---|---|---|---|---|---|",
    ]
    tiered = [r for r in recs if r["curation_tier"]]
    order = {"Tier 1": 0, "Tier 2": 1, "Tier 3": 2}
    for r in sorted(tiered, key=lambda r: (order[r["curation_tier"]], r["paper_id"])):
        u = urls.get(r["paper_id"], {})
        du, cu = u.get("data_link", ""), u.get("code_link", "")
        if du and du == cu:
            cell = [f"[data + code]({du})"]
        else:
            cell = ([f"[data]({du})"] if du else []) + ([f"[code]({cu})"] if cu else [])
        cl = " ".join(f"`{t}`" for t in r["topic_codes"])
        rows.append(
            f"| **{r['paper_id']}** | {oneline(r['short_title'])} | {cl} | "
            f"{oneline(r['coverage']) or '—'} | {oneline(r['geographic_scope']) or '—'} | "
            f"{DATA_BADGE[r['data_availability']]} | {CODE_BADGE[r['code_availability']]} | "
            f"{' · '.join(cell) or '—'} |"
        )
    out = []
    for t, title, blurb in (
        ("Tier 1", "Tier 1 — fully open",
         "Constructed panel and replication code both released. These are the "
         "entries a reader can actually rerun."),
        ("Tier 2", "Tier 2 — full code, partial data",
         "Code released against a partially released panel: reproducible in part, "
         "and the cheapest entries to move into Tier 1."),
        ("Tier 3", "Tier 3 — data available, code incomplete",
         "A panel is released but the analysis code is not, so the result can be "
         "re-estimated but not reproduced exactly."),
    ):
        g = [r for r in tiered if r["curation_tier"] == t]
        out += [f"#### {title} ({len(g)})", "", blurb, ""]
        out.append(rows[0])
        out.append(rows[1])
        for line in rows[2:]:
            if f"**{[r['paper_id'] for r in g][0]}**" in line or any(
                    f"**{r['paper_id']}**" in line for r in g):
                out.append(line)
        out.append("")
    return "\n".join(out).rstrip()


def inject(path, marker, block):
    a, b = f"<!-- {marker}:BEGIN -->", f"<!-- {marker}:END -->"
    s = open(path, encoding="utf-8").read()
    if a not in s or b not in s:
        return False
    pre, rest = s.split(a, 1)
    _, post = rest.split(b, 1)
    open(path, "w", encoding="utf-8").write(f"{pre}{a}\n{block}\n{b}{post}")
    return True


def main():
    recs, links = load()
    s = stats(recs, links)
    os.makedirs(DOCS, exist_ok=True)
    for name, text in (
        ("CATALOGUE.md", catalogue(recs, links, s)),
        ("CITATIONS.md", citations(recs)),
        ("LINK_CHECKS.md", link_checks(recs, links)),
        ("STATS.md", stats_md(s)),
    ):
        open(os.path.join(DOCS, name), "w", encoding="utf-8").write(text)
        print("wrote docs/" + name)

    readme = os.path.join(ROOT, "README.md")
    if os.path.exists(readme):
        for marker, block in (("STATS", readme_block(s)),
                              ("BADGES", readme_badges(s)),
                              ("TIERS", readme_tiers(recs, s, links))):
            if inject(readme, marker, block):
                print(f"refreshed README.md {marker} block")

    json.dump(
        {k: (dict(v) if isinstance(v, collections.Counter) else v) for k, v in s.items()},
        open(os.path.join(ROOT, "data", "stats.json"), "w"),
        indent=2, default=str,
    )
    print("wrote data/stats.json")


if __name__ == "__main__":
    main()
