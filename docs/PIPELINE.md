# Pipeline detail

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
  the best-scoring section becomes `primary_survey_of`.
- **News is *published* as links and metadata only.** GDELT queries run per
  episode and store links. Article text itself is retrieved and held locally where
  it is needed for analysis — LexisNexis full-text exports, and Media Cloud bodies
  via stage 21 — under the §60d UrhG research exception for text and data mining.
  The distinction is between local processing and redistribution: what leaves this
  project is links plus derived annotations, never the article text.
- **Independent cross-check:** where a survey section matched a hazard, the survey's
  own EF rating agrees with DAT's on 97.1% of cases and the fatality count on
  97.1% (n=69, March 2025) — two descriptions of the same survey, compared rather
  than assumed equal.
- **Coverage stops at 2017-01-01 for news**: 590 of 2,795 episodes predate the
  GDELT DOC API's earliest queryable date and are flagged, not silently empty.

See [`outputs/text_qa_report.md`](outputs/text_qa_report.md), which also records the
measurements behind the retrieval choices (query form, match radii).

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
and prominence now comes from Census population estimates joined to GNIS. See
[`docs/linking_coverage_analysis.md`](docs/linking_coverage_analysis.md).

**Links are candidates until annotated.** `scripts/12_sample_annotation.py` draws
blind precision, recall and agreement sheets ([codebook](docs/annotation_codebook.md));
`scripts/14_qa_links.py` turns the returned labels into precision per score band
with Wilson intervals, recall, and Cohen's κ, and only then is a publishable
threshold defined.

### The corpus in time

`scripts/15_analyze_news_time.py` writes
[`outputs/news_time_report.md`](outputs/news_time_report.md): corpus volume and
source mix over time, how quickly coverage appears after a tornado, how it decays
by death toll, the anniversary tail, which events get covered at all, and — the
piece carried over from the early prototype — **when each kind of text arrives**.

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

### Reading articles — `scripts/16_viewer.py`

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

### Filtering the Media Cloud corpus — `scripts/18_filter_media_cloud.py`

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
python scripts/18_filter_media_cloud.py profile   # cue coverage, no LLM needed
python scripts/18_filter_media_cloud.py run       # label + uncertainty + write
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

### Filtering the LexisNexis corpus — `scripts/19_filter_lexisnexis.py`

Same method and the same label vocabulary as stage 18, so the two corpora stay
comparable for the overlap study; the shared machinery lives in
[`text/labelling.py`](src/tornado_dataset/text/labelling.py). Three things differ,
and each changes a design decision.

