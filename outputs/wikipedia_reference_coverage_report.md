# Wikipedia reference coverage — LexisNexis

Generated 2026-10-29T22:39:18+00:00 by `scripts/24_wikipedia_reference_coverage.py match`.

> **Question.** Of the news articles English Wikipedia cites about US tornadoes (2010–2025), how many are in our LexisNexis export (22,896 distinct articles)? Wikipedia's editors chose these without reference to our corpus, so the share is a recall estimate the corpus cannot give about itself — recall on *what Wikipedia cites*, which leans to national, wire and online sources.

## The references

15,553 distinct references on 249 pages (dedicated tornado articles and outbreak articles from stage 23):

| class      |   references |
|:-----------|-------------:|
| nws        |         9064 |
| news       |         5395 |
| social     |          342 |
| reference  |          287 |
| government |          243 |
| other_web  |          222 |

Only `news` enters the denominator. The 5,395 news references are **4,832 distinct cited articles** (one URL cited from several pages counts once); 1,107 (23%) carry no day-precise date, and can only be matched within their outlet and the event year.

## Coverage

**In universe:** 634 of 4,832 cited articles (13%) come from an outlet that appears in our LexisNexis export. The rest come from outlets LexisNexis either does not carry or that never matched the search; those cannot be told apart without LexisNexis's source list.

| tier               |   this tier |   only this tier | cumulative — overall   | cumulative — in universe   |
|:-------------------|------------:|-----------------:|:-----------------------|:---------------------------|
| `title_outlet`     |          61 |                9 | 1.3% (1.0%–1.6%)       | 9.6% (7.6%–12.2%)          |
| `title_syndicated` |          58 |               14 | 2.3% (1.9%–2.7%)       | 12.1% (9.8%–14.9%)         |
| `content`          |         192 |              105 | 4.5% (4.0%–5.1%)       | 18.1% (15.3%–21.3%)        |
| `title_fuzzy`      |          10 |                4 | 4.6% (4.0%–5.2%)       | 18.8% (15.9%–22.0%)        |

Rows are cumulative in the order shown; 95% Wilson intervals in brackets. **The headline figure is the third row** (`title_outlet` + `title_syndicated` + `content`): **4.5% (4.0%–5.1%) overall, 18.1% (15.3%–21.3%) in universe.** `title_fuzzy` is the weak tier and is reported, not counted; the Validation section gives its precision and the adjusted figure.

### The content tier

Text was retrieved for **4,189 of 4,821** cited URLs (87%). Where both a title match and text exist, the text is a check on the title:

| title tier         |   with text |   text confirms | confirmation rate   |
|:-------------------|------------:|----------------:|:--------------------|
| `title_outlet`     |          59 |              50 | 84.7% (73.5%–91.8%) |
| `title_syndicated` |          53 |              42 | 79.2% (66.5%–88.0%) |
| `title_fuzzy`      |           9 |               5 | 55.6% (26.7%–81.1%) |

A title match the text does not confirm is either a false positive or a LexisNexis copy that differs from the web version (print edits, updates); the hand-check separates the two.

### By year of the cited article

