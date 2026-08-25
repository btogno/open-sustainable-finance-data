# Codebook

Every field in the catalogue, what it means, and how it was decided. Read the
scoring keys (§3) and the licensing classification (§4) before citing any
openness figure: both encode judgements, and both are editable in one place.

Two files carry the data. `data/SustFin_Corpus_FINAL.csv` is the **frozen
corpus** — hand-coded, never modified by the build.
`data/sustfin_datasets.csv` is the **derived table** — the frozen fields plus
everything computed from them by `scripts/derive.py`. Analysis should use the
derived table.

The frozen corpus is itself generated, from the *Full Coding* sheet of
`Taxonomy_Coding_Sheet_FINAL.xlsx` via `make import`. The workbook is where
coding corrections are made; the CSV is never hand-edited, because a hand edit
is lost at the next import. See [CONTRIBUTING.md](../CONTRIBUTING.md).

---

## 1. Corpus construction

**Population.** Empirical sustainable finance papers published in the *Journal
of Finance*, *Journal of Financial Economics*, *Review of Financial Studies* and
*Review of Finance*, with issues covered through April 2026. Publication years
run 2011–2026. **n = 109.**

**Not conditioned on openness.** Papers releasing nothing are included.
Including them is what makes the openness rate a measurement: 52 papers in the
corpus have no public data and 69 have no code, and excluding them would make
the quantity of interest unobservable.

**Unit of the row.** One paper. A paper releasing several distinct assets
carries several links in one row rather than several rows, so counts here
reconcile exactly with the 109-paper baseline.

---

## 2. Identification and description

| Field | Meaning |
|---|---|
| `paper_id` | Stable identifier, `P05` / `P101`-style, assigned during coding. The join key across every file here. |
| `journal` | Publishing journal, one of the four. |
| `citation` | Full citation, verbatim as coded. Formats differ by journal because they were taken from each publisher's own export. |
| `short_title` | Hand-written label naming the paper's object and data, used as the display title in the catalogue. |
| `data_description` | One line on what the study's dataset actually is. |
| `paper_link` | Publisher landing page, usually a DOI. |
| `publication_year` | Year of publication. |

---

## 3. Availability and the scoring keys

Two levels are coded per paper and averaged, unweighted, into
`openness_score`. The keys live in `DATA_SCORE` and `CODE_SCORE` in
`scripts/derive.py`; change them there and rerun `make build` to test whether a
result survives a different weighting.

### `data_availability` → `data_score`

| Level | Score | What it means |
|---|---|---|
| `Y` | 1.00 | The constructed analysis panel is released — the dataset the paper's tables were computed from. |
| `Partial` | 0.75 | Some of the analysis data is released; some is withheld, typically the licensed part. |
| `Raw Data` | 0.50 | The raw sources are public and named, but nothing is released. A reader could in principle rebuild the panel from EPA, FEMA, SEC or equivalent sources, at the cost of reconstructing every cleaning decision. |
| `On Demand` | 0.25 | Available from the authors on request. Recorded as coded; not tested. |
| `N` | 0.00 | No public pathway to the data. |

`Raw Data` is the analytically important level and the largest single category
(36 of 109). It marks documented provenance without release: the inputs are
public, but the constructed panel is not.

### `code_availability` → `code_score`

| Level | Score | What it means |
|---|---|---|
| `Y` | 1.00 | Replication code released. |
| `Partial` | 0.50 | Some code released. |
| `On Demand` | 0.25 | Available from the authors on request. |
| `N` | 0.00 | No code. |

### `openness_score` and `openness_band`

`openness_score` is the unweighted mean of the two scores, on [0, 1].
`openness_band` is a coarse label for it — `fully open` · `mostly open` ·
`partly open` · `minimally open` · `closed`. `fully open` is reserved for
`data = Y` **and** `code = Y`, never awarded on score alone, because code
released against no data cannot be run.

`openness_band` and `curation_tier` (§7) are different classifications and the
names are kept apart deliberately. The band summarises the score; the tier
states what a reader can recover.

Treating these ordinal levels as cardinal in order to average them is a
convenience. It supports ranking, but not measurement of a latent quantity.
Nothing in the catalogue depends on the exact spacing.

### `could_be_open`

The coder's judgement on whether a paper's data *could* have been released
given its inputs. This is a judgement rather than an observation. It is useful
for identifying where editorial pressure would have the highest return, and is
not usable as an outcome variable.

---

## 4. Licensing exposure

`licensing_exposure` classifies each paper by the access terms of the raw
sources it draws on, taking the primary and secondary source fields together.
This — not the primary-source class alone — is the licensing measure the
analysis uses.

**Licensed** — access requires a commercial subscription or a negotiated
agreement: `Proprietary Database`, `Market Data`, `Earnings Call transcripts`,
`News & Media`.

