# SPC watch systems — Stage 26

Generated 2026-11-03T12:04:13+00:00. Plan: `docs/plan_watch_linking.md`. Thresholds: *Δt* = 3 h, *d* = 50 km (county edge to county edge), upstream tolerance 149 km (calibrated, below).

> A watch system is a connected sequence of SPC tornado and severe thunderstorm watches — how SPC organised the threat in real time, and the unit in which it was communicated. It is an operational grouping, not a physical one.

## Watches and links

- 10,040 watches with county records, 462,184 county spans (0.0% without a Census county boundary, left out of distances).
- County records dropped before linking: 22,203 marine zones (coastal and lake waters listed with the counties), 49 outside SPC's area (Honolulu numbers its own watches from 1, colliding with SPC's), 124 starting before SPC issued the watch of that number and 60 after it expired (mistyped watch numbers), of 484,990; 132 kept although their number has no SPC polygon.
- Links: rule 1 (same county at the same time) **70**, rule 2 (“replaces”) **449** (0 statements naming no watch that ended within a day before, dropped), rule 3 (inferred succession) **7,680**; 1,823 rule-3 candidates rejected only because they lie upstream of the storm motion (`spc_watch_review_<tag>.csv`, to read a sample).
- **4,247 systems**, 1,810 with at least one SPC tornado.
- Rules 1 and 3 alone reproduce **98.9%** of SPC's own “replaces” links — the test of the inferred rule against forecaster-stated succession.

| systems with tornadoes | median | p95 | max |
|---|---:|---:|---:|
| watches | 2 | 11 | 40 |
| tornadoes | 3 | 34 | 292 |
| offices | 6 | 20 | 44 |
| hours | 11 | 32 | 94 |

## Upstream tolerance — calibrated on SPC's stated successions

For the 449 “replaces” links, the displacement of the successor's footprint centre along the storm motion (negative = upstream): 5th percentile -149 km, quartile -6 km, median +49 km; 27.4% lie upstream at all. The tolerance is set so that 95% of these forecaster-stated successions pass: **149 km**. Upstream offsets of genuine successors come from footprint shape and sideways extension along a line, so this measures that noise rather than choosing it.

## Speed limit (diagnostic)

How often a link's footprint centres lie farther apart than storms at the watch's speed (`MV_SKNT`) travel in the gap plus the hand-over hour. Not a rule — the edge-distance condition already bounds distance — but a check that it does: rule-3 links 95.9%, SPC's “replaces” links 81.4%. Footprint centres move with the watch's shape as well as with the storms, so a share above zero is expected for both; a large difference between the two would mean rule 3 links watches SPC would not have.

Split by whether the two watches overlap in time (the successor begins before its predecessor's last county ends: only the hand-over hour of storm travel is allowed) or follow in sequence:

| links | overlapping | beyond speed | sequential | beyond speed |
|---|---:|---:|---:|---:|
| rule 3 (inferred) | 6,852 | 97.9% | 828 | 79.2% |
| rule 2 (“replaces”) | 344 | 81.5% | 105 | 81.0% |

Read: if the gap between rule 3 and rule 2 sits in the overlapping column, rule 3 is joining side-by-side watches of one system (which SPC does not state as replacements), not successions SPC would reject.

## Two granularities: systems and sequences

Most rule-3 links join watches in force *at the same time* whose counties touch — side-by-side watches along one front. Following them gives **systems**: connected watch coverage. Keeping only hand-overs in time (same county at once, “replaces”, or a successor starting after its predecessor ended) gives **sequences**: one chain of watches. Stage 25 uses systems as an upper bound on an event and sequences as a lower bound.

| | groups with tornadoes | largest (tornadoes) | extent p50 | p90 | max |
|---|---:|---:|---:|---:|---:|
| systems | 1,810 | 292 | 787 km | 1,726 km | 2,499 km |
| sequences | 3,155 | 204 | 262 km | 636 km | 1,990 km |

Extent: distance across a group's tornado start points, weighted by tornadoes (the extent the typical tornado's group has).


## Tornadoes in watches

