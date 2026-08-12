# Superseded code

Kept for reference and for reproducing older outputs. Nothing here is part of the
current pipeline, and nothing in `src/tornado_dataset/` or `scripts/` imports it.

| file | superseded by | why |
|---|---|---|
| `extract_noaa_polygons.py` | `scripts/01_fetch_dat.py` | filtered on non-empty survey `comments` at download time, which discards 68% of damage polygons; the pipeline fetches everything and flags `has_oracle_text` instead |
| `analyze_noaa_data.py` | `scripts/09_analyze_hazards.py` | reported over the older `events_*.geojson` shape, before the Episode/Hazard/Geometry model existed |
| `normalize_noaa_data.py` | the DAT pipeline (stages 01-03) | one-off normalisation absorbed into `dat/geometry.py` and `dat/hazards.py` |
| `parse_lexisnexis_rtf.py` | `tornado_dataset.text.lexisnexis` | was already only a shim re-exporting the module |
| `tornado_filter.py` | `text/mediacloud.py` + `scripts/18_filter_media_cloud.py` | written for LexisNexis headline+lead text; the rewrite works from headline+URL, dedups syndicated copies, and drops the rule/classifier stages that measurement showed were costing recall |
| `13_overlap_report.py` | `scripts/22_corpus_atlas.py` | pairwise LexisNexis ↔ GDELT only, and its denominators assumed one URL per story, which is false for Media Cloud. Its level-2 index probe is ported to `22 --probe` |
| `20_corpus_overlap.py` | `scripts/22_corpus_atlas.py` | pairwise, and counted each corpus in its own native unit — bodies against titles against URLs. Its label-agreement crosstab is ported to stage 22 and now runs over every labelled pair |
| `verify_dat_stormevents_join.py` | — | exploratory join against NCEI Storm Events; no Storm Events data is in the repo. Kept because it is the starting point if that source is ever added |

`tornado_filter.py` and `verify_dat_stormevents_join.py` were copied rather than
moved: their originals live in `local/`, which is gitignored.

The reports the two retired stages produced — `outputs/overlap_report.md` and
`outputs/corpus_overlap_report.md` — are kept for provenance. Both are superseded
by `outputs/corpus_atlas_report.md` and `outputs/corpus_atlas_events_report.md`,
which count in one unit across all three corpora.
