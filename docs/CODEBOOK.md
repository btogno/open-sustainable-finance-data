# Codebook

Every field in the catalogue, what it means, and how it was decided. Read the
scoring keys (§3) and the licensing classification (§4) before citing any
openness figure: both encode judgements, and both are editable in one place.

Two files carry the data. `data/SustFin_Corpus_FINAL.csv` is the **frozen
corpus** — hand-coded, never modified by the build.
`data/sustfin_datasets.csv` is the **derived table** — the frozen fields plus
everything computed from them by `scripts/derive.py`. Analysis should use the
derived table; corrections belong in the frozen corpus (see
[CONTRIBUTING.md](../CONTRIBUTING.md)).

---

## 1. Corpus construction

**Population.** Empirical sustainable finance papers published in the *Journal
of Finance*, *Journal of Financial Economics*, *Review of Financial Studies* and
*Review of Finance*, with issues covered through April 2026. Publication years
run 2011–2026. **n = 109.**

**Not conditioned on openness.** Papers releasing nothing are included. This is
the decision that makes the openness rate a measurement rather than a
description of a self-selected subset: 52 papers in the corpus have no public
data and 69 have no code, and excluding them would make the quantity of
interest unobservable.

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
(36 of 109). It marks documented provenance without release, which is precisely
the position of a paper whose inputs are public but whose constructed panel
never leaves the authors' machines.

### `code_availability` → `code_score`

| Level | Score | What it means |
|---|---|---|
| `Y` | 1.00 | Replication code released. |
| `Partial` | 0.50 | Some code released. |
| `On Demand` | 0.25 | Available from the authors on request. |
| `N` | 0.00 | No code. |

### `openness_score` and `openness_tier`

`openness_score` is the unweighted mean of the two scores, on [0, 1].
`openness_tier` is a label for reading convenience — `fully open` is reserved
for `data = Y` **and** `code = Y`, never awarded on score alone, because code
released against no data cannot be run.

Treating these ordinal levels as cardinal in order to average them is a
convenience. It is defensible for ranking and indefensible as measurement of a
latent quantity; nothing in the catalogue depends on the exact spacing.

### `could_be_open`

The coder's judgement on whether a paper's data *could* have been released
given its inputs. Judgement, not observation, and reported as such. Useful for
identifying where editorial pressure would have the highest return; not usable
as an outcome variable.

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
the build shows immediately how much any conclusion depends on the call.

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
papers primary, 13 any-mention), regulatory filing parsing (0 primary, 4
any-mention) and market data (18 primary, 57 any-mention).

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

One cell in the frozen corpus needs a rule. `P61` records two separate
cross-sections rather than a continuous range, coded `2014; 2017`. The build
takes the earliest listed year as the start and the latest as the end, so the
coverage window spans everything the study observes; `verify.py` asserts that
this is still the only such cell, so a second one cannot slip in unnoticed.

Two cautions. `Global` frequently means a global sample dominated by
developed-market firms, so it does not indicate emerging-market coverage: the
scheme has no emerging-market category, and only two entries study one
substantively (`P74`, China; `P66`, a six-market network including China). And the lag is measured to the
last year of data, not to the last year the data was current: a 2026 paper
using data to 2020 is four years behind at publication and further behind by
the time it is read.

---

## 7. Curation tiers

`curation_tier` ranks the sixteen papers from which something can actually be
retrieved. Mutually exclusive, evaluated in order.

| Tier | Rule | n |
|---|---|---|
| `Tier 1` | `data = Y` and `code = Y` | 6 |
| `Tier 2` | `code = Y` and `data = Partial` | 6 |
| `Tier 3` | `data ∈ {Y, Partial}` and `code ≠ Y` | 4 |
| *(untiered)* | everything else | 93 |

Papers releasing code against named raw sources (`code = Y`, `data = Raw Data`,
8 papers) are deliberately untiered: the code exists, but the panel it runs on
does not, so there is no retrievable asset to curate. They remain in the
catalogue and score 0.75.

---

## 8. Link verification

`data/link_checks.csv` holds one recorded verdict per unique URL;
`data/link_inventory.csv` joins those verdicts back to papers, one row per
paper × link, and carries a second pair of columns for a fresh probe so decay
since the baseline is a column comparison.

| Verdict | Meaning |
|---|---|
| `LIVE` | Resolved and served the expected resource when checked. |
| `REDIRECT` | Resolves, but to a different address than the one the paper gives. The new address is in the note. |
| `RESTRICTED` | Resolves but is not openly accessible — typically a Google Drive or Sheets location asking for sign-in. |
| `BLOCKED` | The host refuses automated requests. **Not evidence of rot**; Harvard Dataverse, Wiley, FEMA, OSF and Mendeley all do this. Needs a browser. |
| `ERROR` | Returned a server error. May be transient. |
| `NOT CHECKED` | Not probed in the baseline pass. All such entries are publisher landing pages, which are DOIs. |
| `NO URL` | The access field holds an email address or a prose note rather than a link. |

A `LIVE` verdict proves a page exists. It does not prove the file behind it is
still the file the paper used, and nothing in this repository verifies that a
released panel reproduces a published table.

---

## 9. Derived fields at a glance

Computed by `scripts/derive.py` and present only in the derived table:
`topic_codes`, `clusters`, `method_codes`, `licensing_exposure`, `data_score`,
`code_score`, `openness_score`, `openness_tier`, `curation_tier`, `coverage`,
`coverage_window_years`, `lag_years`.
