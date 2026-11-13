# Episode definitions compared — Stage 25

> **Scope:** all 9,982 DAT hazards, grouped by each method below. Scores use the 9,444 matched to an NCEI Storm Events row (stage 24), whose `EPISODE_ID` is the reference. Stage 3's episodes are unchanged; this is evidence for deciding whether they should be.

Generated 2026-11-09T15:23:40+00:00. Stage 3's rule re-implemented here reproduces its episodes with ARI 1.0000 (exact).

> **DAT reference.** 8,757 DAT hazards match a Storm Events row themselves; **687 more** reach one through their SPC track (DAT hazard → SPC track → Storm Events row; mostly hazards whose DAT time is off by hours, stage 24). Where both routes exist (8,753 hazards), they name the same Storm Events episode for **98.6%**. 538 have neither. `--dat-reference direct` scores against the hazards' own matches only.

## How to read the scores

- **recall** — of hazard pairs one office put in one Storm Events episode, the share the method also groups. Below 1 means the method cuts a weather system a forecaster saw as one.
- **office precision** — of hazard pairs the method groups *and* one office reported, the share that office also grouped. Below 1 suggests over-merging; it cannot see merges across offices, which Storm Events never makes.
- **SE split** — share of Storm Events episodes (≥2 matched hazards) that the method spreads over more than one episode.
- **linked** columns — the same against `LINKED_EPISODE`, where episodes of different offices that share a crossing tornado are one. Stricter: a method must also keep together what two offices jointly reported.
- Extent and duration describe what an episode *is* under each method: a method can score perfect recall by merging a whole season.

## Results

| method | episodes | singletons | largest | p95 / max extent km | max h | multi-day | recall | recall linked | office precision | SE split | SE split linked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| convective_day 200km (stage 3) | 2,795 | 56% | 115 | 624 / 1,485 | 32 | 0 | 0.90 | 0.87 | 0.79 | 13.5% | 14.3% |
| convective_day 100km | 3,636 | 61% | 115 | 352 / 1,429 | 28 | 0 | 0.85 | 0.81 | 0.80 | 24.3% | 26.4% |
| convective_day 400km | 2,283 | 52% | 122 | 978 / 1,780 | 32 | 0 | 0.90 | 0.88 | 0.79 | 12.6% | 13.3% |
| time-gap 6h, all ratings (Fuhrmann variant) | 1,791 | 43% | 123 | 1,925 / 3,998 | 55 | 106 | 0.95 | 0.96 | 0.79 | 9.6% | 10.3% |
| space_time 100km 1h | 4,456 | 67% | 115 | 295 / 939 | 12 | 30 | 0.73 | 0.69 | 0.82 | 43.2% | 45.5% |
| space_time 100km 3h | 3,825 | 63% | 115 | 335 / 1,585 | 23 | 44 | 0.82 | 0.78 | 0.81 | 28.7% | 30.5% |
| space_time 100km 6h | 3,654 | 62% | 115 | 337 / 1,585 | 25 | 59 | 0.88 | 0.88 | 0.81 | 23.7% | 26.1% |
| space_time 200km 1h | 3,969 | 66% | 115 | 412 / 1,122 | 14 | 32 | 0.79 | 0.76 | 0.81 | 37.1% | 39.2% |
| space_time 200km 3h | 3,098 | 60% | 115 | 591 / 1,630 | 23 | 62 | 0.89 | 0.86 | 0.80 | 18.0% | 19.0% |
| space_time 200km 6h | 2,831 | 58% | 115 | 644 / 1,630 | 27 | 78 | 0.94 | 0.95 | 0.79 | 12.0% | 12.9% |
| space_time 400km 1h | 3,622 | 65% | 118 | 635 / 1,364 | 15 | 33 | 0.81 | 0.78 | 0.81 | 34.3% | 36.5% |
| space_time 400km 3h | 2,702 | 58% | 120 | 835 / 1,793 | 32 | 68 | 0.90 | 0.88 | 0.79 | 15.4% | 16.3% |
| space_time 400km 6h | 2,356 | 55% | 122 | 942 / 2,029 | 40 | 100 | 0.95 | 0.95 | 0.79 | 10.2% | 11.0% |
| st_dbscan 200km 3h minpts=3 | 3,537 | 77% | 115 | 701 / 1,630 | 23 | 58 | 0.87 | 0.85 | 0.79 | 31.1% | 33.5% |
| st_dbscan 200km 3h minpts=5 | 4,433 | 90% | 115 | 840 / 1,630 | 23 | 45 | 0.83 | 0.82 | 0.79 | 48.2% | 51.6% |
| st_dbscan 400km 3h minpts=3 | 3,092 | 76% | 120 | 938 / 1,793 | 32 | 62 | 0.89 | 0.87 | 0.79 | 26.1% | 28.2% |
| st_dbscan 400km 3h minpts=5 | 3,875 | 88% | 120 | 1,067 / 1,793 | 32 | 45 | 0.86 | 0.85 | 0.79 | 40.3% | 43.1% |
| kde day bw=50km | 2,942 | 58% | 115 | 565 / 1,485 | 24 | 2 | 0.90 | 0.87 | 0.79 | 14.6% | 15.3% |
| kde overlap 24h/12h bw=50km | 2,573 | 55% | 132 | 624 / 1,630 | 123 | 284 | 0.98 | 0.99 | 0.77 | 4.5% | 4.9% |
| kde day bw=100km | 2,342 | 53% | 122 | 931 / 1,780 | 24 | 2 | 0.90 | 0.88 | 0.79 | 12.6% | 13.3% |
| kde overlap 24h/12h bw=100km | 1,789 | 51% | 152 | 1,228 / 2,590 | 226 | 344 | 0.99 | 1.00 | 0.74 | 1.3% | 1.4% |

