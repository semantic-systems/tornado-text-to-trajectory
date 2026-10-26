# Wikipedia discovery — US tornado text sources and list census

Generated 2026-10-26T11:15:42+00:00. Window 2010–2025, English Wikipedia, US only. Produced by `scripts/23_discover_wikipedia.py`.

> **Scope.** Text sources are dedicated tornado articles, the per-tornado sections of outbreak articles, and the US event sections of the yearly `Tornadoes of <year>` pages. `List of …` pages are not text — their rows paraphrase the NCEI narrative they cite — but they are parsed into a census of every listed tornado, which is what the text sources are measured against.

## What was found

1,030 distinct pages were returned by at least one channel; **249 are in scope**.

| kind     |   pages |   median_words |
|:---------|--------:|---------------:|
| outbreak |     120 |           1886 |
| tornado  |     113 |           2119 |
| yearly   |      16 |           5123 |

The 120 outbreak articles hold **236 per-tornado sections** with a median of 519 words, 0 of them empty apart from a `{{Main}}` pointer or a table. 86 point to a dedicated article with `{{Main}}`, so a tornado can appear both as a section and as its own article. Linking will treat those as two texts about one hazard, not as two hazards.

Besides these, 246 **day sections** ("April 13 event") group the confirmed-tornado tables by day. 9 of them carry prose — a narrative over several tornadoes, linkable to an episode but not to one hazard; the rest are tables only.

The 16 yearly pages hold **386 US event sections** (90,169 words, median 190). Each is a narrative over one episode, usually several tornadoes; 244 have no `{{Main}}` article of their own, so for those episodes this is the only Wikipedia prose there is. US membership is read from the heading's region (330), or from the prose naming a state for storm-named or region-less events (56).

### By year

|   year |   outbreak |   tornado |   yearly |   tornado sections |   yearly event sections |
|-------:|-----------:|----------:|---------:|-------------------:|------------------------:|
|   2010 |         10 |         7 |        1 |                 13 |                      36 |
|   2011 |          8 |        21 |        1 |                 43 |                      24 |
|   2012 |          8 |         9 |        1 |                 16 |                      17 |
|   2013 |          8 |         7 |        1 |                 12 |                      15 |
|   2014 |          5 |         3 |        1 |                 11 |                      18 |
|   2015 |          6 |         3 |        1 |                  9 |                      18 |
|   2016 |          5 |         2 |        1 |                  7 |                      23 |
|   2017 |          7 |         4 |        1 |                  8 |                      31 |
|   2018 |          4 |         1 |        1 |                  3 |                      24 |
|   2019 |          8 |         6 |        1 |                 13 |                      23 |
|   2020 |          8 |         7 |        1 |                 14 |                      26 |
|   2021 |          7 |         7 |        1 |                 12 |                      31 |
|   2022 |          8 |         4 |        1 |                 10 |                      24 |
|   2023 |          9 |        14 |        1 |                 19 |                      24 |
|   2024 |         13 |         9 |        1 |                 24 |                      29 |
|   2025 |          6 |         9 |        1 |                 22 |                      23 |

## The census

122 list pages (monthly US lists and per-outbreak lists) and the tables inside 86 outbreak articles give **19,585 distinct US tornadoes** — 885 rows listed twice and 113 non-US rows removed. This is Wikipedia counting itself; the annual totals are of the order of the official US counts, and the check against DAT/SPC belongs to the linking stage.

