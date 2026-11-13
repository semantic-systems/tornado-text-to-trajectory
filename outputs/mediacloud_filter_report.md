# Media Cloud filter — Stage 18

Generated 2026-08-10T21:33:50+00:00 from `data/raw/media_cloud/national_state_local_2010-2025.csv`.

## What went in

- **491,432 rows**, 266,258 distinct headlines (45.8% of the export is syndicated copy).
- 2010-01-01 to 2025-12-31, 4,544 outlets.
- Headline and URL only — no body text. Every row mentions a tornado somewhere (full-text query), but only 29.5% say so in the headline or URL, which is all this stage can read.

## What came out

- **110,438 rows labelled `EVENT`** (22.5%), 48,741 distinct headlines.

| primary label | rows | share |
|---|---:|---:|
| `NOT_TORNADO_EVENT` | 292,696 | 59.6% |
| `EVENT` | 110,438 | 22.5% |
| `PROSPECTIVE` | 63,150 | 12.9% |
| `UNCLEAR` | 25,148 | 5.1% |

| flag | rows | share |
|---|---:|---:|
| `is_outbreak` | 32,090 | 6.5% |
| `is_retrospective` | 5,321 | 1.1% |
| `is_fact_check` | 304 | 0.1% |
| `nonmet_sense` | 4,010 | 0.8% |
| `other_hazard` | 112,230 | 22.8% |

## Method

Every distinct headline was labelled by a locally hosted LLM at temperature 0, and the answer propagated to its syndicated copies. There is no rule-based decision stage and no trained classifier: measured against LLM labels on a stratified sample of 385 headlines, the rules agreed 93.4% on the event/not decision after post-stratification, but *missed* ~14,106 headlines the model called events while wrongly calling ~1,615 events — recovering roughly 70% of the event set, to save inference that a local GPU makes free.

The regex cues are retained as audit columns (`cue_*`, `protected`) for stratifying validation and as a drift monitor, but they decide nothing.

## Limitations

1. **Headline and URL only.** An article headlined "storm" cannot be distinguished from one headlined "tornado" on the evidence available here. `UNCLEAR` (5.1% of rows) is the model's own estimate of how often that bites; it is a measured stratum, not a residual.
2. **No human ground truth yet.** Every figure above is the model's output. Precision and recall against human labels require a blind, stratified annotation sample that has not been drawn.
3. **`conf` is self-reported** and is not a calibrated probability. Use the self-consistency `modal_share` from `data/interim/mediacloud_consistency.csv` for uncertainty instead.
4. **Syndicated copies share one label.** Labels are computed per distinct normalised headline; an outlet-specific edit that changes the meaning would be missed.
5. **The corpus is not a census.** Media Cloud covers a subset of US outlets, and per-year row counts vary by more than an order of magnitude (3,050 in 2010 vs 79,619 in 2019), reflecting collection growth at least as much as tornado activity.
6. **854 non-English rows** were labelled with an English prompt and should be treated with caution.
