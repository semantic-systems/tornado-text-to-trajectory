"""
Standalone verification: does the NOAA DAT `event_id` deterministically join to
the NCEI Storm Events `EVENT_ID`?

This script answers that empirically by querying BOTH live sources for the same
time window and measuring the actual set overlap of their event_id values.

It is intentionally standalone: it does NOT import the Stage 0 normalizer and
has no dependency beyond the Python standard library + `requests`. Run it from
any machine with ordinary internet access (the analysis sandbox blocks the NOAA
hosts, which is why this is a separate deliverable).

    pip install requests
    python3 verify_dat_stormevents_join.py --year 2024 --months 5 6

What it does
------------
1. DAT side: paginates the live DamageViewer FeatureServer (Damage Lines layer)
   for each requested month, pulling `event_id` (+ a few context fields). Handles
   ArcGIS's 2000-record page cap via resultOffset paging.
2. Storm Events side: downloads the official NCEI `StormEvents_details-*.csv.gz`
   bulk file(s) for the year, filters to the requested months, and reads the
   `EVENT_ID` column (and EVENT_TYPE/STATE for context).
3. Overlap: normalizes both id sets and reports, per month and overall:
     - how many DAT event_ids are non-null / integer-castable
     - how many DAT integer ids intersect the Storm Events EVENT_ID universe
     - the same intersection computed against ALL years' EVENT_IDs is not done
       (we keep it to the same window, which is the strongest fair test)
   A high intersection rate would indicate a usable deterministic key; a near-zero
   rate confirms the fields are unrelated.

Exit code is 0 on success regardless of the finding; the finding is in the report.

Caveats baked into the report
-----------------------------
- NCEI Storm Events EVENT_ID is an integer primary key. DAT event_id is a
  free-text string (length 30, surveyor-editable). Only integer-castable DAT
  values can possibly match, so the script reports both the raw and the
  integer-castable denominators.
- The NCEI bulk filename carries a creation-date stamp that changes over time,
  so the script discovers the correct filename from the directory listing rather
  than hard-coding it.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import sys
import time
from collections import defaultdict
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    sys.exit("This script needs `requests`:  pip install requests")


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

DAT_LINES_QUERY = (
    "https://services.dat.noaa.gov/arcgis/rest/services/"
    "nws_damageassessmenttoolkit/DamageViewer/FeatureServer/1/query"
)

# NCEI Storm Events bulk CSV directory (files are gzipped, one per year, with a
# creation-date stamp we discover dynamically).
NCEI_DIR = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"

PAGE = 2000  # ArcGIS MaxRecordCount for this service
TIMEOUT = 60
RETRIES = 3
SLEEP = 1.5


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #

def _get(url, params=None, stream=False):
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT, stream=stream)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            sys.stderr.write(f"  [retry {attempt}/{RETRIES}] {url} -> {e}\n")
            time.sleep(SLEEP * attempt)
    raise RuntimeError(f"GET failed after {RETRIES} tries: {url}\n  {last}")


# --------------------------------------------------------------------------- #
# DAT side
# --------------------------------------------------------------------------- #

def month_bounds(year, month):
    """Return (start_iso, end_iso) UTC bounds for an ArcGIS date BETWEEN clause."""
    if month == 12:
        nxt = f"{year + 1}-01-01"
    else:
        nxt = f"{year}-{month + 1:02d}-01"
    return f"{year}-{month:02d}-01 00:00:00", f"{nxt} 00:00:00"


def fetch_dat_event_ids(year, month):
    """Pull all DAT Damage-Lines event_ids for one month via offset paging."""
    start, end = month_bounds(year, month)
    where = (
        f"stormdate >= timestamp '{start}' AND "
        f"stormdate < timestamp '{end}'"
    )
    rows = []
    offset = 0
    while True:
        params = {
            "where": where,
            "outFields": "event_id,stormdate,efscale,wfo",
            "returnGeometry": "false",
            "outSR": "4326",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": PAGE,
            "orderByFields": "objectid",
        }
        r = _get(DAT_LINES_QUERY, params=params)
        try:
            data = r.json()
        except json.JSONDecodeError:
            raise RuntimeError(
                f"DAT returned non-JSON (offset={offset}). "
                f"First 300 chars:\n{r.text[:300]}"
            )
        if "error" in data:
            raise RuntimeError(f"DAT service error: {data['error']}")
        feats = data.get("features", [])
        for f in feats:
            rows.append(f.get("attributes", {}))
        # ArcGIS sets exceededTransferLimit when more pages remain
        if data.get("exceededTransferLimit") or len(feats) == PAGE:
            offset += PAGE
            time.sleep(0.3)
            continue
        break
    return rows


# --------------------------------------------------------------------------- #
# NCEI Storm Events side
# --------------------------------------------------------------------------- #

def discover_ncei_details_url(year):
    """Find the StormEvents_details-*_dYYYY_*.csv.gz file for the given year."""
    listing = _get(NCEI_DIR).text
    # filenames look like:
    #   StormEvents_details-ftp_v1.0_d2024_c20250115.csv.gz
    pat = re.compile(
        rf'StormEvents_details-[^"]*_d{year}_c\d+\.csv\.gz'
    )
    matches = sorted(set(pat.findall(listing)))
    if not matches:
        raise RuntimeError(
            f"No Storm Events details file found for {year} in {NCEI_DIR}"
        )
    # if multiple creation dates exist, take the most recent (last sorted)
    return NCEI_DIR + matches[-1]


def fetch_ncei_event_ids(year, months):
    """Download + parse the NCEI details file; return per-month dict of id sets
    plus a flat set of all EVENT_IDs in the requested months."""
    url = discover_ncei_details_url(year)
    sys.stderr.write(f"  NCEI details file: {url}\n")
    r = _get(url, stream=True)
    raw = io.BytesIO(r.content)
    by_month = defaultdict(set)
    context = {}  # event_id -> (event_type, state)
    want = set(months)
    with gzip.open(raw, mode="rt", newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        # Storm Events month is given as MONTH_NAME and/or BEGIN_YEARMONTH (YYYYMM)
        for row in reader:
            ym = row.get("BEGIN_YEARMONTH") or ""
            mo = None
            if len(ym) == 6 and ym.isdigit():
                mo = int(ym[4:6])
            if mo is None or mo not in want:
                continue
            eid = (row.get("EVENT_ID") or "").strip()
            if not eid:
                continue
            by_month[mo].add(eid)
            context[eid] = (row.get("EVENT_TYPE", ""), row.get("STATE", ""))
    allids = set()
    for s in by_month.values():
        allids |= s
    return by_month, allids, context


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #

def classify_dat_ids(rows):
    """Split DAT event_id values into populated / integer-castable / sample."""
    populated, integerish = [], []
    sample = []
    for a in rows:
        v = a.get("event_id")
        if v is None:
            continue
        s = str(v).strip()
        if s == "":
            continue
        populated.append(s)
        if re.fullmatch(r"\d+", s):
            integerish.append(s)
        if len(sample) < 15:
            sample.append(s)
    return populated, integerish, sample


def run(year, months):
    report = []
    add = report.append
    add("=" * 70)
    add(f"DAT <-> NCEI Storm Events  event_id overlap verification")
    add(f"year={year}  months={months}")
    add("=" * 70)

    # ---- NCEI first (one download covers all months) ----
    sys.stderr.write("[1/2] Fetching NCEI Storm Events ...\n")
    ncei_by_month, ncei_all, ncei_ctx = fetch_ncei_event_ids(year, months)
    add(f"\nNCEI Storm Events EVENT_IDs in window: {len(ncei_all)}")
    for m in sorted(months):
        add(f"  month {m:02d}: {len(ncei_by_month.get(m, set()))} events")

    # ---- DAT per month ----
    sys.stderr.write("[2/2] Fetching DAT Damage Lines per month ...\n")
    grand_pop = grand_int = grand_hit = 0
    all_hits_sample = []
    for m in sorted(months):
        sys.stderr.write(f"  DAT {year}-{m:02d} ...\n")
        rows = fetch_dat_event_ids(year, m)
        pop, integ, sample = classify_dat_ids(rows)
        ncei_set = ncei_by_month.get(m, set())
        # an integer DAT id "matches" if the same string is an NCEI EVENT_ID
        hits = [s for s in integ if s in ncei_set]
        # also test against the whole-year window, not just same month, in case
        # of month-boundary / timezone misattribution
        hits_anymonth = [s for s in integ if s in ncei_all]

        grand_pop += len(pop)
        grand_int += len(integ)
        grand_hit += len(hits_anymonth)
        for s in hits_anymonth[:5]:
            et, st = ncei_ctx.get(s, ("", ""))
            all_hits_sample.append(f"{s} ({et}, {st})")

        add(f"\n--- DAT {year}-{m:02d} ---")
        add(f"  DAT line features:            {len(rows)}")
        add(f"  event_id populated:           {len(pop)}"
            f"  ({pct(len(pop), len(rows))})")
        add(f"  event_id integer-castable:    {len(integ)}"
            f"  ({pct(len(integ), len(pop))} of populated)")
        add(f"  integer ids matching NCEI (same month):  {len(hits)}")
        add(f"  integer ids matching NCEI (same year):   {len(hits_anymonth)}")
        if sample:
            add(f"  sample DAT event_id values: {sample}")

    add("\n" + "=" * 70)
    add("OVERALL")
    add("=" * 70)
    add(f"  DAT event_id populated:               {grand_pop}")
    add(f"  DAT event_id integer-castable:        {grand_int}"
        f"  ({pct(grand_int, grand_pop)} of populated)")
    add(f"  ... of which intersect NCEI EVENT_ID: {grand_hit}"
        f"  ({pct(grand_hit, grand_int)} of integer ids,"
        f" {pct(grand_hit, grand_pop)} of all populated)")
    if all_hits_sample:
        add(f"  matched id samples: {all_hits_sample[:10]}")
    add("")
    add("INTERPRETATION")
    add("-" * 70)
    if grand_hit == 0:
        add("  No DAT event_id matched any NCEI EVENT_ID in the window.")
        add("  => No deterministic ID crosswalk. Use the spatio-temporal-")
        add("     attribute join (stormdate +/- tol, EF agreement, geometry")
        add("     overlap), validated against the DAT comments narrative.")
    elif pct_val(grand_hit, grand_pop) < 5:
        add("  Negligible overlap (<5%). The few matches are most likely")
        add("  coincidental integer collisions, not a real foreign key.")
        add("  => Treat as NO usable deterministic crosswalk.")
    else:
        add("  Non-trivial overlap detected. Inspect the matched id samples")
        add("  above and validate a handful by hand (compare DAT comments to")
        add("  the NCEI EVENT_NARRATIVE for the same EVENT_ID) before relying")
        add("  on the key. Even then, expect one-to-many (a multi-county")
        add("  tornado has several EVENT_IDs per DAT track).")
    return "\n".join(report)


def pct(n, d):
    return f"{(100.0 * n / d):.1f}%" if d else "n/a"


def pct_val(n, d):
    return (100.0 * n / d) if d else 0.0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Verify DAT event_id vs NCEI Storm Events EVENT_ID overlap"
    )
    ap.add_argument("--year", type=int, required=True,
                    help="calendar year to test (e.g. 2024)")
    ap.add_argument("--months", type=int, nargs="+", default=[5, 6],
                    help="months to test (default: 5 6 = May/June peak season)")
    ap.add_argument("--out", default=None,
                    help="optional path to write the report (also printed)")
    args = ap.parse_args(argv)

    bad = [m for m in args.months if not (1 <= m <= 12)]
    if bad:
        sys.exit(f"invalid month(s): {bad}")

    report = run(args.year, sorted(set(args.months)))
    print("\n" + report)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(report + "\n")
        sys.stderr.write(f"\n[written] {args.out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
