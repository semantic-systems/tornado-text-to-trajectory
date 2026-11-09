"""One view over the three news corpora, so they can be compared as a set.

LexisNexis, Media Cloud and GDELT were collected independently and are compared
pairwise in two different scripts, by two different methods, in two different
units. That is enough to answer "do these two overlap" and not enough to answer
the question the dataset actually has to state: **how many distinct tornado
stories do we hold, and what does each source uniquely contribute?**

The unit problem, measured
--------------------------
Each corpus dedups by whatever identity it happens to have:

========== ========= ============================ ==========
corpus     rows      native "one story" is…       distinct
========== ========= ============================ ==========
LexisNexis    24,917 normalised **body**              20,138
Media Cloud  491,432 normalised **title**            266,258
GDELT         83,778 nothing — one row per **URL**    83,778
========== ========= ============================ ==========

Deduping GDELT by title collapses 57.4% of it. So a figure like "12.8% of GDELT
overlaps Media Cloud" was comparing URLs against titles — the same quantity with
different denominators. :data:`STORY_UNIT` fixes that by imposing one comparison
unit on all three: **normalised title + publication date**, the only identity all
three can produce, since LexisNexis publishes no URL and neither web corpus
publishes bodies.

The corpus-native key is kept alongside as ``native_key``. It is the better unit
*within* a corpus — LexisNexis body identity is stricter than any title rule —
and every figure states which unit produced it.

Two matching methods, never pooled
----------------------------------
Which method an edge can use depends on what both sides publish:

* **Media Cloud ↔ GDELT** — both carry URLs, so identity is *read*, not inferred.
* **anything ↔ LexisNexis** — no URL exists, so identity is inferred from
  headline, date and outlet, which is strictly weaker.

Every edge records the ``method`` that produced it. A report that pooled an
exact-URL rate with an inferred one would be quoting two different measurements
as though they were one.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from .. import config
from . import matching

STORY_UNIT = "normalised title + publication date"

# The schema every corpus is normalised to.
COLUMNS = ["corpus", "row_id", "story_id", "native_key", "title", "url",
           "outlet", "date", "primary"]

_WS = re.compile(r"\s+")
_TRAILING_OUTLET = re.compile(r"\s*[|–—-]\s*[a-z0-9. ]{0,24}$")


def normalise_title(title: pd.Series) -> pd.Series:
    """The same rule everywhere, so a story key means one thing across corpora."""
    return (title.fillna("").astype(str).str.lower()
                 .str.replace(_TRAILING_OUTLET, "", regex=True)
                 .str.replace(r"[^\w\s]", " ", regex=True)
                 .str.replace(_WS, " ", regex=True)
                 .str.strip())


# Query parameters that identify the *visit* rather than the article. Anything
# not on this list is kept, because plenty of sites put the article id in the
# query: `ktbb.com/post/?p=1379487` and `tulsaworld.com/…/articlepath.aspx?id=…`
# are distinct articles, and dropping the query merged 454 and 2,253 of them
# respectively into one identifier that then matched everything indiscriminately.
_TRACKING_PARAMS = re.compile(
    r"(?:^|&)(?:utm_[a-z_]+|fbclid|gclid|mc_[ce]id|ref|ref_src|source|"
    r"cmpid|cmp|icid|ncid|smid|partner|__twitter_impression|s|share)=[^&]*", re.I)


def normalise_url(url: pd.Series) -> pd.Series:
    """Comparable URL: no scheme, no www, no tracking parameters, no fragment.

    The identifying part of the query is **kept**. Only known tracking keys are
    removed — the alternative, dropping the query wholesale, silently fabricates
    matches on any site that addresses articles by parameter.
    """
    base = (url.fillna("").astype(str).str.lower()
               .str.replace(r"^https?://(www\.)?", "", regex=True)
               .str.replace(r"#.*$", "", regex=True))
    path = base.str.replace(r"\?.*$", "", regex=True)
    query = (base.str.extract(r"\?(.*)$", expand=False).fillna("")
                 .str.replace(_TRACKING_PARAMS, "", regex=True)
                 .str.strip("&"))
    return (path.str.rstrip("/") + query.where(query == "", "?" + query)).str.rstrip("?")


def _story_id(titles: pd.Series, dates: pd.Series) -> pd.Series:
    """Title + date. Date matters: the same headline recurs across years.

    "Severe storms move through the area" is not one story because it was used
    twice; without the date, a recurring headline would collapse a decade of
    separate events into a single row.
    """
    day = pd.to_datetime(dates, errors="coerce", utc=True).dt.strftime("%Y-%m-%d")
    return normalise_title(titles) + "|" + day.fillna("nodate")


# ── loaders ─────────────────────────────────────────────────────────────────
def _tag() -> str:
    return f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"


def load_lexisnexis() -> pd.DataFrame:
    path = config.PROCESSED_DIR / "lexisnexis_article_labels.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} — run scripts/32_filter_lexisnexis.py apply")
    df = pd.read_csv(path, keep_default_na=False, low_memory=False)
    return pd.DataFrame({
        "corpus": "lexisnexis",
        "row_id": df.textref_uid,
        "story_id": _story_id(df.headline, df.pub_date),
        "native_key": df.body_key,
        "title": df.headline.fillna(""),
        "url": "",                       # LexisNexis publishes none
        "outlet": df.source.fillna(""),
        "date": pd.to_datetime(df.pub_date, errors="coerce", utc=True).dt.tz_localize(None),
        "primary": df.primary,
    })


def load_mediacloud() -> pd.DataFrame:
    path = config.PROCESSED_DIR / "mediacloud_filtered.csv.gz"
    if not path.exists():
        raise FileNotFoundError(f"{path} — run scripts/30_filter_media_cloud.py apply")
    df = pd.read_csv(path, keep_default_na=False, low_memory=False)
    return pd.DataFrame({
        "corpus": "mediacloud",
        "row_id": df.id if "id" in df.columns else df.url,
        "story_id": _story_id(df.title, df.publish_date),
        "native_key": df.dup_group.astype(str),
        "title": df.title.fillna(""),
        "url": df.url.fillna(""),
        "outlet": df.media_name.fillna(""),
        "date": pd.to_datetime(df.publish_date, errors="coerce", utc=True).dt.tz_localize(None),
        "primary": df.primary,
    })


def load_gdelt() -> pd.DataFrame:
    """GDELT, with its labels if stage 30 has been run over it.

    ``primary`` is empty when the corpus has not been labelled, and the atlas
    then omits GDELT from every label-conditioned figure rather than treating
    "unlabelled" as a label.
    """
    path = config.PROCESSED_DIR / f"textrefs_news_{_tag()}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} — run scripts/21_fetch_gdelt.py --cache-only")
    df = pd.read_csv(path, keep_default_na=False, low_memory=False)

    labelled = config.PROCESSED_DIR / "gdelt_filtered.csv.gz"
    if labelled.exists():
        lab = pd.read_csv(labelled, keep_default_na=False, low_memory=False)
        primary = df.url.map(dict(zip(lab.url, lab.primary))).fillna("")
    else:
        primary = pd.Series("", index=df.index)

    return pd.DataFrame({
        "corpus": "gdelt",
        "row_id": df.textref_uid if "textref_uid" in df.columns else df.url,
        "story_id": _story_id(df.title, df.published_at),
        "native_key": normalise_url(df.url),
        "title": df.title.fillna(""),
        "url": df.url.fillna(""),
        "outlet": df.url.map(matching.domain_of),
        "date": pd.to_datetime(df.published_at, errors="coerce",
                               utc=True).dt.tz_localize(None),
        "primary": primary,
    })


LOADERS = {"lexisnexis": load_lexisnexis, "mediacloud": load_mediacloud,
           "gdelt": load_gdelt}


def load(name: str) -> pd.DataFrame:
    return LOADERS[name]()


def is_labelled(frame: pd.DataFrame) -> bool:
    return bool((frame.primary.fillna("") != "").any())


# ── matching ────────────────────────────────────────────────────────────────
def match_edges(left: pd.DataFrame, right: pd.DataFrame, *,
                date_tolerance: int = config.OVERLAP_DATE_TOLERANCE_DAYS,
                domain_map: dict[str, Any] | None = None) -> pd.DataFrame:
    """Story-level edges between two corpora, with the method recorded.

    Exact URL where both sides publish one; headline + date + outlet otherwise.
    Returns one row per matched *story* pair, not per article pair, so a wire
    story running on 200 outlets contributes one edge rather than 200.
    """
    both_have_urls = (left.url != "").any() and (right.url != "").any()
    if both_have_urls:
        lu, ru = normalise_url(left.url), normalise_url(right.url)
        shared = set(lu) & set(ru)
        if not shared:
            return pd.DataFrame(columns=["left_story", "right_story", "method", "score"])
        li = left.assign(_u=lu)[lambda d: d._u.isin(shared)][["story_id", "_u"]]
        ri = right.assign(_u=ru)[lambda d: d._u.isin(shared)][["story_id", "_u"]]
        edges = li.merge(ri, on="_u", suffixes=("_l", "_r"))
        return (edges.rename(columns={"story_id_l": "left_story",
                                      "story_id_r": "right_story"})
                     .assign(method="exact_url", score=1.0)
                     [["left_story", "right_story", "method", "score"]]
                     .drop_duplicates())

    # No shared identifier: fall back to the LexisNexis <-> web method.
    mapping = domain_map or {}
    by_day: dict[dt.date, list[dict[str, Any]]] = defaultdict(list)
    for row in right.itertuples():
        if pd.notna(row.date):
            by_day[row.date.date()].append(
                {"story": row.story_id, "title": row.title, "domain": row.outlet})

    rows = []
    for row in left.itertuples():
        if pd.isna(row.date):
            continue
        day = row.date.date()
        seen: set[str] = set()
        for offset in range(-date_tolerance, date_tolerance + 1):
            for cand in by_day.get(day + dt.timedelta(days=offset), []):
                if cand["story"] in seen:
                    continue
                seen.add(cand["story"])
                s = matching.title_similarity(row.title, cand["title"])
                if s["min_tokens"] < 3:
                    continue
                outlet = matching.same_outlet(row.outlet, cand["domain"], mapping)
                strong = (s["jaccard"] >= config.OVERLAP_TITLE_SIMILARITY
                          or s["containment"] >= config.OVERLAP_TITLE_SIMILARITY_STRICT)
                if not strong:
                    continue
                if not outlet and s["jaccard"] < config.OVERLAP_TITLE_SIMILARITY_STRICT:
                    continue
                rows.append({"left_story": row.story_id, "right_story": cand["story"],
                             "method": "title_date_outlet", "score": s["jaccard"]})
    return pd.DataFrame(rows, columns=["left_story", "right_story", "method",
                                       "score"]).drop_duplicates()


# ── set algebra over the edges ──────────────────────────────────────────────
def components(edges: Iterable[tuple[str, str]]) -> dict[str, int]:
    """Union-find over matched pairs; returns node -> component id.

    Matching is many-to-many and, across three corpora, transitive: if a
    LexisNexis story matches a Media Cloud one that matches a GDELT one, all
    three are the same story. Subtracting pairwise intersections from a total
    would count that story wrong; connected components get it right.
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    roots = {node: find(node) for node in parent}
    ids = {root: i for i, root in enumerate(sorted(set(roots.values())))}
    return {node: ids[root] for node, root in roots.items()}