**Public** — retrievable by any researcher without payment or permission:
`Official Statistics`, `SEC Filings`, `Weather & Hazard`, `Satellite Imagery`,
`CDP Reports`.

**Neither** — author-generated or unclassifiable: `Survey Data`, `Experiment`
outputs, `Social Media`, residual `Other`.

| Class | Rule | n |
|---|---|---|
| `licensed only` | at least one licensed source, no public source | 61 |
| `licensed and public` | at least one of each | 31 |
| `public only` | at least one public source, no licensed source | 11 |
| `neither` | neither category present | 6 |

The classification is the author's judgement and is declared in exactly one
place — `LICENSED` and `PUBLIC` in `scripts/derive.py`. Two calls are worth
flagging as arguable. `Market Data` is treated as licensed because in this
corpus it means CRSP, Compustat or Refinitiv rather than free price feeds.
`News & Media` is treated as licensed because the studies using it access it
through Factiva, RavenPack or equivalent. Reclassifying either and rerunning
the build shows how much a conclusion depends on the call.

---

## 5. Topics, clusters and methods

### Topic flags

Nine substantive flags plus `Other`, **non-exclusive**: a paper can carry
several. 82 of the 109 carry two or more, and the flags sum to 222.

| Code | Flag |
|---|---|
| `PHY` | Climate Physical Risk |
| `TRN` | Climate Transition Risk |
| `DIS` | ESG Disclosure |
| `RAT` | ESG Ratings |
| `BIO` | Biodiversity & Nature |
| `GRB` | Green Bonds & Sustainable Debt |
| `EMI` | Corporate Emissions (Scope 1/2/3) |
| `SOC` | Social Factors |
| `GOV` | Governance |
| `OTH` | Other |

### Consolidation into six clusters

The nine flags collapse into six clusters for analysis. Three merges, each on
the ground that the merged flags share a data-generating process rather than
merely a theme:

| Cluster | Flags | Why |
|---|---|---|
| Biodiversity & Nature | `BIO` | Distinct input class: ecological, geospatial and public-programme data. |
| Climate Physical Risk | `PHY` | Distinct input class: scientific hazard data. |
| Climate Transition Risk & Corporate Emissions | `TRN` + `EMI` | Emissions data is the input to transition-risk measurement. |
| Green Bonds & Sustainable Debt | `GRB` | Distinct input class: security-level issuance data. |
| Social & Governance | `SOC` + `GOV` | Near-identical data-generating processes and openness profiles. |
| ESG Disclosure & Ratings | `DIS` + `RAT` | Ratings are constructed from disclosure. |

Clusters inherit the non-exclusivity of the flags, so cluster counts sum above
109 and no two clusters are disjoint samples. Any cross-cluster comparison is
descriptive.

### Methods

`method_primary` and `method_secondary` are coded separately, and the catalogue
reports methods on an **any-mention** basis across both fields. This matters:
counting primary methods alone understates satellite and remote sensing (2
papers primary, 14 any-mention), regulatory filing parsing (0 primary, 4
any-mention) and market data (18 primary, 57 any-mention). The full table,
including each method's mean openness, is generated into
[STATS.md](STATS.md) and should be cited from there rather than from here.

Codes: `ECON` standard econometrics on accounting and market data · `NLP`
textual analysis · `SAT` satellite and remote sensing · `SURV` survey
instrument · `EXP` experiment · `FILE` regulatory filing parsing · `ML`
machine learning other than NLP · `META` meta-analysis or systematic review ·
`OTH` other.

---

## 6. Coverage, currency and scope

| Field | Meaning |
|---|---|
| `dataset_start_year`, `dataset_end_year` | First and last year of the study's sample. |
| `coverage` | The two above, rendered as a range. The field to check before openness when hunting reusable data. |
| `coverage_window_years` | `end − start + 1`. Median 13 years. |
| `lag_years` | `publication_year − dataset_end_year`. Median 4, mean 4.5, maximum 14. |
| `geographic_scope` | Scope of the **data**, not the authors' institutions: `US`, `Global`, `Europe`, `Asia-Pacific`, `Other / Regional`. |
| `geographic_notes` | Free text where the scope needs qualification. |
| `unit_of_observation` | `Firm-Year`, `Portfolio-Level`, `Asset-Level`, `Document-Level`, `Country-Year`, `Other`. |

### Whose geography is coded

Many studies observe firms in one place and a phenomenon in another: a
multinational sample exposed to a hazard, a policy or a protected area that
exists in a single country. **The scope follows the geography of the
phenomenon under study, not the domicile of the entities observed.** The
question is where the evidence comes from. Evidence about a US regulatory
boundary is US evidence, whatever the domicile of the firms it affects.

