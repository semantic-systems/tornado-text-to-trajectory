# Wikipedia passages

Generated 2026-10-29T23:21:06+00:00 by `scripts/25_wikipedia_passages.py`.

**855 passages, 641,715 words** from 249 pinned revisions, each a text record in `data/processed/wikipedia_textrefs.csv` (text in `data/processed/wikipedia_passages.jsonl`). Wikipedia is CC BY-SA 4.0; every record carries its revision permalink and licence.

| unit              | links to   |   passages |   dropped (< 30 words) |   median words | path-like   | cite an NCEI event id   | flagged derived_from_oracle   | post-survey   |
|:------------------|:-----------|-----------:|-----------------------:|---------------:|:------------|:------------------------|:------------------------------|:--------------|
| tornado_article   | hazard     |        113 |                      0 |           2003 | 98%         | 83%                     | 27%                           | 100%          |
| tornado_section   | hazard     |        236 |                      0 |            515 | 89%         | 68%                     | 78%                           | 100%          |
| outbreak_overview | episode    |        120 |                      0 |            999 | 50%         | 75%                     | 72%                           | 100%          |
| yearly_event      | episode    |        386 |                      0 |            183 | 13%         | 11%                     | 76%                           | 100%          |

- **Path-like** is a heuristic: at least three of touchdown, direction of motion, a length or width, and lifting appear in the passage. It describes the units, it filters nothing.
- **NCEI event ids** are read from the passage's own references (NCEI Storm Events links). They are the exact bridge to a DAT hazard for the linker; a passage without one has to be linked by date, place and rating.
- **derived_from_oracle** (rule `nws_citation_share_0.5`) flags passages where at least 50% of the references cited are NWS/NOAA products. Provisional: the real test is text overlap with the NCEI narrative, which needs the hazard tables from the server.
- **Post-survey** (rule `tier_rules_v1_2026-07+wikipedia_revision_90d`): the pinned revision is at least 90 days after the event. Wikipedia is never the surveying organisation, so post-survey passages are `independent_retrospective`; the rest, revisions of very recent events, fall to tiering's conservative pre-survey default.

## Overlap between units

- 82 of 236 tornado sections point (`{{Main}}`) to a dedicated article that is also a passage; the section is then a summary of that article. Both are kept; `summarises` names the article's `textref_uid` so an experiment can keep one.
- 142 yearly event sections point to an outbreak article; they are the year page's summary of it.

## Against the census

Of the 506 EF3+ tornadoes in the list census, 399 carry an NCEI event id there, and **135** of those are cited by a tornado article or tornado section. That is the floor of what the linker can join exactly; passages that cite no id still describe tornadoes and are linked by date and place.

| rating   |   in census |   cited by a hazard-level passage |
|:---------|------------:|----------------------------------:|
| EF3      |         415 |                                86 |
| EF4      |          82 |                                45 |
| EF5      |           9 |                                 4 |

## By year

|   year |   tornado_article |   tornado_section |   outbreak_overview |   yearly_event |
|-------:|------------------:|------------------:|--------------------:|---------------:|
|   2010 |                 7 |                13 |                  10 |             36 |
|   2011 |                21 |                43 |                   8 |             24 |
|   2012 |                 9 |                16 |                   8 |             17 |
|   2013 |                 7 |                12 |                   8 |             15 |
|   2014 |                 3 |                11 |                   5 |             18 |
|   2015 |                 3 |                 9 |                   6 |             18 |
|   2016 |                 2 |                 7 |                   5 |             23 |
|   2017 |                 4 |                 8 |                   7 |             31 |
|   2018 |                 1 |                 3 |                   4 |             24 |
|   2019 |                 6 |                13 |                   8 |             23 |
|   2020 |                 7 |                14 |                   8 |             26 |
|   2021 |                 7 |                12 |                   7 |             31 |
|   2022 |                 4 |                10 |                   8 |             24 |
|   2023 |                14 |                19 |                   9 |             24 |
|   2024 |                 9 |                24 |                  13 |             29 |
|   2025 |                 9 |                22 |                   6 |             23 |

## Caveats

1. **Event dates** come from the infobox, the heading, the section's first date, or the title, in that order; 0 passages have none. A tornado section's first date is usually its own, but can be a date it compares with.
2. **A tornado section** may describe a family of tornadoes from one storm; it links to a hazard only when the linker finds exactly one.
3. **Revisions are pinned** at discovery (stage 23). Re-running discovery pins newer ones and changes the `textref_uid`s, by design.

