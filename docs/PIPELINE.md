# Pipeline detail

## Where the data lives

`data/` is 4.7 GB and not in git; the canonical copy is at
`192.168.106.17:/data/share/geoai/tornado-text-to-trajectory/data`. Point the
pipeline at a local copy or mount with `TORNADO_DATA_DIR` — every stage resolves
through `config.DATA_DIR`, so nothing else needs changing. `config.require_data()`
turns a missing dataset into a message naming the server rather than a
missing-file traceback.

Per-stage documentation for the dataset pipeline. Orientation, setup and the
stage map live in [the README](../README.md); current state and open threads
in [HANDOVER.md](../HANDOVER.md); the schema in
[DATA_MODEL.md](DATA_MODEL.md).

### Text layer

Each tornado is paired with text on two axes — who wrote it (`same_org_as_geometry`)
and when, relative to the field survey (`temporal_class`) — yielding the roles
`oracle`, `official_timely`, `independent_timely`, `independent_retrospective`.
The rules live in one versioned function (`text/tiering.py`) so the corpus can be
re-tiered reproducibly.

- **NWS text is stored in full** (US-government works): Local Storm Reports as the
  timely stream, and the per-tornado section of a storm-survey PNS as the oracle.
  Survey sections are matched to a track by the coordinates they state, and only
  the best-scoring section becomes `primary_survey_of`. A western longitude
  written without its minus sign is restored (`iem.stated_point`).
- **Stage 20 matches DAT and SPC hazards** (stage 15; an SPC hazard by SPC's
  straight line or point) with stage 16's offices and places. LSRs and survey
  sections are matched on each hazard's start time and convective day. For the
  1,164 DAT hazards whose time stage 14 found wrong (881 by whole hours, 378 of
  them on the wrong date; 98 on the same footprint) or missing (185), these are
  the SPC track's (`episode_table.event_times`). With DAT's own, their LSRs fell outside the time
  window or were looked up on the wrong day, and a date-only hazard had no window
  at all.
- **`20_fetch_nws_text.py --cache-only`** reads nothing from the network: it
  builds from the IEM cache, prints what is missing, and writes its tables with
  the suffix `_cacheonly` unless nothing was missing. Product downloads are
  spaced 0.5 s apart, like the list requests, on the project's User-Agent.
- **News is *published* as links and metadata only.** GDELT queries run per
  episode and store links. Article text itself is retrieved and held locally where
  it is needed for analysis — LexisNexis full-text exports, and Media Cloud bodies
  via stage 33 — under the §60d UrhG research exception for text and data mining.
  The distinction is between local processing and redistribution: what leaves this
  project is links plus derived annotations, never the article text.
- **Independent cross-check:** where a survey section matched a hazard and both
  state the value, the survey's EF rating agrees with DAT's on 96.6% (n=5,348)
  and with SPC's on 97.0% (n=631), the death count on 99.4% and 99.8%, the path
  length within ±10% on 80.4% and 70.9% — two descriptions of the same survey,
  compared rather than assumed equal.
- **Coverage stops at 2017-01-01 for news**: 590 of 2,795 episodes predate the
  GDELT DOC API's earliest queryable date and are flagged, not silently empty.

See [`outputs/text_qa_report.md`](outputs/text_qa_report.md), which also records the
measurements behind the retrieval choices (query form, match radii).

### Text that comes with the records — `scripts/24_import_record_text.py`

Offline. Turns two official texts already on disk into TextRefs and TextLinks in
stage 20's schema (`text/records.py`), all `oracle` (tiering v2):

- **Storm Events event narratives** (`storm_events_narrative`, 23,189): one per
  Storm Events tornado row. Storm Events splits a tornado at county and office
  lines, so a long track has several. Each is linked to one hazard
  (`narrative_of`, `link_route`): the DAT hazard it is matched to (stage 14,
  13,093); else, through its SPC track, the SPC hazard that track is (9,065) or
  the DAT hazard it is the closest track of (930, mostly DAT hazards with a clock
  error); else, for a track that is only a secondary link of a DAT hazard, the
  episode (38). 10,598 DAT and 8,367 SPC hazards get a narrative.
- **Storm Events episode narratives** (`storm_events_episode_narrative`, 8,517): the
  office's account of the weather situation, linked to each stage 15 episode its
  rows fall in (`episode_narrative_of`). Storm Events episodes are per office, so a
  large outbreak has several.
- **DAT comments** (`dat_comment`, 9,412 for 7,850 hazards): one TextRef per distinct
  comment of a hazard, its ID resting on the features (`line:<objectid>`,
  `polygon:<objectid>`) that carry it (`comment_of`). Stage 12's `oracle_text`
  column stays as it was.

`mentions_track` flags an event narrative or comment naming a start, an end, a
direction, a crossing or a movement (80% of narratives, 66% of comments) — a coarse
cue, not a judgement of quality. Texts are not merged or deduplicated here: DAT
comments are mostly excerpts of the survey statement (PNS) and narratives edited
versions of it, which stage 25 records. Writes
`data/processed/textrefs_records_<tag>.csv` and `textlinks_records_<tag>.csv`.

### Edits of one account — `scripts/25_find_same_source_edits.py`

Offline, half a minute (three with the sensitivity reruns). A hazard's official
texts are rarely independent: the narrative is often an edited copy of the survey
statement, the DAT comments excerpts of it, a survey LSR a short version. Stage 25
groups, per hazard, the texts that share their wording (`text/same_source.py`).
They count as one account, both when counting independent descriptions and when
a model trained on one would be tested on another. Compared are the hazard's
primary survey section (stage 20, `primary_survey_of`), its LSRs (`describes`),
narratives (`narrative_of`) and DAT comments (`comment_of`).

