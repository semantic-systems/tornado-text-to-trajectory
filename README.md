# tornado-text-to-trajectory

A dataset pairing natural-language descriptions of tornadoes with authoritative
damage geometries, built to measure how accurately humans and GeoAI systems can
infer a disaster's spatial footprint from text.

**New here? Read in this order:**

1. **[HANDOVER.md](HANDOVER.md)** — what state everything is in right now, where
   the data lives, and the open threads. Start here.
2. [docs/DATA_MODEL.md](docs/DATA_MODEL.md) — the schema: Episode → Hazard →
   Geometry, and how text attaches to it.
3. [docs/PIPELINE.md](docs/PIPELINE.md) — per-stage detail.
4. [docs/FINDINGS.md](docs/FINDINGS.md) — what the project has measured so far.

## Data sources

| source | what it gives | text? |
|---|---|---|
| NOAA [Damage Assessment Toolkit](https://apps.dat.noaa.gov/stormdamage/damageviewer/) | surveyed damage lines and polygons — the geometry ground truth | — |
| NWS via [IEM](https://mesonet.agron.iastate.edu/) | Local Storm Reports (timely) and storm-survey PNS (the oracle) | full, public domain |
| LexisNexis Uni | news coverage as full-text RTF | full body |
| [Media Cloud](https://search.mediacloud.org/) | US national/state/local news index | headline + URL |
| [GDELT DOC 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) | independent news links, 2017 onward | links only |

Text is *published* as links plus derived annotations, never as article text.
Retrieved bodies are held locally for text and data mining under §60d UrhG (EU DSM
Art. 3); see [docs/PIPELINE.md](docs/PIPELINE.md).

## Repository layout

```
src/tornado_dataset/         # the pipeline (package)
  config.py                  # window, thresholds, endpoints — every tunable choice
  http.py  ids.py            # cached/retrying HTTP; deterministic UIDs + manifests
  llm.py                     # OpenAI-compatible client for a local vLLM server
  viz.py                     # shared palette and matplotlib style
  dat/                       # fetch, geometry, line<->polygon linkage, hazards, evaluation
  geo/                       # gazetteer (counties, WFO, GNIS); pixels (shared projection)
  text/
    tiering.py               # versioned two-axis independence rules -> text_role
    iem.py  gdelt.py         # NWS reports/surveys; GDELT news links
    lexisnexis.py            # parse LexisNexis full-text RTF exports
    labelling.py             # shared LLM labelling: vocabulary, schema, protect rule
    mediacloud.py            # Media Cloud corpus: dedup, cues, prompt
    lexisnexis_filter.py     # LexisNexis corpus: evidence windows, prompt
    fulltext.py              # article retrieval: robots, archive, extraction
    linking.py               # article -> event: window, toponyms, corroboration
    matching.py  overlap.py  # same-story matching; the GDELT index probe
    corpora.py               # all three news corpora as one comparable set
  viewer/                    # Flask app for browsing the corpus
scripts/                     # thin CLIs, 00_selftest + 01…22
docs/                        # data model, pipeline detail, findings, codebook
legacy/                      # superseded code, with a README naming replacements
data/                        # raw / interim / processed — not in git (4.7 GB)
outputs/                     # reports (*.md tracked) and figures (not tracked)
```

## The pipeline

```bash
python scripts/00_selftest.py          # no network, no data — check the environment
python scripts/01_fetch_dat.py         # DAT lines+polygons for the configured window
python scripts/02_link_geometry.py     # candidate + accepted line<->polygon links
python scripts/03_build_hazards.py     # hazards (tornadoes) and episodes (outbreaks)
python scripts/04_qa_dat.py            # evaluation + outputs/dat_qa_report.md
python scripts/05_enrich_geography.py  # counties, states, WFO backfill, place names
python scripts/06_fetch_iem_text.py    # NWS LSRs (timely) + storm-survey PNS (oracle)
python scripts/07_fetch_gdelt.py       # independent news links per episode
python scripts/08_qa_text.py           # outputs/text_qa_report.md
python scripts/09_analyze_hazards.py   # descriptive report + figures
python scripts/10_hazard_map.py        # interactive map (self-contained HTML)
python scripts/11_link_articles.py     # articles -> events, with evidence per link
python scripts/12_sample_annotation.py # blind validation sheets
python scripts/14_qa_links.py          # score annotations -> outputs/link_qa_report.md
python scripts/15_analyze_news_time.py # the corpus in time -> news_time_report.md
python scripts/16_viewer.py            # browse the corpus at localhost:8799
python scripts/17_fetch_media_cloud.py # Media Cloud headlines, 2010-2025
python scripts/18_filter_media_cloud.py run    # LLM relevance labels
python scripts/18_filter_media_cloud.py run --source gdelt   # ...and for GDELT
python scripts/19_filter_lexisnexis.py run    # same, for the LexisNexis corpus
python scripts/21_fetch_fulltext.py crawl      # full text for Media Cloud (long)
python scripts/22_corpus_atlas.py --events-only  # all three corpora as a set
```

Stages 13 and 20 are retired — the three-way atlas (stage 22) replaces both;
see [legacy/README.md](legacy/README.md). [HANDOVER.md](HANDOVER.md) has the
per-stage status table.

Long stages cache every response under `data/raw/`, so an interrupted run resumes
where it stopped and a rerun needs no network: IEM ~26k requests (~3.5 h), GDELT
~6.6k (>10 h, one per five seconds), the full-text crawl ~30 h.

Scope and every threshold live in [`config.py`](src/tornado_dataset/config.py); a
run is described by that file plus the git SHA recorded in each manifest. The
default window is 2010-01-01 – 2025-12-31, which yields **11,520 damage lines and
9,989 damage polygons → 9,982 hazards in 2,795 episodes**.

Three design decisions worth knowing before using the outputs:

- **No attribute filter on download.** Requiring non-empty survey `comments`
  discards 68% of damage polygons; every feature is fetched and hazards carry a
  `has_oracle_text` flag instead.
- **Linkage is spatial and temporal only.** `event_id` (free text) and `path_guid`
  (a foreign key, but real on just 289 of 9,989 polygons — the rest hold an
  all-zero placeholder) are recorded *beside* each link so they stay usable as
  independent checks. Against the `path_guid` gold set the geometry linker scores
  99.3% precision [97.4, 99.8] and 96.2% recall [93.3, 97.9] — on 289 polygons
  from 2017 and 2020-2025 only, so it is a sanity check, not a dataset-wide error
  rate.
- **Candidates are generated wider (1 km, ±2 days) than they are accepted**
  (200 m, ±1 day), so `data/interim/dat_links_*.csv` supports re-filtering at a
  different operating point without refetching.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # if not pulled in by requirements.txt
python scripts/00_selftest.py             # confirms the environment
```

### Credentials and services

Nothing is needed for the DAT, IEM or GDELT stages, which use unauthenticated
public APIs. Keys live in the environment, never in the source:

| Variable | Needed by | Where to get it |
|---|---|---|
| `MEDIACLOUD_API_KEY` | `scripts/17_fetch_media_cloud.py` | <https://search.mediacloud.org/> |
| `TORNADO_LLM_BASE` | stages 18–19 (optional) | your own vLLM server; defaults to `http://127.0.0.1:8000/v1` |
| `TORNADO_DATA_DIR` | every stage (optional) | local path or mount point for the 4.7 GB `data/`; see [HANDOVER.md](HANDOVER.md) |
| `TORNADO_OUTPUT_DIR` | every stage (optional) | defaults to `outputs/` in the working tree |

`data/` is not in git. The canonical copy is on the group server at
`192.168.106.17:/data/share/geoai/tornado-text-to-trajectory/data`; copy or mount
it and point `TORNADO_DATA_DIR` at the local path.

Stages 18 and 19 label every article with a locally hosted LLM. If it runs on
another machine, forward the port and the default base URL applies unchanged:

```bash
ssh -N -L 8000:localhost:8000 you@your-server
```

Every answer is cached in `data/interim/*_llm_cache.jsonl`, so re-running those
stages against an existing data copy costs nothing and needs no GPU.
