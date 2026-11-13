# Wikipedia passages

Generated 2026-11-13T18:13:05+00:00 by `scripts/28_wikipedia_passages.py`.

**853 passages, 637,141 words** from 247 pinned revisions, each a text record in `data/processed/wikipedia_textrefs.csv` (text in `data/processed/wikipedia_passages.jsonl`). Wikipedia is CC BY-SA 4.0; every record carries its revision permalink and licence.

| unit              | links to   |   passages |   dropped (< 30 words) |   median words | path-like   | cite an NCEI event id   | flagged derived_from_oracle   | post-survey   |
|:------------------|:-----------|-----------:|-----------------------:|---------------:|:------------|:------------------------|:------------------------------|:--------------|
| tornado_article   | hazard     |        111 |                      0 |           2003 | 99%         | 75%                     | 20%                           | 100%          |
| tornado_section   | hazard     |        236 |                      0 |            515 | 89%         | 58%                     | 76%                           | 100%          |
| outbreak_overview | episode    |        120 |                      0 |            999 | 50%         | 20%                     | 51%                           | 100%          |
| yearly_event      | episode    |        386 |                      0 |            183 | 13%         | 11%                     | 76%                           | 100%          |

- **Path-like** is a heuristic: at least three of touchdown, direction of motion, a length or width, and lifting appear in the passage. It describes the units, it filters nothing.
- **NCEI event ids** are read from the passage's own references (NCEI Storm Events links). They are the exact bridge to a DAT hazard for the linker; a passage without one has to be linked by date, place and rating.
- **derived_from_oracle** (rule `nws_citation_share_0.5`) flags passages where at least 50% of the references cited are NWS/NOAA products. Provisional: the real test is text overlap with the NCEI narrative, which needs the hazard tables from the server.
- **Post-survey** (rule `tier_rules_v2_2026-11+wikipedia_revision_90d`): the pinned revision is at least 90 days after the event. Wikipedia is never the surveying organisation, so post-survey passages are `independent_retrospective`; the rest, revisions of very recent events, fall to tiering's conservative pre-survey default.

## Overlap between units

- 82 of 236 tornado sections point (`{{Main}}`) to a dedicated article that is also a passage; the section is then a summary of that article. Both are kept; `summarises` names the article's `textref_uid` so an experiment can keep one.
- 142 yearly event sections point to an outbreak article; they are the year page's summary of it.

## Facts: infoboxes and table rows

Tables and infoboxes are kept out of the passage text. They are **20,886 fact records** of their own in `data/processed/wikipedia_facts.csv` (20,419 table rows, 467 infoboxes), linked to passages in `data/processed/wikipedia_fact_links.csv`. They are copied from NWS surveys and NCEI, so they are **oracle** data: for labelling and checking links, never as the linker's input.

| relation           |   links |
|:-------------------|--------:|
| listed_in_outbreak |    4277 |
| infobox_of         |     467 |
| same_tornado       |     298 |

- `infobox_of`: the infobox of an article, or of a tornado section (outbreak articles give significant tornadoes their own). `listed_in_outbreak`: a row of the outbreak article's own tables, one of its tornadoes. `same_tornado`: the table row about the tornado a section or article describes, in a state it names, within its dates; `match` says how: `by_id` (the row cites an NCEI id the passage cites), `by_places` (half or more of the heading's places, at least two), `by_one_place` (the only tornado in the window naming one of them, or the only one with the passage's rating). `ambiguous` passages get no row.

How each hazard-level passage matched a table row:

| unit_kind       |   ambiguous |   by_id |   by_one_place |   by_places |   no_match |   no_places |
|:----------------|------------:|--------:|---------------:|------------:|-----------:|------------:|
| tornado_article |          20 |      48 |              7 |          25 |         10 |           1 |
| tornado_section |          18 |     107 |             37 |          66 |          7 |           1 |

**NCEI ids.** A passage's `ncei_event_ids` are those its own prose cites (221 of 347 hazard-level passages); ids cited in the passage's tables are in `ncei_event_ids_tables`, and the ids of its matched facts in `ncei_event_ids_facts` (235 passages; 85 of them have none in their prose). Sections whose prose gave no date of their own take the matched row's date (`event_date_basis = table_row`: 211).

## Against the census

Of the 506 EF3+ tornadoes in the list census, 399 carry an NCEI event id there, and **119** of those are cited by a tornado article or tornado section. That is the floor of what the linker can join exactly; passages that cite no id still describe tornadoes and are linked by date and place.

| rating   |   in census |   cited by a hazard-level passage |
|:---------|------------:|----------------------------------:|
| EF3      |         415 |                                76 |
| EF4      |          82 |                                40 |
| EF5      |           9 |                                 3 |

## By year

|   year |   tornado_article |   tornado_section |   outbreak_overview |   yearly_event |
|-------:|------------------:|------------------:|--------------------:|---------------:|
|   2010 |                 7 |                13 |                  10 |             36 |
|   2011 |                21 |                43 |                   8 |             24 |
|   2012 |                 8 |                16 |                   8 |             17 |
|   2013 |                 7 |                12 |                   8 |             15 |
|   2014 |                 3 |                11 |                   5 |             18 |
|   2015 |                 3 |                 9 |                   6 |             18 |
|   2016 |                 2 |                 7 |                   5 |             23 |
|   2017 |                 4 |                 8 |                   7 |             31 |
|   2018 |                 1 |                 3 |                   4 |             24 |
|   2019 |                 6 |                13 |                   8 |             23 |
|   2020 |                 7 |                14 |                   8 |             26 |
|   2021 |                 6 |                12 |                   7 |             31 |
|   2022 |                 4 |                10 |                   8 |             24 |
|   2023 |                14 |                19 |                   9 |             24 |
|   2024 |                 9 |                24 |                  13 |             29 |
|   2025 |                 9 |                22 |                   6 |             23 |

## Caveats

1. **Event dates** come from the infobox, the heading, the section's first date, or the title, in that order; 0 passages have none. A tornado section's first date is usually its own, but can be a date it compares with.
2. **A tornado section** may describe a family of tornadoes from one storm; it links to a hazard only when the linker finds exactly one.
3. **Revisions are pinned** at discovery (stage 26). Re-running discovery pins newer ones and changes the `textref_uid`s, by design.

