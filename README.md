# tornado-text-to-trajectory

Code and notes for collecting surveyed tornado path geometries as reference data
for ongoing work on reconstructing tornado trajectories and impact corridors from
natural-language reports.

## Data source

This repository currently uses the NOAA Damage Assessment Toolkit (DAT)
FeatureServer.

- Damage Assessment Toolkit GUI — https://apps.dat.noaa.gov/stormdamage/damageviewer/
- Post-Storm Data Acquisition directive — https://www.weather.gov/media/directives/010_pdfs/pd01016004curr.pdf

The text side of the project uses tornado news coverage exported from LexisNexis
Uni as full-text RTF (`data/lexis_nexis_tornado_news/`, git-ignored).

## Repository layout

```
src/tornado_dataset/         # the dataset pipeline (package)
  config.py                  # window, thresholds, endpoints — every tunable choice
  http.py  ids.py            # cached/retrying HTTP; deterministic UIDs + manifests
  dat/fetch.py               # paged DAT download, raw responses cached
  dat/geometry.py            # Esri JSON -> RFC 7946 GeoJSON -> shapely, EPSG:5070
  dat/link.py                # line <-> polygon linkage with recorded evidence
  dat/evaluate.py            # linker evaluation against DAT's own path_guid key
  dat/hazards.py             # hazards (tornado tracks) and episodes (outbreaks)
  geo/gazetteer.py           # NWS county/WFO polygons + GNIS place names
  text/tiering.py            # versioned two-axis independence rules
  text/iem.py                # NWS Local Storm Reports + storm-survey PNS
  text/gdelt.py              # independent news links (GDELT DOC 2.0)
  text/lexisnexis.py         # read LexisNexis full-text RTF exports into a table
scripts/                     # thin CLIs: 01_fetch_dat … 08_qa_text
src/                         # earlier standalone scripts (still runnable)
  extract_noaa_polygons.py   # superseded by scripts/01_fetch_dat.py
  analyze_noaa_data.py       # report over the older events_*.geojson
  parse_lexisnexis_rtf.py    # shim re-exporting tornado_dataset.text.lexisnexis
data/raw/                    # verbatim API responses (never edited)
data/interim/                # per-layer GeoJSON, candidate links
data/processed/              # hazards, episodes, geometries + manifests
outputs/                     # QA report, figures, article table
```

`data/` and `outputs/` are created on demand and are not tracked in git.

## Dataset pipeline

```bash
python scripts/01_fetch_dat.py         # DAT lines+polygons for the configured window
python scripts/02_link_geometry.py     # candidate + accepted line<->polygon links
python scripts/03_build_hazards.py     # hazards (tornadoes) and episodes (outbreaks)
python scripts/04_qa_dat.py            # evaluation + outputs/dat_qa_report.md
python scripts/05_enrich_geography.py  # counties, states, WFO backfill, place names
python scripts/06_fetch_iem_text.py    # NWS LSRs (timely) + storm-survey PNS (oracle)
python scripts/07_fetch_gdelt.py       # independent news links per episode
python scripts/08_qa_text.py           # outputs/text_qa_report.md
```

Stages 6 and 7 are long: the full window is ~26k IEM requests (~3.5 h) and ~6.6k
GDELT requests (~10 h, capped by the API at one per five seconds). Both cache
every response under `data/raw/`, so an interrupted run resumes where it stopped
and a rerun needs no network. Use `--sample-days N` (stage 6) or `--limit N`
(stage 7, largest outbreaks first) for a pilot.

Scope and every threshold live in [`config.py`](src/tornado_dataset/config.py);
a run is described by that file plus the git SHA recorded in each manifest. The
default window is 2010-01-01 – 2025-12-31, which currently yields **11,520 damage
lines and 9,989 damage polygons → 9,982 hazards in 2,795 episodes**.

Three design decisions worth knowing before using the outputs:

- **No attribute filter on download.** Requiring non-empty survey `comments`
  (as `extract_noaa_polygons.py` does) discards 68% of damage polygons; instead
  every feature is fetched and hazards carry a `has_oracle_text` flag.
- **Linkage is spatial and temporal only.** `event_id` (free text) and
  `path_guid` (a foreign key, but real on just 289 of 9,989 polygons — the rest
  hold an all-zero placeholder) are recorded *beside* each link so they stay
  usable as independent checks. Against the `path_guid` gold set the linker
  scores 99.3% precision [97.4, 99.8] and 96.2% recall [93.3, 97.9] — on 289
  polygons from 2017 and 2020-2025 only, so it is a sanity check, not a
  dataset-wide error rate.
- **Candidates are generated wider (1 km, ±2 days) than they are accepted**
  (200 m, ±1 day), so `data/interim/dat_links_*.csv` supports re-filtering at a
  different operating point without refetching. See
  [`outputs/dat_qa_report.md`](outputs/dat_qa_report.md) for the sweep.

### Text layer

Each tornado is paired with text on two axes — who wrote it (`same_org_as_geometry`)
and when, relative to the field survey (`temporal_class`) — yielding the roles
`oracle`, `official_timely`, `independent_timely`, `independent_retrospective`.
The rules live in one versioned function (`text/tiering.py`) so the corpus can be
re-tiered reproducibly.