- **Evidence is wording specific to the tornado.** Texts become lower-case tokens
  ("EF-1" → "ef1"). A run of 5 tokens shared by two texts counts only if it
  occurs in the texts of at most one hazard besides the pair's own. Anything more
  common is a phrase of the language or an office formula ("an NWS storm survey
  found that an EF1 tornado began at"). Each text counts for one hazard, an LSR
  within reach of several for the nearest. Counting by episode instead let
  formulas through that an office repeats for every tornado of one outbreak.
  Counting only single-hazard texts missed the LSRs' templates, because almost
  half of the LSRs are linked to several hazards.
- **Link: at least 10 tokens in shared specific runs** (counted in both texts,
  the lower count used). This is two runs' worth, so one shared place description
  ("2 miles southwest of Whigham") never links. Coverage, the share of a text's
  specific tokens the other shares, is recorded, but decides nothing.
- **Calibrated without hand labels.** Each text of a within-hazard pair is paired
  with a random text of the other's source type and office, of two kinds:
  - from *another episode* of the same year: no copy and no shared topic, a lower
    bound;
  - from *the same episode, another hazard*: same day, office and templates, but
    also real copies between pieces of one tornado and through LSRs linked to the
    wrong tornado, an upper bound; identical texts are excluded.

  The rule is the smallest number of shared tokens, from 10, at which at most
  0.1% of the first set and 1% of the second would link. It comes out at 10.
  The two sets link 0.016% and 0.54% of their pairs, so of the 29,176 linked
  within-hazard pairs (of 172,739), **0.1% to 3.2% are expected to be false**. A
  comparison pair spans two hazards, so it is allowed one hazard more, and both
  kinds of pair are held to the same rule; without that, the comparison sets
  could hardly link and would understate false links.
- **Recall**, without labels either:
  - Edited copies of 400 real texts per source type, matched back to their
    original. Dropping, reordering or inserting a sentence: ≥99%. Changing every
    number: 94%. A random 10% of words replaced: 93%; 30% replaced: 69%, where
    copying fades into paraphrase, which the method does not claim to detect.
    Short texts are the weak spot: a 170-character cut is missed in 17% of cases,
    and a quarter of such cuts and of one-sentence excerpts are too short to
    compare at all.
  - **Real copies:** the comments in the ten hand-saved SPC daily report files
    (`data/raw/spc_reports/`) against the LSR at the same place and minute, which
    SPC copies (cut, office appended, or an earlier version). 95.9% are linked
    (607 of 633; 120 too short).
- **Groups** are connected linked texts of one hazard, since two excerpts of one
  text go back to one account. `bridged` flags a group whose members are not all
  linked directly.
- **No origin is inferred.** Narratives and DAT comments carry no time, an LSR's
  timestamp is the event's, and a hazard has one primary survey section, so no
  linked pair has two publication times. An excerpt, an expansion and a shared
  unrecorded draft also leave the same evidence. What is recorded:
  - `contained_in`: the member covering at least 80% of the text;
  - the representative (`is_representative`): the member covering most of the
    other members' wording, ties broken PNS, narrative, DAT comment, LSR as a
    convention.

  47% of DAT comments and 24% of narratives are contained in another text; the
  representatives are mostly narratives (4,469) and PNS sections (4,197).
- **LSRs.** 21% of the survey LSRs, but 3% of the real-time ones, share an
  account with a survey statement, narrative or DAT comment. Stage 20 tiers every
  LSR `official_timely` by its timestamp, which is the event's time, not when the
  remark was written. The group shows which ones carry the survey's wording.
- **Sensitivity:** run lengths 4, 6 and 8 and common-run cut-offs of 2, 5 and 10
  hazards. Each recalibrates the rule and agrees with the main run on 97.7–99.3%
  of pairs. With no cut-off, 23 shared tokens are needed and agreement is 95.2%.

18,198 hazards with two or more texts hold 89,785 texts in 70,296 accounts (22%
fewer accounts than texts). Writes
`data/processed/same_source_edits_<tag>.csv` (one row per hazard and text),
`data/interim/same_source_pairs_<tag>.csv` (every pair, both coverages),
`manifest_same_source_<tag>.json` and `outputs/same_source_edits_report.md`.

**Checking by eye.** `python scripts/25_find_same_source_edits.py samples` reruns
the method and writes only `outputs/same_source_samples_<tag>.html`
(`text/same_source_view.py`; gitignored). It is one self-contained page of
stratified samples, 25 per stratum (`--per-stratum`, `--seed` for another draw):
- random hazards with two or more texts;
- links just over the rule and pairs just under it;
- links with low coverage;
- survey statement and narrative left apart (paraphrase);
- bridged groups;
- real-time LSRs in a survey account;
- comparison pairs that linked.

The wording the method counted is highlighted:
- shared within an account;
- shared by the pair in question;
- shared only with another account, below the rule;
- greyed out when common to three or more tornadoes.

A pair table gives shared tokens and coverages. Each sample takes a verdict and
a note, kept in the browser and exported as CSV, so a hand check of any stratum
yields a precision or miss rate.

### Importing the LexisNexis exports — `scripts/23_import_lexisnexis.py`

LexisNexis Uni offers no API for this corpus; the articles were exported by hand
as RTF into `data/lexis_nexis_tornado_news/` (`config.LEXISNEXIS_EXPORT_DIR`, so it
follows `TORNADO_DATA_DIR`). Stage 23 parses each file
(`text/lexisnexis.py`, after the R package `LexisNexisTools`) into headline,
source, dates, byline, section, body and the remaining labelled fields, and flags
verbatim duplicates — bodies identical after lower-casing and collapsing
non-word characters, which the export repeats where download batches
overlapped (`dup_group`, `is_duplicate`; Python's `re`, so accented letters stay
word characters whatever pandas' string engine). Writes
`outputs/lexisnexis_articles.{csv,jsonl}` — gitignored, since they hold the
article text — and `data/interim/manifest_lexisnexis_import.json` with the parse
checks (missing dates, empty bodies, bodies whose word count is off LexisNexis's
own `Length` by more than 10%). About 6 minutes for the 24,917 files.

### Linking articles to events

Plan and rationale: [`docs/stage_c_plan.md`](docs/stage_c_plan.md).

An article is matched to the outbreak (and where the evidence allows, the single
tornado) it describes, in four steps: a date window of −14/+3 days as a cheap
shortlist, IDF-weighted toponym matching as the decision, corroborating signals
(EF rating, casualty counts, dates in the text, outlet locality) to break ties, and
a descent to one tornado only where one clearly wins. A second pass reads dates out
of the text so anniversary pieces are reachable at all.

Two properties of the data drive the design and are worth knowing:

- **The window is not a link.** It leaves a median of ~25 candidate episodes per
  article; the toponyms decide.
- **Place names must be weighted and case-matched.** Half of the 29,447 gazetteer
  names belong to exactly one hazard, but *Midway* belongs to 172 — hence the IDF
  weighting. And matching is case-sensitive because the US has towns called
  Enough, Hurricane and March, which otherwise match ordinary prose.

The gazetteer has **two separate place lists per hazard**, and the split matters:

| column | built from | used for |
|---|---|---|
| `places` | 8 nearest populated places | **GDELT query strings only** — frozen, because the query is a cache key for a multi-day sweep |
| `places_matching` | everything within 25 km, plus places over 20k people out to 50 km, plus each county's largest town (~75 names) | **article matching only** |

Keeping them apart is what let the matching set grow ninefold without invalidating
the GDELT cache. Selecting the eight *nearest* names was the single largest cause
of missed links — it kept hamlets like *Buffalo Mop* and dropped *Tuscaloosa* —
and prominence now comes from Census population estimates joined to GNIS by name,
state and location (stage 16). See
[`docs/linking_coverage_analysis.md`](docs/linking_coverage_analysis.md).

**Links are candidates until annotated.** `scripts/40_sample_annotation.py` draws
blind precision, recall and agreement sheets ([codebook](docs/annotation_codebook.md));
`scripts/41_qa_links.py` turns the returned labels into precision per score band
with Wilson intervals, recall, and Cohen's κ, and only then is a publishable
threshold defined.

### The corpus in time

`scripts/42_analyze_news_time.py` writes
[`outputs/news_time_report.md`](outputs/news_time_report.md): corpus volume and
source mix over time, how quickly coverage appears after a tornado, how it decays
by death toll, the anniversary tail, which events get covered at all, and — the
piece carried over from the early prototype — **when each kind of text arrives**.
It reads stage 31's links by episode and stops if they name episodes not in the
current table, as they do until stage 31 is rerun on stage 15's episodes; the
report and the figures below are from August.

That last figure puts NWS products and news on one axis using
`text/tiering.py`, and reproduces at corpus scale what `TEXT_TIER_SUMMARY.md`
found on a single outbreak:

| text | prototype (n=89) | corpus |
|---|---|---|
| NWS Local Storm Reports (`official_timely`) | 0.8 h | 0.0 h (n=27,501) |
| news (`independent_timely`) | 15.4 h | 9.2 h (n=10,094) |
| NWS survey (`oracle`) | 65.0 h | 58.3 h (n=15,447) |
| news (`independent_retrospective`) | 65.0 h | 96.6 h (n=7,376) |

The ordering is the point: field reports land within the hour, news within the
day, the survey days later. Note the news hours are date-resolution (LexisNexis
gives a date, not a timestamp), so compare streams by order and scale, not by the
hour — the report says so where it matters.

### Reading articles — `scripts/viewer.py`

A local Flask app at `http://127.0.0.1:8799` for going through the corpus without
opening an 18 MB CSV. It loads once (~30 s) and then serves instantly:

- **List** with search over headline and source, and filters for year, link
  status, relation, score band and linked/unlinked.
- **Article** view showing every parsed field, the full body with paragraphs, and
  **the matched place names highlighted** — so what the linker keyed on is visible
  rather than inferred.
- **Linked events** with the score split into its place and corroboration parts,
  which signals fired, and whether the link came from the retrospective or
  year-only pass. Clicking a link card shows that event on the map.
- **An interactive map on an OpenStreetMap basemap** — pan, zoom, and click a
  track for its rating, path length, width, casualties, start time, county and
  office. Where the link names a single tornado, that track is drawn boldly and
  the rest of the outbreak recedes to context, so the claim being judged is
  obvious. At street zoom you can see which roads a path crossed, which is what
  makes a place-name match checkable rather than plausible.
- `j`/`k` to move, `/` to search, `#<textref_uid>` deep links.

Leaflet 1.9.4 is **vendored** into `viewer/static/vendor/` rather than loaded from
a CDN, so the app has no third-party runtime dependency; only the map tiles come
over the network, from `tile.openstreetmap.org` with the required
"© OpenStreetMap contributors" attribution shown. Turn the basemap off in the map
bar to work offline or to see the geometry unobstructed.

This is the surface the annotation UI will be built on, since judging a link means
reading the article and the event side by side.

`--corpus mediacloud` opens a second view over the full texts stage 33 retrieved —
see *Inspecting the full texts* below.

### Filtering the Media Cloud corpus — `scripts/30_filter_media_cloud.py`

The Media Cloud export is 491,432 rows of **headline and URL only** — no body, no
lead paragraph. It was collected with the full-text query
`tornado* AND (wind? OR storm? OR rain? OR damage? OR emergency)`, so every row
mentions a tornado *somewhere*, but only 29.5% say so in the headline or URL. A
headline reading "Storm rips through Marshall County" may well be a tornado
report, and from the headline alone there is no way to tell.

Every distinct headline is labelled by a locally hosted LLM and the answer
propagates to its syndicated copies — 45.8% of the export is repeat copy, up to
370 outlets running one headline in a day, so this halves the work and stops one
viral headline from dominating any distribution computed over the corpus. The
representative of each group is the copy with the **longest URL slug**, since the
slug often carries the deciding word.

There is no rule-based decision stage and no trained classifier. Both were
removed on measurement, not taste:

- **The rules** were compared with LLM labels on a stratified sample of 385
  headlines. On the decision that matters — tornado event or not — they agreed
  93.4% after post-stratifying to corpus frequency, but the disagreement ran
  almost entirely one way: the rules called ~1,615 headlines an event the model
  did not, and **missed ~14,106** that it did, recovering only ~70% of the event
  set. That recall gap bought nothing but saved inference.
- **The classifier** would have been trained on LLM labels, making it a lossy
  approximation of the LLM with the LLM's accuracy as its ceiling. On a local GPU
  the whole corpus labels in ~2.5 h, so there is nothing to distil.

The regex cues survive as **audit columns** (`cue_*`, `protected`) for
stratifying validation and as a drift monitor, but they decide nothing.

**Labels.** An exclusive primary label carries the decision; independent flags
carry the detail. Nine mutually-exclusive categories were tried first and were a
mistake — "Opinion: how to prepare for hurricane season" is simultaneously
opinion, advisory and other-hazard, so forcing one choice manufactures
disagreement and makes an inter-annotator κ uninterpretable.

| primary | meaning |
|---|---|
| `EVENT` | headline/URL indicate a tornado actually occurred |
| `PROSPECTIVE` | forecast, watch, warning or risk only |
| `NOT_TORNADO_EVENT` | clearly not a report of a tornado occurring |
| `UNCLEAR` | headline and URL genuinely do not settle it |

Flags: `is_outbreak`, `is_retrospective`, `is_fact_check`, `nonmet_sense`,
`other_hazard`.

`UNCLEAR` is load-bearing. Headlines under-determine the answer, and without an
abstention the model must guess — turning a knowable quantity into a silent
error. With it, "cannot be decided from a headline" becomes a measured stratum:
an honest denominator for any recall claim, and the obvious population to hand a
human annotator.

**The protect rule** — a row naming `tornado*`, `severe weather`, `inclement
weather`, `winds`, `storm*`, `flooding`, or a weather word with `power outage`,
in the headline *or* the URL — is enforced as a guard on the `nonmet_sense` flag.
The model never gets the last word on it, and it is re-checked on what is written
to disk. Protection is promoted to the headline *group*, because labels are
computed per headline while the terms are read from headline **and** URL, and
copies of one headline have different URLs.

**Two temperatures, for two different questions.** Labels are produced at **T=0**
— classification wants the argmax, and greedy decoding is what makes a rerun
reproducible. (vLLM is not bitwise deterministic even at T=0, since continuous
batching changes floating-point reduction order, so the response cache rather
than the temperature is what actually guarantees reproducibility.) Uncertainty is
measured by re-labelling a random 10% k=3 times at **T=1.0**, the model's
unmodified predictive distribution; sampling below 1.0 sharpens the very thing
being measured, and *varying* temperature across the draws would confound the
model's uncertainty with temperature's effect on entropy. `modal_share` in
`mediacloud_consistency.csv` is the resulting per-row agreement — a far better
uncertainty signal than the model's self-reported `conf`, which is not calibrated.

```bash
ssh -N -L 8000:localhost:8000 you@your-server
python scripts/30_filter_media_cloud.py profile   # cue coverage, no LLM needed
python scripts/30_filter_media_cloud.py run       # label + uncertainty + write
```

`--api-base`, `--model` (default: ask the server which model it has loaded),
`--concurrency` and `--thinking` control the client. `--limit N` is a smoke test.
`--provenance` adds a note telling the model every item matched a tornado
full-text search; it is **off** by default because it biases toward `EVENT`, and
the flag exists so that can be measured as an ablation rather than argued about.
`sensitivity` labels one subset across T ∈ {0, 0.3, 0.7, 1.0} to check the T=0
choice sits on a plateau.

**Not yet done:** no human ground truth exists for this corpus. Every figure the
stage reports is model output, so precision and recall against human labels still
require a blind, stratified annotation sample — the `UNCLEAR` stratum and the
rows with `modal_share < 1.0` are where it should be concentrated.

### Filtering the LexisNexis corpus — `scripts/32_filter_lexisnexis.py`

Same method and the same label vocabulary as stage 30, so the two corpora stay
comparable for the overlap study; the shared machinery lives in
[`text/labelling.py`](src/tornado_dataset/text/labelling.py). Three things differ,
and each changes a design decision.

**Full body text is available.** 24,917 rows collapse to **20,138 distinct
bodies** (the labelling unit) carrying 22,896 `textref_uid`s (the downstream join
key). Median body is 525 words. The headline under-determination that made
`UNCLEAR` load-bearing in stage 30 largely disappears — so if `UNCLEAR` stays
common here, something is wrong with the evidence window or the prompt rather
than with the corpus.

**The hard question is aboutness, not detection.** 15.7% of bodies mention a
tornado exactly once — a lawsuit over failed sirens, an obituary, a charity
fundraiser, and literally *"The Week contest: Tornado wedding"*, a caption
competition. The tornado is usually real; the article is about something else.
That is `NOT_TORNADO_EVENT` with `is_passing_mention`, a flag rather than a
primary category, so the primary axis stays aligned with Media Cloud's. Two more
corpus-specific flags: `is_press_release` (22.7% of bodies come from press-release
and financial wires) and `is_roundup` (round-ups drive linker fan-out, which is
capped at `LINK_MAX_PER_ARTICLE`).

**Sending whole bodies is 17.8M tokens and mostly wasted**, but blind truncation
is worse than it looks: 18.2% of articles never say "tornado" in their first 150
words, so a prefix can miss the only evidence there is. The default `windows`
mode sends the lede plus ±40 words around each mention, up to 6 spread across the
article, with omissions marked `[…]`. It averages **257 words — cheaper than a
400-word prefix** while covering the whole article.

Which window is right is measured, not assumed:

```bash
python scripts/32_filter_lexisnexis.py window
```

labels a mention-count-stratified sample under all four modes and reports each
one's agreement with `full2000`, separately for single-mention bodies. Pick the
cheapest acceptable mode and record it.

The protect rule is reused but evaluated on **headline + lede only** — across 525
median words virtually every article contains "storm", so a full-body protect
rule is vacuously true and stops being a guard.

```bash
python scripts/32_filter_lexisnexis.py profile    # corpus shape, no LLM
python scripts/32_filter_lexisnexis.py window     # choose the evidence window
python scripts/32_filter_lexisnexis.py run        # label + uncertainty + write
python scripts/32_filter_lexisnexis.py crosstab   # validate against stage 31
```

Both stages take `--tag`, and anything experimental should use it: output paths
derive from it, so a smoke test cannot overwrite a real run. `--limit` bounds only
how much of the corpus is *read*, which is not the same protection. The response
cache is shared across tags, so a tagged run still inherits every answer already
paid for.

### Full text for the Media Cloud corpus — `scripts/33_fetch_fulltext.py`

Media Cloud supplies headline, URL and date but no body. That bounds what stage 30
can decide and, more importantly, leaves its 48,741 `EVENT` stories **unlinkable**:
stage 31 matches toponyms in the article text, so without a body they cannot enter
the dataset at all. Retrieving them would roughly triple the linkable corpus over
the 12,077 LexisNexis articles available today.

**The Media Cloud API is not a route.** It extracts and indexes article text so
boolean search can run against it, but the Story Guide states the text "is not
available for download due to copyright restrictions", and the documented response
carries no `text` key. Crawling is the only option.

A 594-URL pilot, stratified by year band × domain size, measured what is
achievable — and corrected two expectations:

| | |
|---|---|
| Retrieved (1 s archive interval) | 319/594 = **54%** |
| Of the 275 failures, archive *connection* errors | **250** |
| Of the 275 failures, genuinely no archived copy | **16** |
| Same URLs at a 5 s archive interval | 10/12 vs 6/12 |

The binding constraint is **patience, not availability**. At 5 s the connection
errors disappear, putting the ceiling near 85-90% — about 41,000 articles rather
than 26,000. The cost is time: roughly half the corpus routes through the archive,
which is serialised globally, so a full pass runs well over a day.

Retrieval bias turned out **milder than predicted**. Small outlets retrieve at 49%
against 57% for large ones, with overlapping intervals, so local coverage survives
about as well as national. Age matters more but gradually: 42% (2010-2015) → 62%
(2021-2025).

One finding matters specifically for running this from Europe: **US local news
sites return HTTP 451 to EU traffic**, and every one of those recovered through the
archive, which serves from the US. Left unhandled it would have been a silent,
systematic hole in exactly the local coverage the project needs.

```bash
python scripts/33_fetch_fulltext.py pilot          # measure, ~600 URLs
python scripts/33_fetch_fulltext.py crawl          # the full pass, resumable
python scripts/33_fetch_fulltext.py status         # progress; safe during a crawl
python scripts/33_fetch_fulltext.py crawl --retry-failed   # transients only
```

`crawl` appends every outcome to `data/raw/fulltext/retrievals.jsonl` as it happens,
so an interrupted run loses at most the article in flight and a restart skips what
is done. `--retry-failed` re-attempts only failures that describe the network
(connection errors, 429s), never settled ones — a robots disallow, a missing
snapshot, a paywall.

Politeness is structural, not decorative: `robots.txt` is honoured per domain
including `Crawl-delay` (a domain asking for 300 s yields one article and the rest
are recorded as skipped, rather than stalling a worker for days); requests to one
domain are serialised while domains run in parallel; and archive.org is throttled
globally, because it is a single host no matter which publisher an article came
from — the first pilot ignored that and had all 271 of its lookups rejected.
Paywall teasers and bot-blocks are recorded as failures rather than accepted as
short articles. Nothing circumvents a block.

**Storage and publication differ.** Retrieved text is held locally for text and data
mining under §60d UrhG, which implements EU DSM Art. 3 and cannot be reserved
against by rights holders for research use. What the project *publishes* stays what
it always was: links and derived annotations, never the article text.

### Gating the linker

`scripts/31_link_articles.py --labels data/processed/lexisnexis_article_labels.csv`
links only `EVENT` articles. The rest are **recorded, not dropped** — they get
`link_status = filtered_<primary>`, because `article_status_*.csv` is a complete
census of the corpus that the report and the viewer both read. An article stage 32
did not judge is still linked, and counted, rather than silently discarded.

The existing regex heuristics in `classify_scope` are superseded but kept: they
still populate the `scope` column, and their disagreement with the model is a free
drift monitor.

Gating is one-directional — once the linker runs gated, a filter false negative
becomes invisible. Run `crosstab` **before** re-running stage 31: it compares the
labels against the ungated `link_status` already on disk and lists both
disagreement directions. Its first run already showed that several `EVENT`
articles the linker could not place are non-US tornadoes (Sechelt BC, Ayr Ontario,
a Puerto Rico F4) that DAT structurally cannot cover.

### Exploring the data

`scripts/18_analyze_events.py` writes
[`outputs/hazard_analysis_report.md`](outputs/hazard_analysis_report.md): what the
dataset holds and how representative its surveys are. SPC's tornado list is the
population and DAT the surveyed subset, so every figure shows both: the
population in grey, DAT in blue (DAT and SPC hazards: blue and orange). Times,
ratings, lengths and casualties are SPC's for both, one record for the comparison,
free of DAT's clock errors. Sections:
1. the way from SPC's tornadoes to the dataset's hazards, every count reconciled;
2. DAT coverage per year;
3. **representativeness**: the share of tornadoes with a DAT survey by rating,
   season, time of day (local solar), track length, deaths and Census division,
   within three eras, so that adoption over time does not pass for a property of
   the category;
4. season, time of day and track length;
5. density and DAT coverage on an equal-area map;
6. deaths from SPC's record, with the ten deadliest tornadoes;
7. which official texts each hazard has (`text/official.py`: survey statement,
   narrative, DAT comment, survey and real-time LSR) and how many independent
   accounts (stage 25). News is left out: it is not official text.

Each section opens with a finding computed from the data; longer tables are in
collapsible blocks. Census divisions come from `gazetteer.census_division`.

`scripts/19_event_map.py` writes `outputs/hazard_map.html`, a single file (~8 MB,
no build step) showing every hazard over an **OpenStreetMap basemap**, as in the
watch hand check: DAT's surveyed tracks solid, SPC tornadoes without a DAT survey
dashed (SPC's straight line, or a hollow dot where SPC records no end). Controls:
- **by month or by day**: a slider with play button, a date to jump to, and a
  window (this month or day / so far this year or month / everything so far). Day
  steps run over the 2,837 convective days with at least one hazard, not every
  calendar day;
- filters for rating, hazard source and official text, and the basemap on or off;
- hover details: source, place, office, the record's casualties, episode, texts
  and accounts;
- a table of the deadliest and strongest hazards in view.

**Clicking a hazard shows its whole episode** and zooms to it, for checking how
tornadoes were grouped (Esc returns). Dates follow `episode_table.event_times`, so a
DAT hazard with a repaired clock sits on its SPC day. Surveyed **damage
footprints** appear from zoom 11, where a polygon is more than a smudge; at street
zoom a track can be checked against the roads and towns it crossed. A footprint
smaller than the simplification tolerance becomes a dot rather than vanishing.

Leaflet 1.9.4 is embedded from the viewer's vendored copy, so the page needs no
CDN; only the tiles come over the network, from `tile.openstreetmap.org` with the
required attribution. The tiles are shown in greyscale (inverted in dark mode) so
the tracks lead. The tile servers refuse requests without a referring page, which
a file opened from disk does not send: serve `outputs/` (below). Without tiles,
offline or with the basemap off, the map draws state outlines instead and says
why.

The tiles fix the projection: **Web Mercator**, which enlarges northern areas.
Compare densities on stage 18's equal-area maps, not here. Tracks are simplified
(60 m) and projected in Python to integer world pixels at zoom 14 (`geo/pixels.py`,
`mercator_world`, about 7.5 m per unit), and drawn on one canvas above the map. The
browser only scales them by 2^(zoom − 14), which keeps 20,000 hazards interactive.
Stroke widths are divided by the scale so lines keep their screen width, and each
track carries a bounding box so off-screen work is culled.

Ratings use one validated single-hue ordinal ramp (`src/tornado_dataset/viz.py`),
shared by the figures and the map. The dark-mode ramp is its own set of steps
chosen for the dark surface — not the light ramp flipped — so **darker means
stronger in light mode and brighter means stronger in dark mode**; the map's
caption follows the active theme rather than asserting one direction.
EF4 and EF5 share the top class — the conventional "violent" grouping, and also
the number of steps the ramp supports while keeping adjacent steps distinguishable.
Unrated records are grey, never a ramp step: a missing rating is not a weak one.

To view the map locally:

```bash
python -m http.server 8791 --directory outputs
```


### Rebuilding GDELT from cache — `scripts/21_fetch_gdelt.py --cache-only`

Every GDELT response is cached under `data/raw/gdelt/`, so the tables can be
rebuilt without touching the network. `--cache-only` skips any query that was
never fetched instead of requesting it, which matters because a partial sweep
would otherwise stall for days on the remainder at one request per five seconds.

Skipped queries are counted as `uncached_queries` and `episodes_fully_uncached`
in the manifest, kept separate from `failed_queries`. The distinction is the same
one `query_articles` already makes between `None` and `[]`: "not attempted",
"refused" and "genuinely empty" are three different facts, and a rebuild that
conflated them would report partial coverage as complete.

### Labelling a second headline corpus — `30_filter_media_cloud.py --source`

GDELT is the same shape as Media Cloud — headline, URL, date, outlet, no body —
so it needs no separate labeller, only a loader that renames its columns.
`--source {mediacloud,gdelt}` selects the input and the output prefix; the dedup,
cues, prompt, protect rule and label vocabulary are identical, which is the point:
two corpora labelled by different code could not be compared.

Each source keeps its own response cache. The prompt embeds the URL and the date,
so the same headline in two corpora produces different prompts and different cache
keys — a shared cache would buy nothing, and renaming the existing one would
orphan the answers already paid for.

### The corpus atlas — `scripts/43_corpus_atlas.py`

Replaces the retired pairwise overlap stages (`legacy/`). Run it twice; the two scopes answer
different questions and write to different files:

```bash
python scripts/43_corpus_atlas.py                 # what was collected
python scripts/43_corpus_atlas.py --events-only   # what is usable  <- the relevant one
python scripts/43_corpus_atlas.py --probe         # + ask GDELT about missed stories
```

`--events-only` restricts to stories labelled `EVENT` and writes
`corpus_atlas_events_report.md`; the unrestricted run writes
`corpus_atlas_report.md`. Each report states its scope in its first line.

Compares all three news corpora as a set. Supersedes the pairwise overlap stages, which are
retained in `legacy/` until the atlas has run against a labelled GDELT.

Three design points, each fixing something the pairwise scripts got wrong:

**One unit.** The corpora natively deduplicate by body (LexisNexis), by title
(Media Cloud) and not at all (GDELT). Comparing them natively produced a published
figure measuring URLs against titles. The atlas imposes `normalised title +
publication date`, the only identity all three can produce, and keeps the native
key alongside for within-corpus statements.

**Method recorded per edge.** Media Cloud and GDELT both publish URLs, so their
identity is read directly; LexisNexis publishes none, so its edges are inferred
from headline, date and outlet. The two are never pooled.

**Union from connected components**, not from subtracting pairwise intersections
— matching is many-to-many and transitive across three corpora.

`normalise_url` keeps the identifying part of the query and strips only known
tracking keys. Dropping the query wholesale merged `ktbb.com/post/?p=…` (454
articles) and `tulsaworld.com/…/articlepath.aspx?id=…` (2,253) into single
identifiers that then matched indiscriminately, fabricating 6,559 of 14,018
Media Cloud ↔ GDELT edges.

### Wikipedia — `scripts/26_…` to `29_…`

English Wikipedia enters twice: as a text source, and as an outside yardstick for
the news corpora. US tornadoes only, inside the dataset window.

- **Stage 26 (discovery).** Finds the dedicated tornado articles, outbreak
  articles and yearly "Tornadoes of <year>" pages through six independent
  channels, pins each page to one revision and stores its wikitext. The "List of
  … tornadoes" pages are parsed into a **census** (one row per confirmed
  tornado, with its NCEI event id) — lookup only, never text, since a list row
  paraphrases the NCEI narrative it cites.
- **Stage 27 (reference coverage).** Every news article those pages cite is
  matched against the LexisNexis export (title, syndicated title, full text via
  publisher or archive.org). A blind hand-check measures each match tier;
  `outputs/wikipedia_reference_coverage_report.md` has the figures, and the
  labels are kept in `outputs/annotation/wikipedia_ref_handcheck_labels.csv`.
- **Stage 28 (passages).** Cuts the pinned revisions into text records:
  `tornado_article` and `tornado_section` (one tornado → hazard level),
  `outbreak_overview` and `yearly_event` (→ episode level). Each record keeps the
  text, revision permalink and licence (CC BY-SA 4.0, so the text may be stored),
  the event date, infobox facts, the NCEI event ids its own references cite, and
  the independence axes. Wikipedia is never the surveying organisation; a
  revision at least 90 days after the event is `post_survey`, so these are
  `independent_retrospective`. `derived_from_oracle` flags passages whose
  citations are mostly NWS products — a provisional rule until the text can be
  compared with the NCEI narratives.
- **Stage 29 (cited news).** The cited news articles LexisNexis does not hold
  become text records of their own (`collection = wikipedia_citations`), with
  or without text; the ones it holds go to a cross-reference table with the
  LexisNexis `textref_uid`. Each fetched text gets a `text_quality` (good ·
  doubtful · unusable · none) from the cited headline and the known failure
  pages (consent walls, site fronts, the same text back for different
  citations, another article altogether); syndicated copies share a
  `story_id`; the citing passages are written out as a long table, each with
  its event date and NCEI ids, as link hints. Bodies stay in `data/`
  (copyright); the timing axis is provisional until linking.

```bash
python scripts/26_discover_wikipedia.py
python scripts/27_wikipedia_reference_coverage.py extract
python scripts/27_wikipedia_reference_coverage.py fetch      # resumable, hours
python scripts/27_wikipedia_reference_coverage.py match
python scripts/28_wikipedia_passages.py                      # no network
python scripts/29_wikipedia_cited_news.py                    # no network
python scripts/browse_wikipedia.py                           # browse it all at localhost:8001
```

`browse_wikipedia.py` loads the Wikipedia tables (passages, cited news, the
citations between them, pages, refs, census) into one SQLite file,
`data/processed/wikipedia_browse.db`, with full-text search on the texts, and
serves it with [Datasette](https://datasette.io): click a value to filter,
facet counts above each table, one page per record with its full text. It binds
to 127.0.0.1 only, since the cited news texts are copyrighted.

Linking the passages and cited articles to DAT hazards is not done yet; it needs
the hazard tables.


### Full-text quality — `33_fetch_fulltext.py quality`

Offline. Retrieval `ok` only means extraction produced enough words that are not
an obvious paywall; `quality` asks whether the body is the article the headline
names. Hard flags decide `quality_ok`: `no_tornado_mention` (Media Cloud's own
`tornado*` query matched the page, so a correct body should mention one),
`redirected_home` (a soft 404 to the front page), `template_body` (one off-topic
page served under many headlines) and `not_english`. Soft flags are reported only:
`title_mismatch`, `high_boilerplate`, `very_long`.

`title_mismatch` began as a hard flag and was demoted on evidence: the articles it
rejected on its own mentioned tornadoes *more* often than passing ones, because
pages are retitled as stories develop. The same test — do the rejected bodies
mention a tornado? — is the one to rerun after changing any threshold.

The report names articles by URL and headline only and never quotes a body: it is
tracked in git, and the project publishes links and derived annotations, not text.
`report` regenerates the coverage report from the store without crawling.

`refetch` then tries the archive for every *direct* body failing a hard check —
the crawl never did, because extraction had technically succeeded. It is
sequential (archive.org is throttled globally anyway), resumable, and conservative
about the store: a copy is appended, superseding the direct record, only when it
extracts cleanly and mentions a tornado; anything else goes to
`data/raw/fulltext/archive_refetch.jsonl` and the direct body stays. Records it
writes carry `note = "archive_refetch: …"`, which the coverage report counts.
`--flags` restricts it to bodies failing particular checks, `--dry-run` shows the
candidates without fetching. Re-run `quality` afterwards, then stage 34 — cached
answers mean only the replaced bodies cost model calls.

### Labelling the full texts — `scripts/34_label_fulltext.py`

Stage 32's prompt, JSON schema, evidence window (`windows` by default) and token
budget, applied unchanged to the Media Cloud bodies, so a full-text label means the
same thing in both corpora. Same subcommands and guarantees as stage 32: `label`
at T=0 over distinct bodies, `uncertainty` (k=3 at T=1 on 10%), `apply` to
propagate to every story under the protect invariant, `run` for all of it, `--tag`
for isolation, answers cached in `data/interim/mediacloud_fulltext_llm_cache.jsonl`.

Only bodies passing every hard quality check are labelled (`--include-flagged` to
override): a front page labelled as though it were the article would surface as a
spurious disagreement. The labelling unit is the distinct body; when one body sits
under several headlines, the representative is chosen after sorting by URL, so the
headline the model sees does not depend on crawl order.

`apply` writes `data/processed/mediacloud_fulltext_story_labels.csv` — one row per
story, the stage 30 label under `hl_` and the full-text label under `ft_`, no text.
`compare` reads it and writes `outputs/mediacloud_fulltext_vs_headline_report.md`.
The comparison functions live in `tornado_dataset.text.fulltext_corpus`
(`primary_crosstab`, `flag_agreement` with Cohen's κ, `agreement_by`,
`transitions`, `cross_corpus`), so they can be used from a notebook as well.

The crawl covered headline-`EVENT` stories only, so the report measures headline
**precision**; it says so in its scope line, and adapts if non-`EVENT` stories are
ever crawled.

### Inspecting the full texts — `scripts/viewer.py --corpus mediacloud`

Filters for quality (pass, fail, any single flag), full-text label, headline versus
full-text agreement, route, years, shared bodies and inspected/not. The article view
shows the quality flags with the measures behind them, links to the live page and
the archive copy, both labels side by side, other headlines carrying the same body,
and the body with tornado mentions highlighted; `v` switches to the exact evidence
window the model saw, `m` jumps between mentions.

Verdicts are one key each — `1` right article, `2` wrong page, `3` partial; `e`, `p`,
`n`, `u` for a label — appended to `data/interim/fulltext_inspection.csv` with the
active filter and whether the article was drawn at random (`r`). Stage 34's
`compare` reports headline and full-text accuracy against them, separately for
random draws, because only those support an estimate.

### Official tornado records — `scripts/13_fetch_references.py`, `14_match_references.py`

Stage 13 downloads the newest `StormEvents_details-*.csv.gz` per year from
<https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/> into
`data/raw/storm_events/` (NCEI revises files in place, so the newest creation
stamp is discovered from the listing; provenance in `provenance.jsonl`). Stage 14
matches every tornado row to DAT hazards within 5 km of the track and 30 min of
its interval — Storm Data times are local *standard* time all year and converted
with `CZ_TIMEZONE` — and writes `data/processed/storm_events_links_<tag>.csv`
(`EVENT_ID`, `EPISODE_ID`, `WFO`, `hazard_uid`, distance, gap, ranks).
Rows are county segments; `load_tornadoes` chains them into whole tornadoes by
following each row's `TOR_OTHER_*` pointer to the row in the named office and
county within 30 min (`TORNADO_KEY`), and joins episodes that share a tornado
(`LINKED_EPISODE`) — which spans offices only where a tornado crossed between
them. Stage 17's `outputs/events_qa_report.md` reports per-year completeness in
tornadoes, both directions, in its section on the official records. One hazard can match several rows; the closest
(`rank_for_hazard == 1`) gives the hazard's reference episode, and stage 51
scores against both `EPISODE_ID` and `LINKED_EPISODE`.
`--from-dir` reads details files from elsewhere, e.g. ones downloaded by hand.

SPC's `*_actual_tornadoes.csv` (one reviewed record per whole track) is **saved
by hand** into `data/raw/spc/`: spc.noaa.gov's robots.txt disallows every automated
client, so stage 13 never contacts it. Open <https://www.spc.noaa.gov/wcm/> in a
browser, download the `YYYY-YYYY_actual_tornadoes.csv` with the latest end year
(not `all_tornadoes`, which holds segments), and save it unchanged; stage 13 prints
these steps when the file is missing and records the saved file's size and SHA-256 in
`data/raw/spc/provenance.jsonl`. SPC's daily storm-report comments were checked and
left out: on ten sample days, 94% are the IEM LSR remarks stage 20 already holds
(half of them cut at ~170 characters), the rest earlier versions of them. Stage 14 keeps
`sg == 1` records in the window, converts SPC's CST to UTC, and matches them to
DAT hazards by the same rule (`data/processed/spc_tornado_links_<tag>.csv`). It
also matches every Storm Events row to its closest SPC track, which checks the
`TOR_OTHER_*` chaining: a chain should land on exactly one SPC tornado
(`data/interim/spc_chain_crosscheck_<tag>.json`, and stage 17's report).
Those row ↔ track pairs are kept (`data/processed/spc_storm_events_links_<tag>.csv`):
they give each SPC track its Storm Events episode for stage 51's `--anchor spc`.
A **second pass** takes the DAT hazards the strict rule leaves without an SPC
track and links each to an SPC track within the same 5 km whose start differs
by a whole number of hours, 1 ≤ |k| ≤ 48, to within 10 min
(`--repair-max-residual-min`, `--repair-max-offset-h`; `--no-time-repair`
skips it). These are DAT clock and date errors — the local clock stored as UTC
(+4…+7 h), daylight saving (±1 h), a wrong date (±24 h) — and the offsets pile
up on the minute, which random coincidences do not. The links are appended to
the same file with `link_method = time_repaired`, `time_offset_h`,
`offset_class` (its cause, `spc_tornadoes.offset_class`), `residual_min`,
`spc_already_linked` (the SPC track also has a first-pass DAT hazard: probably a
second survey) and `ef_agrees`; first-pass rows carry the same columns with
offset 0, and every row an `id_date` check (does a date written in DAT's
free-text `event_id` side with SPC or with DAT). DAT's own times are not
changed. Stage 17's report checks the pass three ways that do not use the time field:
the residual distribution against its far-from-the-hour density (an upper
bound on chance pairs), rating agreement against the first pass and against
chance (from which the share of wrong pairs follows), and the `event_id` dates.
A **third pass** (`spc_tornadoes.footprint_links`) takes the DAT hazards both
passes leave unlinked and links each to an SPC track that no DAT hazard has when
both ends of SPC's track lie within 1 km of DAT's and the starts are at most 72 h
apart. DAT drew its track through the survey's coordinates, which SPC also
records, so the two coincide to metres (median 23 m for the farther end) while
the time is wrong in a way the second pass does not cover: 00:00 entered for an
unknown time, a date three days off, an offset that is not whole hours. 98
hazards; ratings agree on 97%, as in the first pass. Unlinked, each was counted
twice: as the DAT hazard, in no episode, and as an SPC hazard. `link_method =
footprint_match`, `endpoint_m`, `time_offset_h`, `offset_class` (`dat_midnight`,
`whole_hours`, `other`). Beyond 72 h, and for DAT hazards with no time, ratings
agree on about 60% and the pass is not applied.
What is still unmatched goes to `data/interim/spc_unmatched_dat_<tag>.csv`
with its nearest SPC track within 20 km and 72 h, for a hand check.
SPC's `om` is a per-year number up to September 2007 and a text identifier
(`YYMMDDHHMM-NN`, start time in CST plus a sequence) after; `spc_id` keeps it as text.
`--spc-file` uses a file from elsewhere; without one, the SPC part is skipped.

Hazards built from damage polygons alone (stage 12, `geometry_source = polygon`)
are matched by their polygons. Most carry a time and go through both passes like
any hazard; those whose DAT survey gives only a date are matched by the same
distance and an official start date within a day (`link_method = date_only`,
`storm_events.MATCH_DATE_DAYS`), for Storm Events and SPC alike. Every SPC link
carries `hazards_on_track`, the number of DAT hazards whose closest SPC track it
is: above 1, one tornado is in DAT more than once — typically a polygon-only
hazard beside the line hazard of the same tornado, or a track drawn in separated
pieces. They are flagged, not merged; stage 17 counts them.

### Episodes — `scripts/15_build_episodes.py`

Offline. Groups SPC's complete tornado list (stage 14's `spc_tornadoes.csv`) by
single linkage within `config.EPISODE_MAX_DISTANCE_M` (400 km, closest points of
the straight tracks) and `EPISODE_MAX_GAP_H` (6 h, end of one tornado to start of
the next), with no day boundary — the rule stage 51 compared with the
alternatives.

**SPC is the population: every SPC episode is published** (4,325), and `has_dat`
flags the 2,130 holding a DAT survey. Publishing only those would make coverage
follow DAT's adoption (10 such episodes in 2010, 212 in 2025) and drop outbreaks
such as Joplin, 22 May 2011. Counts and distributions use all episodes; a user
wanting surveyed tracks filters on `has_dat` (episodes) or `hazard_source`
(hazards).

The hazards of an episode come from two sources:

- **DAT** (`hazard_source = dat`): each DAT hazard takes the episode of its closest
  SPC track (stage 14's links, time-repaired, footprint and date-only ones included).
- **SPC** (`hazard_source = spc`, 8,346): an SPC tornado with no DAT link at all is a
  hazard of its own, `data/processed/spc_hazards_<tag>.csv`/`.geojson`, with SPC's
  straight start→end line (`geometry_source = spc_line`; `spc_point` for the 1,530
  SPC gives no end for). An SPC track linked to a DAT hazard without being its
  closest (1,010; median distance 0 m — mostly a piece of the same tornado) is not,
  or one tornado would count twice. `data/interim/spc_episodes_<tag>.csv` records
  each track's `role`.

A **DAT hazard with no SPC track** (357) is in no episode: counting it as one would
add single-hazard episodes the official record does not confirm and count 44 probable
duplicates twice; dropping it would hide what DAT holds. It stays in the hazards
table, `in_spc` false, with `spc_match_status` and its nearest SPC track
(`time_mismatch`, `probable_duplicate`, `spc_far`, `no_spc_nearby`,
`untimed_no_spc`).

Outputs: `data/processed/episodes_<tag>.csv` (first and all convective days, SPC
start and end, `n_hazards`, `n_dat`, `n_spc_hazards`, `n_spc`, `n_spc_ef1plus`,
`n_spc_unrated`, SPC casualties, DAT casualties and rating where it has DAT,
offices from DAT and Storm Events, member IDs) and `hazard_episodes_<tag>.csv`
(every DAT and SPC hazard → episode, SPC track, how it was matched, status, and
its times).

**A hazard's times** are in `hazard_episodes_<tag>.csv`, from one rule
(`episode_table.event_times`): `begin_utc`, `end_utc`, `convective_day`, and
`time_source`. A DAT hazard whose time stage 14 found wrong or missing takes its
SPC track's start and end (`spc_track`, 1,164); every other hazard keeps its own
(`dat`, `spc`). A DAT end before the start or more than 5 h after it has a
mistyped date: where its clock time gives at most 5 h it is kept on the start's
date (`end_repaired`, 314), otherwise the end is left empty, as for the 1,033
polygon-only hazards DAT gives no end for (1,162 empty in all). The hazards
table's `time_begin_utc` and `time_end_utc` stay as DAT entered them.
Episode IDs hash the method and the member SPC tracks, so they are stable across
reruns. The hazards table carries no episode; stages read it through
`episode_table.hazards_with_episodes`, `episode_of` or `geography`. Stops if
stage 14's outputs are missing rather than grouping DAT alone. Stage 17 reports the
result.

### Geography — `scripts/16_enrich_geography.py`

For every DAT and SPC hazard, from the hazard's geometry in equal-area metres:

- **Counties** from the NWS county polygons of the hazard's year (IEM, one snapshot
  per year, as offices are reorganised). A county counts when it holds
  `config.COUNTY_MIN_SHARE` (5%) of the track, or `COUNTY_MIN_TRACK_M` (1 km) of it
  — of the damage area for a hazard without a track line — and the county with
  most of it always counts. The outlines are simplified for web display, so without
  the threshold a track along a county line picked up its neighbour's office too
  (323 hazards with several offices by the county join, against 282 by Storm
  Events; now 286). No county intersecting → the nearest, `county_fallback`.
- **WFO** (`gazetteer.choose_wfo`): DAT's own field, else the linked Storm Events
  segments (stage 14; the office where the tornado began first), else the county
  join. `wfo_source` says which; `wfo_all` keeps every office of every source, and
  `wfo_dat`, `wfo_storm_events`, `wfo_spatial` each source's. The three agree on
  98.5–99% of DAT hazards; every hazard has an office.
- **Places** from GNIS: `places` (the eight nearest within 25 km — GDELT's query
  terms, unchanged so its cache stays valid) and `places_matching` (see *Linking
  articles to events*), ranked by Census 2024 population. A Census place's
  population goes to the same-named GNIS place nearest its Census Gazetteer point
  (`gazetteer.assign_population`), not to every place of that name: a join by name
  and state alone gave a hamlet called Oxford in Amite County the population of
  Oxford, Lafayette County, and 1,670 names occur more than once in a state.
  Census legal suffixes ("Tuscaloosa city") are stripped from Census names only;
  stripping them from GNIS too had left Oklahoma City, Kansas City and 700 other
  "… City" places without a population.

Stage 16 also measures how well a straight SPC line stands in for a surveyed track:
for the 10,861 DAT hazards with an SPC track, the SPC line finds 98.6% of the
counties and 98% of the places of the DAT geometry (stage 17, "Geography"). Names
and populations are today's, not the event year's. Downloads and caches the NWS
county polygons, GNIS, and the Census population and Gazetteer files in
`data/raw/gazetteer/` when missing. Writes `data/processed/hazard_geography_<tag>.csv`
(no episode: join `hazard_episodes` or use `episode_table.geography`).

### Comparing episode definitions — `scripts/51_compare_episodes.py`

Offline and read-only towards the pipeline. Runs the former convective-day rule
(200 km, `convective_day 200km`) and the alternatives in
`tornado_dataset.dat.episodes` on the same hazards: space-time single linkage
(no day boundary; with unlimited distance and a 6 h gap, a variant of the
outbreak-sequence rule of Fuhrmann et al. 2014 — all ratings chain, the gap runs
end to start, no minimum count), ST-DBSCAN (Birant & Kut 2007) and kernel-density
regions per convective day (Shafer & Doswell 2011) or over overlapping windows
(Shafer, Grondin & Doswell 2015). Each is scored against Storm Events episodes —
recall of forecaster-grouped pairs, within-office precision, share of Storm
Events episodes split — and described by size, extent, duration and multi-day
count. Outputs: `../local/archive/episode_comparison_report.md`,
`data/interim/episode_comparison_metrics.csv` and `..._assignments.csv` (one
column of episode labels per method). Implausible DAT end times are repaired in
memory first; see HANDOVER's traps.

`--anchor spc` runs the same methods on SPC's whole tracks (stage 14) instead of
DAT hazards — the complete, reviewed tornado list, so tornadoes DAT lacks cannot
cut an outbreak — scored against each track's closest Storm Events row. Its
episodes are then carried to DAT hazards (each takes its closest SPC track's
episode; a hazard without an SPC match is its own) and scored against the DAT
reference, with the ARI against stage 15's published episodes — exactly 1 for
`space_time 400km 6h`, the check that stage 15 publishes that rule. Outputs carry an
`_spc` suffix. SPC geometry is a straight start→end line, so distances between
long curved tracks are approximate.

No grouping applies a minimum size. `--anchor spc` therefore also writes
`data/interim/episode_counts_spc.csv`: per method and episode, its SPC tornadoes
(`n_spc`), those rated EF1+ (`n_spc_ef1plus`) and unrated (`n_spc_unrated`, EF-U),
and the DAT hazards carried into it (`n_dat`). These are the counts a dataset user
cannot recompute from DAT, which lacks many SPC tornadoes; an outbreak threshold
such as ≥6 EF1+ (Fuhrmann et al.) is a filter on them. The report shows what that
threshold keeps per method. For the published rule they are stage 15's episode
columns.

The DAT hazards' reference is their own Storm Events match, **extended through
SPC** where they have none: DAT hazard → closest SPC track (including stage 14's
time-repaired links) → that track's closest Storm Events row
(`episodes.reference_via_spc`, `combine_references`). This reaches the hazards
whose DAT time is off by hours, which can never match Storm Events directly.
Where both routes exist they name the same episode for 98.6% of hazards; the
report states the counts. `--dat-reference direct` scores against the hazards'
own matches only, as before.

With stage 50's `spc_watch_systems_<tag>.csv` present, every method is also
scored against SPC watches (DAT hazards through their closest SPC track), on
watched tornadoes only: **within systems** — of pairs a method groups, the
share inside one watch system, and the part on pairs from two offices — as an
upper bound, and **sequences kept** — of pairs in one watch sequence, the share
the method keeps — as a lower bound. F1 against each is in the metrics CSV.
Where stage 50's `no-motion` variant exists as well (`link --no-motion-check`),
every method is scored against it too (`alt_` columns), and the report sets both
side by side, with the largest change and Kendall's τ of the method order per
score: whether a conclusion depends on the motion check. `--watch-variant`
names another variant, `''` turns this off.

### Watch systems — `scripts/50_watch_systems.py`

The watch reference from `docs/plan_watch_linking.md`, steps 0–4.
`probe` makes about 25 cached requests to the IEM archives
(`data/raw/spc_watches/probe/`) — county-level watch records (VTEC TO.A/SV.A,
the official area), the SPC watch polygons with their attributes, and the SEL
watch texts — and writes `outputs/watch_probe_report.md` and
`data/interim/watch_probe.json`: from which year county records are complete
(one April per year, default 2004–2012), how often counties end before their
watch expires, whether counties and polygons place stage 14's SPC tornadoes in
the same watches (one season, default spring 2011), and how often the texts
state "replaces watch N" (that season by month, plus April 2024 for the newer
mixed-case format). A tornado's county is SPC's `st` + `C` + `f1` (UGC code),
so no county shapes are needed. The "CONTINUE…WW" list in a watch text names
watches in effect elsewhere and is counted apart: it is concurrency, not
succession.

`fetch` caches, per year 2010–2025, the county records, the polygons and twelve
months of SEL texts under `data/raw/spc_watches/<year>/` (~225 requests, 2 s
apart), plus the Census 2020 county boundary file (1:500,000, ~12 MB) under
`data/raw/census/`, read with `pyogrio` and simplified to 500 m. `link` is offline. It first
drops county records that do not belong to an SPC watch, and counts them: marine
zones listed with the counties (~22,000), Honolulu's own watches, which are
numbered from 1 like SPC's and collide with them, and records starting before
SPC issued the watch of that number or after it expired (mistyped numbers, ~180).
A "replaces watch N" statement is matched to the watch of that number that ended
within a day before — last year's, for a watch in early January. It then builds one row per watch (year +
number; tornado and severe thunderstorm watches share the numbering) with
times from the county records and motion/PDS from the polygons, links watches
by the plan's three rules — same county at the same time; "replaces watch N";
inferred succession within `--gap-h` (3) and `--edge-km` (50, county edge to
county edge) and not upstream of the storm motion beyond a tolerance
calibrated on the "replaces" links (`--motion-slack-km` sets it,
`--no-motion-check` switches it off and writes a variant, below) — and takes
connected components as systems (`ws_<year>_<number>` of the earliest watch),
and, keeping only hand-overs in time, as sequences (`wq_…`).
Each SPC tornado takes the system of the watch its county (SPC's `st` + `f1`)
was under at its start, by polygon only where SPC records no county. Outputs:
`data/processed/spc_watch_systems_<tag>.csv` (per tornado: watches, method,
system, margins), `data/interim/spc_watches_<tag>.csv`,
`..._watch_links_<tag>.csv` (rule per link), `..._watch_review_<tag>.csv`
(candidates rejected only as upstream), `..._watch_sensitivity_<tag>.csv`
(Δt × d × motion check), and `outputs/watch_systems_report.md`: links by rule,
system sizes, share of SPC's "replaces" links that rules 1 and 3 reproduce,
the tolerance calibration, the speed-limit diagnostic,
watched share by year and rating, agreement with Storm Events episodes,
sensitivity, and the named outbreaks for a hand check.

`link --variant NAME` writes all of these with a `_NAME` suffix
(`spc_watch_systems_<tag>_NAME.csv`, `outputs/watch_systems_NAME_report.md`, …)
and leaves the main ones alone; `--no-motion-check` implies `--variant
no-motion`, which stage 51 picks up to test whether its conclusions depend on the
motion check.

`sheets` writes the two hand checks to `outputs/annotation/` (instructions in
`HOW_TO_ANNOTATE_watches.txt`): `watch_outbreak_sheet.csv` — each of the 10 named
outbreaks (`NAMED_OUTBREAKS`) grouped nine ways on SPC tracks (watch systems and
sequences, the former convective-day rule, convective day 400 km, the 6 h time-gap rule (Fuhrmann variant),
space-time 400 km / 6 h, KDE per day 100 km and the overlapping-window KDE at
50 and 100 km; `OUTBREAK_GROUPINGS`), blinded as groupings A–I — 90 labels —
each to be labelled
`matches` / `too_coarse` / `too_fine` / `cannot_tell` against the official
summaries — and `watch_review_sheet.csv`, a seeded sample of 50 motion-check
rejections with links to both SPC watch pages, labelled `separate_systems` /
`should_link` / `cannot_tell`. The `*_key.csv` files hold what the sheets hide.
It refuses to overwrite sheets that already hold labels. `review` opens a
local map app on both sheets (`tornado_dataset.viewer.watch_review`,
http://127.0.0.1:8800): for an outbreak, every SPC track coloured by group under
the chosen grouping (keys a–i), a timeline of the groups with the 12Z
convective-day boundaries, a time slider and
window, optional watch outlines and the SPC report pages; for a pair, both
watch polygons, the counties each covered and when, both storm-motion vectors,
the other watches in effect nearby, the period's tornadoes and both SEL texts.
The browser gets only letters and per-outbreak group numbers — never the
method, raw group ids or the rejection distances — and labels are written back
into the sheets' `label` and `notes` columns. Once every outbreak row is
labelled, a read-only Compare tab shows one outbreak under the groupings in
`COMPARE_GROUPINGS` (space-time 400 km/6 h, the 6 h time gap, watch systems and
sequences), unblinded, on four synced maps with one time slider and each
grouping's blind label; colours follow a chosen reference grouping (each group
takes the colour of the reference group it shares most tracks with), so splits
and merges show as colour changes, and a toggle fades every track that agrees
with the reference. `check` scores them
into `outputs/watch_hand_checks_report.md`.