### Recall by period

DAT holds a small share of the official tornadoes before ~2020 (stage 24), so early-period scores rest on fewer, possibly unrepresentative, hazards.

| method | 2010–2015 | 2016–2020 | 2021–2025 |
|---|---:|---:|---:|
| convective_day 200km (stage 3) | 0.78 | 0.90 | 0.94 |
| convective_day 100km | 0.75 | 0.85 | 0.87 |
| convective_day 400km | 0.78 | 0.90 | 0.94 |
| time-gap 6h, all ratings (Fuhrmann variant) | 0.93 | 0.93 | 0.96 |
| space_time 100km 1h | 0.59 | 0.74 | 0.76 |
| space_time 100km 3h | 0.69 | 0.85 | 0.84 |
| space_time 100km 6h | 0.89 | 0.87 | 0.88 |
| space_time 200km 1h | 0.65 | 0.80 | 0.82 |
| space_time 200km 3h | 0.72 | 0.90 | 0.92 |
| space_time 200km 6h | 0.92 | 0.92 | 0.95 |
| space_time 400km 1h | 0.66 | 0.81 | 0.84 |
| space_time 400km 3h | 0.75 | 0.91 | 0.94 |
| space_time 400km 6h | 0.93 | 0.93 | 0.96 |
| st_dbscan 200km 3h minpts=3 | 0.70 | 0.88 | 0.91 |
| st_dbscan 200km 3h minpts=5 | 0.65 | 0.83 | 0.88 |
| st_dbscan 400km 3h minpts=3 | 0.74 | 0.89 | 0.93 |
| st_dbscan 400km 3h minpts=5 | 0.69 | 0.85 | 0.91 |
| kde day bw=50km | 0.77 | 0.90 | 0.93 |
| kde overlap 24h/12h bw=50km | 0.97 | 0.98 | 0.99 |
| kde day bw=100km | 0.78 | 0.90 | 0.94 |
| kde overlap 24h/12h bw=100km | 0.98 | 0.99 | 1.00 |

## Against SPC watches: upper and lower bounds

Scored on the 7,427 DAT hazards in a watch (stage 26; unwatched tornadoes — about a quarter, mostly weak — are left out). Watches are how SPC organised the threat in real time, across offices: an operational and communication unit, not a physical one. Stage 26 gives two granularities, and they bracket every method:

- **Watch systems** (side-by-side watches joined; typically ~800 km across) are coarser than any method. Read as an **upper bound**: of pairs a method groups, the share inside one system — **within systems**, and its **cross-office** part. Below 1, the method merges what SPC never connected.
- **Watch sequences** (one chain of hand-overs; typically ~300 km) are finer than any method. Read as a **lower bound**: of pairs SPC carried in one sequence, the share the method keeps together — **sequences kept**, and the share of sequences **split**. Below 1, the method cuts a chain SPC ran as one.

A method consistent with SPC's operations scores near 1 on both. F1 against either alone is not reported here as a ranking: it measures how close a method's granularity is to that one definition, and the ranking flips between the two (the F1 columns are in the metrics CSV).

