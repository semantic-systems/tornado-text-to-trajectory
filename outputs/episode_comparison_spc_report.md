# Episode definitions compared — Stage 51 (SPC tracks)

> **Scope:** all 20,164 SPC whole tracks, grouped by each method below. Scores use the 20,008 matched to an NCEI Storm Events row (stage 14), whose `EPISODE_ID` is the reference. This is the evidence behind the rule stage 15 publishes.

Generated 2026-11-09T21:01:39+00:00. `space_time 400km 6h`, carried to DAT hazards, reproduces stage 15's published episodes with ARI 1.0000 (exact).

## How to read the scores

- **recall** — of hazard pairs one office put in one Storm Events episode, the share the method also groups. Below 1 means the method cuts a weather system a forecaster saw as one.
- **office precision** — of hazard pairs the method groups *and* one office reported, the share that office also grouped. Below 1 suggests over-merging; it cannot see merges across offices, which Storm Events never makes.
- **SE split** — share of Storm Events episodes (≥2 matched hazards) that the method spreads over more than one episode.
- **linked** columns — the same against `LINKED_EPISODE`, where episodes of different offices that share a crossing tornado are one. Stricter: a method must also keep together what two offices jointly reported.
- Extent and duration describe what an episode *is* under each method: a method can score perfect recall by merging a whole season.

## Results

| method | episodes | singletons | largest | p95 / max extent km | max h | multi-day | recall | recall linked | office precision | SE split | SE split linked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| convective_day 200km | 5,336 | 55% | 173 | 632 / 1,849 | 24 | 0 | 0.95 | 0.88 | 0.81 | 7.1% | 7.5% |
| convective_day 100km | 7,050 | 59% | 130 | 328 / 1,429 | 23 | 0 | 0.89 | 0.81 | 0.82 | 19.6% | 21.0% |
| convective_day 400km | 4,254 | 50% | 176 | 1,008 / 1,919 | 24 | 0 | 0.95 | 0.88 | 0.81 | 6.1% | 6.3% |
| time-gap 6h, all ratings (Fuhrmann variant) | 2,867 | 34% | 304 | 2,771 / 7,808 | 55 | 170 | 0.98 | 0.98 | 0.81 | 3.6% | 3.9% |
| space_time 100km 1h | 8,676 | 65% | 125 | 267 / 1,299 | 16 | 50 | 0.76 | 0.69 | 0.84 | 40.0% | 41.9% |
| space_time 100km 3h | 7,336 | 61% | 130 | 327 / 1,715 | 24 | 78 | 0.86 | 0.79 | 0.83 | 23.5% | 24.8% |
| space_time 100km 6h | 7,075 | 60% | 226 | 330 / 1,715 | 40 | 95 | 0.90 | 0.89 | 0.83 | 19.4% | 21.0% |
| space_time 200km 1h | 7,648 | 63% | 125 | 391 / 1,521 | 16 | 54 | 0.82 | 0.77 | 0.83 | 32.7% | 34.5% |
| space_time 200km 3h | 5,826 | 58% | 280 | 582 / 2,323 | 42 | 97 | 0.94 | 0.95 | 0.82 | 11.1% | 12.0% |
| space_time 200km 6h | 5,378 | 56% | 285 | 644 / 2,323 | 50 | 123 | 0.97 | 0.97 | 0.81 | 6.0% | 6.6% |
| space_time 400km 1h | 6,857 | 62% | 145 | 638 / 1,849 | 24 | 54 | 0.85 | 0.80 | 0.82 | 29.4% | 31.1% |
| space_time 400km 3h | 4,970 | 55% | 285 | 892 / 2,375 | 42 | 111 | 0.95 | 0.96 | 0.81 | 8.7% | 9.3% |
| space_time 400km 6h | 4,325 | 52% | 297 | 1,033 / 2,537 | 50 | 160 | 0.98 | 0.98 | 0.81 | 4.2% | 4.6% |
| st_dbscan 200km 3h minpts=3 | 6,671 | 76% | 280 | 693 / 2,323 | 42 | 90 | 0.93 | 0.95 | 0.82 | 26.2% | 28.2% |
| st_dbscan 200km 3h minpts=5 | 8,515 | 89% | 275 | 837 / 2,323 | 42 | 75 | 0.89 | 0.92 | 0.82 | 45.0% | 48.3% |
| st_dbscan 400km 3h minpts=3 | 5,678 | 73% | 285 | 983 / 2,375 | 42 | 102 | 0.94 | 0.96 | 0.81 | 20.1% | 21.6% |
| st_dbscan 400km 3h minpts=5 | 7,242 | 87% | 285 | 1,109 / 2,375 | 42 | 81 | 0.91 | 0.94 | 0.81 | 35.8% | 38.4% |
| kde day bw=50km | 5,567 | 56% | 171 | 570 / 1,849 | 24 | 0 | 0.94 | 0.88 | 0.81 | 7.9% | 8.5% |
| kde overlap 24h/12h bw=50km | 5,025 | 57% | 346 | 663 / 2,553 | 123 | 378 | 0.99 | 0.99 | 0.75 | 2.9% | 3.4% |
| kde day bw=100km | 4,363 | 52% | 176 | 1,003 / 1,919 | 24 | 0 | 0.95 | 0.88 | 0.81 | 6.1% | 6.4% |
| kde overlap 24h/12h bw=100km | 3,485 | 53% | 394 | 1,313 / 2,855 | 240 | 531 | 1.00 | 1.00 | 0.71 | 0.7% | 0.7% |

