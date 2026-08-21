# Open Sustainable Finance Data — build targets.
# Standard library only; no virtualenv required.

PY ?= python3

.PHONY: all build derive docs verify check-links check-links-offline clean help

all: build verify

## build: regenerate the derived table and every generated document
build: derive docs

## derive: rebuild data/sustfin_datasets.{csv,json} from the frozen corpus
derive:
	$(PY) scripts/derive.py

## docs: render README stats, CATALOGUE, CITATIONS and STATS
docs:
	$(PY) scripts/check_links.py --no-probe
	$(PY) scripts/build_docs.py

## verify: re-derive every headline figure independently and assert it
verify:
	$(PY) scripts/verify.py

## check-links: re-probe every URL and diff against the recorded baseline
check-links:
	$(PY) scripts/check_links.py
	$(PY) scripts/build_docs.py

## check-links-offline: rebuild the inventory from the recorded baseline only
check-links-offline:
	$(PY) scripts/check_links.py --no-probe

## clean: remove generated files (the frozen corpus and baseline are kept)
clean:
	rm -f data/sustfin_datasets.csv data/sustfin_datasets.json data/stats.json
	rm -f data/link_inventory.csv
	rm -f docs/CATALOGUE.md docs/CITATIONS.md docs/STATS.md

## help: list targets
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
