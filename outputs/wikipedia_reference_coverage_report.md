# Wikipedia reference coverage — LexisNexis

Generated 2026-10-21T19:14:38+00:00 by `scripts/24_wikipedia_reference_coverage.py match`.

> **Question.** Of the news articles English Wikipedia cites about US tornadoes (2010–2025), how many are in our LexisNexis export (22,896 distinct articles)? Wikipedia's editors chose these without reference to our corpus, so the share is a recall estimate the corpus cannot give about itself — recall on *what Wikipedia cites*, which leans to national, wire and online sources.

## The references

13,766 distinct references on 232 pages (dedicated tornado articles and outbreak articles from stage 23):

| class      |   references |
|:-----------|-------------:|
| nws        |         8005 |
| news       |         4813 |
| social     |          270 |
| reference  |          263 |
| government |          235 |
| other_web  |          180 |

Only `news` enters the denominator. The 4,813 news references are **4,379 distinct cited articles** (one URL cited from several pages counts once); 943 (22%) carry no day-precise date, and can only be matched within their outlet and the event year.

## Coverage

**In universe:** 571 of 4,379 cited articles (13%) come from an outlet that appears in our LexisNexis export. The rest come from outlets LexisNexis either does not carry or that never matched the search; those cannot be told apart without LexisNexis's source list.

| tier               |   this tier |   only this tier | cumulative — overall   | cumulative — in universe   |
|:-------------------|------------:|-----------------:|:-----------------------|:---------------------------|
| `title_outlet`     |          58 |                9 | 1.3% (1.0%–1.7%)       | 10.2% (7.9%–12.9%)         |
| `title_syndicated` |          48 |               13 | 2.3% (1.9%–2.7%)       | 12.1% (9.7%–15.0%)         |
| `content`          |         175 |               97 | 4.5% (4.0%–5.2%)       | 18.0% (15.1%–21.4%)        |
| `title_fuzzy`      |           9 |                4 | 4.6% (4.1%–5.3%)       | 18.7% (15.8%–22.1%)        |

Rows are cumulative in the order shown; 95% Wilson intervals in brackets. **The headline figure is the third row** (`title_outlet` + `title_syndicated` + `content`): **4.5% (4.0%–5.2%) overall, 18.0% (15.1%–21.4%) in universe.** `title_fuzzy` is the weak tier and is reported, not counted, until the hand-check measures its precision.

### The content tier

Text was retrieved for **3,800 of 4,368** cited URLs (87%). Where both a title match and text exist, the text is a check on the title:

| title tier         |   with text |   text confirms | confirmation rate   |
|:-------------------|------------:|----------------:|:--------------------|
| `title_outlet`     |          56 |              48 | 85.7% (74.3%–92.6%) |
| `title_syndicated` |          43 |              34 | 79.1% (64.8%–88.6%) |
| `title_fuzzy`      |           8 |               4 | 50.0% (21.5%–78.5%) |

A title match the text does not confirm is either a false positive or a LexisNexis copy that differs from the web version (print edits, updates); the hand-check separates the two.

### By year of the cited article

|   year |   cited |   in universe |   matched (strong) | recall — overall   | recall — in universe   |
|-------:|--------:|--------------:|-------------------:|:-------------------|:-----------------------|
|   2006 |       1 |             0 |                  0 | 0.0% (0.0%–79.3%)  | –                      |
|   2007 |       1 |             0 |                  0 | 0.0% (0.0%–79.3%)  | –                      |
|   2010 |     123 |            23 |                  4 | 3.3% (1.3%–8.1%)   | 4.3% (0.8%–21.0%)      |
|   2011 |     400 |            58 |                 11 | 2.8% (1.5%–4.9%)   | 15.5% (8.4%–26.9%)     |
|   2012 |     206 |            32 |                  8 | 3.9% (2.0%–7.5%)   | 6.2% (1.7%–20.1%)      |
|   2013 |     315 |            77 |                  7 | 2.2% (1.1%–4.5%)   | 3.9% (1.3%–10.8%)      |
|   2014 |     183 |            30 |                  5 | 2.7% (1.2%–6.2%)   | 10.0% (3.5%–25.6%)     |
|   2015 |     140 |            19 |                  4 | 2.9% (1.1%–7.1%)   | 15.8% (5.5%–37.6%)     |
|   2016 |      74 |            10 |                  3 | 4.1% (1.4%–11.3%)  | 10.0% (1.8%–40.4%)     |
|   2017 |     111 |            11 |                  3 | 2.7% (0.9%–7.6%)   | 18.2% (5.1%–47.7%)     |
|   2018 |      85 |            19 |                  4 | 4.7% (1.8%–11.5%)  | 15.8% (5.5%–37.6%)     |
|   2019 |     210 |            22 |                 16 | 7.6% (4.7%–12.0%)  | 31.8% (16.4%–52.7%)    |
|   2020 |     417 |            31 |                 20 | 4.8% (3.1%–7.3%)   | 32.3% (18.6%–49.9%)    |
|   2021 |     414 |            63 |                 27 | 6.5% (4.5%–9.3%)   | 25.4% (16.3%–37.3%)    |
|   2022 |     220 |            11 |                  8 | 3.6% (1.9%–7.0%)   | 18.2% (5.1%–47.7%)     |
|   2023 |     597 |            54 |                 33 | 5.5% (4.0%–7.7%)   | 24.1% (14.6%–36.9%)    |
|   2024 |     413 |            45 |                 23 | 5.6% (3.7%–8.2%)   | 31.1% (19.5%–45.7%)    |
|   2025 |     444 |            65 |                 23 | 5.2% (3.5%–7.7%)   | 21.5% (13.3%–33.0%)    |
|   2026 |      25 |             1 |                  0 | 0.0% (0.0%–13.3%)  | 0.0% (0.0%–79.3%)      |