|   year |   tornadoes |   ef2 |   ef3_plus | with_ncei_id   | with_start_point   |
|-------:|------------:|------:|-----------:|:---------------|:-------------------|
|   2010 |        1172 |   119 |         43 | 58%            | 100%               |
|   2011 |        1691 |   199 |         85 | 54%            | 96%                |
|   2012 |         856 |    84 |         28 | 22%            | 100%               |
|   2013 |         910 |    80 |         28 | 100%           | 100%               |
|   2014 |         896 |    67 |         24 | 100%           | 100%               |
|   2015 |        1168 |    65 |         22 | 99%            | 97%                |
|   2016 |         956 |    70 |         29 | 100%           | 100%               |
|   2017 |        1397 |   124 |         14 | 97%            | 100%               |
|   2018 |        1094 |    72 |         11 | 100%           | 100%               |
|   2019 |        1448 |   111 |         34 | 97%            | 100%               |
|   2020 |        1065 |    85 |         24 | 97%            | 100%               |
|   2021 |        1274 |   101 |         23 | 99%            | 100%               |
|   2022 |        1161 |   118 |         24 | 96%            | 100%               |
|   2023 |        1328 |   129 |         30 | 91%            | 99%                |
|   2024 |        1819 |   139 |         46 | 90%            | 100%               |
|   2025 |        1350 |   136 |         41 | 87%            | 100%               |

NCEI event ids are the bridge to DAT. Lists that cite survey statements or the SPC instead of NCEI leave them empty, which is why some years have few.

## Where the prose about significant tornadoes lives

For each of the **506 EF3+ tornadoes** in the census: the most specific Wikipedia prose that mentions it. **Heuristic** — a town from the row's location named in a dedicated article's title, an outbreak section's heading, or a yearly event section's text, in the same year — until the linking stage replaces it with NCEI ids and geometry.

| year   |   dedicated article |   outbreak section |   yearly event section |   list row only |   all |
|:-------|--------------------:|-------------------:|-----------------------:|----------------:|------:|
| 2010   |                   4 |                  8 |                     15 |              16 |    43 |
| 2011   |                  26 |                 21 |                     10 |              28 |    85 |
| 2012   |                   5 |                 11 |                      9 |               3 |    28 |
| 2013   |                   7 |                  5 |                      5 |              11 |    28 |
| 2014   |                   4 |                  5 |                      9 |               6 |    24 |
| 2015   |                   1 |                  7 |                     13 |               1 |    22 |
| 2016   |                   1 |                  5 |                     16 |               7 |    29 |
| 2017   |                   2 |                  6 |                      5 |               1 |    14 |
| 2018   |                   0 |                  2 |                      9 |               0 |    11 |
| 2019   |                   6 |                  8 |                     11 |               9 |    34 |
| 2020   |                   7 |                  6 |                      3 |               8 |    24 |
| 2021   |                   6 |                  9 |                      8 |               0 |    23 |
| 2022   |                   3 |                  9 |                     10 |               2 |    24 |
| 2023   |                  13 |                  6 |                     10 |               1 |    30 |
| 2024   |                   9 |                 16 |                     18 |               3 |    46 |
| 2025   |                   6 |                 15 |                      9 |              11 |    41 |
| all    |                 100 |                139 |                    160 |             107 |   506 |

239 have per-tornado prose; 160 are covered only inside an episode narrative on a yearly page; **107 have no Wikipedia prose beyond their list row.** That last group is a property of Wikipedia, not of discovery: every in-scope page the hub lists link to is already found (see `list_links`).

## What each channel contributes

A page found by one channel only is the kind of page a different run would miss, so the *only* column is the measure of how much each channel matters.

| channel    |   raw hits |   in-scope pages | share of in-scope   |   only this channel |
|:-----------|-----------:|-----------------:|:--------------------|--------------------:|
| category   |        423 |              247 | 99%                 |                   0 |
| navbox     |        298 |              240 | 96%                 |                   0 |
| yearly     |        287 |              204 | 82%                 |                   0 |
| search     |        712 |              233 | 94%                 |                   1 |
| wikidata   |        598 |              198 | 80%                 |                   0 |
| list_links |        945 |              233 | 94%                 |                   1 |
| main_link  |        262 |              215 | 86%                 |                   0 |

Pages by number of the 6 search channels that found them: 1 → 2, 2 → 3, 3 → 9, 4 → 16, 5 → 58, 6 → 161.

### Pairwise agreement

