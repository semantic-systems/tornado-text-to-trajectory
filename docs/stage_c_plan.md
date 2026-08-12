# Stage C — linking articles to events, and the LexisNexis ↔ GDELT overlap

Plan of record. Written 2026-07-30, while the LexisNexis download and the GDELT
sweep are still running. Everything here can be **built and dry-run now** against
the 994 articles already parsed and the GDELT pilot output; the final run is the
same commands on the finished corpora.

## 1. What Stage C has to deliver

| # | Deliverable | Why it exists |
|---|---|---|
| C-1 | Each news article linked to the tornado (or outbreak) it describes, with the evidence and a confidence | Improvement #2: the dataset's text side is worthless if an article is attached to the wrong tornado |
| C-2 | A hand-annotated validation sample with measured precision and recall | Without it, the links are assertions. Unvalidated links do not get published as links |
| C-3 | The LexisNexis ↔ GDELT overlap, measured in both directions | Improvement #3: how much of the licensed full text is reachable from an open URL feed, and vice versa |

## 2. The size of the problem (measured, not estimated)

| Quantity | Value |
|---|---|
| LexisNexis articles parsed today | 994 (930 after removing verbatim wire duplicates) |
| Their date range | 2021-04-07 … 2025-12-29 |
| Hazards inside that range | 5,337 of 9,982 |
| Episodes (outbreak days) inside that range | 1,292 of 2,795 |

With the date window you proposed, **events from 3 days before to 14 days after
publication** (equivalently: for an article published on day *T*, events whose
convective day falls in *T−14 … T+3*):

| Level | Candidates per article: median | 90th pct | max | Total pairs to score |
|---|---|---|---|---|
| hazard (one tornado) | 125 | 268 | 317 | 128,642 |
| episode (one outbreak day) | 22 | 44 | 50 | 24,148 |

**What this tells us.** The date window is a real 40× cut (from 5,337 candidate
hazards to ~125), but 125 candidates per article is nowhere near a link — it is
still a shortlist. The toponym step has to do the actual work. It also tells us to
**link at episode level first**: 22 candidates is a comfortable shortlist, and the
number of pairs to score is trivial computationally.

## 3. The linking pipeline

Five steps, cheapest and most reliable first. Each step *records* what it found
rather than just filtering, so a reviewer can see why a link exists.

### Step 1 — Date window (the cheap cut)

For every article, take episodes whose convective day is in *T−14 … T+3*.

- **Why −14:** the aftermath reporting window. Survey products, funerals, FEMA
  declarations and "what we know" pieces run about two weeks.
- **Why +3:** an article can precede the event it is about — forecast and watch
  coverage ("dangerous severe weather expected Friday"). Those cannot *describe*
  damage, so they are marked differently in step 5.
- Recorded per pair: `day_offset` (article date − event day).

Two article classes escape this window and are handled separately:

- **Anniversary and retrospective pieces — 45 articles (4.5%)**, e.g. *"40 years
  after twisters, is a Pa. repeat possible?"*, *"100 years ago, nation's worst
  tornado…"*. A publication-date window can never reach their event. They get a
  second pass that reads the date *out of the text* (see step 3) and, failing
  that, are labelled `no_event_window` rather than silently dropped.
- **General and explainer pieces — 29 articles (2.9%)**, e.g. *"How to Prepare for
  Tornado Season"*. These describe no single event and must end up with **no**
  link. They are the reason the annotation codebook needs a "no event" class:
  a linker that always produces a link would score well on articles that have an
  answer and be wrong on these.

### Step 2 — Toponym scoring (the step that decides)

Every hazard already carries authoritative place names from Stage 5 (populated
places within 25 km of the track, plus county and state). Aggregating those over an
episode gives its toponym set.

The naive version — "does any place name appear in the article?" — fails, and the
data says exactly why:

| | value |
|---|---|
| distinct place names across all hazards | 29,447 |
| names belonging to exactly one hazard | 14,681 (50%) |
| most reused names | Midway (172 hazards), Fairview (98), Oak Grove (94), Union (93) |

So a hit on "Cushman" is near-proof and a hit on "Midway" is nearly worthless.
The fix is standard and defensible: weight each matched name by its **inverse
document frequency** across the gazetteer,

    weight(name) = log(total_hazards / hazards_containing(name))

which gives "Cushman" a large weight and "Midway" a small one, from the data rather
than from a hand-made stoplist. On top of that:

- **Position matters.** A place in the headline or the LexisNexis `dateline`
  (146 articles have one) counts more than one buried in paragraph 30 — headlines
  name the subject, bodies also name context.
- **Specificity matters.** city > county > state. A state-only match is weak
  evidence on its own and never sufficient for a link.