`P80` is the worked example. It studies
multinational firms operating near newly protected biodiversity areas, and the
protected areas are all in the United States — so the note describes global
firms while the scope is coded `US`. Both are correct and they are not in
conflict. `verify.py` still raises this pairing as a warning, because a scope
that disagrees with its own note is usually an error; it is listed as a known
and accepted warning rather than suppressed, so the same pattern in a new entry
is still surfaced for a human to judge.

Two cautions. `Global` frequently means a global sample dominated by
developed-market firms, so it does not indicate emerging-market coverage: the
scheme has no emerging-market category, and only two entries study one
substantively (`P74`, China; `P66`, a six-market network including China). And the lag is measured to the
last year of data, not to the last year the data was current: a 2026 paper
using data to 2022 is four years behind at publication and further behind by
the time it is read.

---

## 7. Curation tiers

`curation_tier` ranks every paper by what a reader can recover from it. The
seven tiers are mutually exclusive, are evaluated in order, and cover all 109
entries: no paper is untiered.

| Tier | Rule | n | What can be recovered |
|---|---|---|---|
| `Tier 1` | `data = Y` and `code = Y` | 6 | Panel and code. Rerunnable as published. |
| `Tier 2` | `code = Y` and `data = Partial` | 6 | Code, and part of the panel. |
| `Tier 3` | `data ∈ {Y, Partial}` and `code ≠ Y` | 4 | A panel, but not the analysis code. |
| `Tier 4` | `code = Y` and `data = Raw Data` | 8 | No panel; the code names the public sources and shows what was done to them. |
| `Tier 5` | `code = Y` and `data = N` | 17 | No panel and no public inputs; the code documents the pipeline. |
| `Tier 6` | `data ∈ {Raw Data, On Demand}` and `code ≠ Y` | 33 | Provenance only. Rebuilding means reconstructing every cleaning decision. |
| `Tier 7` | `data = N` and `code ≠ Y` | 35 | Nothing. |

The ladder groups into three. **Tiers 1 to 3** have something downloadable.
**Tiers 4 to 6** have nothing downloadable but do record how the analysis was
built, whether in code or in named sources. **Tier 7** records neither.

Tiers 4 and 5 are worth separating from the rest because the openness score
alone understates them. Neither releases an analysis panel, so neither can be
rerun; but the released code names the inputs and shows the transformations
applied to them, which is most of what a reader needs in order to build the
same thing from their own subscription. Tier 5 in particular is usually a
licensing outcome rather than a disclosure choice: the authors published
everything they were able to publish.

Tier 6 is the largest reconstructable group and the one where the cost falls
entirely on the reader. The sources are named and public, so the data is
obtainable in principle; what is missing is every decision made between the raw
source and the estimation sample.

---

## 8. Link verification

`data/link_checks.csv` holds one recorded verdict per unique URL;
`data/link_inventory.csv` joins those verdicts back to papers, one row per
paper × link, and carries a second pair of columns for a fresh probe so decay
since the baseline is a column comparison. [LINK_CHECKS.md](LINK_CHECKS.md) is
the readable rendering of the same thing.

| Verdict | Meaning |
|---|---|
| `LIVE` | Resolved and served the expected resource when checked. |
| `REDIRECT` | Resolves, but to a different address than the one the paper gives. The new address is in the note. |
| `RESTRICTED` | Resolves, but access is genuinely conditional — a registration wall or an explicit permission request, established by hand rather than inferred from a status code. |
| `BLOCKED` | The host refuses automated requests, or answers every one of them identically whatever the file's real permissions. **Not evidence of rot**; Harvard Dataverse, Wiley, FEMA, OSF, Mendeley, Google Drive and Google Sheets all do this. Needs a browser. |
| `ERROR` | Returned a server error. May be transient. |
| `NOT CHECKED` | Not probed in the baseline pass. All such entries are publisher landing pages, which are DOIs. |
| `NO URL` | The access field holds an email address or a prose note rather than a link. |

A `LIVE` verdict proves a page exists. It does not prove the file behind it is
still the file the paper used, and nothing in this repository verifies that a
released panel reproduces a published table.

The `method` column of `data/link_checks.csv` records how each verdict was
reached — `web` for an automated probe, `manual` for a human opening the link
in a browser. A `manual` verdict overrides an automated one and should not be
overwritten by a later `make check-links` run without someone looking again.

---

## 9. Derived fields at a glance

Computed by `scripts/derive.py` and present only in the derived table:
`topic_codes`, `clusters`, `method_codes`, `source_codes`,
`licensing_exposure`, `licensing_code`, `data_score`, `code_score`,
`openness_score`, `openness_band`, `curation_tier`, `coverage`,
`coverage_window_years`, `lag_years`.

`source_codes` and `licensing_code` exist so that a paper's inputs and its
licensing exposure fit in a table cell. The codes are declared in `SOURCE_CODE`
and `LICENSING_CODE` in `scripts/derive.py`; the classification that produces
them is §4 above.