| method | within systems | cross-office | sequences kept | sequences split |
|---|---:|---:|---:|---:|
| convective_day 200km (stage 3) | 1.00 | 0.99 | 0.88 | 21.5% |
| convective_day 100km | 1.00 | 1.00 | 0.76 | 44.6% |
| convective_day 400km | 0.98 | 0.97 | 0.90 | 15.1% |
| time-gap 6h, all ratings (Fuhrmann variant) | 0.96 | 0.94 | 0.97 | 10.7% |
| space_time 100km 1h | 1.00 | 1.00 | 0.65 | 60.5% |
| space_time 100km 3h | 1.00 | 1.00 | 0.75 | 47.5% |
| space_time 100km 6h | 1.00 | 1.00 | 0.81 | 44.4% |
| space_time 200km 1h | 1.00 | 1.00 | 0.75 | 50.5% |
| space_time 200km 3h | 1.00 | 1.00 | 0.87 | 25.0% |
| space_time 200km 6h | 1.00 | 1.00 | 0.94 | 19.4% |
| space_time 400km 1h | 0.99 | 0.99 | 0.80 | 45.0% |
| space_time 400km 3h | 0.99 | 0.99 | 0.91 | 18.4% |
| space_time 400km 6h | 0.99 | 0.99 | 0.96 | 11.7% |
| st_dbscan 200km 3h minpts=3 | 1.00 | 1.00 | 0.86 | 38.5% |
| st_dbscan 200km 3h minpts=5 | 1.00 | 1.00 | 0.84 | 55.5% |
| st_dbscan 400km 3h minpts=3 | 0.99 | 0.99 | 0.90 | 29.7% |
| st_dbscan 400km 3h minpts=5 | 0.99 | 0.99 | 0.88 | 45.4% |
| kde day bw=50km | 1.00 | 0.99 | 0.88 | 24.6% |
| kde overlap 24h/12h bw=50km | 0.89 | 0.87 | 0.96 | 15.0% |
| kde day bw=100km | 0.98 | 0.97 | 0.90 | 15.1% |
| kde overlap 24h/12h bw=100km | 0.75 | 0.70 | 1.00 | 2.0% |

## Against SPC watches: does it depend on the linking? (`no-motion`)

The same scores against watch systems linked without the upstream-motion check (`link --no-motion-check`). Systems: 1,030 → 979 with a scored tornado; sequences: 1,786 → 1,763. Each cell reads *main → variant*. A conclusion drawn from the watch bounds should hold in both columns; **Kendall τ** says whether the methods keep their order.

| method | within systems | cross-office | sequences kept | sequences split |
|---|---:|---:|---:|---:|
| convective_day 200km (stage 3) | 1.00 → 1.00 | 0.99 → 1.00 | 0.88 → 0.86 | 21.5% → 22.0% |
| convective_day 100km | 1.00 → 1.00 | 1.00 → 1.00 | 0.76 → 0.75 | 44.6% → 45.1% |
| convective_day 400km | 0.98 → 0.99 | 0.97 → 0.99 | 0.90 → 0.88 | 15.1% → 15.3% |
| time-gap 6h, all ratings (Fuhrmann variant) | 0.96 → 0.96 | 0.94 → 0.95 | 0.97 → 0.97 | 10.7% → 11.1% |
| space_time 100km 1h | 1.00 → 1.00 | 1.00 → 1.00 | 0.65 → 0.63 | 60.5% → 60.9% |
| space_time 100km 3h | 1.00 → 1.00 | 1.00 → 1.00 | 0.75 → 0.73 | 47.5% → 48.0% |
| space_time 100km 6h | 1.00 → 1.00 | 1.00 → 1.00 | 0.81 → 0.81 | 44.4% → 45.1% |
| space_time 200km 1h | 1.00 → 1.00 | 1.00 → 1.00 | 0.75 → 0.73 | 50.5% → 50.9% |
| space_time 200km 3h | 1.00 → 1.00 | 1.00 → 1.00 | 0.87 → 0.84 | 25.0% → 25.9% |
| space_time 200km 6h | 1.00 → 1.00 | 1.00 → 1.00 | 0.94 → 0.94 | 19.4% → 20.3% |
| space_time 400km 1h | 0.99 → 1.00 | 0.99 → 1.00 | 0.80 → 0.77 | 45.0% → 45.7% |
| space_time 400km 3h | 0.99 → 1.00 | 0.99 → 0.99 | 0.91 → 0.89 | 18.4% → 19.3% |
| space_time 400km 6h | 0.99 → 0.99 | 0.99 → 0.99 | 0.96 → 0.96 | 11.7% → 12.5% |
| st_dbscan 200km 3h minpts=3 | 1.00 → 1.00 | 1.00 → 1.00 | 0.86 → 0.84 | 38.5% → 39.3% |
| st_dbscan 200km 3h minpts=5 | 1.00 → 1.00 | 1.00 → 1.00 | 0.84 → 0.82 | 55.5% → 56.2% |
| st_dbscan 400km 3h minpts=3 | 0.99 → 1.00 | 0.99 → 0.99 | 0.90 → 0.88 | 29.7% → 30.5% |
| st_dbscan 400km 3h minpts=5 | 0.99 → 1.00 | 0.99 → 0.99 | 0.88 → 0.86 | 45.4% → 46.1% |
| kde day bw=50km | 1.00 → 1.00 | 0.99 → 1.00 | 0.88 → 0.86 | 24.6% → 25.1% |
| kde overlap 24h/12h bw=50km | 0.89 → 0.89 | 0.87 → 0.88 | 0.96 → 0.96 | 15.0% → 15.4% |
| kde day bw=100km | 0.98 → 0.99 | 0.97 → 0.99 | 0.90 → 0.88 | 15.1% → 15.4% |
| kde overlap 24h/12h bw=100km | 0.75 → 0.76 | 0.70 → 0.72 | 1.00 → 0.99 | 2.0% → 2.4% |

