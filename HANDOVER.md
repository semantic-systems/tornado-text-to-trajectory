# Handover — state of play

Written 2026-08-12, as the project owner leaves for several weeks. This page is
the current state; [README.md](README.md) is the orientation,
[docs/PIPELINE.md](docs/PIPELINE.md) the per-stage detail.

Read the **traps** section before quoting any number out of this repository.

## Where the data is

Nothing under `data/` or `outputs/figures/` is in git. The reports
(`outputs/*.md`) are, so the findings are readable from a clone alone.

| | size | in git |
|---|---:|---|
| `data/` | 4.7 GB | no — ask the owner for a copy |
| `outputs/` figures | ~300 MB | no |
| `outputs/*.md` (12 reports) | small | **yes** |

Regenerating from scratch is days of work, not hours: IEM ~3.5 h, GDELT >10 h,
Media Cloud LLM labelling ~2.5 h of GPU, full-text crawl ~30 h. **Get a copy of
`data/` rather than rebuilding it.** Every stage caches its raw responses, so with
a copy in place a re-run costs no network and no GPU.

## Stage status

| stage | state |
|---|---|
| 01–05 DAT | **complete.** 11,520 lines + 9,989 polygons → 9,982 hazards in 2,795 episodes. Geometry linker validated at 99.3% precision / 96.2% recall on the 289-polygon `path_guid` gold set |
| 06 IEM text | **complete.** 15,687 LSRs + 14,956 survey products; 7,314 hazards (73.3%) have survey text |
| 07 GDELT | **partial and the processed table is stale — see traps.** Sweep stopped at 5,155/6,615 queries (78%). Cache holds **153,354 distinct URLs**; the table holds 66,034 |
| 08–10 QA, analysis, map | complete against the data as of early August |
| 11 article linking | ran **ungated**; 18,306 of 22,896 articles linked (80%). The `--labels` gate is wired but has never been used |
| 12–16 annotation, overlap, viewer | sheets drawn and viewer working; **no annotations have been made** |
| 17 Media Cloud fetch | complete. 491,432 rows, 266,258 distinct headlines, 2010–2025 |
| 18 Media Cloud labels | **complete.** 110,438 EVENT rows / 48,741 distinct stories. Self-consistency: 88.9% unanimous over 3 draws at T=1 |
| 19 LexisNexis labels | **complete.** 15,324 EVENT articles / 12,077 distinct bodies — but see traps |
| 20 corpus overlap | **complete.** Union of both corpora = **58,467** distinct tornado-event stories; the two overlap by only 1.4% |
| 21 full text | **pilot only.** Crawl built, verified resumable, never run |

## Traps

Things that will produce wrong answers if taken at face value.

**The GDELT table is nine days older than its cache.** `textrefs_news_*.csv` was
written 2 Aug and holds 66,034 URLs; the cache under `data/raw/gdelt/` holds
**153,354**. Every GDELT figure in the reports — including the conclusion in
`outputs/corpus_overlap_report.md` that GDELT adds little — rests on less than
half the collected data. Rebuilding the table from cache needs no network. The
sweep process was killed on 11 Aug at 78% (5,155 of 6,615 queries) after its rate
had collapsed roughly tenfold, most likely because the 45 s × attempt backoff in
`config.HTTP_RATE_LIMIT_BACKOFF` over-corrects against sustained 429s.

**Stage 19 looks like it over-calls `EVENT`.** 61.5% of LexisNexis articles are
`EVENT` against 22.5% of Media Cloud; `UNCLEAR` never fires once in 24,917
articles; and `is_passing_mention` — the flag built for this corpus's main failure
mode — is 0.0% of the EVENT set. Spot-checks of the stage-20 disagreements found
the *headline-only* Media Cloud label was often the better one, on opinion pieces,
1925 retrospectives and study explainers. The suspected cause is the `windows`
evidence mode: it selects ±40 words around each tornado mention, which for a
retrospective concentrates the damage language and discards the framing that would
reveal what the article is. `scripts/19_filter_lexisnexis.py window` runs the
ablation that would confirm or refute this.

**`--limit` bounds reads, not writes.** On stages 18 and 19 it caps how much of the
corpus is *read*, so a "small test" happily reuses a full labels file and then
overwrites the processed outputs with a fraction of the corpus. This destroyed a
real run's outputs once. **Always pass `--tag` for anything experimental**; output
paths derive from it and the response cache is shared, so a tagged run still
inherits every answer already paid for.

**archive.org needs a global throttle.** It is one host regardless of which
publisher an article came from. Treating it as just another domain got all 271
lookups in the first pilot rejected with 429. `fulltext.ARCHIVE_INTERVAL` is 5 s,
measured — at 1 s the connection errors return.

**Nothing is validated against humans.** Neither LLM label set, nor the article
linker, has a gold standard. Every accuracy-shaped number in the reports is either
model-versus-model agreement or model-versus-rules agreement. The geometry linker
is the one exception, and its gold set covers 289 of 9,989 polygons.

## Open threads

Four, in no fixed order. Each is self-contained.

### 1. Media Cloud full-text crawl

Media Cloud gives headline and URL but no body, which leaves its 48,741 `EVENT`
stories **unlinkable** — `scripts/11_link_articles.py` matches toponyms in the
body. Retrieving them would roughly triple the linkable corpus over the 12,077
LexisNexis articles available today.

Built, verified resumable, never run:

```bash
python scripts/21_fetch_fulltext.py status   # what the store holds
python scripts/21_fetch_fulltext.py crawl    # ~30 h, resumable
```

