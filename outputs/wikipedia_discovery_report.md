# Wikipedia discovery — US tornado and outbreak articles

Generated 2026-10-21T11:21:29+00:00. Window 2010–2025, English Wikipedia, US only. Produced by `scripts/23_discover_wikipedia.py`.

> **Scope.** Text sources are dedicated tornado articles and the per-tornado sections of outbreak articles. `List of …` pages are excluded as text — their rows paraphrase the NCEI narrative they cite — and kept for lookup only.

## What was found

899 distinct pages were returned by at least one channel; **232 are in scope**.

| kind     |   pages |   median_words |
|:---------|--------:|---------------:|
| outbreak |     119 |           1874 |
| tornado  |     113 |           2118 |

The 119 outbreak articles hold **235 per-tornado sections** with a median of 520 words, 0 of them empty apart from a `{{Main}}` pointer or a table. 86 point to a dedicated article with `{{Main}}`, so a tornado can appear both as a section and as its own article. Linking will treat those as two texts about one hazard, not as two hazards.

Besides these, 246 **day sections** ("April 13 event") group the confirmed-tornado tables by day. 9 of them carry prose — a narrative over several tornadoes, linkable to an episode but not to one hazard; the rest are tables only.

### By year

|   year |   outbreak |   tornado |   tornado sections |
|-------:|-----------:|----------:|-------------------:|
|   2010 |         10 |         7 |                 13 |
|   2011 |          8 |        21 |                 42 |
|   2012 |          7 |         9 |                 16 |
|   2013 |          8 |         7 |                 12 |
|   2014 |          5 |         3 |                 11 |
|   2015 |          6 |         3 |                  9 |
|   2016 |          5 |         2 |                  7 |
|   2017 |          7 |         4 |                  8 |
|   2018 |          4 |         1 |                  3 |
|   2019 |          8 |         6 |                 13 |
|   2020 |          8 |         7 |                 14 |
|   2021 |          7 |         7 |                 12 |
|   2022 |          8 |         4 |                 10 |
|   2023 |          9 |        14 |                 19 |
|   2024 |         13 |         9 |                 24 |
|   2025 |          6 |         9 |                 22 |

## What each channel contributes

A page found by one channel only is the kind of page a different run would miss, so the *only* column is the measure of how much each channel matters.

| channel   |   raw hits |   in-scope pages | share of in-scope   |   only this channel |
|:----------|-----------:|-----------------:|:--------------------|--------------------:|
| category  |        423 |              231 | 100%                |                   0 |
| navbox    |        298 |              224 | 97%                 |                   0 |
| yearly    |        287 |              202 | 87%                 |                   0 |
| search    |        712 |              221 | 95%                 |                   1 |
| wikidata  |        598 |              192 | 83%                 |                   0 |
| main_link |         86 |               86 | 37%                 |                   0 |

Pages by number of the five search channels that found them: 1 → 1, 2 → 3, 3 → 13, 4 → 51, 5 → 164.

### Pairwise agreement

| pair                |   both |   jaccard |
|:--------------------|-------:|----------:|
| category × navbox   |    224 |      0.97 |
| category × yearly   |    202 |      0.87 |
| category × search   |    220 |      0.95 |
| category × wikidata |    192 |      0.83 |
| navbox × yearly     |    196 |      0.85 |
| navbox × search     |    214 |      0.93 |
| navbox × wikidata   |    187 |      0.82 |
| yearly × search     |    193 |      0.84 |
| yearly × wikidata   |    168 |      0.74 |
| search × wikidata   |    192 |      0.87 |

### Found by at most one search channel — worth a look

| title                 | kind    |   year | channels   |
|:----------------------|:--------|-------:|:-----------|
| 2012 Hawaii hailstorm | tornado |   2012 | search     |

## What was excluded, and why

