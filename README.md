# tornado-text-to-trajectory

Code and notes for collecting surveyed tornado path geometries as reference data
for ongoing work on reconstructing tornado trajectories and impact corridors from
natural-language reports.

## Data source

This repository currently uses the NOAA Damage Assessment Toolkit (DAT)
FeatureServer.

- Damage Assessment Toolkit GUI — https://apps.dat.noaa.gov/stormdamage/damageviewer/
- Post-Storm Data Acquisition directive — https://www.weather.gov/media/directives/010_pdfs/pd01016004curr.pdf

## Repository layout

```
src/
  extract_noaa_polygons.py   # download + clean tornado geometries from NOAA DAT
  analyze_noaa_data.py       # build a visual analysis report from the events file
data/                        # downloaded GeoJSON  (generated, git-ignored)
outputs/                     # report, figures, georeferenceable subset  (generated, git-ignored)
requirements.txt
README.md
```

`data/` and `outputs/` are created on demand and are not tracked in git.

## `extract_noaa_polygons.py`

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
```

Both scripts resolve `data/` and `outputs/` relative to the repository root, so
they can be run from anywhere.