- within systems: largest change 0.01, Kendall τ 0.89
- cross-office: largest change 0.01, Kendall τ 0.90
- sequences kept: largest change 0.03, Kendall τ 1.00
- sequences split: largest change 1.0%, Kendall τ 0.98

## Methods

- **convective_day** — stage 3: same 1200–1159 UTC day, single linkage on track distance.
- **space_time** — single linkage on track distance and the gap between time intervals; no day boundary.
- **time-gap 6h, all ratings (Fuhrmann variant)** — after the outbreak-sequence rule of Fuhrmann et al.: consecutive tornadoes ≤6 h apart, with no distance limit. Unlike theirs, tornadoes of every rating chain (they used F/EF1+), the gap runs from one tornado's end to the next one's start (theirs from start to start), and no minimum count (their ≥6) applies; a count threshold is a filter on the episode counts. Their common synoptic-scale system has no objective test here, so this shows what the time rule alone does.
- **st_dbscan** — Birant & Kut: a hazard needs `minpts` neighbours (itself included) to be a core point; only core points link clusters, so chains of isolated tornadoes do not bridge outbreaks. Noise points stay singletons.
- **kde day** — Shafer & Doswell (2011): Gaussian kernel density of track midpoints per convective day on a 10 km grid; each connected region above half of one isolated tornado's peak is one episode.
- **kde overlap 24h/12h** — the Shafer, Grondin & Doswell (2015) extension: 24 h windows every 12 h, with regions that intersect in consecutive windows joined, so an outbreak is not cut at 12 UTC.

Neither KDE variant replicates the papers: they clustered all severe reports and discarded sparse clusters to rank outbreaks, whereas here every tornado needs an episode. Bandwidths and the threshold are this project's choices.

## Limitations

1. **The reference is office-bounded.** Storm Events episodes never span two offices; linked episodes span offices only where a tornado crossed between them. Both test splitting well and merging only within one office.
2. **Offices differ** in how finely they divide episodes; office precision mixes method behaviour with office practice.
3. **Only matched tornadoes are scored** — for DAT hazards about nine in ten from 2020, fewer before; SPC tracks match Storm Events almost completely (stage 24 report).
4. **The grid is coarse on purpose**: three distances × three gaps, two density settings. A finer search would overfit the one reference available.
5. **SPC geometry is a straight start→end line**; distances between long, curved tracks are approximate under `--anchor spc`.
6. **Watches are a forecast-made reference** (stage 26): they score only watched tornadoes, and they group what SPC expected to be one threat. They are the only reference here that spans offices; as bounds rather than a target, they flag over-merging (systems) and splitting (sequences). Conclusions should hold against both the office episodes and the watch bounds.

## References

- SPC storm reports, organised 1200–1159 UTC: <https://www.spc.noaa.gov/climo/reports/210126_rpts.html>
- Fuhrmann, C. M., et al. (2014). Ranking of tornado outbreaks across the United States and their climatological characteristics. *Weather and Forecasting* 29(3), 684–701, doi:10.1175/WAF-D-13-00128.1. Outbreak definition as in the authors' 2012 abstract: <https://ams.confex.com/ams/26SLS/webprogram/Paper212025.html>
- Birant, D., & Kut, A. (2007). ST-DBSCAN: An algorithm for clustering spatial–temporal data. *Data & Knowledge Engineering* 60(1), 208–221, doi:10.1016/j.datak.2006.01.013
- Shafer, C. M., & Doswell, C. A. (2011). Using kernel density estimation to identify, rank, and classify severe weather outbreak events. *EJSSM* 6(2): <https://ejssm.com/ojs/index.php/site/article/view/29>
- Shafer, C. M., Grondin, N. S., & Doswell, C. A. (2015). Extensions to ranking and classifying severe weather outbreaks using kernel density estimation. 16th Conf. on Mesoscale Processes: <https://ams.confex.com/ams/16Meso/webprogram/Paper274887.html>