### By outlet type

Heuristic: wire = AP/Reuters/AFP/UPI or an agency credit; national = a fixed list of national outlets; local broadcast = a call-sign domain.

| outlet type     |   cited |   in universe |   matched (strong) | recall — overall    | recall — in universe   |
|:----------------|--------:|--------------:|-------------------:|:--------------------|:-----------------------|
| local_broadcast |     990 |            17 |                 17 | 1.7% (1.1%–2.7%)    | 11.8% (3.3%–34.3%)     |
| local_other     |    2404 |           230 |                 71 | 3.0% (2.3%–3.7%)    | 11.3% (7.8%–16.0%)     |
| national        |     650 |           302 |                 90 | 13.8% (11.4%–16.7%) | 21.9% (17.6%–26.9%)    |
| weather_media   |     262 |             0 |                  0 | 0.0% (0.0%–1.4%)    | –                      |
| wire            |      73 |            22 |                 21 | 28.8% (19.7%–40.0%) | 40.9% (23.3%–61.3%)    |

## Coverage per event

- **Pages:** 110 of 227 pages that cite news (48%) have at least one cited article in LexisNexis.
- **Per-tornado sections:** 138 of 869 outbreak sections that cite news (16%) do.

## Matcher or export?

Of the 387 dated in-universe citations with no match, **255 (66%) have no LexisNexis article at all from that outlet within ±3 days.** For those, the export does not hold the outlet's coverage of that event, and no matcher could recover them. The other 132 are where matcher misses can hide — a rewritten print headline, or a different story the same week — and the content tier and the hand-check are what resolve them.

## Where the misses are

### Outlets in universe, cited often, matched rarely

Each is either a matcher failure (rewritten print headline, wrong date) or an outlet whose LexisNexis feed is partial. The hand-check sheet samples from these rows.

| outlet                  |   cited |   matched | lexisnexis_names                                                                 |
|:------------------------|--------:|----------:|:---------------------------------------------------------------------------------|
| CNN                     |      60 |        14 | CNN.com                                                                          |
| The New York Times      |      60 |        15 | The New York Times|The New York Times - International Edition|The New York Times |
| NBC News                |      39 |         3 | NBCNEWS.com                                                                      |
| USA Today               |      30 |         6 | USA TODAY|USA Today|USA Today Online                                             |
| USA TODAY               |      19 |         7 | USA TODAY|USA Today|USA Today Online                                             |
| cnn.com                 |      18 |         3 | CNN.com                                                                          |
| The Guardian            |      14 |         5 | Associated Press Financial Wire|Associated Press International|Associated Press  |
| nbcnews.com             |      13 |         1 | NBCNEWS.com                                                                      |
| Associated Press        |      12 |         7 | Associated Press Financial Wire|Associated Press International|Associated Press  |
| CBC News                |       8 |         0 | CBC (News)                                                                       |
| Iowa Capital Dispatch   |       8 |         3 | Iowa Capital Dispatch                                                            |
| cbc.ca                  |       7 |         0 | CBC (News)                                                                       |
| Newsweek                |       6 |         2 | Newsweek.com                                                                     |
| St. Louis Post-Dispatch |       5 |         1 | St. Louis Post-Dispatch (Missouri)                                               |
| Time                    |       5 |         0 | Time Online                                                                      |
| Deseret News            |       5 |         0 | The Deseret News                                                                 |
| Insurance Journal       |       5 |         1 | Insurance Journal - Wells Media                                                  |
| The Hill                |       5 |         0 | The Hill|TheHill.com                                                             |
| foxnews.com             |       4 |         0 | Associated Press Financial Wire|Associated Press International|Associated Press  |
| The Texas Tribune       |       4 |         0 | The Texas Tribune                                                                |
| The Independent         |       4 |         2 | The Independent (London)|The Independent (United Kingdom)                        |
| usatoday.com            |       4 |         1 | USA TODAY|USA Today|USA Today Online                                             |
| Arkansas Advocate       |       4 |         2 | Arkansas Advocate                                                                |
| National Post           |       4 |         0 | National Post (f/k/a The Financial Post) (Canada)|National Post's Financial Post |
| Daily News              |       4 |         0 | Daily News (New York)|Daily News (South Africa)|Daily News (Sri Lanka)           |

