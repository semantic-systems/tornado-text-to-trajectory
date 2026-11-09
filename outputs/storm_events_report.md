# NCEI Storm Events against DAT — Stage 24

Generated 2026-11-05T16:01:44+00:00. Storm Events rows matched to DAT hazards when within the `join` tolerances (default 5 km and 30 min, in UTC converted from Storm Data's local standard time).

> Storm Events has one row per tornado **per county**. Rows are chained into whole tornadoes through their `TOR_OTHER_*` pointers (`TORNADO_KEY`), and the tornado counts below are what compare with DAT hazards; the row counts are county segments.

## Coverage by year

| year | SE rows | SE tornadoes | DAT hazards | SE tornadoes found in DAT | DAT hazards found in SE |
|---|---:|---:|---:|---|---|
| 2010 | 1,450 | 1,294 | 18 | 1% [1%, 2%] | 83% [61%, 94%] |
| 2011 | 2,075 | 1,692 | 168 | 9% [8%, 11%] | 82% [76%, 87%] |
| 2012 | 1,058 | 941 | 111 | 4% [3%, 5%] | 27% [20%, 36%] |
| 2013 | 1,053 | 913 | 209 | 20% [17%, 23%] | 80% [74%, 85%] |
| 2014 | 1,064 | 933 | 271 | 31% [28%, 34%] | 74% [68%, 79%] |
| 2015 | 1,320 | 1,177 | 459 | 37% [34%, 39%] | 81% [77%, 84%] |
| 2016 | 1,081 | 983 | 427 | 43% [40%, 46%] | 86% [83%, 89%] |
| 2017 | 1,663 | 1,446 | 695 | 47% [44%, 49%] | 89% [87%, 91%] |
| 2018 | 1,256 | 1,131 | 524 | 47% [44%, 50%] | 88% [85%, 91%] |
| 2019 | 1,737 | 1,521 | 934 | 59% [56%, 61%] | 88% [86%, 90%] |
| 2020 | 1,253 | 1,087 | 706 | 63% [60%, 66%] | 91% [88%, 93%] |
| 2021 | 1,545 | 1,319 | 964 | 69% [67%, 72%] | 87% [84%, 89%] |
| 2022 | 1,384 | 1,169 | 892 | 74% [71%, 76%] | 91% [89%, 93%] |
| 2023 | 1,522 | 1,323 | 971 | 76% [73%, 78%] | 91% [89%, 92%] |
| 2024 | 2,137 | 1,787 | 1,471 | 84% [82%, 85%] | 92% [90%, 93%] |
| 2025 | 1,591 | 1,332 | 1,162 | 85% [83%, 86%] | 89% [87%, 91%] |

The fifth column is **DAT completeness**: the share of officially recorded tornadoes that have a DAT survey. DAT was adopted unevenly by the offices, so it is low in the early years; every figure built on DAT geometry inherits that.
The sixth is the share of DAT hazards with an official record. A DAT hazard without one is usually a timing or location disagreement beyond the tolerances, occasionally a survey Storm Data never received.

## Episodes

- 8,517 Storm Events episodes hold tornadoes; the most offices any one spans is **1**. Episodes are filed per office, so a multi-state outbreak is many episodes.
- **Linked episodes.** 3,190 rows point to a continuation county, 454 of them in another office. Joining episodes that share a tornado turns 8,517 episodes into 7,995 (`LINKED_EPISODE`), 279 of which span more than one office (at most 9). Offices whose parts of an outbreak share no crossing tornado stay separate, so large outbreaks remain several episodes.
- 3,681 episodes are matched to at least one DAT hazard; `scripts/25_compare_episodes.py` scores grouping methods against both `EPISODE_ID` and `LINKED_EPISODE`.

## SPC whole tracks

SPC's database holds one reviewed record per tornado — the official version of the chaining above. Same matching rule; the last column adds the time-repaired second pass (next section).

| year | SPC tornadoes | DAT hazards | SPC tornadoes found in DAT | DAT hazards found in SPC | … with time repair |
|---|---:|---:|---|---|---|
| 2010 | 1,302 | 18 | 2% [1%, 2%] | 83% [61%, 94%] | 89% [67%, 97%] |
| 2011 | 1,704 | 168 | 10% [8%, 11%] | 82% [76%, 87%] | 90% [84%, 94%] |
| 2012 | 948 | 111 | 4% [3%, 5%] | 27% [20%, 36%] | 86% [79%, 92%] |
| 2013 | 916 | 209 | 20% [17%, 22%] | 80% [74%, 85%] | 95% [91%, 97%] |
| 2014 | 928 | 271 | 30% [27%, 33%] | 74% [68%, 79%] | 95% [92%, 97%] |
| 2015 | 1,182 | 459 | 36% [34%, 39%] | 81% [77%, 84%] | 93% [91%, 95%] |
| 2016 | 976 | 427 | 43% [40%, 46%] | 86% [83%, 89%] | 96% [93%, 97%] |
| 2017 | 1,442 | 695 | 47% [44%, 49%] | 89% [87%, 91%] | 96% [94%, 97%] |
| 2018 | 1,138 | 524 | 46% [43%, 49%] | 88% [85%, 91%] | 95% [93%, 97%] |
| 2019 | 1,534 | 934 | 59% [57%, 61%] | 90% [87%, 91%] | 96% [94%, 97%] |
| 2020 | 1,090 | 706 | 64% [61%, 66%] | 92% [90%, 94%] | 97% [95%, 98%] |
| 2021 | 1,328 | 964 | 71% [68%, 73%] | 89% [87%, 91%] | 95% [94%, 96%] |
| 2022 | 1,167 | 892 | 74% [71%, 76%] | 92% [90%, 93%] | 97% [96%, 98%] |
| 2023 | 1,321 | 971 | 76% [74%, 78%] | 91% [89%, 92%] | 96% [94%, 97%] |
| 2024 | 1,805 | 1,471 | 84% [82%, 85%] | 93% [91%, 94%] | 96% [95%, 97%] |
| 2025 | 1,383 | 1,162 | 85% [84%, 87%] | 94% [92%, 95%] | 97% [96%, 98%] |

- **Chaining check.** Of 19,991 Storm Events tornadoes (chained county segments) matched to an SPC track, **98.3%** correspond one-to-one. 69 chains spread over several SPC tracks (over-chained, or SPC keeps them apart); 154 SPC tracks hold several chains (a `TOR_OTHER_*` pointer that did not resolve).
- Records dropped on loading: 0 not whole-track, 0 with an unknown time zone.

## Time-repaired matches (second pass)

The strict rule leaves 1,114 of 9,982 DAT hazards without an SPC track. Most have one within metres whose start differs by a **whole number of hours, to the minute** — the DAT time was saved in the wrong zone or on the wrong date. The second pass links a hazard to an SPC track within 5 km whose start is k hours away, 1 ≤ |k| ≤ 48, to within ±10 min. DAT's times are never changed; the offset is kept on the link (`link_method = time_repaired`, `time_offset_h`, `offset_class`).

**690 more hazards** are linked (88.8% → 95.8% of DAT).

Three checks that do not rest on the time field:

- **The offsets pile up on the hour.** Of 939 candidate pairs within the distance, 613 are within 2 min of a whole hour. Pairs that are not one tornado fall anywhere in the hour; their density 20–30 min from it puts chance at ≈ 67 of the 757 candidates kept (9%, an upper bound — it counts candidates, and most hazards with a chance candidate also have a real one).
- **Ratings agree as often as in the first pass.** EF ratings match on 97% of second-pass links, 97% of first-pass links, and 38% for ratings drawn at random; solving (1 − f)·0.968 + f·0.378 = 0.966 puts the share of wrong pairs at **≈ 0.3%**.
- **DAT's own `event_id` sides with SPC.** Where it holds a legible date (38 links), it is SPC's local date and not DAT's for 18, DAT's and not SPC's for 1. For the date repairs alone (19 with a date): SPC 17, DAT 1.

| cause | hazards | EF agrees | SPC track also has a first-pass hazard |
|---|---:|---:|---:|
| `date` | 195 | 96% | 17 |
| `date+dst` | 10 | 100% | 4 |
| `date+local_as_utc` | 19 | 94% | 1 |
| `date+unexplained` | 20 | 100% | 2 |
| `date+utc_as_local` | 7 | 83% | 3 |
| `dst` | 136 | 96% | 2 |
| `local_as_utc` | 255 | 98% | 5 |
| `unexplained` | 42 | 95% | 1 |
| `utc_as_local` | 6 | 100% | 0 |

Most common class per year (repaired hazards): 2010 dst (1), 2011 local_as_utc (13), 2012 local_as_utc (66), 2013 local_as_utc (32), 2014 local_as_utc (57), 2015 dst (57), 2016 local_as_utc (39), 2017 dst (48), 2018 local_as_utc (36), 2019 date+1 (59), 2020 local_as_utc (36), 2021 local_as_utc (59), 2022 local_as_utc (47), 2023 local_as_utc (48), 2024 local_as_utc (51), 2025 dst (41).

- `local_as_utc` (+4…+7 h): the local clock saved as if it were UTC, so DAT is early by the zone's offset — 5 h for CDT, 6 h for CST.
- `dst` (±1 h): daylight saving applied or missed. `date±n`: the date wrong by n days; combined with an hour part when both are wrong.
- `unexplained`: a whole-hour offset no clock error accounts for; kept, but filter on `offset_class` to drop them.
- A hazard whose SPC track already has a first-pass hazard is probably a second survey of the same tornado in DAT.

### Still without an SPC track

424 DAT hazards (4.2%). 187 have an SPC track within 20 km and 72 h (listed with its distance and offset), **237 have none** — candidates for tornadoes not in the official record (reclassified, never submitted, a duplicate or a test entry). One row each in `data/interim/spc_unmatched_dat_2010-01-01_2025-12-31.csv`, for a hand check.

## Notes

- NCEI revises each year's file in place and publishes the current year with a lag of months; `fetch` always takes the newest revision.
- `EVENT_ID` and `EPISODE_ID` are joined to hazards by space and time, not by key: DAT's own `event_id` is free text and does not reliably equal either.