Read `outputs/fulltext_pilot_report.md` first. The pilot measured 54% retrieval at
a 1 s archive interval, but 250 of its 275 failures were archive *connection*
errors and only 16 articles had no archived copy at all — so the real ceiling is
near 85–90% and the binding constraint is patience. Retrieval bias turned out
milder than expected (small outlets 49% vs large 57%), and HTTP 451 geo-blocking,
which is invisible and systematic from Europe, is fully resolved by the archive.

Outcomes append to `data/raw/fulltext/retrievals.jsonl` as they happen; killing and
resuming across sessions is safe. `--retry-failed` re-attempts only transient
failures, never settled ones.

### 2. Schema design for the assembled corpus

Design the published schema by reusing existing ontologies where they fit, and
defining new terms only where the disaster↔text combination has no precedent.
Research task; no code needed to start. Read
[docs/DATA_MODEL.md](docs/DATA_MODEL.md) first — it specifies the current model
(Episode → Hazard → Geometry, with TextRef/TextLink) and the decisions already
locked for v0.2.

Standards worth evaluating against it:

| standard | fit |
|---|---|
| **schema.org** (`Event`, `Place`, `NewsArticle`, `GeoShape`) | the text↔event join, and web publication |
| **IPTC NewsML / rNews** | news article metadata and corpus-side provenance |
| **W3C PROV-O** | already implicit — `retrieved_at`, per-run manifests, git SHA |
| **SOSA/SSN** | frames the NWS damage survey as an *observation* of the event |
| **GeoSPARQL**, **OWL-Time** | track geometry; the temporal axis |
| **CAP** (OASIS) | the watch/warning side, and already the NWS's own format |
| **NIEM** emergency management domain | US-government alignment |
| **CIDOC-CRM** | generic event-centric modelling, if a heavier formalism is wanted |

The part with no precedent, and therefore the contribution: the **two-axis
independence model** in `src/tornado_dataset/text/tiering.py` —
`same_org_as_geometry` × `temporal_class` → `text_role` (oracle / official_timely /
independent_timely / independent_retrospective). None of the standards above can
express "this text is the oracle for this event" versus "this text is independent
and contemporaneous". That distinction is what makes the corpus usable for
evaluating text-to-trajectory reconstruction at all, and it currently exists only
as a column.

Deliverable: a design note in `docs/` proposing the mapping and the new terms,
before any serialisation work.

### 3. Making the linker more faithful

`src/tornado_dataset/text/linking.py` with `scripts/11_link_articles.py`. Current
approach: a −14/+3 day window as a cheap shortlist, IDF-weighted toponym matching
as the decision, corroborating signals (EF rating, casualty counts, dates stated in
the text, outlet locality) to break ties, plus a second pass that reads dates out
of the text so anniversary pieces are reachable. It links 80% of articles and its
precision is **unmeasured**.

Known weaknesses, roughly in order of expected payoff:

- **Toponym resolution is shallow.** Proper-noun n-grams plus a stoplist, adopted
  after case-insensitive matching proved catastrophic — "IN" matched the word
  "in", and GNIS towns named *Enough*, *Hurricane* and *March* matched ordinary
  prose. Real NER plus gazetteer disambiguation is the obvious upgrade.
- **Numeric corroboration is weak.** Fatality counts and EF ratings are matched
  loosely, although both are strong identifying signals.
- **The outbreak-versus-single-tornado decision** rests on one margin ratio
  (`config.LINK_HAZARD_MARGIN = 1.4`), which was a guess.
- **Wire copy is linked independently per article**, ignoring that syndicated
  copies describe one event. `text/matching.py` already has the machinery for
  cross-document identity.
- **LLM reranking of candidates** is now cheap, given the local vLLM server.
- **There is a hard ceiling.** DAT has no geometry at all for some major
  tornadoes — the Joplin EF5 of 22 May 2011, 158 dead, is absent — so those
  articles cannot be linked correctly however good the linker becomes. Quantifying
  that ceiling against NCEI Storm Events matters as much as improving the matcher.
  `legacy/verify_dat_stormevents_join.py` is the starting point.

Sequence this with thread 4: no improvement here is measurable until a gold set
exists. `docs/linking_coverage_analysis.md` records the last diagnosis, which took
linking from 55% to 80%.

### 4. Human annotation

The highest-leverage unblocking work. Three separate measurements are waiting on
it: article-link precision, stage 18/19 label accuracy, and the stage 19
over-calling question in the traps section.

Infrastructure exists. `docs/annotation_codebook.md` defines the labels;
`outputs/annotation/` holds blind sheets drawn by
`scripts/12_sample_annotation.py`; `scripts/14_qa_links.py` already consumes a
`label` column; and `scripts/16_viewer.py` was built to become the annotation UI —
an `/annotate` screen is designed but not implemented.

Strata worth concentrating on rather than sampling uniformly:

- `UNCLEAR` rows from stage 18 — 12,906 headlines the model itself could not
  decide, and only 45.4% stable across draws (against ~91% for every other label),
  which is good evidence the abstention is meaningful rather than a dumping ground.
- Low `modal_share` rows in `data/interim/*_consistency.csv`.
- The stage-20 disputed pairs — stories present in both corpora where the two
  labels disagree, in `data/interim/corpus_overlap_matches.csv`.

Draw blind and stratified, before looking at model output, with a second annotator
on a subset for κ. **The codebook needs a v2**: it currently instructs the
annotator not to open the full article, but the viewer now shows the body — the
same evidence the linker used. That changes what the precision figure means and
has to be recorded in the codebook version line and in the datasheet.

## If you change the pipeline

- `scripts/00_selftest.py` runs in seconds with no network, GPU or credentials.
  Run it after any change to the library modules.
- Every threshold lives in `src/tornado_dataset/config.py`, with the reasoning in
  a comment beside it. Those comments are dataset documentation, not incidental.
- Long stages are resumable through their caches. Prefer resuming to restarting.