- **Repetition matters, with a cap.** An article naming a town five times is more
  likely about it, but the count is capped so a boilerplate footer cannot dominate.
- Recorded per pair: every matched name, its level, its weight, where it was found.

Place names are matched against the article with a gazetteer-driven matcher
restricted to the candidate episodes' own toponym sets, not open-domain NER. The
question is not "what places does this article mention?" but "does it mention
*these* places?" — a much easier and more precise question. (spaCy NER stays
available as a fallback for the retrospective pass, where we do not yet have a
candidate set.)

### Step 3 — Corroborating signals (breaking the ties)

Toponyms alone will tie when two outbreaks hit the same region within two weeks —
which is common. These signals are recorded for every surviving pair:

| Signal | Available in | How it corroborates |
|---|---|---|
| EF rating stated in the text | 278 articles (28%) | matches the hazard's `efscale` |
| Fatality / injury counts | 528 articles (53%) mention deaths | matches the hazard or episode total |
| Explicit dates and weekdays in the text | most | "Friday's tornado", "the March 14 storms" → resolve against the event date |
| Source locality | all | a local outlet (e.g. *St. Louis Post-Dispatch*) reporting an event in its own state is more likely describing it than a national wire |
| Survey-text overlap | 4,910 hazards | distinctive strings shared with the NWS survey or DAT comments (road names, landmarks) |

Numbers are the strongest of these: "EF3" plus "3 killed" plus a matching county
pins an event almost uniquely. They are also what makes the retrospective pass
possible — an anniversary piece usually states the original date outright.

### Step 4 — Down to the individual tornado

Once an article is attached to an episode, the same scoring runs over that
episode's hazards only (3.6 hazards per episode on average, but 60+ for a big
outbreak). Three outcomes, all legitimate:

- **one hazard clearly wins** → `link_level = hazard`
- **several hazards tie** (the article is about the outbreak, not one tornado) →
  stay at `link_level = episode`. This is the honest answer, not a failure.
- **the article names several tornadoes** → one `describes` link for the primary
  subject, `mentions` links for the others.

### Step 5 — Decision, relation, confidence

- A pair becomes a link when its score clears the threshold **set from the
  annotated sample** (step 6), never from intuition.
- `link_relation`: `describes` for the article's subject; `mentions` for events it
  refers to in passing. Pre-onset (forecast) articles can only ever be `mentions`
  — they cannot describe damage that has not happened. `temporal_class` from
  `text/tiering.py` records the timing independently.
- `link_confidence` is the calibrated score, with the reliability table published
  alongside — the Stage A lesson was that an uncalibrated confidence is a
  decoration.
- Articles that legitimately match nothing keep a row with `link_status =
  no_event` / `no_event_window`, so coverage can be computed honestly.

## 4. Validation (deliverable C-2)

This is the part that makes the links usable in a paper, and it needs your hands
for a few hours. Nothing about it depends on the downloads finishing.

**Codebook** (`docs/annotation_codebook.md`): written rules and worked examples for
five labels — `describes`, `mentions`, `unrelated`, `article_has_no_event`,
`cannot_tell`. Written *before* seeing the pipeline's output, so the labels are not
shaped by them.

**Precision sample.** ~200 (article, event) pairs, stratified across score bands
(so both confident and marginal links are measured, not just the easy ones),
presented blind: article headline, date, source, an excerpt, and the candidate
event's date, rating, counties and places — without the score. → precision per
band with Wilson 95% CIs.

**Recall sample.** A separate ~100 randomly sampled *articles*. You label the true
event from the text first, then we check whether the pipeline found it. This is the
only way to measure what the linker misses; measuring on its own output cannot.

**Agreement.** A 50-pair subset labelled twice (by you on two occasions, or by a
second annotator) to report Cohen's κ. Without it, "precision 0.93" rests on one
person's unexamined judgement.

**Acceptance bar.** Proposed: publish as links only the score bands whose measured
precision is ≥ 0.90, and ship everything below that as `candidate_links` in a
separate file. Stated in the datasheet either way.

## 5. GDELT articles

Same machinery, thinner input: GDELT gives title, domain, date — **no body**. So:

- Toponym matching runs on the title only; scores will be lower and more ties will
  survive. Most GDELT links will legitimately stay at `link_level = episode`.
- One extra piece of evidence is free: the article was *retrieved by* a particular
  episode's toponym query, which is itself weak positional evidence, already
  recorded as `link_evidence = gdelt_toponym_query`.
- The same validation applies, on its own sample — GDELT link precision must be
  reported separately from LexisNexis, because the input is not comparable.

## 6. The overlap study (deliverable C-3)

The question "how many LexisNexis articles are in GDELT?" hides two different
questions, and answering only the easy one would be misleading.