14,918 of 20,164 SPC tornadoes (74.0%) started in a county under a watch (by polygon where SPC gives no county). 0 fall in two systems at once (expected 0: rule 1 links such watches).

| year | tornadoes | in a watch | EF0 | EF1 | EF2+ |
|---|---:|---:|---:|---:|---:|
| 2010 | 1,302 | 77.4% | 73.5% | 80.9% | 87.9% |
| 2011 | 1,704 | 86.3% | 79.4% | 91.0% | 95.1% |
| 2012 | 948 | 73.0% | 66.4% | 80.3% | 89.0% |
| 2013 | 916 | 73.4% | 65.8% | 79.2% | 91.8% |
| 2014 | 928 | 68.2% | 58.7% | 78.1% | 85.7% |
| 2015 | 1,182 | 69.8% | 64.9% | 75.6% | 82.4% |
| 2016 | 976 | 65.7% | 57.4% | 73.9% | 88.6% |
| 2017 | 1,442 | 72.9% | 62.4% | 80.0% | 83.6% |
| 2018 | 1,138 | 65.7% | 55.2% | 77.9% | 84.8% |
| 2019 | 1,534 | 72.6% | 64.2% | 78.1% | 89.5% |
| 2020 | 1,090 | 71.0% | 65.1% | 77.4% | 88.5% |
| 2021 | 1,328 | 68.9% | 58.7% | 75.1% | 89.9% |
| 2022 | 1,167 | 77.2% | 68.6% | 85.6% | 90.5% |
| 2023 | 1,321 | 74.0% | 64.5% | 80.4% | 87.1% |
| 2024 | 1,805 | 78.3% | 69.7% | 85.8% | 91.5% |
| 2025 | 1,383 | 78.3% | 71.9% | 84.2% | 90.6% |

Unwatched tornadoes are a known, non-random class (weak, quickly forming, QLCS and tropical-cyclone tornadoes); scores against watch systems are conditional on being watched.

## Agreement with the office episodes (validation 2)

On watched SPC tornadoes with a Storm Events episode:

- **0.98** of tornado pairs one office put in one episode are in one watch system (linked episodes: 0.98).
- 1.9% of office episodes are split over two or more systems — cases to read: an office episode spanning two systems is either two systems SPC kept apart, or a gap in the watch chain.

## Sensitivity (validation 4)

