# Silver links: Wikipedia text and cited news to tornadoes

Generated 2026-11-13T13:40:00+00:00 by `scripts/44_wikipedia_silver_links.py`.

Wikipedia passages about one tornado cite its NCEI Storm Events record; Storm Events chains county segments into tornadoes and stage 14 links them to DAT hazards. The news a passage cites inherits its tornado. These are **silver** labels — drawn by editors, checked automatically against Storm Events, not by a person — for evaluating the news → tornado linker. Written to `data/processed/wikipedia_silver_links.csv`.

## Tornado-level links

| text_kind         |   strong |   medium |   weak |   rejected |   with a DAT polygon |   with any DAT hazard |
|:------------------|---------:|---------:|-------:|-----------:|---------------------:|----------------------:|
| cited_news        |      917 |      637 |    550 |          0 |                 1046 |                  1612 |
| lexisnexis        |       48 |       20 |     33 |          0 |                   66 |                    87 |
| wikipedia_passage |      203 |       49 |     33 |          1 |                  152 |                   208 |

- **286 Wikipedia passages** and **2205 news articles** (2104 cited articles outside LexisNexis, 101 in it) link to one tornado; 1796 of the news articles have text that checks out as the article (`text_quality = good`, or LexisNexis).
- 229 distinct tornadoes; 121 of them have a DAT damage polygon.

**Strength** (`text.silver.strength`): *strong* — the passage names one tornado and its date (±1 day), state and a place agree with the Storm Events record; *medium* — one tornado, nothing disagrees, a place or the rating agrees; *weak* — nothing disagrees but little could be checked, or the tornado was chosen among several the passage cites; *rejected* — the date or state disagrees (kept for inspection, not for evaluation). A news article takes its weakest citing passage's strength, one step lower if it was published before the event or more than 60 days after, or names none of the tornado's places.

### How a passage's tornado was found

| evidence                |   strong |   medium |   weak |   rejected |
|:------------------------|---------:|---------:|-------:|-----------:|
| infobox                 |        4 |        0 |      0 |          0 |
| infobox|table_row       |       17 |        3 |      1 |          0 |
| prose                   |       45 |        7 |     12 |          0 |
| prose|infobox           |        5 |        3 |      4 |          1 |
| prose|infobox|table_row |       22 |        7 |      2 |          0 |
| prose|table_row         |       71 |       19 |      6 |          0 |
| table_row               |       39 |       10 |      8 |          0 |

`prose`: an NCEI id the passage's own text cites; `infobox`: one its infobox cites; `table_row`: one its matched table row cites (stage 28).

## Episode-level links

131 outbreak overviews and yearly events link to the set of tornadoes their prose, tables and infobox cite (median 24); 1221 news articles cited only by one such passage inherit that set.

## Not linked

| reason                                                 |   texts |
|:-------------------------------------------------------|--------:|
| news: no citing passage with a tornado or one outbreak |    1291 |
| episode: no NCEI id in Storm Events                    |     375 |
| tornado: no NCEI id in prose, infobox or matched row   |      48 |
| news: citing passages name different tornadoes         |      21 |
| tornado: several tornadoes, none stands out            |      12 |
| news: only rejected passages cite it                   |      10 |
| tornado: its NCEI ids are not Storm Events tornadoes   |       3 |

## Hand check

`outputs/annotation/wikipedia_silver_handcheck.csv` holds 96 tornado-level links, stratified by kind and strength, **blind** (no strength or checks shown; the key is in `data/interim/wikipedia_silver_handcheck_key.csv`). For each row, read the text (or open the URL) and the tornado's Storm Events summary, and put one label: `same_tornado`, `other_tornado`, `outbreak_only`, `not_about_a_tornado`, `unsure`. Save the labelled copy as `outputs/annotation/wikipedia_silver_handcheck_labels.csv` (tracked in git); the precision per strength comes from it.

## Caveats

1. **A citation is not a label.** A news article cited in one tornado's section can be about the whole outbreak; the place check catches some, the hand check measures the rest.
2. **Wikipedia text is easier than news.** It is written after the survey and often from it; evaluate the linker on the news rows, and use the passages as a check.
3. **DAT is incomplete in early years** (stage 17): a tornado without a DAT hazard has no polygon here; SPC's track (stage 14's SPC part) would give it a line.
4. **Storm Events dates are local standard time**; the date check allows ±1 day.

