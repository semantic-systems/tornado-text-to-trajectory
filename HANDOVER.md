# Handover — state of play

Written 2026-08-12. This page is
the current state; [README.md](README.md) is the orientation,
[docs/PIPELINE.md](docs/PIPELINE.md) the per-stage detail.

Read the **traps** section before quoting any number out of this repository.

## Where the data is

Nothing under `data/` or `outputs/figures/` is in git. The reports
(`outputs/*.md`) are, so the findings are readable from a clone alone.

| | size | in git                                                                                         |
|---|---:|------------------------------------------------------------------------------------------------|
| `data/` | 4.7 GB | no — on the group server, see below |
| `outputs/` figures | ~300 MB | no                                                                                             |
| `outputs/*.md` (12 reports) | small | **yes**                                                                                        |


## Stage status

| stage | state |
|---|---|
| 01–05 DAT | **complete.** 11,520 lines + 9,989 polygons → 9,982 hazards in 2,795 episodes. Geometry linker validated at 99.3% precision / 96.2% recall on the 289-polygon `path_guid` gold set |
| 06 IEM text | **complete.** 15,687 LSRs + 14,956 survey products; 7,314 hazards (73.3%) have survey text |
| 07 GDELT | **rebuilt from cache 12 Aug; partial by construction.** The sweep stopped at 5,155/6,615 queries (78%), so 1,442 queries were never fetched and 57 episodes have no cached slice at all. From what *was* fetched: **83,778 unique URLs** (was 66,034), 100,661 links, **1,857 episodes covered** — 66.4% of all episodes, 84.2% within GDELT's own 2017+ era |
| 08–10 QA, analysis, map | 08 refreshed 12 Aug against the rebuilt GDELT tables; 09–10 read DAT tables that have not changed |
| 11 article linking | ran **ungated**; 18,306 of 22,896 articles linked (80%). The `--labels` gate is wired but has never been used |
| 12–16 annotation, overlap, viewer | sheets drawn and viewer working; **no annotations have been made** |
| 17 Media Cloud fetch | complete. 491,432 rows, 266,258 distinct headlines, 2010–2025 |
| 18 Media Cloud labels | **complete.** 110,438 EVENT rows / 48,741 distinct stories. Self-consistency: 88.9% unanimous over 3 draws at T=1 |
| 19 LexisNexis labels | **complete.** 15,324 EVENT articles / 12,077 distinct bodies — but see traps |
| 13, 20 pairwise overlap | **retired** to `legacy/` — superseded by stage 22, which counts all three in one unit. Their unique functions (the GDELT index probe, the label-agreement crosstab) are ported |
| 22 corpus atlas | **complete.** All three corpora as a set. Run twice: `corpus_atlas_report.md` (collected) and `corpus_atlas_events_report.md` (**the usable subset — the one to read**) |
| 21 full text | **crawled 7 Oct.** 78% of the 48,741 `EVENT` stories retrieved; `report` and `quality` run offline over the store |
| 23 full-text labels | **built, not run.** Stage 19's prompt over the retrieved bodies, compared with stage 18's headline labels |
| 24 Storm Events + SPC | **run, 2010–2025.** SPC's reviewed whole-track tornado file matched to DAT as the tornado-level reference (98.3% of Storm Events chains match one SPC track); NCEI Storm Events tornado rows chained into whole tornadoes through `TOR_OTHER_*` and cross-checked against SPC, matched to DAT hazards by space and time, episodes linked across offices where a tornado crossed between them; DAT completeness rises from 1% of tornadoes (2010) to 85% (2025) |
| 26 watch systems | **`probe` run (results in `docs/plan_watch_linking.md`, step 0); `fetch` and `link` run on 2010–2025; watch systems (connected coverage) and sequences (hand-over chains) written per SPC tornado; scored in stage 25 as upper and lower bounds. Rerun `link` after the sequence change, then stage 25.** Feasibility check for the watch reference (plan step 0): county-record coverage per year, county vs polygon timing and placement of SPC tornadoes, "replaces" statements in watch texts. County records complete from 2006; ~20% of tornadoes placed differently by polygons |
| 25 episode comparison | **run on DAT; `--anchor spc` built, tested on the real data in a scratch copy, not run by you.** Stage 3's convective-day rule against space-time, ST-DBSCAN and kernel-density alternatives, scored on Storm Events episodes; `--anchor spc` groups SPC's complete tornado list and carries the episodes to DAT hazards |

## Traps

Things that will produce wrong answers if taken at face value.

**GDELT is 78% of its intended sweep, and structurally blind before 2017.** 1,442 queries
were never fetched (`uncached_queries`), and 57 episodes have no cached slice at
all, so every GDELT coverage figure is a **lower bound**. Separately, the API
cannot return anything before 2017-01-01, which is 590 of 2,795 episodes and
92,000 Media Cloud stories that GDELT can never reach.