### Recall by period

SPC tracks are complete in every period, so differences between periods here are not a coverage effect.

| method | 2010–2015 | 2016–2020 | 2021–2025 |
|---|---:|---:|---:|
| convective_day 200km | 0.94 | 0.94 | 0.95 |
| convective_day 100km | 0.90 | 0.88 | 0.89 |
| convective_day 400km | 0.94 | 0.94 | 0.95 |
| time-gap 6h, all ratings (Fuhrmann variant) | 0.99 | 0.97 | 0.98 |
| space_time 100km 1h | 0.75 | 0.75 | 0.78 |
| space_time 100km 3h | 0.86 | 0.87 | 0.86 |
| space_time 100km 6h | 0.93 | 0.89 | 0.89 |
| space_time 200km 1h | 0.81 | 0.81 | 0.84 |
| space_time 200km 3h | 0.97 | 0.92 | 0.94 |
| space_time 200km 6h | 0.98 | 0.96 | 0.96 |
| space_time 400km 1h | 0.83 | 0.84 | 0.87 |
| space_time 400km 3h | 0.97 | 0.93 | 0.95 |
| space_time 400km 6h | 0.98 | 0.97 | 0.97 |
| st_dbscan 200km 3h minpts=3 | 0.95 | 0.91 | 0.93 |
| st_dbscan 200km 3h minpts=5 | 0.91 | 0.86 | 0.90 |
| st_dbscan 400km 3h minpts=3 | 0.96 | 0.92 | 0.94 |
| st_dbscan 400km 3h minpts=5 | 0.93 | 0.88 | 0.92 |
| kde day bw=50km | 0.94 | 0.94 | 0.95 |
| kde overlap 24h/12h bw=50km | 0.99 | 0.99 | 0.99 |
| kde day bw=100km | 0.94 | 0.94 | 0.95 |
| kde overlap 24h/12h bw=100km | 1.00 | 1.00 | 1.00 |

## Against SPC watches: upper and lower bounds

Scored on the 14,918 SPC whole tracks in a watch (stage 50; unwatched tornadoes — about a quarter, mostly weak — are left out). Watches are how SPC organised the threat in real time, across offices: an operational and communication unit, not a physical one. Stage 50 gives two granularities, and they bracket every method:

- **Watch systems** (side-by-side watches joined; typically ~800 km across) are coarser than any method. Read as an **upper bound**: of pairs a method groups, the share inside one system — **within systems**, and its **cross-office** part. Below 1, the method merges what SPC never connected.
- **Watch sequences** (one chain of hand-overs; typically ~300 km) are finer than any method. Read as a **lower bound**: of pairs SPC carried in one sequence, the share the method keeps together — **sequences kept**, and the share of sequences **split**. Below 1, the method cuts a chain SPC ran as one.

