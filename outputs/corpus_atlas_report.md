# Corpus atlas — the three news corpora as a set

Generated 2026-08-12T15:22:33+00:00.

> **Scope: every retrieved story, whatever its label.** This describes what was collected, not what is usable. For the tornado-event subset — usually the more relevant view — see `corpus_atlas_events_report.md`.

**Unit: normalised title + publication date.** The corpora natively deduplicate by body (LexisNexis), by title (Media Cloud) and not at all (GDELT); comparing them in their native units produced a published figure that measured URLs against titles. Every number here uses the one unit all three can produce. Native counts are kept in the table below for within-corpus use.

## What went in

| corpus | rows | stories | native units | labelled |
|---|---:|---:|---:|---|
| lexisnexis | 24,917 | 18,444 | 20,138 | yes |
| mediacloud | 491,432 | 282,716 | 266,258 | yes |
| gdelt | 83,778 | 38,150 | 83,429 | yes |

## How many distinct stories

| region | stories | share |
|---|---:|---:|
| mediacloud | 271,497 | 83.4% |
| gdelt | 30,123 | 9.2% |
| lexisnexis | 14,446 | 4.4% |
| mediacloud + gdelt | 6,094 | 1.9% |
| lexisnexis + mediacloud | 2,624 | 0.8% |
| lexisnexis + mediacloud + gdelt | 660 | 0.2% |
| lexisnexis + gdelt | 246 | 0.1% |
| **union** | **325,690** | 100% |

The union is the number of **connected components** of the match graph, not a sum minus pairwise intersections. Matching is many-to-many and transitive across three corpora, so a story reached through an intermediate corpus must count once.

## Method per edge

| pair | edges | method |
|---|---:|---|
| lexisnexis × gdelt | 1,795 | `title_date_outlet` |
| lexisnexis × mediacloud | 5,709 | `title_date_outlet` |
| mediacloud × gdelt | 7,459 | `exact_url` |

Exact-URL and inferred edges are **not comparable** and are never pooled. Media Cloud and GDELT both publish URLs, so their identity is read directly. LexisNexis publishes none, so its edges are inferred from headline, date and outlet — strictly weaker, and a lower bound.

## Limitations

1. **Overlap is a lower bound, the union an upper bound.** Rewritten headlines and outlets absent from one collection cannot match.
2. **The corpora have different frames.** GDELT holds nothing before 2017-01-01; Media Cloud covers US national/state/local collections; the LexisNexis export includes wire services, broadcast transcripts and non-US outlets that neither web corpus sampled.
3. **Capture–recapture is reported but not usable as a population estimate.** It assumes one shared sampling frame; these three have partly disjoint frames, so the small overlaps reflect how differently the corpora were built rather than how much coverage exists, and they send the estimate toward infinity. The spread between pairs is informative; the values are not.
5. **Transitive merging can over-collapse.** A story matching many on the other side pulls all of them into one component. The run prints a hub count; large hubs usually mean a template URL or a generic headline, not one very widely syndicated story.
4. **Labels are model output** and, for the corpora that have them, unvalidated against humans.