**Level 1 — retrieval overlap.** How many LexisNexis articles appear among the URLs
our GDELT episode queries actually returned, and vice versa. Matching on:
normalised headline similarity + publication date within ±3 days + source→domain.
The source→domain map is seeded from the **118 LexisNexis bodies that contain their
own URL**, then extended by hand for the top sources (which cover most of the
corpus). Reported both directions.

**Level 2 — index probe.** For a random sample of LexisNexis articles that found no
GDELT counterpart, query the GDELT API *directly* by domain + date + title terms.
This separates two very different findings: *"GDELT does not index this outlet"*
versus *"our episode queries missed it"*. Only level 2 can distinguish them, and
the second is a limitation of our retrieval, not of GDELT.

**Expected structural non-overlap** — to be characterised, not fixed: LexisNexis
carries print-only editions, broadcast transcripts (ABC/CBS/NBC, ~40 in the
current corpus) and paywalled wire copy, none of which has a public web URL for
GDELT to index. The overlap number is only interpretable once broken down by source
type.

## 7. Code and outputs

New modules, mirroring the existing structure:

```
src/tornado_dataset/text/
  linking.py     # candidate generation, IDF toponym scoring, corroboration, decisions
  matching.py    # normalised title/date/domain matching (used by the overlap study)
  overlap.py     # the two-level LexisNexis <-> GDELT analysis
scripts/
  11_link_articles.py    # LexisNexis + GDELT -> textrefs / textlinks / candidates
  12_sample_annotation.py # draws the stratified samples, writes blind sheets
  13_overlap_report.py   # the overlap study
  14_qa_links.py         # scores the returned annotations, calibration, QA report
docs/
  annotation_codebook.md
```

Outputs: `textrefs_lexisnexis_*.csv`, `textlinks_articles_*.csv`,
`candidate_links_*.csv`, `outputs/annotation/*.csv`,
`outputs/link_qa_report.md`, `outputs/overlap_report.md`, plus manifests.

## 8. Order of work, and what blocks on what

| Step | Blocked by | Runtime |
|---|---|---|
| Build `linking.py`, `matching.py`, `overlap.py` and the scripts | nothing | — |
| Dry-run on today's 994 articles + GDELT pilot | nothing | seconds |
| Write the annotation codebook | nothing | — |
| Draw the annotation samples | a full linking run | seconds |
| **Your annotation work** | the samples | a few hours |
| Threshold + calibration + QA report | annotations returned | seconds |
| Final linking run on the complete corpora | LexisNexis download, GDELT sweep | minutes |
| Level-2 index probe | GDELT sweep done (shares the rate limit) | ~1 request / 5 s over the sample |

Nothing in the linking step is slow: it is all local scoring over ~25k pairs. The
long poles are the downloads (running) and the annotation (yours).

## 9. Limitations that go into the datasheet regardless of how well this works

1. **The LexisNexis corpus is one query's complete export** (`(Tornado) and
   length >= 50`) — not a random sample of coverage, and not truncated. Recall
   figures computed on it are conditional on that query, not on a retrieval cap.
   *(Corrected 2026-08-12: this section was written against an early 994-article
   pilot export that was capped at 1,000 hits. The full corpus is 24,917 rows /
   22,896 unique articles; the per-article counts below still describe the pilot.)*
2. **Wire copy is duplicated.** 64 of 994 articles are verbatim re-runs. Article
   counts are reported both raw and deduplicated (`dup_group`).
3. **Linking is a measurement, not ground truth.** Even at 0.95 precision, one
   link in twenty is wrong; downstream experiments should use `link_confidence`.
4. **News coverage is not uniform.** Deadly, photogenic and urban tornadoes are
   covered far more than rural EF0s — the dataset inherits that bias, and any
   text→geometry result must be read against it.
5. **The +3/−14 window is a modelling choice.** It excludes anniversary coverage by
   construction; the retrospective pass mitigates but does not remove this.

## 10. Open decisions (my recommendations in bold)

1. **Retrospective articles:** run the text-date second pass (**yes** — it is ~45
   articles and they are exactly the `independent_retrospective` class the
   experiments need), or exclude and document?
2. **Annotation volume:** 200 precision pairs + 100 recall articles + 50 double-labelled
   (**recommended**), or a lighter 100/50/30 first pass to check the codebook before
   committing time?
3. **Acceptance bar:** publish only bands with precision ≥ 0.90 (**recommended**),
   or ≥ 0.80 with the confidence exposed?
4. **Hazard-level ambition:** attach articles to individual tornadoes wherever the
   evidence allows (**recommended**), or keep all news at episode level and treat
   hazard-level attribution as a separate later experiment?