### Most-cited outlets not in our export

These decide the in-universe/overall gap. Looking them up in the LexisNexis source directory turns the proxy into a partly verified list: an outlet LexisNexis carries belongs in the universe, and its citations are misses of our search rather than of LexisNexis.

| outlet                  | domain                |   cited |
|:------------------------|:----------------------|--------:|
| The Weather Channel     | weather.com           |      59 |
| The Washington Post     | washingtonpost.com    |      51 |
| CBS News                | cbsnews.com           |      43 |
| ABC News                | abcnews.go.com        |      37 |
| weather.com             | weather.com           |      37 |
| FOX Weather             | foxweather.com        |      35 |
| masslive.com            | masslive.com          |      33 |
| AL                      | al.com                |      27 |
| Dallas News             | dallasnews.com        |      25 |
| Reuters                 | reuters.com           |      23 |
| www.kcrg.com            | kcrg.com              |      21 |
| www.cbsnews.com         | cbsnews.com           |      21 |
| cbsnews.com             | cbsnews.com           |      21 |
| The Gazette             | thegazette.com        |      19 |
| NBC 5 Dallas-Fort Worth | nbcdfw.com            |      18 |
| The Tennessean          | tennessean.com        |      18 |
| Washington Post         | washingtonpost.com    |      18 |
| KCCI                    | kcci.com              |      18 |
| The Clarion-Ledger      | clarionledger.com     |      17 |
| The Oklahoman           | oklahoman.com         |      17 |
| KOCO                    | koco.com              |      16 |
| FOX 4                   | fox4news.com          |      15 |
| The Des Moines Register | desmoinesregister.com |      15 |
| accuweather.com         | accuweather.com       |      14 |
| WTVF                    | newschannel5.com      |      14 |
| WFAA                    | wfaa.com              |      13 |
| Los Angeles Times       | latimes.com           |      13 |
| NPR                     | npr.org               |      12 |
| Peoria Journal Star     | pjstar.com            |      12 |
| telegram.com            | telegram.com          |      12 |

### `other_web` references (180), excluded from the denominator

Cited without a publication name on a domain that is not NWS, government, social or reference. Many look like local news; if so, the classifier is conservative and the denominator slightly small.

 (39), met.fu-berlin.de (9), kmov.com (3), dailyregister.com (3), weather.com (3), ottawacitizen.com (3), supertalk.fm (3), kstp.com (2), wsaz.com (2), stltoday.com (2), wfmynews2.com (2), ejssm.org (2), kansascity.com (2), accuweather.com (2), zocalo.com.mx (2), flowers-law.com (2), washingtonpost.com (2), cbc.ca (2), kshb.com (2), wibw.com (2), wkrn.com (2), fox23.com (2), finance-commerce.com (2), firstalert4.com (2), dioceselongisland.org (1)

## Validation

`outputs/annotation/wikipedia_ref_handcheck.csv` is blind: each row pairs a cited article with one LexisNexis article, and the tier that proposed the pair is in `data/interim/wikipedia_ref_handcheck_key.csv`, not on the sheet. Up to 20 pairs per tier measure each tier's precision; 30 pairs are a miss with its nearest same-outlet candidate, which measures what the matcher leaves behind. Labels: `same_article`, `same_article_edited` (the same piece in another version — print edit, update, trimmed wire copy), `different_article`, `unsure`.

## Limitations

1. **Recall on what Wikipedia cites**, not on tornado news. Editors cite online, national and wire sources; local print is under-represented.
2. **The universe is a proxy** (outlets present in our export), which makes in-universe recall optimistic. Overall recall is the conservative figure.
3. **Undated citations** are matched within their outlet and event year only, and cannot reach the syndicated tier.
4. **Outlet identity is inferred** from names and domains. A Wikipedia citation of a Gannett paper may be held in LexisNexis under a different masthead; the content tier is what catches those.
5. **Nothing here is validated against humans until the hand-check is filled.**
