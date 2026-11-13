# Silver links: Wikipedia text and cited news to tornadoes

Generated 2026-11-13T19:03:55+00:00 by `scripts/44_wikipedia_silver_links.py`.

Wikipedia passages about one tornado cite its NCEI Storm Events record; Storm Events chains county segments into tornadoes and stage 14 links them to DAT hazards. The news a passage cites inherits its tornado. These are **silver** labels — drawn by editors, checked automatically against Storm Events, not by a person — for evaluating the news → tornado linker. Written to `data/processed/wikipedia_silver_links.csv`.

## Tornado-level links

| text_kind         |   strong |   medium |   weak |   rejected |   geometry: dat_polygon |   geometry: dat_line |   geometry: spc_track |   geometry: none |
|:------------------|---------:|---------:|-------:|-----------:|------------------------:|---------------------:|----------------------:|-----------------:|
| cited_news        |     1183 |      397 |    392 |         82 |                    1264 |                  417 |                   373 |                0 |
| lexisnexis        |       62 |       14 |     20 |          1 |                      69 |                   16 |                    12 |                0 |
| wikipedia_passage |      248 |       12 |     35 |          1 |                     176 |                   57 |                    63 |                0 |

- **296 Wikipedia passages** and **2151 news articles** (2054 cited articles outside LexisNexis, 97 in it) link to one tornado; 1750 of the news articles have text that checks out as the article (`text_quality = good`, or LexisNexis).
- 234 distinct tornadoes; 136 of them have a DAT damage polygon, 45 a DAT track line only, 53 only SPC's straight track (no DAT survey), 0 none.
- DAT hazards found through the SPC track and not through Storm Events directly: 163 links.

**Geometry** is the tornado's best: a DAT damage polygon, else DAT's track line, else SPC's start–end line (stage 15's SPC hazards), else none.

**Strength** (`text.silver.strength`): *strong* — the passage names one tornado and its date (±1 day), state and a place agree with the Storm Events record; *medium* — one tornado, nothing disagrees, a place or the rating agrees; *weak* — nothing disagrees but little could be checked, or the tornado was chosen among several the passage cites; *rejected* — the date or state disagrees (kept for inspection, not for evaluation). A news article takes its weakest citing passage's strength, one step lower if it was published before the event or more than 60 days after; it is *rejected* when its intact text (`text_quality = good`, or LexisNexis) names none of the tornado's places — heading towns, counties, Storm Data's begin and end towns — since Wikipedia then cites it for something else (a comparison, the whole outbreak).

### Rejected

| text_kind         | reject_reason                                 |   links |
|:------------------|:----------------------------------------------|--------:|
| cited_news        | names none of the tornado's places            |      82 |
| lexisnexis        | names none of the tornado's places            |       1 |
| wikipedia_passage | date and state disagree with the cited record |       1 |

### How a passage's tornado was found

| evidence                |   strong |   medium |   weak |   rejected |
|:------------------------|---------:|---------:|-------:|-----------:|
| infobox                 |        4 |        0 |      0 |          0 |
| infobox|table_row       |       20 |        0 |      1 |          0 |
| prose                   |       49 |        4 |     14 |          0 |
| prose|infobox           |        7 |        0 |      6 |          1 |
| prose|infobox|table_row |       27 |        3 |      1 |          0 |
| prose|table_row         |       88 |        2 |      6 |          0 |
| table_row               |       53 |        3 |      7 |          0 |

`prose`: an NCEI id the passage's own text cites; `infobox`: one its infobox cites; `table_row`: one its matched table row cites (stage 28).

## Episode-level links

131 outbreak overviews and yearly events link to the set of tornadoes their prose, tables and infobox cite (median 24); 1216 news articles cited only by one such passage inherit that set.

## Not linked

| reason                                                 |   texts |
|:-------------------------------------------------------|--------:|
| news: no citing passage with a tornado or one outbreak |    1217 |
| episode: no NCEI id in Storm Events                    |     375 |
| tornado: no NCEI id in prose, infobox or matched row   |      41 |
| news: citing passages name different tornadoes         |      32 |
| news: only rejected passages cite it                   |      10 |
| tornado: several tornadoes, none stands out            |       7 |
| tornado: its NCEI ids are not Storm Events tornadoes   |       3 |

## Hand check

`outputs/annotation/wikipedia_silver_handcheck.csv` holds 97 tornado-level links, stratified by kind and strength, **blind** (no strength or checks shown; the key is in `data/interim/wikipedia_silver_handcheck_key.csv`). For each row, read the text (or open the URL) and the tornado's Storm Events summary, and put one label: `same_tornado`, `other_tornado`, `outbreak_only`, `not_about_a_tornado`, `unsure`. Save the labelled copy as `outputs/annotation/wikipedia_silver_handcheck_labels.csv` (tracked in git); the precision per strength comes from it.

## Caveats

1. **A citation is not a label.** A news article cited in one tornado's section can be about the whole outbreak; the place check catches some, the hand check measures the rest.
2. **Wikipedia text is easier than news.** It is written after the survey and often from it; evaluate the linker on the news rows, and use the passages as a check.
3. **DAT is incomplete in early years** (stage 17): a tornado without a DAT hazard has SPC's straight start–end line at best — fine for which-tornado, not for where-exactly.
4. **Storm Events dates are local standard time**; the date check allows ±1 day.

## On Media Cloud

`data/processed/wikipedia_silver_mediacloud.csv`: the tornado-level news links as stories of our Media Cloud export — **499 distinct headlines** (Media Cloud's `dup_group`; 2,137 rows, since one wire story runs in many outlets — one cited article reaches up to 199) **linked to one of 101 tornadoes**, 404 of them labelled `EVENT` by stage 30 (the ones the linker is run on; `mc_representative` marks the row stage 30 labelled). A story is found through a cited article (stage 27: its URL, the same headline in its outlet, or wire copy in another); one story found through several cited articles takes its tornado only when they agree (0 dropped because they do not) and the weakest strength.

Distinct headlines, by how the first was found and the link's strength:

| mc_tier          |   strong |   medium |   weak |
|:-----------------|---------:|---------:|-------:|
| title_outlet     |       77 |        8 |     12 |
| title_syndicated |       65 |       17 |     21 |
| url              |      180 |       75 |     44 |

With a DAT polygon: 375; only SPC's track: 43. Labels: EVENT 404, NOT_TORNADO_EVENT 72, UNCLEAR 20, PROSPECTIVE 3.

A story labelled anything but `EVENT` that a citation ties to a tornado is a filter miss worth reading — or a citation for context (a relief fund, a power outage); the strength and the hand check tell them apart.

