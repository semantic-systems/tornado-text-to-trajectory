# LexisNexis filter — Stage 19

Generated 2026-08-10T22:39:06+00:00 from `outputs/lexisnexis_articles.jsonl`.

## What went in

- **24,917 articles**, 20,138 distinct bodies (19.2% verbatim wire copy), 22,896 distinct `textref_uid`.
- 2010-01-16 to 2025-12-29, 1,487 sources.
- Full body text, median 540 words. Evidence sent to the model: **windows** (see the window ablation).

## What came out

- **15,324 articles labelled `EVENT`** (61.5%), 12,077 distinct bodies. These are the articles stage 11 links; everything else is recorded with its reason and skipped.

| primary label | articles | share |
|---|---:|---:|
| `EVENT` | 15,324 | 61.5% |
| `NOT_TORNADO_EVENT` | 9,126 | 36.6% |
| `PROSPECTIVE` | 467 | 1.9% |

| flag | articles | share |
|---|---:|---:|
| `is_outbreak` | 9,456 | 37.9% |
| `is_retrospective` | 449 | 1.8% |
| `is_fact_check` | 31 | 0.1% |
| `nonmet_sense` | 8 | 0.0% |
| `other_hazard` | 3,017 | 12.1% |
| `is_passing_mention` | 8,783 | 35.2% |
| `is_press_release` | 4,877 | 19.6% |
| `is_roundup` | 1,458 | 5.9% |

## Method

Every distinct article body was labelled by a locally hosted LLM at temperature 0 and the answer propagated to the articles sharing that body. Same label vocabulary as stage 18, so the two corpora remain comparable for the overlap study; the corpus-specific distinctions (`is_passing_mention`, `is_press_release`, `is_roundup`) are flags, not primary categories.

The decisive question here is *aboutness*: 15.2% of articles mention a tornado at most once, and those references are usually to a real tornado in an article about something else — a lawsuit, an obituary, a fundraiser. No keyword separates those from a report, which is why the rules were never given the decision.

## Limitations

1. **No human ground truth.** Every figure is model output. This corpus is where that should be fixed first: the annotation sheets, the codebook and the viewer already exist, and `is_passing_mention` plus the low `modal_share` rows are the strata a sample should concentrate on.
2. **The evidence window bounds what is knowable.** An article whose only tornado content falls outside the window cannot be labelled on it; the `window` subcommand measures the size of that effect rather than assuming it away.
3. **Exact-duplicate detection only.** Bodies are grouped by normalised identity, the cheap variant of `LexisNexisTools::lnt_similarity`, so lightly edited wire copy is counted as distinct.
4. **Gating is one-directional.** Once stage 11 runs gated, filtered articles are not linked and a filter false negative becomes invisible. The `crosstab` subcommand is the only check on this, and only while stage 11's ungated run is still on disk.
5. **The corpus is one LexisNexis query's complete export** — 22,896 unique articles, not truncated — but not a census of coverage: it is bounded by which outlets LexisNexis indexes and by the query terms.