|   year |   cited |   in universe |   matched (strong) | recall — overall   | recall — in universe   |
|-------:|--------:|--------------:|-------------------:|:-------------------|:-----------------------|
|   2006 |       1 |             0 |                  0 | 0.0% (0.0%–79.3%)  | –                      |
|   2007 |       1 |             0 |                  0 | 0.0% (0.0%–79.3%)  | –                      |
|   2010 |     140 |            26 |                  5 | 3.6% (1.5%–8.1%)   | 3.8% (0.7%–18.9%)      |
|   2011 |     422 |            61 |                 11 | 2.6% (1.5%–4.6%)   | 14.8% (8.0%–25.7%)     |
|   2012 |     253 |            42 |                  9 | 3.6% (1.9%–6.6%)   | 4.8% (1.3%–15.8%)      |
|   2013 |     329 |            82 |                  7 | 2.1% (1.0%–4.3%)   | 3.7% (1.3%–10.2%)      |
|   2014 |     194 |            32 |                  5 | 2.6% (1.1%–5.9%)   | 9.4% (3.2%–24.2%)      |
|   2015 |     146 |            19 |                  4 | 2.7% (1.1%–6.8%)   | 15.8% (5.5%–37.6%)     |
|   2016 |      85 |            11 |                  3 | 3.5% (1.2%–9.9%)   | 9.1% (1.6%–37.7%)      |
|   2017 |     121 |            11 |                  4 | 3.3% (1.3%–8.2%)   | 18.2% (5.1%–47.7%)     |
|   2018 |     110 |            20 |                  5 | 4.5% (2.0%–10.2%)  | 20.0% (8.1%–41.6%)     |
|   2019 |     232 |            23 |                 17 | 7.3% (4.6%–11.4%)  | 34.8% (18.8%–55.1%)    |
|   2020 |     447 |            35 |                 21 | 4.7% (3.1%–7.1%)   | 28.6% (16.3%–45.1%)    |
|   2021 |     448 |            70 |                 29 | 6.5% (4.5%–9.1%)   | 24.3% (15.8%–35.5%)    |
|   2022 |     259 |            15 |                  9 | 3.5% (1.8%–6.5%)   | 20.0% (7.0%–45.2%)     |
|   2023 |     689 |            63 |                 35 | 5.1% (3.7%–7.0%)   | 23.8% (15.0%–35.6%)    |
|   2024 |     455 |            50 |                 26 | 5.7% (3.9%–8.2%)   | 32.0% (20.8%–45.8%)    |
|   2025 |     476 |            73 |                 28 | 5.9% (4.1%–8.4%)   | 24.7% (16.2%–35.6%)    |
|   2026 |      24 |             1 |                  0 | 0.0% (0.0%–13.8%)  | 0.0% (0.0%–79.3%)      |

### By outlet type

Heuristic: wire = AP/Reuters/AFP/UPI or an agency credit; national = a fixed list of national outlets; local broadcast = a call-sign domain.

| outlet type     |   cited |   in universe |   matched (strong) | recall — overall    | recall — in universe   |
|:----------------|--------:|--------------:|-------------------:|:--------------------|:-----------------------|
| local_broadcast |    1086 |            18 |                 18 | 1.7% (1.1%–2.6%)    | 11.1% (3.1%–32.8%)     |
| local_other     |    2609 |           247 |                 77 | 3.0% (2.4%–3.7%)    | 12.1% (8.6%–16.8%)     |
| national        |     733 |           344 |                101 | 13.8% (11.5%–16.5%) | 21.2% (17.2%–25.8%)    |
| weather_media   |     324 |             0 |                  0 | 0.0% (0.0%–1.2%)    | –                      |
| wire            |      80 |            25 |                 22 | 27.5% (18.9%–38.1%) | 40.0% (23.4%–59.3%)    |

## Coverage per event

- **Pages:** 121 of 244 pages that cite news (50%) have at least one cited article in LexisNexis.
- **Per-tornado outbreak sections:** 132 of 236 cite news; 25 of those (19%) have at least one cited article in LexisNexis.
- **Yearly event sections:** 209 of 386 cite news; 23 of those (11%) have at least one cited article in LexisNexis.

## Matcher or export?

Of the 426 dated in-universe citations with no match, **284 (67%) have no LexisNexis article at all from that outlet within ±3 days.** For those, the export does not hold the outlet's coverage of that event, and no matcher could recover them. The other 142 are where matcher misses can hide — a rewritten print headline, or a different story the same week — and the content tier and the hand-check are what resolve them.

## Where the misses are

### Outlets in universe, cited often, matched rarely

Each is either a matcher failure (rewritten print headline, wrong date) or an outlet whose LexisNexis feed is partial. The hand-check sheet samples from these rows.

