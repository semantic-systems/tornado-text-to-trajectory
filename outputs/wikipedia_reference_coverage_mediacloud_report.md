# Wikipedia reference coverage — Media Cloud

Generated 2026-11-13T18:57:16+00:00 by `scripts/27_wikipedia_reference_coverage.py match`.

> **Question.** Of the news articles English Wikipedia cites about US tornadoes (2010–2025), how many are in our Media Cloud export (491,432 stories from the US national and state & local collections matching `tornado* AND (wind? OR storm? OR rain? OR damage? OR emergency)`, stage 22)? And would our filter keep them? The same question as the LexisNexis report, so the two can be set side by side.

## Coverage

**4,720 distinct cited articles** (stage 27 `extract`). **In universe:** 3,093 (66%) come from an outlet (domain) with at least one story in our export — a proxy, as for LexisNexis, so in-universe recall is optimistic and overall recall the conservative figure.

| tier                                   |   articles | overall             | in universe         |
|:---------------------------------------|-----------:|:--------------------|:--------------------|
| url                                    |        650 | 13.8% (12.8%–14.8%) | 20.5% (19.1%–21.9%) |
| title_outlet                           |        615 | 13.0% (12.1%–14.0%) | 19.9% (18.5%–21.3%) |
| title_syndicated                       |        286 | 6.1% (5.4%–6.8%)    | 6.7% (5.8%–7.6%)    |
| title_fuzzy                            |         99 | 2.1% (1.7%–2.5%)    | 3.2% (2.6%–3.9%)    |
| **same article** (url or title_outlet) |        817 | 17.3% (16.3%–18.4%) | 25.9% (24.4%–27.4%) |
| **strong** (+ title_syndicated)        |        977 | 20.7% (19.6%–21.9%) | 28.8% (27.2%–30.4%) |

`url`: the citation's URL, normalised (scheme, `www`, tracking parameters and fragment removed), is a story's URL. `title_outlet`: same outlet (domain), ±3 days, headlines agree — the same article under another URL. `title_syndicated`: another outlet, ±3 days, near-identical headline — the same wire story, not the cited copy. `title_fuzzy`: same outlet, ±7 days, headlines partly agree — weak, reported apart. Tiers overlap; each row counts articles with at least one match in that tier. Undated citations are matched within their outlet and the event year only.

## Would our filter keep them?

Stage 30's label on the best-matching story of the 977 held articles. Only `EVENT` stories go on to linking; the others are what the filter drops.

| label             |   articles | share   |
|:------------------|-----------:|:--------|
| EVENT             |        670 | 69%     |
| NOT_TORNADO_EVENT |        214 | 22%     |
| UNCLEAR           |         60 | 6%      |
| PROSPECTIVE       |         33 | 3%      |

## LexisNexis and Media Cloud together

| held by                        |   articles | share               |
|:-------------------------------|-----------:|:--------------------|
| LexisNexis (strong)            |        218 | 4.6% (4.1%–5.3%)    |
| Media Cloud (strong)           |        977 | 20.7% (19.6%–21.9%) |
| both                           |        130 | 2.8% (2.3%–3.3%)    |
| **either**                     |       1065 | 22.6% (21.4%–23.8%) |
| Media Cloud and labelled EVENT |        670 | 14.2% (13.2%–15.2%) |

LexisNexis *strong* is its own report's: `title_outlet`, `title_syndicated` or `content`. A cited article held by neither is missing from both corpora.

### By year of the article

Media Cloud's collections are thin before 2017 (stage 22 holds 3,050 stories for 2010, 79,619 for 2019).