A method consistent with SPC's operations scores near 1 on both. F1 against either alone is not reported here as a ranking: it measures how close a method's granularity is to that one definition, and the ranking flips between the two (the F1 columns are in the metrics CSV).

| method | within systems | cross-office | sequences kept | sequences split |
|---|---:|---:|---:|---:|
| convective_day 200km | 0.99 | 0.99 | 0.81 | 17.1% |
| convective_day 100km | 1.00 | 0.99 | 0.68 | 45.5% |
| convective_day 400km | 0.98 | 0.97 | 0.84 | 6.0% |
| time-gap 6h, all ratings (Fuhrmann variant) | 0.94 | 0.93 | 0.99 | 2.1% |
| space_time 100km 1h | 1.00 | 1.00 | 0.56 | 61.6% |
| space_time 100km 3h | 1.00 | 1.00 | 0.65 | 47.2% |
| space_time 100km 6h | 1.00 | 1.00 | 0.73 | 45.1% |
| space_time 200km 1h | 1.00 | 0.99 | 0.66 | 50.8% |
| space_time 200km 3h | 1.00 | 1.00 | 0.87 | 21.4% |
| space_time 200km 6h | 1.00 | 0.99 | 0.91 | 15.7% |
| space_time 400km 1h | 0.99 | 0.99 | 0.72 | 43.3% |
| space_time 400km 3h | 0.99 | 0.99 | 0.91 | 10.8% |
| space_time 400km 6h | 0.99 | 0.98 | 0.98 | 3.4% |
| st_dbscan 200km 3h minpts=3 | 1.00 | 1.00 | 0.87 | 34.2% |
| st_dbscan 200km 3h minpts=5 | 1.00 | 1.00 | 0.84 | 53.5% |
| st_dbscan 400km 3h minpts=3 | 0.99 | 0.99 | 0.91 | 21.1% |
| st_dbscan 400km 3h minpts=5 | 0.99 | 0.99 | 0.90 | 38.0% |
| kde day bw=50km | 0.99 | 0.99 | 0.80 | 21.0% |
| kde overlap 24h/12h bw=50km | 0.80 | 0.76 | 0.92 | 16.9% |
| kde day bw=100km | 0.97 | 0.96 | 0.84 | 6.3% |
| kde overlap 24h/12h bw=100km | 0.64 | 0.60 | 1.00 | 1.1% |

## Against SPC watches: does it depend on the linking? (`no-motion`)

The same scores against watch systems linked without the upstream-motion check (`link --no-motion-check`). Systems: 1,810 → 1,703 with a scored tornado; sequences: 3,155 → 3,100. Each cell reads *main → variant*. A conclusion drawn from the watch bounds should hold in both columns; **Kendall τ** says whether the methods keep their order.