def membership(frames: dict[str, pd.DataFrame],
               edges: pd.DataFrame) -> pd.DataFrame:
    """One row per distinct story, with a boolean column per corpus.

    A story that no edge touches is its own component of size one, which is what
    makes "unique to this corpus" computable in the same pass as the overlaps.
    """
    tagged = {name: {f"{name}::{s}" for s in set(frame.story_id)}
              for name, frame in frames.items()}
    pairs = [(f"{e.left_corpus}::{e.left_story}", f"{e.right_corpus}::{e.right_story}")
             for e in edges.itertuples()] if len(edges) else []
    comp = components(pairs)

    records: dict[int | str, dict[str, Any]] = {}
    for name, nodes in tagged.items():
        for node in nodes:
            key = comp.get(node, node)          # unmatched node = its own story
            rec = records.setdefault(key, {n: False for n in frames})
            rec[name] = True
    return pd.DataFrame.from_records(list(records.values()))


# ── capture–recapture ───────────────────────────────────────────────────────
def lincoln_petersen(n1: int, n2: int, m: int) -> tuple[float, float]:
    """Chapman-corrected two-sample population estimate and its SE.

    **Do not quote these numbers as a population estimate.** Two assumptions fail
    here, and the second is fatal rather than merely awkward:

    1. *Independence.* Wire copy is systematically more capturable than local
       reporting in all three corpora. Positive dependence inflates the overlap
       and so biases the estimate downward.
    2. *One population.* The estimator assumes both samples are drawn from the
       same frame. They are not: Media Cloud samples US national/state/local web
       collections, GDELT samples a different and partly international web index
       from 2017 only, and LexisNexis includes wire services, broadcast
       transcripts and print editions that neither web corpus can contain. With
       partly disjoint frames the overlap is small for *structural* reasons, and
       a small overlap sends the estimate toward infinity. What the number then
       measures is how differently the corpora were built, not how much tornado
       coverage exists.

    It is computed because the shape of the disagreement is informative — a pair
    with near-zero overlap has near-disjoint frames — not because the population
    size is identifiable from these data. Making it identifiable needs a
    log-linear model with interaction terms *and* corpora sharing a frame.
    """
    if m <= 0:
        return float("nan"), float("nan")
    n_hat = (n1 + 1) * (n2 + 1) / (m + 1) - 1
    var = ((n1 + 1) * (n2 + 1) * (n1 - m) * (n2 - m)) / ((m + 1) ** 2 * (m + 2))
    return n_hat, float(np.sqrt(var))