- **NWS text is stored in full** (US-government works): Local Storm Reports as the
  timely stream, and the per-tornado section of a storm-survey PNS as the oracle.
  Survey sections are matched to a track by the coordinates they state, and only
  the best-scoring section becomes `primary_survey_of`.
- **News is stored as links and metadata only.** GDELT queries run per episode.
- **Independent cross-check:** where a survey section matched a hazard, the survey's
  own EF rating agrees with DAT's on 97.1% of cases and the fatality count on
  97.1% (n=69, March 2025) — two descriptions of the same survey, compared rather
  than assumed equal.
- **Coverage stops at 2017-01-01 for news**: 590 of 2,795 episodes predate the
  GDELT DOC API's earliest queryable date and are flagged, not silently empty.

See [`outputs/text_qa_report.md`](outputs/text_qa_report.md), which also records the
measurements behind the retrieval choices (query form, match radii).

## `extract_noaa_polygons.py` (superseded)

The original standalone downloader, kept because `analyze_noaa_data.py` and the
existing `data/events_*.geojson` still depend on its output format. For new work
use `scripts/01_fetch_dat.py`, which fetches without the `comments` filter and
links geometry by measured evidence rather than bounding-box overlap.

Downloads tornado damage geometries from the DAT FeatureServer and writes them to
`data/`. It can:

- query the polygon layer, the path-line layer, or both;
- filter by date range and optionally require a non-empty field (e.g. `comments`),
  excluding placeholder values such as `None` / `N/A` / `NULL`;
- convert Esri JSON to RFC 7946 GeoJSON (correct ring winding, holes vs. shells);
- group overlapping polygons/lines into single tornado **events** (by `event_id`
  plus spatial/temporal clustering) and aggregate their attributes, writing an
  `events_*.geojson`.

All behaviour is controlled by the `CONFIG` block at the top of the script
(`geometry_type`, `start_date`, `end_date`, `non_empty_field`, `output_dir`,
`group_into_events`, …).

Outputs in `data/`:

- `polygons_<start>_<end>_nonempty-<field>.geojson`
- `lines_<start>_<end>_nonempty-<field>.geojson`
- `events_<start>_<end>_nonempty-<field>.geojson` (one feature per grouped event)

## `analyze_noaa_data.py`

Reads the most recent `events_*.geojson` in `data/` and writes a Markdown report
plus figures to `outputs/`:

- EF-scale distribution, events per year, and a seasonal (polar) breakdown;
- geographic distribution (significant-event map + density hexbin);
- track-length and damage-width distributions;
- injuries/fatalities by EF-scale, and the deadliest/costliest events;
- a comment / **georeferencing** analysis: each event's `comments` field is run
  through spaCy NER (`en_core_web_sm`); events whose comment contains a place
  entity (`GPE`/`LOC`/`FAC`) — i.e. could be georeferenced from text alone — are
  counted and exported to `outputs/georeferenceable_events.geojson`.

## LexisNexis RTF parsing (`tornado_dataset.text.lexisnexis`)

LexisNexis Uni only exports full text as RTF (one document per file). This script
is the Python counterpart to the R package
[LexisNexisTools](https://jbgruber.r-universe.dev/LexisNexisTools): it converts
each RTF with `striprtf` and splits the document into headline, source,
publication date, the labelled metadata block (`Length`, `Byline`, `Section`,
`Dateline`, `Highlight`, …), the body, the optional `Graphic` / `Notes` /
`Classification` sections and `Load-Date`. Unknown labels are kept in a `meta`
JSON column, so nothing is silently dropped.

```bash
python src/parse_lexisnexis_rtf.py                      # data/lexis_nexis_tornado_news
python src/parse_lexisnexis_rtf.py path/to/rtfs -f csv  # any other export
```

Writes `outputs/lexisnexis_articles.csv` and `.jsonl` (one row per article).
Used as a library:

```python
from tornado_dataset.text.lexisnexis import parse_directory, to_dataframe, add_duplicate_flags

df = add_duplicate_flags(to_dataframe(parse_directory("data/lexis_nexis_tornado_news")))
df.loc[~df.is_duplicate, ["pub_date", "source", "headline", "body"]]
```

Notes on the output:

- `length_words` is LexisNexis' own word count, `n_words` the count of the
  extracted body — comparing the two is a built-in check that the body was cut
  at the right place (they agree within 10% for ~88% of the tornado corpus;
  LexisNexis counts headline/byline tokens differently).
- `dup_group` / `is_duplicate` mark verbatim re-runs of the same wire story
  (64 of the 994 downloaded tornado articles).
- `warnings` collects per-document parsing anomalies (e.g. monthly editions
  without a day of month, whose `pub_date` is set to the 1st).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # if not pulled in by requirements.txt
```

## Usage

```bash
python src/extract_noaa_polygons.py   # populate data/
python src/analyze_noaa_data.py       # build outputs/ report + figures
python src/parse_lexisnexis_rtf.py    # news RTFs -> outputs/lexisnexis_articles.*
```

Both scripts resolve `data/` and `outputs/` relative to the repository root, so
they can be run from anywhere.
