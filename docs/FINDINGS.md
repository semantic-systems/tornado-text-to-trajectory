# Findings

An index of the reports in `outputs/`, each with the number it exists to state.
The reports themselves are tracked in git; the figures they reference are not.

Read [../HANDOVER.md](../HANDOVER.md) first — several of these figures carry
caveats that the reports do not yet record.

**Currency:** as of 12 Aug 2026 every figure below reflects the data on disk.
That is not the same as complete — the GDELT sweep stopped at 78% and the
full-text crawl has never run, so the figures resting on those are lower
bounds and are marked as such.

## Geometry

| report | headline finding |
|---|---|
| [events_qa_report.md](../outputs/events_qa_report.md) | The line↔polygon linker scores **99.3% precision** [97.4, 99.8] and **96.2% recall** [93.3, 97.9] against DAT's own `path_guid` key. Only 289 of 9,989 polygons carry a real `path_guid` — the rest hold an all-zero placeholder — so this is a sanity check, not a dataset-wide error rate. For the same tornado, DAT and SPC agree on the rating for 97.0% and on deaths for 99.4%, but differ widely for a few (listed in section 6). |
| [hazard_analysis_report.md](../outputs/hazard_analysis_report.md) | Of SPC's 20,164 tornadoes (2010–2025), **59% have a DAT survey**, rising from 2% (2010) to 89% (2025). Within an era DAT is not a random subset (2020–2025: 64% of tracks under 1 mile against 97% of 15 miles or more; 82% of tornadoes without deaths against 98% with; East South Central 98% against about 25% in the Mountain and Pacific divisions). Deaths from SPC's record. |

## Text layer

| report | headline finding |
|---|---|
| [text_qa_report.md](../outputs/text_qa_report.md) | NWS text for 94.1% of DAT and 89.1% of SPC hazards, a primary survey section for 49.3% and 8.1%. Where survey and record both state the value, the survey's rating agrees with DAT's on **96.6%** (n=5,348) and the death count on **99.4%** — two descriptions of the same survey, compared rather than assumed equal. GDELT's links name episodes from before stage 15's rework until stage 21 is rerun. |
| [news_time_report.md](../outputs/news_time_report.md) | *(August, on the episodes before stage 15's rework; stage 42 stops until stage 31 is rerun.)* Coverage arrives in a consistent order: LSRs at 0.0 h after onset, news at 9.2 h, the oracle survey at 58.3 h, retrospectives at 96.6 h. Reproduces the single-outbreak prototype's ordering at corpus scale. Publication timestamps are date-only for about half the corpus. |
| [link_qa_report.md](../outputs/link_qa_report.md) | What the article→event linker produced. **No annotations have been made**, so this reports volume and score distributions, not precision. |

## News corpora

| report | headline finding |
|---|---|
| [mediacloud_filter_report.md](../outputs/mediacloud_filter_report.md) | 491,432 rows → 266,258 distinct headlines → **48,741 distinct `EVENT` stories**. Self-consistency at T=1: 88.9% unanimous over 3 draws overall, but only **45.4% for `UNCLEAR`** against ~91% for every other label — good evidence the abstention is meaningful rather than a dumping ground. |
| [lexisnexis_filter_report.md](../outputs/lexisnexis_filter_report.md) | 24,917 articles → 20,138 distinct bodies → **12,077 distinct `EVENT` bodies**. See the traps section of HANDOVER: this label set appears to over-call `EVENT`. |
| [corpus_overlap_report.md](../outputs/corpus_overlap_report.md) *(superseded by the atlas)* | The two corpora are **almost disjoint** — 1.4% of Media Cloud stories and 22.0% of LexisNexis bodies have a counterpart. Union = **58,467 distinct tornado-event stories**. Labels agree on 76.3% of shared stories. |
| [overlap_report.md](../outputs/overlap_report.md) *(superseded by the atlas)* | LexisNexis ↔ GDELT: **7.0%** and **16.5%** in the two directions (rebuilt GDELT table, 12 Aug). Broadcast transcripts overlap at **0.0%** — they have no URL for GDELT to index, so their non-overlap is structural. The +27% larger GDELT corpus barely moved the second figure, which says the new material is the same kind as the old. |

| [**corpus_atlas_events_report.md**](../outputs/corpus_atlas_events_report.md) | **The usable corpus.** All three corpora restricted to `EVENT`, in one unit: **76,536 distinct tornado-event stories**, of which 438 are held by all three. Media Cloud 59.6% alone, GDELT 22.0%, LexisNexis 11.7% — close to complementary. **Read this one first.** |
| [corpus_atlas_report.md](../outputs/corpus_atlas_report.md) | The same, unrestricted: what was *collected* rather than what is usable. **325,690 distinct stories**. Also carries the label-agreement crosstabs: the two headline-only corpora agree at **92.2%** with each other but only **74.8%** / **69.1%** with LexisNexis, always in the same direction — evidence that stage 32 over-calls `EVENT`. Capture–recapture is reported but is **not** a population estimate (partly disjoint sampling frames). |

## Retrieval

| report | headline finding |
|---|---|
| [fulltext_pilot_report.md](../outputs/fulltext_pilot_report.md) | 54% of Media Cloud articles retrievable at a 1 s archive interval; 250 of 275 failures were archive *connection* errors and only 16 articles had no archived copy, so the ceiling is ~85–90%. Bias is mild: small outlets 49% vs large 57%. All 10 HTTP 451 geo-blocks in the pilot recovered via the archive — at full scale 472 did not. |
| [fulltext_coverage_report.md](../outputs/fulltext_coverage_report.md) | Full crawl, 2026-10-07: **38,058 / 48,741 = 78.1%** retrieved. Regenerate with `33_fetch_fulltext.py report` — a copy written before that describes the 40-article August resume test, not the corpus. |
| [fulltext_quality_report.md](../outputs/fulltext_quality_report.md) | Is each body the article its headline names? **84.0%** of retrieved bodies pass every hard check → **65.6% of `EVENT` stories have usable full text.** Archive copies pass at 98.5%, live fetches at 70.3% — soft 404s serve front pages with HTTP 200. 38,070 headlines carry 31,931 distinct bodies. |

## Superseded

| report | note |
|---|---|
| [tornado_analysis_report.md](../legacy/tornado_analysis_report.md) (legacy) | Generated 2026-06-15 by `legacy/analyze_noaa_data.py` over the older `events_*.geojson`, which filtered on non-empty survey comments and so covers a different, smaller population. Kept for provenance; superseded by `hazard_analysis_report.md`. |

