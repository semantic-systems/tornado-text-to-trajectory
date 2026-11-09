#!/usr/bin/env python
"""Stage 13 — download the official tornado records DAT is checked against.

NCEI Storm Events is the NWS's own tornado record, filed by each forecast office
as *Storm Data*: one row per tornado per county, with the office's episodes.
SPC's tornado database holds one reviewed record per whole track. Stage 14
matches both to DAT hazards; stage 17 reports on the match.

    python scripts/13_fetch_references.py      # ~16 Storm Events files + 1 SPC file

Needs the network (ncei.noaa.gov, spc.noaa.gov). Files already present are
skipped: NCEI revises each year's file in place and publishes the current year
with a lag of months, so the newest revision is discovered from the listing.
Downloads go to ``data/raw/storm_events/`` and ``data/raw/spc/``, each with a
``provenance.jsonl``.
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from tornado_dataset.dat import references as refs


def main() -> None:
    argparse.ArgumentParser(description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    records, spc = refs.download()
    for r in records:
        print(f"  {r['year']}  {r['status']:<14} {r.get('file') or ''}")
    missing = [r["year"] for r in records if r["status"] == "not_published"]
    if missing:
        print(f"\nnot yet published by NCEI: {missing} — the database lags by months.")
    print(f"  SPC   {spc['status']:<14} {spc.get('file') or ''}")


if __name__ == "__main__":
    main()