| method | within systems | cross-office | sequences kept | sequences split |
|---|---:|---:|---:|---:|
| convective_day 200km | 0.99 → 1.00 | 0.99 → 1.00 | 0.81 → 0.77 | 17.1% → 17.8% |
| convective_day 100km | 1.00 → 1.00 | 0.99 → 1.00 | 0.68 → 0.62 | 45.5% → 46.1% |
| convective_day 400km | 0.98 → 0.99 | 0.97 → 0.99 | 0.84 → 0.80 | 6.0% → 6.6% |
| time-gap 6h, all ratings (Fuhrmann variant) | 0.94 → 0.96 | 0.93 → 0.95 | 0.99 → 0.99 | 2.1% → 2.4% |
| space_time 100km 1h | 1.00 → 1.00 | 1.00 → 1.00 | 0.56 → 0.51 | 61.6% → 62.0% |
| space_time 100km 3h | 1.00 → 1.00 | 1.00 → 1.00 | 0.65 → 0.60 | 47.2% → 47.7% |
| space_time 100km 6h | 1.00 → 1.00 | 1.00 → 1.00 | 0.73 → 0.70 | 45.1% → 45.8% |
| space_time 200km 1h | 1.00 → 1.00 | 0.99 → 1.00 | 0.66 → 0.60 | 50.8% → 51.2% |
| space_time 200km 3h | 1.00 → 1.00 | 1.00 → 1.00 | 0.87 → 0.87 | 21.4% → 22.5% |
| space_time 200km 6h | 1.00 → 1.00 | 0.99 → 1.00 | 0.91 → 0.91 | 15.7% → 16.8% |
| space_time 400km 1h | 0.99 → 1.00 | 0.99 → 1.00 | 0.72 → 0.67 | 43.3% → 43.9% |
| space_time 400km 3h | 0.99 → 1.00 | 0.99 → 0.99 | 0.91 → 0.91 | 10.8% → 11.8% |
| space_time 400km 6h | 0.99 → 0.99 | 0.98 → 0.99 | 0.98 → 0.98 | 3.4% → 4.3% |
| st_dbscan 200km 3h minpts=3 | 1.00 → 1.00 | 1.00 → 1.00 | 0.87 → 0.87 | 34.2% → 35.2% |
| st_dbscan 200km 3h minpts=5 | 1.00 → 1.00 | 1.00 → 1.00 | 0.84 → 0.84 | 53.5% → 54.2% |
| st_dbscan 400km 3h minpts=3 | 0.99 → 1.00 | 0.99 → 0.99 | 0.91 → 0.91 | 21.1% → 22.1% |
| st_dbscan 400km 3h minpts=5 | 0.99 → 1.00 | 0.99 → 0.99 | 0.90 → 0.90 | 38.0% → 38.9% |
| kde day bw=50km | 0.99 → 1.00 | 0.99 → 1.00 | 0.80 → 0.76 | 21.0% → 21.7% |
| kde overlap 24h/12h bw=50km | 0.80 → 0.81 | 0.76 → 0.77 | 0.92 → 0.91 | 16.9% → 17.6% |
| kde day bw=100km | 0.97 → 0.99 | 0.96 → 0.98 | 0.84 → 0.80 | 6.3% → 6.9% |
| kde overlap 24h/12h bw=100km | 0.64 → 0.66 | 0.60 → 0.62 | 1.00 → 1.00 | 1.1% → 1.4% |

- within systems: largest change 0.02, Kendall τ 0.91
- cross-office: largest change 0.02, Kendall τ 0.87
- sequences kept: largest change 0.06, Kendall τ 1.00
- sequences split: largest change 1.1%, Kendall τ 1.00

## Outbreak thresholds on the episode counts

`episode_counts_spc.csv` holds, per method and episode, its SPC tornadoes (`n_spc`), those rated EF1+ (`n_spc_ef1plus`) and unrated (`n_spc_unrated`), and the DAT hazards carried into it (`n_dat`). A minimum size is a filter on these; the groupings themselves apply none. With ≥6 EF1+ (Fuhrmann et al.) the result is close to, not identical with, their outbreaks, since here EF0 tornadoes also chain an episode.

| method | episodes ≥6 tornadoes | ≥6 EF1+ | tornadoes in ≥6 EF1+ |
|---|---:|---:|---:|
| convective_day 200km | 821 | 385 | 43.7% |
| convective_day 100km | 732 | 343 | 32.8% |
| convective_day 400km | 821 | 396 | 50.7% |
| time-gap 6h, all ratings (Fuhrmann variant) | 857 | 397 | 58.1% |
| space_time 100km 1h | 612 | 286 | 26.2% |
| space_time 100km 3h | 716 | 332 | 31.6% |
| space_time 100km 6h | 722 | 339 | 32.8% |
| space_time 200km 1h | 675 | 319 | 31.8% |
| space_time 200km 3h | 778 | 371 | 41.6% |
| space_time 200km 6h | 785 | 373 | 44.2% |
| space_time 400km 1h | 693 | 337 | 37.1% |
| space_time 400km 3h | 772 | 378 | 47.9% |
| space_time 400km 6h | 781 | 386 | 52.1% |
| st_dbscan 200km 3h minpts=3 | 778 | 371 | 41.6% |
| st_dbscan 200km 3h minpts=5 | 760 | 361 | 40.6% |
| st_dbscan 400km 3h minpts=3 | 772 | 378 | 47.9% |
| st_dbscan 400km 3h minpts=5 | 756 | 372 | 47.3% |
| kde day bw=50km | 800 | 382 | 43.0% |
| kde overlap 24h/12h bw=50km | 733 | 360 | 48.7% |
| kde day bw=100km | 811 | 393 | 50.7% |
| kde overlap 24h/12h bw=100km | 647 | 339 | 62.2% |