**Full body text is available.** 24,917 rows collapse to **20,138 distinct
bodies** (the labelling unit) carrying 22,896 `textref_uid`s (the downstream join
key). Median body is 525 words. The headline under-determination that made
`UNCLEAR` load-bearing in stage 18 largely disappears — so if `UNCLEAR` stays
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
python scripts/19_filter_lexisnexis.py window
```

labels a mention-count-stratified sample under all four modes and reports each
one's agreement with `full2000`, separately for single-mention bodies. Pick the
cheapest acceptable mode and record it.

The protect rule is reused but evaluated on **headline + lede only** — across 525
median words virtually every article contains "storm", so a full-body protect
rule is vacuously true and stops being a guard.

```bash
python scripts/19_filter_lexisnexis.py profile    # corpus shape, no LLM
python scripts/19_filter_lexisnexis.py window     # choose the evidence window
python scripts/19_filter_lexisnexis.py run        # label + uncertainty + write
python scripts/19_filter_lexisnexis.py crosstab   # validate against stage 11
```

Both stages take `--tag`, and anything experimental should use it: output paths
derive from it, so a smoke test cannot overwrite a real run. `--limit` bounds only
how much of the corpus is *read*, which is not the same protection. The response
cache is shared across tags, so a tagged run still inherits every answer already
paid for.

### Full text for the Media Cloud corpus — `scripts/21_fetch_fulltext.py`

Media Cloud supplies headline, URL and date but no body. That bounds what stage 18
can decide and, more importantly, leaves its 48,741 `EVENT` stories **unlinkable**:
stage 11 matches toponyms in the article text, so without a body they cannot enter
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
python scripts/21_fetch_fulltext.py pilot          # measure, ~600 URLs
python scripts/21_fetch_fulltext.py crawl          # the full pass, resumable
python scripts/21_fetch_fulltext.py status         # progress; safe during a crawl
python scripts/21_fetch_fulltext.py crawl --retry-failed   # transients only
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

`scripts/11_link_articles.py --labels data/processed/lexisnexis_article_labels.csv`
links only `EVENT` articles. The rest are **recorded, not dropped** — they get
`link_status = filtered_<primary>`, because `article_status_*.csv` is a complete
census of the corpus that the report and the viewer both read. An article stage 19
did not judge is still linked, and counted, rather than silently discarded.

The existing regex heuristics in `classify_scope` are superseded but kept: they
still populate the `scope` column, and their disagreement with the model is a free
drift monitor.

Gating is one-directional — once the linker runs gated, a filter false negative
becomes invisible. Run `crosstab` **before** re-running stage 11: it compares the
labels against the ungated `link_status` already on disk and lists both
disagreement directions. Its first run already showed that several `EVENT`
articles the linker could not place are non-US tornadoes (Sechelt BC, Ayr Ontario,
a Puerto Rico F4) that DAT structurally cannot cover.

### Exploring the data

`scripts/09_analyze_hazards.py` writes
[`outputs/hazard_analysis_report.md`](outputs/hazard_analysis_report.md) with figures
for counts per year, rating distribution and mix, season and time of day (in local
solar time, since a UTC histogram smears the afternoon peak across four time
zones), track geometry, human impact, a density map in equal-area projection, and
per-year coverage of each layer.

`scripts/10_hazard_map.py` writes `outputs/hazard_map.html` — a single
self-contained file (~3 MB, no network, no build step) showing all 9,982 tracks on
a US map with a month slider and play button, a window mode (month / year /
cumulative), a rating filter, hover details and a table of the strongest tracks in
view. It zooms to 120× (scroll, pinch, double-click, or the buttons) and pans by
dragging; surveyed **damage footprints** appear from 20×, where a polygon is more
than a smudge.

Tracks are pre-projected and simplified in Python so the browser only draws
integer coordinates, which is what keeps 10k tracks interactive on a canvas. Two
details make deep zoom work: coordinates ship in **sub-pixel units** (1/32 px), so
detail is not discarded at build time, and the simplification tolerance is 60 m
(~1 px at 70×). Stroke widths are divided by the zoom so lines stay the same
thickness on screen, and each track carries a bounding box so off-screen work is
culled.

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


### Rebuilding GDELT from cache — `scripts/07_fetch_gdelt.py --cache-only`

Every GDELT response is cached under `data/raw/gdelt/`, so the tables can be
rebuilt without touching the network. `--cache-only` skips any query that was
never fetched instead of requesting it, which matters because a partial sweep
would otherwise stall for days on the remainder at one request per five seconds.

Skipped queries are counted as `uncached_queries` and `episodes_fully_uncached`
in the manifest, kept separate from `failed_queries`. The distinction is the same
one `query_articles` already makes between `None` and `[]`: "not attempted",
"refused" and "genuinely empty" are three different facts, and a rebuild that
conflated them would report partial coverage as complete.

### Labelling a second headline corpus — `18_filter_media_cloud.py --source`

GDELT is the same shape as Media Cloud — headline, URL, date, outlet, no body —
so it needs no separate labeller, only a loader that renames its columns.
`--source {mediacloud,gdelt}` selects the input and the output prefix; the dedup,
cues, prompt, protect rule and label vocabulary are identical, which is the point:
two corpora labelled by different code could not be compared.

Each source keeps its own response cache. The prompt embeds the URL and the date,
so the same headline in two corpora produces different prompts and different cache
keys — a shared cache would buy nothing, and renaming the existing one would
orphan the answers already paid for.

### The corpus atlas — `scripts/22_corpus_atlas.py`

Replaces the retired stages 13 and 20. Run it twice; the two scopes answer
different questions and write to different files:

```bash
python scripts/22_corpus_atlas.py                 # what was collected
python scripts/22_corpus_atlas.py --events-only   # what is usable  <- the relevant one
python scripts/22_corpus_atlas.py --probe         # + ask GDELT about missed stories
```

`--events-only` restricts to stories labelled `EVENT` and writes
`corpus_atlas_events_report.md`; the unrestricted run writes
`corpus_atlas_report.md`. Each report states its scope in its first line.

Compares all three news corpora as a set. Supersedes stages 13 and 20, which are
retained until the atlas has run against a labelled GDELT.

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