| Δt h | d km | upstream tolerance | systems with tornadoes | largest (tornadoes) | “replaces” recovered | office recall | office episodes split | linked recall |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 1,978 | 286 | 84.9% | 0.98 | 3.2% | 0.98 |
| 1 | 0 | calibrated (149 km) | 1,865 | 292 | 98.4% | 0.98 | 2.2% | 0.98 |
| 1 | 0 | 2× calibrated (298 km) | 1,821 | 293 | 99.8% | 0.99 | 2.1% | 0.99 |
| 1 | 0 | off | 1,761 | 294 | 99.8% | 0.99 | 1.8% | 0.99 |
| 1 | 50 | 0 | 1,945 | 287 | 85.5% | 0.98 | 3.0% | 0.98 |
| 1 | 50 | calibrated (149 km) | 1,844 | 292 | 98.4% | 0.98 | 2.2% | 0.98 |
| 1 | 50 | 2× calibrated (298 km) | 1,799 | 293 | 99.8% | 0.99 | 2.0% | 0.99 |
| 1 | 50 | off | 1,735 | 294 | 99.8% | 0.99 | 1.8% | 0.99 |
| 1 | 150 | 0 | 1,888 | 287 | 86.4% | 0.98 | 3.0% | 0.98 |
| 1 | 150 | calibrated (149 km) | 1,799 | 292 | 98.4% | 0.98 | 2.2% | 0.98 |
| 1 | 150 | 2× calibrated (298 km) | 1,759 | 293 | 99.8% | 0.99 | 1.9% | 0.99 |
| 1 | 150 | off | 1,688 | 294 | 99.8% | 0.99 | 1.6% | 0.99 |
| 3 | 0 | 0 | 1,954 | 292 | 86.4% | 0.98 | 3.0% | 0.98 |
| 3 | 0 | calibrated (149 km) | 1,841 | 292 | 98.9% | 0.98 | 1.9% | 0.98 |
| 3 | 0 | 2× calibrated (298 km) | 1,789 | 293 | 99.8% | 0.99 | 1.6% | 0.99 |
| 3 | 0 | off | 1,736 | 294 | 99.8% | 0.99 | 1.6% | 0.99 |
| 3 | 50 | 0 | 1,909 | 292 | 87.1% | 0.98 | 2.8% | 0.98 |
| 3 | 50 | calibrated (149 km) | 1,810 | 292 | 98.9% | 0.98 | 1.9% | 0.98 |
| 3 | 50 | 2× calibrated (298 km) | 1,757 | 293 | 99.8% | 0.99 | 1.6% | 0.99 |
| 3 | 50 | off | 1,703 | 294 | 99.8% | 0.99 | 1.5% | 0.99 |
| 3 | 150 | 0 | 1,846 | 292 | 88.0% | 0.98 | 2.7% | 0.98 |
| 3 | 150 | calibrated (149 km) | 1,763 | 292 | 98.9% | 0.98 | 1.9% | 0.98 |
| 3 | 150 | 2× calibrated (298 km) | 1,714 | 293 | 99.8% | 0.99 | 1.6% | 0.99 |
| 3 | 150 | off | 1,651 | 294 | 99.8% | 0.99 | 1.5% | 0.99 |
| 6 | 0 | 0 | 1,906 | 292 | 88.4% | 0.98 | 2.4% | 0.98 |
| 6 | 0 | calibrated (149 km) | 1,794 | 292 | 99.3% | 0.99 | 1.6% | 0.98 |
| 6 | 0 | 2× calibrated (298 km) | 1,738 | 293 | 99.8% | 0.99 | 1.4% | 0.99 |
| 6 | 0 | off | 1,681 | 294 | 99.8% | 0.99 | 1.3% | 0.99 |
| 6 | 50 | 0 | 1,858 | 292 | 89.3% | 0.98 | 2.2% | 0.98 |
| 6 | 50 | calibrated (149 km) | 1,758 | 293 | 99.3% | 0.99 | 1.6% | 0.98 |
| 6 | 50 | 2× calibrated (298 km) | 1,701 | 294 | 99.8% | 0.99 | 1.4% | 0.99 |
| 6 | 50 | off | 1,648 | 294 | 99.8% | 0.99 | 1.3% | 0.99 |
| 6 | 150 | 0 | 1,785 | 292 | 90.6% | 0.98 | 2.1% | 0.98 |
| 6 | 150 | calibrated (149 km) | 1,704 | 293 | 99.3% | 0.99 | 1.6% | 0.98 |
| 6 | 150 | 2× calibrated (298 km) | 1,651 | 294 | 99.8% | 0.99 | 1.4% | 0.99 |
| 6 | 150 | off | 1,588 | 294 | 99.8% | 0.99 | 1.3% | 0.99 |

A reference whose conclusions flip within this range is not a reference.

## Named outbreaks (validation 3, for a hand check)

Tornadoes from 12 UTC on the first day to 12 UTC after the last.

| outbreak | tornadoes | in a watch | systems | largest: tornadoes · watches · offices · hours |
|---|---:|---:|---:|---|
| 2011-04-25 – 2011-04-28 | 355 | 95.8% | 5 | 292 · 40 · 41 · 54 |
| 2013-11-17 | 76 | 98.7% | 1 | 75 · 14 · 25 · 21 |
| 2020-04-12 – 2020-04-13 | 136 | 99.3% | 1 | 135 · 19 · 35 · 50 |
| 2021-12-10 – 2021-12-11 | 71 | 93.0% | 1 | 66 · 11 · 20 · 19 |
| 2023-03-31 – 2023-04-01 | 149 | 98.0% | 2 | 137 · 12 · 27 · 20 |
| 2024-04-26 – 2024-04-28 | 153 | 98.0% | 4 | 69 · 8 · 17 · 26 |

Check each against NWS office and SPC event summaries: one system, several, or merged with another event?
