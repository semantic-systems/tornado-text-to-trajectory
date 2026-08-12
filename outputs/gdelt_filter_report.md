# gdelt filter — Stage 18

Generated 2026-08-12T14:30:54+00:00 from `data/processed/textrefs_news_2010-01-01_2025-12-31.csv`.

## What went in

- **83,778 rows**, 35,713 distinct headlines (57.4% of the export is syndicated copy).
- 2017-01-02 to 2025-12-30, 6,383 outlets.
- Headline and URL only — no body text. Every row mentions a tornado somewhere (full-text query), but only 65.7% say so in the headline or URL, which is all this stage can read.

## What came out

- **47,354 rows labelled `EVENT`** (56.5%), 19,922 distinct headlines.

| primary label | rows | share |
|---|---:|---:|
| `EVENT` | 47,354 | 56.5% |
| `NOT_TORNADO_EVENT` | 16,715 | 20.0% |
| `PROSPECTIVE` | 9,932 | 11.9% |
| `UNCLEAR` | 9,777 | 11.7% |

| flag | rows | share |
|---|---:|---:|
| `is_outbreak` | 14,416 | 17.2% |
| `is_retrospective` | 776 | 0.9% |
| `is_fact_check` | 59 | 0.1% |
| `nonmet_sense` | 171 | 0.2% |
| `other_hazard` | 7,677 | 9.2% |

## Method

Every distinct headline was labelled by a locally hosted LLM at temperature 0, and the answer propagated to its syndicated copies. There is no rule-based decision stage and no trained classifier: measured against LLM labels on a stratified sample of 385 headlines, the rules agreed 93.4% on the event/not decision after post-stratification, but *missed* ~14,106 headlines the model called events while wrongly calling ~1,615 events — recovering roughly 70% of the event set, to save inference that a local GPU makes free.

The regex cues are retained as audit columns (`cue_*`, `protected`) for stratifying validation and as a drift monitor, but they decide nothing.

## Limitations

1. **Headline and URL only.** An article headlined "storm" cannot be distinguished from one headlined "tornado" on the evidence available here. `UNCLEAR` (11.7% of rows) is the model's own estimate of how often that bites; it is a measured stratum, not a residual.
2. **No human ground truth yet.** Every figure above is the model's output. Precision and recall against human labels require a blind, stratified annotation sample that has not been drawn.
3. **`conf` is self-reported** and is not a calibrated probability. Use the self-consistency `modal_share` from `data/interim/gdelt_consistency.csv` for uncertainty instead.
4. **Syndicated copies share one label.** Labels are computed per distinct normalised headline; an outlet-specific edit that changes the meaning would be missed.
5. **The corpus is not a census.** Media Cloud covers a subset of US outlets, and per-year row counts vary by more than an order of magnitude (3,050 in 2010 vs 79,619 in 2019), reflecting collection growth at least as much as tornado activity.
6. **1,054 non-English rows** were labelled with an English prompt and should be treated with caution.