Finishing the remaining 1,442 queries is possible but was abandoned deliberately:
the sweep's rate had collapsed roughly tenfold, most likely because the 45 s ×
attempt backoff in `config.HTTP_RATE_LIMIT_BACKOFF` over-corrects against
sustained 429s. Tune that before restarting, or the last 22% will take weeks.

**DAT start times are off by whole hours for ~7% of hazards.** Of 1,114 DAT
hazards with no SPC track by the strict rule (5 km, 30 min), 690 have one within
5 km whose start differs by a whole number of hours to within 10 min — mostly
to the minute: the local clock saved as UTC (+4…+7 h; nearly all of 2012's
gap, which is why 73% of 2012 was unmatched), daylight saving (±1 h) or the
wrong date (±24 h). Stage 24's second pass links them (`link_method =
time_repaired`, offset and cause on each link); ratings agree on 97% of them,
as on the first pass, against 38% by chance. **DAT's `time_begin_utc` itself is
not corrected** — anything that reads DAT times directly (stage 3's convective
day, the news-timing analysis) still sees the wrong hour for these hazards.

**DAT end times are often wrong — 561 of 9,982 hazards.** `time_end_utc` in the
stage 3 tables is hand-entered and frequently carries a mistyped *date* with a
plausible clock time: 427 hazards "last" over a day (one 6.6 years) and 61 end
before they start. Stage 3's episode grouping does not use end times, but its
`time_end_utc` columns and episode durations are wrong for these rows. Stages 24
and 25 repair them in memory (`episodes.repair_end_times`: keep the clock time
when it gives ≤5 h, else set the end to the start); stage 3 itself is unchanged.

**DAT is incomplete before ~2020.** Against NCEI Storm Events, 2015 DAT holds 37%
of the officially recorded tornadoes, 2025 DAT 85%. Every count of
tornadoes or episodes from DAT is a lower bound that grows with time for reasons
of adoption, not climate. Stage 24's report gives the per-year figure.

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

Five, in no fixed order. Each is self-contained.

### 1. Media Cloud full-text crawl

Media Cloud gives headline and URL but no body, which leaves its 48,741 `EVENT`
stories **unlinkable** — `scripts/11_link_articles.py` matches toponyms in the
body. Retrieving them would roughly triple the linkable corpus over the 12,077
LexisNexis articles available today.

**Crawled on 2026-10-07.** 38,058 of 48,741 retrieved = **78.1%**, close to the
pilot's projected ceiling. 2,529 failures are transient and worth one more pass;
the rest are settled (6,997 HTTP errors, 2,603 extraction failures, 326 robots
disallows, 257 skipped for an excessive `Crawl-delay`).

Retrieved is not the same as usable, so there is now an offline quality pass:

```bash
python scripts/21_fetch_fulltext.py crawl --retry-failed   # the 2,529 transients
python scripts/21_fetch_fulltext.py report                 # coverage, no network
python scripts/21_fetch_fulltext.py quality                # is it the right article?
```

`quality` asks whether each body is the article its headline names, which
extraction cannot tell. Measured before handing it over: **84.0%** of retrieved
bodies pass every hard check — **65.6% of the 48,741 `EVENT` stories** end up with
usable full text. The checks that do the work are a body that never mentions a
tornado (Media Cloud's own `tornado*` query matched the page, so a correct body
should), a direct fetch that landed on the site's front page, and one page served
under many unrelated headlines. Failing articles have a median of 0 tornado
mentions against 6 for passing ones, which is the property a quality filter
should have.

Two findings worth knowing before you use the text:

- **Archive copies are better than live ones.** 98.5% of archive fetches pass
  against 70.3% of direct fetches. The difference is soft 404s: dead articles that
  now return HTTP 200 with the outlet's front page. The archive serves the page as
  it was.
- **Count by body, not headline.** 38,070 retrieved headlines carry 31,931 distinct
  bodies. Media Cloud deduplicates by headline, so wire copy retitled by each
  outlet survives as separate stories.

**Correction to the pilot's claim**: the archive does *not* fully resolve HTTP 451
geo-blocking. It recovered 10 of 10 in the pilot, but at full scale 472 articles
remain `geo_blocked` with no archived copy. Still a minority, but not zero.

Outcomes append to `data/raw/fulltext/retrievals.jsonl` as they happen; killing and
resuming is safe. `--retry-failed` re-attempts only transient failures, never
settled ones. The quality table (`data/interim/fulltext_quality.csv`) carries every
raw measure, so a threshold can be moved without re-reading the bodies.

**Labelling the bodies and comparing with the headlines** — stage 23, built and
tested on a stub model, not yet run on the GPU:

```bash
python scripts/23_label_fulltext.py profile    # ~31,300 distinct bodies, ~10.5M tokens; no LLM
python scripts/23_label_fulltext.py run        # label + uncertainty + apply + compare
python scripts/16_viewer.py --corpus mediacloud   # read the bodies next to both labels
```

It applies stage 19's prompt, schema, evidence window and temperature unchanged to
every body that passes the quality checks, so a Media Cloud full-text label and a
LexisNexis label mean the same thing. `compare` writes
`outputs/mediacloud_fulltext_vs_headline_report.md`: the headline × full-text
crosstab, which full-text flags explain the changes, agreement by headline
confidence, mentions, year, outlet size and route, disagreement on rows where both
labellers were unanimous (so not noise), and — on stories LexisNexis also holds —
whether the same prompt on two copies of one story agrees, which bears directly on
the LexisNexis over-calling question in the traps section.

**Only headline-`EVENT` stories were crawled, so the comparison measures headline
precision, not recall.** Crawling a random sample of `UNCLEAR` and
`NOT_TORNADO_EVENT` headlines would fill in the rest of the crosstab without any
code change.

The viewer's `--corpus mediacloud` mode shows each body with its quality flags and
the measures behind them, links to the live page and the archived copy, the
headline label beside the full-text label, and a switch (`v`) to exactly the
evidence window the model saw. Single keys record whether the body is the article
(`1`–`3`) and what a reader would label it (`e`/`p`/`n`/`u`) into
`data/interim/fulltext_inspection.csv` — URL, headline and verdict only — and
`compare` reports accuracy against them. **Use `r` (random draw) when the aim is an
estimate**: verdicts reached through a filter such as "labels disagree" are chosen
because they are hard and overstate everyone's error.

**Recoverable failures — `refetch`.** 5,836 of the 6,110 bodies failing a hard
check came from direct fetches, where a dead article now returns the front page or
a consent wall with HTTP 200. Archive copies pass at 98.5%, so:

```bash
python scripts/21_fetch_fulltext.py refetch --dry-run   # candidates by flag and domain
python scripts/21_fetch_fulltext.py refetch             # ~8 h at the 5 s archive interval
python scripts/21_fetch_fulltext.py quality             # score the replaced bodies
```

An archive copy replaces the direct body only if it extracts cleanly *and*
mentions a tornado; otherwise the direct record stays and the attempt is logged in
`data/raw/fulltext/archive_refetch.jsonl`, which makes the command resumable and
retries only transient errors. On a random test of 6 domains, 3 came back as
proper articles. **The 1,070 consent-wall retrievals** (a group of TV-station
sites — ksdk.com, wkyc.com, wnep.com, whas11.com — redirecting to a YouTube
consent page) **are probably not recoverable this way**: the archive's own
snapshot of those URLs is the same YouTube page, and the guard rejects it.

**Then**: export the usable bodies in the shape stage 11 reads, which is what makes
them linkable.

### 2. Re-Assess the news coverage
Finish the GDELT crawl, then analyze the coverage in terms of events and unique headlines. If there are any gains
(which is likely), try to crawl the full text of the articles in GDELT that contain event descriptions. Assess the
overlap between LexisNexis, Media Cloud, and GDELT full-texts.

### 3. Schema design for the assembled corpus

Design the published schema by reusing existing ontologies where they fit, and
defining new terms where the disaster↔text combination has no precedent.
Read
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

### 4. Making the linker more faithful

`src/tornado_dataset/text/linking.py` with `scripts/11_link_articles.py`. Current
approach: a −14/+3 day window as a cheap shortlist, IDF-weighted toponym matching
as the decision, corroborating signals (EF rating, casualty counts, dates stated in
the text, outlet locality) to break ties, plus a second pass that reads dates out
of the text so anniversary pieces are reachable. It links 80% of articles and its
precision is **unmeasured**.

Known weaknesses, roughly in order of expected payoff:

- **Toponym resolution is weak and relies on the cities the tornados passed through. Probably most improvement lies in here.
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

### 5. Human annotation

Three separate measurements are waiting on
human annotation: article-link precision, stage 18/19 label accuracy, and the stage 19
over-calling question in the traps section.

Infrastructure exists. `docs/annotation_codebook.md` defines the labels;
`outputs/annotation/` holds blind sheets drawn by
`scripts/12_sample_annotation.py`; `scripts/14_qa_links.py` already consumes a
`label` column; and `scripts/16_viewer.py` was built to become the annotation UI —
an `/annotate` screen is designed but not implemented for LexisNexis. For Media
Cloud full text, `16_viewer.py --corpus mediacloud` already records body and label
verdicts with one key each (thread 1).

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

### 6. Episode definition

Stage 3 groups tornadoes by SPC's convective day (1200–1159 UTC) and joins those
within 200 km. The 12 UTC cut splits overnight outbreaks, and 200 km is a choice,
not a measurement. Stage 25 compares the alternatives from the literature on the
same hazards, scored against NCEI Storm Events episodes:

```bash
python scripts/24_storm_events.py run       # download (~16 files), join, coverage report
python scripts/25_compare_episodes.py       # ~1 min; outputs/episode_comparison_report.md
python scripts/25_compare_episodes.py --anchor spc   # ~5 min; ..._spc_report.md
```

Full run, 2010–2025. On DAT hazards the current rule keeps 92% of
forecaster-grouped pairs together and splits 7.7% of Storm Events episodes;
widening it to 400 km changes nothing (0.92). Dropping the day boundary does:
space-time 200 km / 6 h reaches 0.96 and 5.9% at almost the same extent (p95 644
against 624 km), with 78 multi-day episodes. The time-only rule (Fuhrmann variant) and
the overlapping-window KDE over-merge (episodes up to ~4,000 km and 226 h).
"Office precision" is ~0.79 for every method — it cannot see over-merging,
which is what the watch reference is for.

Grouping SPC's complete tornado list instead (`--anchor spc`) gives the same
ranking: stage 3's rule 0.94–0.95 in every period. The low early recall on DAT
(0.80 in 2010–2015) is therefore *not* missing tornadoes breaking outbreaks up:
DAT's early sample is small (922 scored hazards) and dominated by three office
episodes of 27 April 2011 (HUN, JAN, BMX) that run from the morning squall line
before 12 UTC into the afternoon supercells, which the day rule cuts in two.
Carried to DAT hazards, SPC-built episodes match stage 3's closely (ARI 0.95 for
the same rule); 11% of DAT hazards have no SPC track and stand alone.
**No change to
stage 3 has been made**: the decision depends on what an episode is for, and
changing it invalidates every `episode_uid` downstream (stage 11 links,
annotation sheets).

Storm Events episodes cannot judge over-merging across offices. The planned
next reference is SPC watch systems, built from county-level watch records:
a forecaster-made grouping that does cross offices, and the unit in which the
threat was communicated to the public and the press — see
[docs/plan_watch_linking.md](docs/plan_watch_linking.md). Physical references
(radar storm tracks, cyclone attribution) were considered and deliberately left
out of scope; the plan says why.

Watch results (stage 26, 2010–2025): 10,040 watches; rules 1 and 3 reproduce
98.9% of SPC's own "replaces" links; 74% of SPC tornadoes were in a watch
(85–95% of EF2+). Watch systems are coarser than every grouping method and watch
sequences finer, so stage 25 reads them as bounds. Against them (DAT anchor):
stage 3 stays within systems (1.00) but keeps only 0.91 of sequence pairs
(0.81 on SPC tracks) — it cuts watch chains, mostly at 12 UTC; space-time
400 km / 6 h scores 0.99 and 0.99; the overlapping-window KDE merges beyond
systems (0.75). This agrees with the Storm Events result: the day boundary is
stage 3's weakness. Still open: the hand checks (`python scripts/26_watch_systems.py sheets`, fill in
`outputs/annotation/watch_*_sheet.csv`, then `check`) and the decision whether
to change stage 3. `python scripts/26_watch_systems.py review` opens both
worksheets on a map (http://127.0.0.1:8800) and saves the labels into them.
The time-repaired DAT ↔ SPC pass (stage 24, built, tested on the real data in
a scratch copy, not run by you) raises DAT hazards with an SPC track from 88.8%
to 95.8%; rerun stage 24 `join` + `report`, then stage 25, to use it. The 237
hazards with no SPC track within 20 km and 72 h are listed in
`data/interim/spc_unmatched_dat_<tag>.csv` for a hand check. Stage 25 now scores DAT
hazards against a Storm Events reference extended through their SPC track
(+687 hazards, the time-repaired ones; `--dat-reference direct` for the old
reference): episodes built on SPC and carried to DAT keep their recall
(space-time 400 km / 6 h 0.97), episodes built on DAT's own times lose it
(0.97 → 0.95; stage 3's rule 0.92 → 0.90) — the cost of DAT's clock errors.

## If you change the pipeline

- `scripts/00_selftest.py` runs in seconds with no network, GPU or credentials.
  Run it after any change to the library modules.
- Every threshold lives in `src/tornado_dataset/config.py`, with the reasoning in
  a comment beside it. Those comments are dataset documentation, not incidental.
- Long stages are resumable through their caches. Prefer resuming to restarting.