## Carried to DAT hazards

Each DAT hazard takes the episode of its closest SPC track (stage 14 links); 96.0% have one. The other 4.0% become their own episode, which costs recall where such a hazard belongs to an outbreak. Scores use the DAT hazards' own Storm Events reference, so they compare directly with `episode_comparison_report.md`; **ARI vs published** says how far each SPC-built grouping is from the episodes stage 15 publishes.

> **DAT reference.** 9,868 DAT hazards match a Storm Events row themselves; **878 more** reach one through their SPC track (DAT hazard → SPC track → Storm Events row; mostly hazards whose DAT time is off by hours, stage 14). Where both routes exist (9,864 hazards), they name the same Storm Events episode for **98.6%**. 570 have neither. `--dat-reference direct` scores against the hazards' own matches only.

| method | DAT episodes | recall | recall linked | office precision | SE split | ARI vs published | 2010–2015 | 2016–2020 | 2021–2025 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| convective_day 200km | 3,095 | 0.93 | 0.89 | 0.79 | 7.3% | 0.83 | 0.86 | 0.95 | 0.95 |
| convective_day 100km | 4,029 | 0.88 | 0.83 | 0.80 | 18.5% | 0.69 | 0.83 | 0.90 | 0.89 |
| convective_day 400km | 2,563 | 0.93 | 0.89 | 0.79 | 6.6% | 0.89 | 0.87 | 0.95 | 0.95 |
| time-gap 6h, all ratings (Fuhrmann variant) | 2,122 | 0.98 | 0.98 | 0.79 | 3.2% | 0.93 | 0.99 | 0.98 | 0.98 |
| space_time 100km 1h | 4,871 | 0.77 | 0.72 | 0.82 | 37.1% | 0.58 | 0.73 | 0.79 | 0.78 |
| space_time 100km 3h | 4,160 | 0.87 | 0.82 | 0.81 | 21.6% | 0.69 | 0.83 | 0.90 | 0.86 |
| space_time 100km 6h | 4,031 | 0.91 | 0.91 | 0.81 | 17.9% | 0.73 | 0.95 | 0.91 | 0.89 |
| space_time 200km 1h | 4,323 | 0.83 | 0.79 | 0.81 | 29.9% | 0.69 | 0.76 | 0.84 | 0.84 |
| space_time 200km 3h | 3,341 | 0.95 | 0.95 | 0.80 | 10.0% | 0.85 | 0.97 | 0.95 | 0.94 |
| space_time 200km 6h | 3,107 | 0.97 | 0.97 | 0.79 | 5.7% | 0.90 | 0.98 | 0.97 | 0.96 |
| space_time 400km 1h | 3,915 | 0.86 | 0.82 | 0.80 | 26.2% | 0.79 | 0.79 | 0.87 | 0.87 |
| space_time 400km 3h | 2,923 | 0.96 | 0.96 | 0.80 | 8.1% | 0.94 | 0.98 | 0.96 | 0.95 |
| space_time 400km 6h | 2,585 | 0.97 | 0.97 | 0.79 | 3.9% | 1.00 | 0.99 | 0.97 | 0.97 |
| st_dbscan 200km 3h minpts=3 | 3,648 | 0.94 | 0.94 | 0.80 | 19.2% | 0.85 | 0.96 | 0.94 | 0.93 |
| st_dbscan 200km 3h minpts=5 | 4,429 | 0.91 | 0.93 | 0.80 | 35.3% | 0.84 | 0.93 | 0.91 | 0.90 |
| st_dbscan 400km 3h minpts=3 | 3,166 | 0.95 | 0.96 | 0.79 | 14.8% | 0.94 | 0.97 | 0.95 | 0.95 |
| st_dbscan 400km 3h minpts=5 | 3,785 | 0.93 | 0.94 | 0.79 | 26.8% | 0.93 | 0.95 | 0.93 | 0.92 |
| kde day bw=50km | 3,215 | 0.93 | 0.88 | 0.79 | 8.1% | 0.82 | 0.86 | 0.94 | 0.94 |
| kde overlap 24h/12h bw=50km | 2,939 | 0.99 | 0.99 | 0.76 | 2.6% | 0.83 | 0.99 | 0.99 | 0.99 |
| kde day bw=100km | 2,601 | 0.93 | 0.89 | 0.79 | 6.6% | 0.89 | 0.87 | 0.95 | 0.95 |
| kde overlap 24h/12h bw=100km | 2,127 | 1.00 | 1.00 | 0.73 | 0.6% | 0.77 | 1.00 | 1.00 | 1.00 |