|   year |   cited |   lexisnexis |   mediacloud |   either |
|-------:|--------:|-------------:|-------------:|---------:|
|   2006 |       1 |           0% |           0% |       0% |
|   2007 |       1 |           0% |           0% |       0% |
|   2010 |     140 |           4% |           9% |      10% |
|   2011 |     422 |           3% |          15% |      17% |
|   2012 |     248 |           4% |           9% |      12% |
|   2013 |     329 |           2% |          19% |      19% |
|   2014 |     194 |           3% |          14% |      15% |
|   2015 |     146 |           3% |          15% |      16% |
|   2016 |      85 |           4% |           9% |      11% |
|   2017 |     120 |           3% |          21% |      22% |
|   2018 |     110 |           5% |          10% |      14% |
|   2019 |     232 |           7% |          34% |      37% |
|   2020 |     447 |           5% |          25% |      26% |
|   2021 |     347 |           8% |          34% |      37% |
|   2022 |     257 |           4% |          22% |      23% |
|   2023 |     689 |           5% |          19% |      21% |
|   2024 |     452 |           6% |          27% |      29% |
|   2025 |     476 |           6% |          23% |      25% |
|   2026 |      24 |           0% |           0% |       0% |

### By kind of outlet

| outlet_type     |   cited |   lexisnexis |   mediacloud |   either |
|:----------------|--------:|-------------:|-------------:|---------:|
| local_other     |    2549 |           3% |          14% |      16% |
| local_broadcast |    1069 |           2% |          19% |      20% |
| national        |     709 |          14% |          51% |      55% |
| weather_media   |     315 |           0% |           0% |       0% |
| wire            |      78 |          28% |          60% |      62% |

### In-universe outlets with the most misses

Cited articles from outlets our export does carry, but that no strong tier found: either the story never matched the query (it has to say "tornado" and a storm word) or Media Cloud's feed of that outlet is partial.

| outlet                |   cited |   held |   missed |
|:----------------------|--------:|-------:|---------:|
| cbsnews.com           |     111 |     46 |       65 |
| al.com                |      52 |     15 |       37 |
| cnn.com               |      98 |     61 |       37 |
| usatoday.com          |      60 |     23 |       37 |
| masslive.com          |      36 |      0 |       36 |
| nytimes.com           |      67 |     36 |       31 |
| kcrg.com              |      27 |      0 |       27 |
| desmoinesregister.com |      27 |      3 |       24 |
| nbcnews.com           |      59 |     35 |       24 |
| washingtonpost.com    |      80 |     56 |       24 |
| newschannel5.com      |      25 |      2 |       23 |
| oklahoman.com         |      22 |      1 |       21 |
| thegazette.com        |      21 |      0 |       21 |
| abcnews.go.com        |      59 |     39 |       20 |
| news9.com             |      21 |      1 |       20 |
| clarionledger.com     |      26 |      7 |       19 |
| kcci.com              |      34 |     16 |       18 |
| wfaa.com              |      26 |      8 |       18 |
| fox4news.com          |      18 |      0 |       18 |
| dallasnews.com        |      25 |      8 |       17 |

### Most-cited outlets not in our export

| outlet                    |   cited |
|:--------------------------|--------:|
| weather.com               |     130 |
| foxweather.com            |      80 |
| accuweather.com           |      58 |
| apnews.com                |      40 |
| wlbt.com                  |      26 |
| wunderground.com          |      25 |
| cbc.ca                    |      25 |
| msn.com                   |      23 |
| theweathernetwork.com     |      21 |
| ctvnews.ca                |      20 |
| yahoo.com                 |      14 |
| newsok.com                |      14 |
| wbrc.com                  |      13 |
| spectrumnews1.com         |      12 |
| ottawacitizen.com         |      11 |
| globalnews.ca             |      11 |
|                           |      11 |
| thoughtleadership.aon.com |      11 |
| wvlt.tv                   |      10 |
| local3news.com            |       9 |

## Limitations

1. **Recall on what Wikipedia cites**, which leans to national, wire and online sources — Media Cloud's own strength, so this figure flatters it more than the LexisNexis one flatters LexisNexis.
2. **The universe is a proxy** (domains present in our export).
3. **No content tier**: Media Cloud's export has no text, so a story re-headlined under a new URL is missed; `url` and `title_outlet` are a lower bound on the same article.
4. **Not hand-checked.** `url` needs none; the title tiers use the LexisNexis report's thresholds, whose hand check is in that report.
5. **The query** reaches only stories that say "tornado" and a storm word; a cited aftermath story that says neither is out of scope by construction.