| pair                  |   both |   jaccard |
|:----------------------|-------:|----------:|
| category × navbox     |    240 |      0.97 |
| category × yearly     |    204 |      0.83 |
| category × search     |    232 |      0.94 |
| category × wikidata   |    198 |      0.8  |
| category × list_links |    232 |      0.94 |
| navbox × yearly       |    198 |      0.8  |
| navbox × search       |    226 |      0.91 |
| navbox × wikidata     |    193 |      0.79 |
| navbox × list_links   |    229 |      0.94 |
| yearly × search       |    195 |      0.81 |
| yearly × wikidata     |    169 |      0.73 |
| yearly × list_links   |    194 |      0.8  |
| search × wikidata     |    198 |      0.85 |
| search × list_links   |    221 |      0.9  |
| wikidata × list_links |    192 |      0.8  |

### Found by at most one search channel — worth a look

| title                            | kind     |   year | channels   |
|:---------------------------------|:---------|-------:|:-----------|
| 2012 Hawaii hailstorm            | tornado  |   2012 | search     |
| June 2012 North American derecho | outbreak |   2012 | list_links |

## What was excluded, and why

| reason              |   pages | examples                                                                                                                                                                                         |
|:--------------------|--------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| out_of_window       |     385 | 1893 Pomeroy tornado; 1896 Sherman tornado; 1896 St. Louis–East St. Louis tornado; Tornado outbreaks of mid-to-late May, 1896                                                                    |
| kind:list           |     187 | List of F4 tornadoes (1950–1959); List of tornadoes in the outbreak sequence of April 2–5, 1957; List of F4 tornadoes (1960–1969); List of tornadoes in the outbreak sequence of May 14–31, 1962 |
| kind:other          |     126 | 1904 Waconia Cyclone; Great Blue Norther of November 11, 1911; Hurricane Carla; Hurricane Isbell                                                                                                 |
| no_year             |      43 | 1680 Lexington, Massachusetts tornado; 1764 Woldegk tornado; 1835 Middlesex County tornado; 1845 Montville tornado                                                                               |
| not_us              |      19 | 2011 Goderich tornado; 2012 Buenos Aires tornadoes; 2013 Brahmanbaria tornado; 2016 Funing tornado                                                                                               |
| kind:disambiguation |      13 | May 2008 tornado outbreak; June 2010 tornado outbreak; May 2010 tornado outbreak; 2011 outbreak                                                                                                  |
| kind:index          |       8 | 1945 tornado outbreak; Tornado outbreak sequence of May 2019; Tornado outbreak sequence of May 19–27, 2024; Tornadoes in Bermuda                                                                 |

**19 tornado/outbreak pages in the window were excluded as not US**, because none of their categories names a state or the United States. Most should be Canadian or European; check the list for US pages with missing categories:

- 2011 Goderich tornado (2011)
- 2012 Buenos Aires tornadoes (2012)
- 2013 Brahmanbaria tornado (2013)
- 2016 Funing tornado (2016)
- 2018 South America tornado outbreak (2018)
- 2019 Bara–Parsa tornado (2019)
- 2019 Havana tornado (2019)
- 2019–20 United Kingdom floods (2019)
- 2021 South Moravia tornado (2021)
- 2022 Russia–Ukraine tornado outbreak (2022)
- May 2022 Canadian derecho (2022)
- October 2022 European tornado outbreak (2022)
- 2023 Jersey tornado (2023)
- 2024 Šiauliai tornado (2024)
- June 2024 South African storm complex (2024)
- 2025 Magang tornado (2025)
- 2025 Rio Bonito do Iguaçu tornado (2025)
- 2025 Southern Brazil tornado outbreak (2025)
- Winter of 2025–26 in Great Britain and Ireland (2025)

12 in-scope pages were reached at least once through a redirect to a section — a tornado with a name but no article of its own, covered as a section of the page listed.

## Outbreak articles with no per-tornado sections (7)

No level-2 heading matched `config.WIKIPEDIA_TORNADO_SECTION_PARENTS`. Either the article describes its tornadoes in running prose only, or it uses a heading the parser does not know; the second kind is a fixable miss.

- July 2011 Midwest derecho (2011, 631 words)
- June 2012 North American derecho (2012, 2,364 words)
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