## Carried to DAT hazards — against SPC watches

Scored on the 8,483 DAT hazards with an SPC track in a watch (stage 50; unwatched tornadoes — about a quarter, mostly weak — are left out). Watches are how SPC organised the threat in real time, across offices: an operational and communication unit, not a physical one. Stage 50 gives two granularities, and they bracket every method:

- **Watch systems** (side-by-side watches joined; typically ~800 km across) are coarser than any method. Read as an **upper bound**: of pairs a method groups, the share inside one system — **within systems**, and its **cross-office** part. Below 1, the method merges what SPC never connected.
- **Watch sequences** (one chain of hand-overs; typically ~300 km) are finer than any method. Read as a **lower bound**: of pairs SPC carried in one sequence, the share the method keeps together — **sequences kept**, and the share of sequences **split**. Below 1, the method cuts a chain SPC ran as one.

A method consistent with SPC's operations scores near 1 on both. F1 against either alone is not reported here as a ranking: it measures how close a method's granularity is to that one definition, and the ranking flips between the two (the F1 columns are in the metrics CSV).

| method | within systems | cross-office | sequences kept | sequences split |
|---|---:|---:|---:|---:|
| convective_day 200km | 1.00 | 0.99 | 0.90 | 13.3% |
| convective_day 100km | 1.00 | 1.00 | 0.79 | 38.9% |
| convective_day 400km | 0.97 | 0.96 | 0.92 | 6.5% |
| time-gap 6h, all ratings (Fuhrmann variant) | 0.95 | 0.94 | 1.00 | 1.7% |
| space_time 100km 1h | 1.00 | 1.00 | 0.68 | 55.1% |
| space_time 100km 3h | 1.00 | 1.00 | 0.78 | 40.0% |
| space_time 100km 6h | 1.00 | 1.00 | 0.84 | 38.2% |
| space_time 200km 1h | 1.00 | 1.00 | 0.78 | 43.8% |
| space_time 200km 3h | 1.00 | 1.00 | 0.93 | 15.7% |
| space_time 200km 6h | 1.00 | 1.00 | 0.97 | 10.7% |
| space_time 400km 1h | 0.99 | 0.99 | 0.83 | 36.7% |
| space_time 400km 3h | 0.99 | 0.99 | 0.97 | 8.5% |
| space_time 400km 6h | 0.99 | 0.98 | 0.99 | 2.5% |
| st_dbscan 200km 3h minpts=3 | 1.00 | 1.00 | 0.93 | 25.0% |
| st_dbscan 200km 3h minpts=5 | 1.00 | 1.00 | 0.91 | 41.7% |
| st_dbscan 400km 3h minpts=3 | 0.99 | 0.99 | 0.97 | 15.6% |
| st_dbscan 400km 3h minpts=5 | 0.99 | 0.99 | 0.95 | 27.6% |
| kde day bw=50km | 0.99 | 0.99 | 0.89 | 16.6% |
| kde overlap 24h/12h bw=50km | 0.86 | 0.84 | 0.97 | 11.5% |
| kde day bw=100km | 0.97 | 0.96 | 0.92 | 6.5% |
| kde overlap 24h/12h bw=100km | 0.72 | 0.67 | 1.00 | 0.3% |