| outlet                  |   cited |   matched | lexisnexis_names                                                                 |
|:------------------------|--------:|----------:|:---------------------------------------------------------------------------------|
| CNN                     |      68 |        17 | CNN.com                                                                          |
| The New York Times      |      65 |        16 | The New York Times|The New York Times - International Edition|The New York Times |
| NBC News                |      39 |         3 | NBCNEWS.com                                                                      |
| USA Today               |      35 |         7 | USA TODAY|USA Today|USA Today Online                                             |
| cnn.com                 |      28 |         5 | CNN.com                                                                          |
| nbcnews.com             |      19 |         2 | NBCNEWS.com                                                                      |
| USA TODAY               |      18 |         6 | USA TODAY|USA Today|USA Today Online                                             |
| The Guardian            |      14 |         5 | Associated Press Financial Wire|Associated Press International|Associated Press  |
| Associated Press        |      13 |         7 | Associated Press Financial Wire|Associated Press International|Associated Press  |
| CBC News                |       9 |         0 | CBC (News)                                                                       |
| Iowa Capital Dispatch   |       8 |         3 | Iowa Capital Dispatch                                                            |
| cbc.ca                  |       8 |         1 | CBC (News)                                                                       |
| Newsweek                |       6 |         2 | Newsweek.com                                                                     |
| Daily News              |       5 |         0 | Daily News (New York)|Daily News (South Africa)|Daily News (Sri Lanka)           |
| The Hill                |       5 |         0 | The Hill|TheHill.com                                                             |
| The Independent         |       5 |         2 | The Independent (London)|The Independent (United Kingdom)                        |
| St. Louis Post-Dispatch |       5 |         1 | St. Louis Post-Dispatch (Missouri)                                               |
| Insurance Journal       |       5 |         1 | Insurance Journal - Wells Media                                                  |
| Time                    |       5 |         0 | Time Online                                                                      |
| Deseret News            |       5 |         0 | The Deseret News                                                                 |
| The Texas Tribune       |       4 |         0 | The Texas Tribune                                                                |
| foxnews.com             |       4 |         0 | Associated Press Financial Wire|Associated Press International|Associated Press  |
| Ottawa Citizen          |       4 |         2 | Ottawa Citizen                                                                   |
| usatoday.com            |       4 |         1 | USA TODAY|USA Today|USA Today Online                                             |
| New York Daily News     |       4 |         0 | New York Daily News                                                              |

### Most-cited outlets not in our export

These decide the in-universe/overall gap. Looking them up in the LexisNexis source directory turns the proxy into a partly verified list: an outlet LexisNexis carries belongs in the universe, and its citations are misses of our search rather than of LexisNexis.

| outlet                  | domain                |   cited |
|:------------------------|:----------------------|--------:|
| The Weather Channel     | weather.com           |      61 |
| The Washington Post     | washingtonpost.com    |      56 |
| weather.com             | weather.com           |      50 |
| CBS News                | cbsnews.com           |      45 |
| ABC News                | abcnews.go.com        |      41 |
| FOX Weather             | foxweather.com        |      39 |
| masslive.com            | masslive.com          |      33 |
| AL                      | al.com                |      26 |
| Dallas News             | dallasnews.com        |      25 |
| Reuters                 | reuters.com           |      25 |
| www.cbsnews.com         | cbsnews.com           |      24 |
| cbsnews.com             | cbsnews.com           |      24 |
| www.kcrg.com            | kcrg.com              |      21 |
| KCCI                    | kcci.com              |      20 |
| Washington Post         | washingtonpost.com    |      20 |
| accuweather.com         | accuweather.com       |      20 |
| The Tennessean          | tennessean.com        |      19 |
| The Gazette             | thegazette.com        |      19 |
| The Oklahoman           | oklahoman.com         |      19 |
| KOCO                    | koco.com              |      18 |
| NBC 5 Dallas-Fort Worth | nbcdfw.com            |      17 |
| The Clarion-Ledger      | clarionledger.com     |      17 |
| FOX 4                   | fox4news.com          |      15 |
| The Des Moines Register | desmoinesregister.com |      15 |
| Chicago Tribune         | chicagotribune.com    |      14 |
| WTVF                    | newschannel5.com      |      14 |
| WFAA                    | wfaa.com              |      13 |
| Los Angeles Times       | latimes.com           |      13 |
| ksdk.com                | ksdk.com              |      13 |
| AP News                 | apnews.com            |      13 |

### `other_web` references (222), excluded from the denominator