| reason              |   pages | examples                                                                                                                                                                                                                                              |
|:--------------------|--------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| out_of_window       |     361 | 1893 Pomeroy tornado; 1896 Sherman tornado; 1896 St. Louis–East St. Louis tornado; Tornado outbreaks of mid-to-late May, 1896                                                                                                                         |
| kind:list           |     157 | List of tornadoes in the outbreak sequence of April 2–5, 1957; List of tornadoes in the outbreak sequence of May 14–31, 1962; List of tornadoes in the 1965 Palm Sunday tornado outbreak; List of tornadoes in the May 1995 tornado outbreak sequence |
| kind:other          |      49 | 1904 Waconia Cyclone; Great Blue Norther of November 11, 1911; Hurricane Carla; Hurricane Isbell                                                                                                                                                      |
| no_year             |      37 | 1680 Lexington, Massachusetts tornado; 1764 Woldegk tornado; 1835 Middlesex County tornado; 1845 Montville tornado                                                                                                                                    |
| kind:index          |      29 | 1945 tornado outbreak; Tornadoes of 1946; Tornadoes of 1976; Tornadoes of 1988                                                                                                                                                                        |
| not_us              |      21 | 2011 Goderich tornado; 2012 Buenos Aires tornadoes; 2013 Brahmanbaria tornado; Peninsular Malaysia tornado outbreak of 2014                                                                                                                           |
| kind:disambiguation |      13 | May 2008 tornado outbreak; June 2010 tornado outbreak; May 2010 tornado outbreak; 2011 outbreak                                                                                                                                                       |

**21 tornado/outbreak pages in the window were excluded as not US**, because none of their categories names a state or the United States. Most should be Canadian or European; check the list for US pages with missing categories:

- 2011 Goderich tornado (2011)
- 2012 Buenos Aires tornadoes (2012)
- 2013 Brahmanbaria tornado (2013)
- Peninsular Malaysia tornado outbreak of 2014 (2014)
- 2015 Pakistan tornado (2015)
- 2016 Funing tornado (2016)
- 2018 South America tornado outbreak (2018)
- 2019 Bara–Parsa tornado (2019)
- 2019 Havana tornado (2019)
- 2019–20 United Kingdom floods (2019)
- 2021 South Moravia tornado (2021)
- 2022 Russia–Ukraine tornado outbreak (2022)
- May 2022 Canadian derecho (2022)
- October 2022 European tornado outbreak (2022)
- 2023 Aung Myin Kone–Tada U tornado (2023)
- 2023 Jersey tornado (2023)
- 2024 Šiauliai tornado (2024)
- June 2024 South African storm complex (2024)
- 2025 Rio Bonito do Iguaçu tornado (2025)
- 2025 Southern Brazil tornado outbreak (2025)
- Winter of 2025–26 in Great Britain and Ireland (2025)

4 in-scope pages were reached at least once through a redirect to a section — a tornado with a name but no article of its own, covered as a section of the page listed.

## Outbreak articles with no per-tornado sections (6)

No level-2 heading matched `config.WIKIPEDIA_TORNADO_SECTION_PARENTS`. Either the article describes its tornadoes in running prose only, or it uses a heading the parser does not know; the second kind is a fixable miss.

- July 2011 Midwest derecho (2011, 631 words)
- 2020 Midwest derecho (2020, 5,807 words)
- November 2020 North American storm complex (2020, 700 words)
- Tornado outbreak and derecho of December 15–16, 2021 (2021, 2,131 words)
- February 2023 North American storm complex (2023, 3,227 words)
- January 8–10, 2024 North American storm complex (2024, 1,709 words)

## Limitations

1. **Completeness is estimated, not known.** Agreement between channels bounds how much a single channel misses; it cannot see a page that *every* channel misses. The check that can — every EF4+ or fatal DAT hazard should have a section or article — needs the hazard tables and runs at the linking stage.
2. **The Wikidata channel does not follow subclasses** (it uses the search API because the query service was rate-limiting), so its share understates what Wikidata holds.
3. **US membership comes from categories.** A US page whose editors gave it no state category is excluded; the not-US list above is where to look.
4. **Pinned revisions.** Text is read from the revision current at first discovery. `--refresh` re-pins every page; the revision id is in `wikipedia_pages.csv`.