## Methods

- **convective_day** — the former episode rule (200 km): same 1200–1159 UTC day, single linkage on track distance.
- **space_time** — single linkage on track distance and the gap between time intervals; no day boundary.
- **time-gap 6h, all ratings (Fuhrmann variant)** — after the outbreak-sequence rule of Fuhrmann et al.: consecutive tornadoes ≤6 h apart, with no distance limit. Unlike theirs, tornadoes of every rating chain (they used F/EF1+), the gap runs from one tornado's end to the next one's start (theirs from start to start), and no minimum count (their ≥6) applies; a count threshold is a filter on the episode counts. Their common synoptic-scale system has no objective test here, so this shows what the time rule alone does.
- **st_dbscan** — Birant & Kut: a hazard needs `minpts` neighbours (itself included) to be a core point; only core points link clusters, so chains of isolated tornadoes do not bridge outbreaks. Noise points stay singletons.
- **kde day** — Shafer & Doswell (2011): Gaussian kernel density of track midpoints per convective day on a 10 km grid; each connected region above half of one isolated tornado's peak is one episode.
- **kde overlap 24h/12h** — the Shafer, Grondin & Doswell (2015) extension: 24 h windows every 12 h, with regions that intersect in consecutive windows joined, so an outbreak is not cut at 12 UTC.

Neither KDE variant replicates the papers: they clustered all severe reports and discarded sparse clusters to rank outbreaks, whereas here every tornado needs an episode. Bandwidths and the threshold are this project's choices.

## Limitations

1. **The reference is office-bounded.** Storm Events episodes never span two offices; linked episodes span offices only where a tornado crossed between them. Both test splitting well and merging only within one office.
2. **Offices differ** in how finely they divide episodes; office precision mixes method behaviour with office practice.
3. **Only matched tornadoes are scored** — for DAT hazards about nine in ten from 2020, fewer before; SPC tracks match Storm Events almost completely (stage 14 report).
4. **The grid is coarse on purpose**: three distances × three gaps, two density settings. A finer search would overfit the one reference available.
5. **SPC geometry is a straight start→end line**; distances between long, curved tracks are approximate under `--anchor spc`.
6. **Watches are a forecast-made reference** (stage 50): they score only watched tornadoes, and they group what SPC expected to be one threat. They are the only reference here that spans offices; as bounds rather than a target, they flag over-merging (systems) and splitting (sequences). Conclusions should hold against both the office episodes and the watch bounds.

## References

- SPC storm reports, organised 1200–1159 UTC: <https://www.spc.noaa.gov/climo/reports/210126_rpts.html>
- Fuhrmann, C. M., et al. (2014). Ranking of tornado outbreaks across the United States and their climatological characteristics. *Weather and Forecasting* 29(3), 684–701, doi:10.1175/WAF-D-13-00128.1. Outbreak definition as in the authors' 2012 abstract: <https://ams.confex.com/ams/26SLS/webprogram/Paper212025.html>
- Birant, D., & Kut, A. (2007). ST-DBSCAN: An algorithm for clustering spatial–temporal data. *Data & Knowledge Engineering* 60(1), 208–221, doi:10.1016/j.datak.2006.01.013
- Shafer, C. M., & Doswell, C. A. (2011). Using kernel density estimation to identify, rank, and classify severe weather outbreak events. *EJSSM* 6(2): <https://ejssm.com/ojs/index.php/site/article/view/29>
- Shafer, C. M., Grondin, N. S., & Doswell, C. A. (2015). Extensions to ranking and classifying severe weather outbreaks using kernel density estimation. 16th Conf. on Mesoscale Processes: <https://ams.confex.com/ams/16Meso/webprogram/Paper274887.html>
