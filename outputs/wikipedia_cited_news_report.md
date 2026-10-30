# News articles cited by Wikipedia

Generated 2026-10-30T13:51:54+00:00 by `scripts/26_wikipedia_cited_news.py`.

The tornado pages cite **4,832 distinct news articles**. **218** are already in LexisNexis (strong match, stage 24) and get no second copy: they are listed in `data/processed/wikipedia_cited_lexisnexis.csv` with the LexisNexis `textref_uid`. The other **4,614** are new text records (`collection = wikipedia_citations`), **3,978 with text** (2,622,547 words, median 456), and **3,697 with text that checks out as the cited article**.

Text bodies stay in `data/processed/wikipedia_cited_news.jsonl` (gitignored): news is copyrighted. The CSV carries metadata and a 30-word snippet.

## Is the text the article?

| text_quality   |   articles | share   |
|:---------------|-----------:|:--------|
| good           |       3697 | 80%     |
| none           |        636 | 14%     |
| unusable       |        213 | 5%      |
| doubtful       |         68 | 1%      |

- **good**: most of the cited headline's words appear near the top of the text (≥ 50%), or in the page's own title (≥ 60%), and none of the problems below.
- **doubtful**: the headline is not found (often the same story under a later headline: archive copies of live pages), the page is mostly navigation with the headline missing, or a differently titled citation on the same site returned nearly the same text.
- **unusable**: a video page, a consent wall or a site front ("Before you continue to YouTube", a TV station's homepage), exactly the same text came back for differently titled citations, or the headline is missing and the text never mentions a storm (another article altogether).
- **none**: no text was retrieved (reasons below).

| reason                           |   articles |
|:---------------------------------|-----------:|
| no_text                          |        636 |
| title_not_found                  |        238 |
| different_article                |        170 |
| same_text_as_other_citations     |        144 |
| navigation_heavy                 |        128 |
| near_same_text_as_other_citation |        108 |
| wall_or_homepage                 |         49 |
| title_unknown                    |         10 |

398 texts never mention a tornado or storm. Wikipedia cites some articles for context (power outages, relief efforts, a building's history), so this is not a quality flag; a relevance label (as for Media Cloud and LexisNexis, stages 18/19) is the next step.

### By outlet type

| outlet_type     |   good |   doubtful |   unusable |   none |   total |
|:----------------|-------:|-----------:|-----------:|-------:|--------:|
| local_broadcast |    839 |         17 |         54 |    158 |    1068 |
| local_other     |   2007 |         29 |        136 |    360 |    2532 |
| national        |    552 |         14 |         12 |     54 |     632 |
| weather_media   |    276 |          8 |         11 |     29 |     324 |
| wire            |     23 |          0 |          0 |     35 |      58 |

### Why there is no text

| retrieval_status            |   articles | share   |
|:----------------------------|-----------:|:--------|
| http_error                  |        288 | 45%     |
| extraction_failed           |        234 | 37%     |
| robots_disallowed           |         77 | 12%     |
| geo_blocked                 |         12 | 2%      |
| no_url                      |         11 | 2%      |
| robots_crawl_delay_too_long |          8 | 1%      |
| blocked                     |          4 | 1%      |
| archive_rate_limited        |          2 | 0%      |

## Retrieval route

| via     |   articles | share   |
|:--------|-----------:|:--------|
| direct  |       2487 | 63%     |
| wayback |       1491 | 37%     |

An archive.org copy is the capture nearest the publication date (mid-year of the event year for undated citations), but the capture time itself was not recorded. A live page captured later shows up as a headline mismatch (doubtful), which is the main risk.

## Stories across outlets

The 3,765 usable texts form **3,701 stories**; 52 stories have more than one copy (largest: 10). Copies are joined by the same headline (five words or more) on the same day, or when at least 50% of the shorter text's 8-word shingles are in the longer one within 14 days. `story_primary` marks one copy per story (best quality, then longest).

| joined by           |   articles | share   |
|:--------------------|-----------:|:--------|
| single copy         |       3649 | 97%     |
| shared_text         |        100 | 3%      |
| same_title_same_day |         16 | 0%      |

## Citation context

5,112 (article, citing passage) pairs in `data/processed/wikipedia_cited_news_citations.csv`. Every article is cited from at least one stage 25 passage.

| event date taken from   |   articles |
|:------------------------|-----------:|
| hazard                  |       2595 |
| episode                 |       2019 |

3,418 articles are cited by a passage that also cites NCEI event ids: a candidate hazard for the linker, to be confirmed by date and place since a passage can cite several.

### Publication relative to the event

For the 3,543 articles with a day-precise date and an event date:

| published        |   articles |
|:-----------------|-----------:|
| before the event |         76 |
| same day         |        319 |
| next day         |        716 |
| 2–7 days         |       1281 |
| 8–30 days        |        387 |
| 31–365 days      |        375 |
| over a year      |        389 |

"Before the event" is mostly forecasts and outlooks, and some passage dates that are the start of a multi-day outbreak.

## Independence axes

Rule `tier_rules_v1_2026-07+event_date_from_citing_passage`: none of these outlets is the surveying organisation; the timing axis uses the event date of the citing passage and, with no survey time yet, never says post-survey (tiering's conservative default). The linker replaces both with the DAT hazard's begin time and survey date.

| temporal_class        |   articles | share   |
|:----------------------|-----------:|:--------|
| post_event_pre_survey |       3503 | 76%     |
| nowcast               |       1035 | 22%     |
| forecast              |         76 | 2%      |

## Caveats

1. **A curated sample, not a census.** Editors cite what they find online, for the tornadoes notable enough to have an article: national, wire and TV-station sites over small papers, recent years over early ones.
2. **LexisNexis overlap is excluded at stage 24's precision.** The title tiers were 100% right in the hand-check and the content tier 95%, so about 10 of the 218 excluded articles may not be in LexisNexis after all.
3. **The title check misses** an article quoted under a different headline and can pass a site front that happens to contain the headline in a list of links; see the examples in stage 24's hand-check.

