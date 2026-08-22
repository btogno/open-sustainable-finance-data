# Contributing

This catalogue is meant to outlive the thesis it was built for. That imposes
one hard constraint and a few soft ones.

## Where the data actually comes from

The coding was done in a spreadsheet, `Taxonomy_Coding_Sheet_FINAL.xlsx`, and
that workbook is the source of truth for the coding itself.
`data/SustFin_Corpus_FINAL.csv` is generated from its *Full Coding* sheet:

```bash
make import WORKBOOK=path/to/Taxonomy_Coding_Sheet_FINAL.xlsx
```

which converts the sheet, then runs `build` and `verify`. The importer refuses
to write if the workbook's columns have been renamed or reordered, so a
restructured sheet cannot quietly corrupt the corpus. It is the one script here
that needs a third-party package: `pip install openpyxl`.

**Never hand-edit `data/SustFin_Corpus_FINAL.csv`.** A coding correction made
there is lost the next time the workbook is reimported. Correct the workbook.

## The hard constraint: the released baseline does not change

`data/SustFin_Corpus_FINAL.csv` as tagged `v1.0.0` is the baseline the thesis's
numbers are computed from. A reader following the citation must find the corpus
the thesis describes, not a later and better one.

Before the thesis is submitted and the DOI minted, correcting the workbook and
reimporting is the right move — a known coding error should not be carried into
submission for the sake of a rule. **After that point the baseline is closed**,
and:

- **New papers do not go into it.** They go into `data/extensions/` (see below).
- **Corrections do not go into it silently either.** They go through the
  correction procedure, which records what changed and why, and are folded into
  a new baseline at the next major version.

Everything else in the repository is generated, so it can be rebuilt at will:

```bash
make build      # regenerate the derived table and all documentation
make verify     # re-derive every headline figure and assert it independently
```

## Adding a paper

Open a pull request adding one row per paper to
`data/extensions/<yyyy>-<short-name>.csv`, using the same column headers as the
frozen corpus. Create the file if it does not exist.

Before opening it, check the following. Entries that fail these are not
rejected out of hand, but they need an explanation in the PR description.

1. **In scope?** The catalogue covers *empirical* sustainable finance research.
   Theory papers with no dataset have nothing to catalogue.
2. **Every field coded?** Blanks are worse than a defensible judgement call, and
   `derive.py` will fail loudly on an unrecognised availability level.
3. **Availability coded as published, not as hoped.** `Y` means the constructed
   analysis panel is released. If the paper names public sources but releases
   nothing, that is `Raw Data`, not `Y` — this is the most common coding error
   and the one that would quietly inflate every headline figure.
4. **Links point at the landing page, not the file.** A Dataverse dataset URL
   survives a file being re-uploaded; a `file.xhtml?fileId=...` URL does not.
5. **Coverage years are the study's sample**, not the publication year.

Say in the PR description which paper it is, where the availability judgement
was close, and what you checked in the paper itself rather than in its abstract.

## Correcting an existing entry

Corrections to the frozen corpus are welcome and are handled as amendments
rather than edits, so that the thesis's numbers and the corrected numbers can
both be reproduced.

Add a row to `data/corrections.csv` with these columns:

| Column | Content |
|---|---|
| `paper_id` | Which entry. |
| `field` | Which column of the frozen corpus. |
| `frozen_value` | What it says now. |
| `corrected_value` | What it should say. |
| `evidence` | Where you checked — a URL, a page number, a quoted sentence. |
| `reported_by` | Your name or handle. |
| `date` | ISO date. |

The build reads corrections and reports them; it does not apply them to the
frozen file. A future v2.0.0 will fold accumulated corrections into a new
baseline and say so in the release notes.

If you have found a **dead link** rather than a coding error, that is not a
correction — update `data/link_checks.csv` instead, with a new `checked_on`
date and a note saying what it does now.

## Re-verifying links

The most useful recurring contribution, and the one the catalogue decays
without.

```bash
make check-links
```

This re-probes every URL and writes both the recorded baseline verdict and the
fresh result into `data/link_inventory.csv`, so what changed is a column
comparison. Two things to keep in mind before reporting rot:

- `BLOCKED` is not rot. Harvard Dataverse, Wiley, FEMA, OSF and Mendeley all
  refuse automated requests; those need checking in a browser.
- A `200` proves a page exists, not that the file behind it is the one the
  paper used.

Update `data/link_checks.csv` with what you find, keeping one row per unique
URL, and put the new date in `checked_on`.

## What does not belong here

- **The datasets themselves.** This repository catalogues and links. Almost
  every entry involves at least one commercially licensed input, and mirroring
  the open ones would create a maintenance burden and a licensing hazard for no
  gain over linking to the authoritative deposit.
- **Working papers**, for now. The corpus is peer-reviewed publications in four
  journals. Unrefereed working papers are a different population with a
  different self-selection problem, and mixing them silently would make the
  openness rate uninterpretable. If they are added it will be as a separately
  labelled corpus.
- **Quality judgements about the papers.** The tiers rank what is *retrievable*,
  not what is good.

## Style

Python in `scripts/` is standard-library only — `import_corpus.py` and its
`openpyxl` dependency are the single exception, and it is not needed to build
or verify the repository. The code is meant to be read by an economist, not
admired by an engineer. Keep it dependency-free, keep every
scoring key and classification declared in exactly one place, and keep the
comment that explains *why* a judgement was made next to the judgement.

Documentation is British-spelled, written in prose rather than bullet
fragments, and states limitations where the reader is standing rather than in a
footnote at the end.