Cited without a publication name on a domain that is not NWS, government, social or reference. Many look like local news; if so, the classifier is conservative and the denominator slightly small.

 (41), met.fu-berlin.de (9), kstp.com (4), stltoday.com (4), weather.com (4), wsaz.com (3), accuweather.com (3), dailyregister.com (3), zocalo.com.mx (3), ottawacitizen.com (3), supertalk.fm (3), fergusfallsjournal.com (2), wfmynews2.com (2), ejssm.org (2), theweathernetwork.com (2), kmbc.com (2), kansascity.com (2), kmov.com (2), windsorite.ca (2), flowers-law.com (2), washingtonpost.com (2), cbc.ca (2), kshb.com (2), wibw.com (2), wkrn.com (2)

## Validation

`outputs/annotation/wikipedia_ref_handcheck.csv` is blind: each row pairs a cited article with one LexisNexis article, and the tier that proposed the pair is in `data/interim/wikipedia_ref_handcheck_key.csv`, not on the sheet. Up to 20 pairs per tier measure each tier's precision; 30 pairs are a miss with its nearest same-outlet candidate, which measures what the matcher leaves behind. Labels: `same_article`, `same_article_edited` (the same piece in another version — print edit, update, trimmed wire copy), `different_article`, `unsure`.

### Precision per tier

| tier               |   pairs |   same |   same, edited |   different |   unsure | precision             |
|:-------------------|--------:|-------:|---------------:|------------:|---------:|:----------------------|
| `title_outlet`     |      20 |     16 |              4 |           0 |        0 | 100.0% (83.9%–100.0%) |
| `title_syndicated` |      20 |     17 |              3 |           0 |        0 | 100.0% (83.9%–100.0%) |
| `content`          |      20 |     15 |              4 |           1 |        0 | 95.0% (76.4%–99.1%)   |
| `title_fuzzy`      |      10 |      4 |              1 |           4 |        1 | 55.6% (26.7%–81.1%)   |

Precision counts `same_article` and `same_article_edited` as correct and leaves `unsure` out. Where two articles were the same, the labeller found the difference almost always in the front matter — a dateline ("JACKSON, Miss. (AP) —"), the headline repeated as the first line, or a lead-in sentence ("The following information was released by …:"). None of that moves a match: the title tiers compare headlines, and a prefix touches only the first few of a text's hundreds of shingles.

### Pairs labelled different

Full-text overlap in both directions (unsampled 8-word shingles). Where both are high, the pair is likely one story with a rewritten opening — a wire write-through or a live page at another update — which the lede on the sheet hides; such rows are worth a second look at the full text.

| row   | tier          | cited text found in LexisNexis   | LexisNexis text found in cited   | both ≥ 50%   |
|:------|:--------------|:---------------------------------|:---------------------------------|:-------------|
| h014  | `content`     | 91%                              | 6%                               |              |
| h019  | `title_fuzzy` | 20%                              | 36%                              |              |
| h033  | `title_fuzzy` | 8%                               | 8%                               |              |
| h039  | `title_fuzzy` | 36%                              | 39%                              |              |
| h098  | `title_fuzzy` | 0%                               | 0%                               |              |

### Misses

Of 28 judgeable sampled misses, **1** was the cited article after all (3.6% (0.6%–17.7%)). The sample frame — dated in-universe citations with no match but a same-outlet LexisNexis article within ±7 days — holds 161, so about **6** held articles go unmatched there. Citations outside the frame have no candidate to miss.

### Adjusted coverage

| | raw (strong tiers) | adjusted for precision and misses |
|---|---|---|
| overall | 4.5% | 4.5% |
| in universe | 18.1% | 18.7% |

A point estimate only: it carries the hand-check's sampling error, which at 20 pairs per tier is several points either way. `title_fuzzy` stays out of the count at a measured precision of 56%.

## Limitations

1. **Recall on what Wikipedia cites**, not on tornado news. Editors cite online, national and wire sources; local print is under-represented.
2. **The universe is a proxy** (outlets present in our export), which makes in-universe recall optimistic. Overall recall is the conservative figure.
3. **Undated citations** are matched within their outlet and event year only, and cannot reach the syndicated tier.
4. **Outlet identity is inferred** from names and domains. A Wikipedia citation of a Gannett paper may be held in LexisNexis under a different masthead; the content tier is what catches those.
5. **The hand-check is small** (20 pairs per tier, one labeller) and was judged from 80-word ledes; its intervals are wide, and the adjusted figure inherits them.
