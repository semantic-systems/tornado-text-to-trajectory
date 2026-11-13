# Methods (draft): Wikipedia as text source, coverage yardstick and silver labels

*First draft of a methods subsection. Numbers are from the run of 2026-11-13;
the full account, with files and tools, is in [`WIKIPEDIA.md`](WIKIPEDIA.md).
Script names refer to the repository.*

## Wikipedia pages

We collected English Wikipedia articles on US tornadoes from 2010–2025 through
seven independent channels: year categories, year navigation boxes, links from
the *Tornadoes of <year>* pages, full-text search, Wikidata items of the
classes tornado and tornado outbreak, links from list pages, and `{{Main}}`
links inside outbreak articles (`26_discover_wikipedia.py`). Pages were
classified by title and infobox into dedicated tornado articles (n = 111),
outbreak articles (120) and yearly overview pages (16). List pages were
excluded as text, since their rows paraphrase the NCEI records they cite, and
so were articles on other events that carry a tornado infobox (e.g., winter
storms). Each page was pinned to its revision at retrieval (21–26 October
2026) and the wikitext was stored. Of the 247 pages, 246 were found by at
least two channels.

## Passages and facts

We segmented each pinned revision into passages (`28_wikipedia_passages.py`):
a dedicated article is one passage about one tornado; an outbreak article
yields one passage per tornado section and an overview of the remaining text;
a yearly page yields its US event sections. This gave 853 passages (347 about
a single tornado, 506 about an outbreak or episode; 637,141 words).

Tables and infoboxes were excluded from the passage text and stored as
separate **fact records** (20,419 table rows and 467 infoboxes). These hold the
date, UTC time, rating, location, counties, path length and width, NCEI Storm
Events identifiers, and the page's Wikidata item. As they reproduce the
official survey, facts are used only as reference data, never as linker input.

Every citation was assigned to the section and the context (prose, table or
infobox) it occurs in. A passage's NCEI identifiers are those cited in its own
prose. A tornado section was matched to its row in the article's tables by a
shared NCEI identifier, or else by the place names in its heading, within the
outbreak's dates and the heading's states. 290 of the 347 single-tornado
passages were matched this way.

## Cited news and corpus coverage

All references were extracted from the pinned revisions and classified by
domain and citation template (`27_wikipedia_reference_coverage.py`). The
5,278 news references correspond to 4,720 distinct articles after URL
normalisation. Article text was retrieved from the publisher or, failing that,
from the Internet Archive capture nearest the citation date, honouring
robots.txt (4,093 of 4,709 URLs).

Because editors selected these articles independently of our corpora, the
share we hold estimates recall. We matched each cited article against two
corpora:

**LexisNexis** (22,896 articles; no URLs), in tiers:
- same outlet, publication dates within ±3 days, headline token Jaccard ≥ 0.72
  or containment ≥ 0.90;
- another outlet with a near-identical headline (Jaccard ≥ 0.90, ≥ 5 tokens):
  syndicated copy;
- text containment: ≥ 50% of the cited text's sampled 8-word shingles occur in
  one LexisNexis body within ±14 days.

A blind check of 20 pairs per tier gave precision of 100%, 100% and 95%,
respectively.

**Media Cloud** (491,432 stories from the US national and state & local
collections matching `tornado* AND (wind? OR storm? OR rain? OR damage? OR
emergency)`): first by normalised URL (scheme, `www`, tracking parameters and
fragment removed), then by the two headline tiers above, with outlets
identified by domain.

The strong tiers hold 4.6% (95% Wilson CI 4.1–5.3%) of the cited articles in
LexisNexis, 20.7% (19.6–21.9%) in Media Cloud, and 22.6% (21.4–23.8%) in
either (Fig. 1). Coverage is highest for national (55% in either corpus) and
wire outlets (62%) and lowest for local outlets (16–20%); weather media were
in neither corpus.

## Silver labels

We derived silver links from texts to tornado paths through the NCEI
identifiers Wikipedia cites (`44_wikipedia_silver_links.py`).

**The chain.** A single-tornado passage's evidence is the identifiers in its
prose, in its own infobox and in its matched table row. Each identifier names
a county segment in NCEI Storm Events. We chained segments into whole
tornadoes by following each record's pointer to the county the tornado
continued into (`TOR_OTHER_*`), and joined each tornado to its best
geometry, in this order:
1. its NOAA Damage Assessment Toolkit (DAT) damage polygon;
2. else its DAT track;
3. else the straight start–end track of the SPC tornado database, for
   tornadoes without a DAT survey.

**The checks.** Each link was compared with the Storm Events record:
- date within ±1 day; within 14 days for sections dated only by their
  outbreak's start;
- state;
- place: a heading town among the tornado's counties, its begin or end town,
  or in its narrative;
- EF rating.

**Strength.** *Strong*: one tornado cited, and date, state and place agree.
*Medium*: one tornado, no disagreement, and place or rating agree. *Weak*:
nothing disagrees but little could be checked, or the tornado was chosen among
several cited. *Rejected*: the date or state disagrees.

**News.** A cited news article inherits a tornado only when every
single-tornado passage citing it agrees. It takes the weakest of their
strengths, lowered one step if published before the event or more than 60
days after. It is rejected if its retrieved text names none of the tornado's
places: heading towns, counties, Storm Data begin or end towns, or gazetteer
places within 25 km of the path written as proper names. Such articles are
cited for comparison or outbreak context, not as reports of that tornado.

**Result.** 295 passages and 2,068 news articles link to one of 234 tornadoes
(Fig. 2). By strength:

| | strong | medium | weak |
|---|---:|---:|---:|
| passages | 248 | 12 | 35 |
| news articles | 1,245 | 411 | 412 |

83 news links and 1 passage were rejected. 136 tornadoes have a DAT polygon,
45 only a DAT track, and 53 only an SPC track. Mapped to Media Cloud, the
silver set comprises 499 distinct headlines on 101 tornadoes; 404 of them pass
our relevance filter (label `EVENT`) and form the evaluation set for the
news-to-path linker.

The precision of each strength is to be measured on a blind, stratified
sample of 97 links (to be labelled). Wikipedia text is written after the
survey and often draws on it, so we use the passages as a check and evaluate
the linker on the news.

## Figures

- **Fig. 1:** share of cited news articles held by LexisNexis, Media Cloud
  and either, by year (`docs/figures/wikipedia_coverage_by_year.png`) and by
  kind of outlet (`docs/figures/wikipedia_coverage_by_outlet.png`).
- **Fig. 2:** silver links by text kind and strength, and the linked
  tornadoes by best geometry (`docs/figures/wikipedia_silver_set.png`).

## Reproduction

```bash
python scripts/26_discover_wikipedia.py
python scripts/27_wikipedia_reference_coverage.py extract
python scripts/27_wikipedia_reference_coverage.py fetch
python scripts/27_wikipedia_reference_coverage.py match
python scripts/28_wikipedia_passages.py
python scripts/29_wikipedia_cited_news.py
python scripts/44_wikipedia_silver_links.py
python scripts/figures_wikipedia.py
```

Parameters are in `src/tornado_dataset/config.py` (`OVERLAP_*`, `WIKI_REF_*`)
and `src/tornado_dataset/text/silver.py` (`NEWS_MAX_DAYS`).
