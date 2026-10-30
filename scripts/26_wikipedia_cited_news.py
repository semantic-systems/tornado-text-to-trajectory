#!/usr/bin/env python
"""Stage 26 — news articles cited by Wikipedia, as text records.

The tornado pages cite 4,832 distinct news articles (stage 24). The ones
LexisNexis already holds get no second copy: they go to a cross-reference
table instead. Every other cited article becomes one text record, whether or
not its text could be fetched — a TextRef is a reference first.

Each record carries:

* **what and where**: outlet, headline as cited, publication date, URL, the
  Wikipedia archive link, and how the text was retrieved (publisher or
  archive.org) — see ``fulltext``;
* **whether the text is the article** (``text_quality`` and its reasons —
  see ``citednews``): nothing is dropped, an experiment picks its threshold;
* **one story across outlets** (``story_id``): syndicated copies grouped;
* **who cites it**: the Wikipedia passages (stage 25) whose references
  include it, written out as a separate long table. Each gives an event date
  and, often, NCEI event ids — a candidate link for the hazard linker and the
  event date the timing axis needs.

The full text stays in ``data/`` (gitignored), like the LexisNexis bodies:
news is copyrighted, so the CSV carries a short snippet only (DATA_MODEL.md).

These records are a **curated sample, not a census**: editors cite national,
wire and online outlets, mostly for notable tornadoes. Every record is tagged
``collection = wikipedia_citations`` so it can be kept apart.

Usage::

    python scripts/26_wikipedia_cited_news.py

Reads ``data/interim/wikipedia_news_articles.csv`` and
``wikipedia_ref_matches.csv`` (stage 24), ``data/raw/wikipedia/ref_fulltext.jsonl``
(the fetched texts) and ``data/processed/wikipedia_passages.jsonl`` (stage 25);
writes ``data/processed/wikipedia_cited_news.jsonl`` (with text),
``wikipedia_cited_news_textrefs.csv`` (without), ``wikipedia_cited_news_citations.csv``
(article × citing passage), ``wikipedia_cited_lexisnexis.csv`` and
``outputs/wikipedia_cited_news_report.md``. Needs no network.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

import _bootstrap  # noqa: F401

from tornado_dataset import config
from tornado_dataset.ids import uid, write_manifest
from tornado_dataset.text import citednews as cn
from tornado_dataset.text import fulltext
from tornado_dataset.text import refcoverage as rc
from tornado_dataset.text import tiering

ARTICLES_CSV = config.INTERIM_DIR / "wikipedia_news_articles.csv"
MATCHES_CSV = config.INTERIM_DIR / "wikipedia_ref_matches.csv"
STORE = config.RAW_DIR / "wikipedia" / "ref_fulltext.jsonl"
PASSAGES_JSONL = config.PROCESSED_DIR / "wikipedia_passages.jsonl"
NEWS_JSONL = config.PROCESSED_DIR / "wikipedia_cited_news.jsonl"
TEXTREFS_CSV = config.PROCESSED_DIR / "wikipedia_cited_news_textrefs.csv"
CITATIONS_CSV = config.PROCESSED_DIR / "wikipedia_cited_news_citations.csv"
LEXIS_XREF_CSV = config.PROCESSED_DIR / "wikipedia_cited_lexisnexis.csv"
REPORT = config.OUTPUT_DIR / "wikipedia_cited_news_report.md"

COLLECTION = "wikipedia_citations"
# The event date comes from the citing passage, so the timing axis here is a
# hint until the linker attaches the article to a DAT hazard.
TIER_RULE = f"{tiering.TIER_RULE_VERSION}+event_date_from_citing_passage"
SNIPPET_WORDS = 30
HAZARD_KINDS = ("tornado_article", "tornado_section")


def _bool(series: pd.Series) -> pd.Series:
    return series.astype(str).eq("True")


def _date(value: str, precision: str) -> str:
    return value if precision == "day" and len(str(value)) == 10 else ""


# ── inputs ───────────────────────────────────────────────────────────────────
def load() -> tuple[pd.DataFrame, pd.DataFrame, dict, list[dict]]:
    for path in (ARTICLES_CSV, MATCHES_CSV, STORE, PASSAGES_JSONL):
        config.require_data(path)
    articles = pd.read_csv(ARTICLES_CSV, keep_default_na=False)
    matches = pd.read_csv(MATCHES_CSV, keep_default_na=False)
    store = fulltext.load_store(STORE)
    passages = [json.loads(line) for line in PASSAGES_JSONL.open(encoding="utf-8")]
    if passages and "cited_article_keys" not in passages[0]:
        raise SystemExit(f"{PASSAGES_JSONL.name} predates cited_article_keys — "
                         "rerun scripts/25_wikipedia_passages.py")
    return articles, matches, store, passages


# ── citing passages ──────────────────────────────────────────────────────────
def citations(passages: list[dict], keys: set[str]) -> pd.DataFrame:
    """One row per (cited article, citing passage)."""
    rows = []
    for p in passages:
        for key in p["cited_article_keys"]:
            if key in keys:
                rows.append({"article_key": key, "passage_uid": p["textref_uid"],
                             "unit_kind": p["unit_kind"], "link_level": p["link_level"],
                             "page_title": p["page_title"], "section_path": p["section_path"],
                             "event_date": p["event_date"],
                             "ncei_event_ids": p["ncei_event_ids"]})
    return pd.DataFrame(rows, columns=["article_key", "passage_uid", "unit_kind", "link_level",
                                       "page_title", "section_path", "event_date",
                                       "ncei_event_ids"])


def event_hint(cites: pd.DataFrame) -> dict:
    """The event date an article reports on, from the passages citing it.

    A tornado-level passage is preferred over an outbreak or year round-up;
    across several, the earliest date (a follow-up story is later than the
    event, never earlier).
    """
    if cites.empty:
        return {"event_date_hint": "", "event_date_hint_level": "none",
                "n_event_dates": 0, "ncei_event_ids": "", "n_ncei_ids": 0}
    hazard = cites[cites.unit_kind.isin(HAZARD_KINDS) & (cites.event_date != "")]
    use = hazard if len(hazard) else cites[cites.event_date != ""]
    ids = sorted(set("|".join(cites.ncei_event_ids).split("|")) - {""}, key=int)
    return {"event_date_hint": use.event_date.min() if len(use) else "",
            "event_date_hint_level": ("hazard" if len(hazard) else "episode") if len(use)
            else "none",
            "n_event_dates": use.event_date.nunique(),
            "ncei_event_ids": "|".join(ids), "n_ncei_ids": len(ids)}


# ── build ────────────────────────────────────────────────────────────────────
def lexis_xref(articles: pd.DataFrame, matches: pd.DataFrame,
               cites: pd.DataFrame) -> pd.DataFrame:
    """Cited articles LexisNexis already holds: which LexisNexis record, how found."""
    held = articles[_bool(articles.matched_strong)]
    strong = matches[matches.tier.isin(rc.STRONG_TIERS)
                     & matches.article_key.isin(held.article_key)]
    order = {t: i for i, t in enumerate(rc.STRONG_TIERS)}
    strong = strong.assign(_o=strong.tier.map(order)).sort_values(["article_key", "_o"])
    best = strong.groupby("article_key").agg(
        lexis_textref_uid=("textref_uid", "first"),
        lexis_source=("lexis_source", "first"),
        lexis_date=("lexis_date", "first"),
        match_tiers=("tier", lambda s: "|".join(dict.fromkeys(s))))
    passages = cites.groupby("article_key").passage_uid.agg(lambda s: "|".join(sorted(set(s))))
    out = held[["article_key", "url", "title", "work", "pub_date", "domain", "outlet_type"]] \
        .set_index("article_key").join(best).join(passages.rename("citing_passages"))
    return out.reset_index()


def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    articles, matches, store, passages = load()
    new = articles[~_bool(articles.matched_strong)].reset_index(drop=True)
    cites = citations(passages, set(articles.article_key))
    xref = lexis_xref(articles, matches, cites)
    cites_new = cites[cites.article_key.isin(new.article_key)]
    by_article = {k: g for k, g in cites_new.groupby("article_key")}
    empty = cites_new.iloc[0:0]

    fetched = {a.article_key: store.get(a.url, {}) if a.url else {}
               for a in new.itertuples()}
    texts = {k: r.get("text", "") for k, r in fetched.items() if r.get("status") == "ok"}

    # Walls and site fronts: the same text back for differently titled citations.
    title = dict(zip(new.article_key, new.title))
    norm = {k: " ".join(sorted(cn._words(t))) for k, t in title.items()}
    by_hash: dict[str, set[str]] = {}
    for k, t in texts.items():
        by_hash.setdefault(hashlib.sha1(t.encode("utf-8")).hexdigest(), set()).add(k)
    shared_with = {}
    for keys in by_hash.values():
        for k in keys:
            shared_with[k] = len({norm[o] for o in keys if o != k} - {norm[k]})
    pairs = cn.overlaps(texts)
    domain = dict(zip(new.article_key, new.domain))
    site_front = set()
    for (a, b), (ab, ba) in pairs.items():
        if (domain[a] and domain[a] == domain[b] and min(ab, ba) >= cn.SAME_SITE_OVERLAP
                and (cn.title_share(title[a], title[b]) or 0) < 0.5):
            site_front.update((a, b))

    rows = []
    for a in new.itertuples():
        r = fetched[a.article_key]
        text = texts.get(a.article_key, "")
        q = cn.assess(a.title, r.get("title", ""), text, a.domain,
                      shared_with=shared_with.get(a.article_key, 0),
                      same_site_front=a.article_key in site_front)
        hint = event_hint(by_article.get(a.article_key, empty))
        published = _date(a.pub_date, a.date_precision)
        source_type = "wire" if a.outlet_type == "wire" else "news"
        author = a.work or a.publisher or a.agency or a.domain
        axes = tiering.derive(author, source_type, published, hint["event_date_hint"] or None)
        axes["tier_rule_version"] = TIER_RULE
        days = ((dt.date.fromisoformat(published)
                 - dt.date.fromisoformat(hint["event_date_hint"])).days
                if published and hint["event_date_hint"] else None)
        rows.append({
            "textref_uid": uid("textref", "wikipedia_cited", a.article_key),
            "article_key": a.article_key,
            "collection": COLLECTION,
            "source_name": author, "source_type": source_type, "author_org": author,
            "outlet_type": a.outlet_type, "domain": a.domain,
            "in_lexis_universe": a.in_universe, "language": "en",
            "title": a.title, "extracted_title": r.get("title", ""),
            "authors": a.authors, "published_at": published,
            "pub_date_cited": a.pub_date, "date_precision": a.date_precision,
            "url": a.url, "wikipedia_archive_url": a.archive_url,
            "retrieval_status": r.get("status", "no_url" if not a.url else "not_attempted"),
            "retrieval_via": r.get("via", "") if text else "",
            "retrieval_error": r.get("error", "") if not text else "",
            # The snapshot stage 24 requested: archive.org redirects it to the
            # capture nearest that date. The capture time was not recorded.
            "wayback_snapshot_url": fulltext.wayback_url(
                a.url, rc.fetch_date(a.pub_date, a.page_years) or None)
            if r.get("via") == "wayback" and text else "",
            "retrieved_at": r.get("retrieved_at", ""),
            "words": len(text.split()),
            **q,
            "n_citing_pages": a.n_pages, "citing_pages": a.pages,
            "n_citing_passages": len(by_article.get(a.article_key, empty)),
            **hint,
            "days_after_event": days,
            **axes,
            "snippet": " ".join(text.split()[:SNIPPET_WORDS]),
            "content_hash": hashlib.sha1(text.encode("utf-8")).hexdigest()[:16] if text else "",
            "text": text,
        })
    frame = pd.DataFrame(rows)

    usable = set(frame.article_key[frame.text_quality.isin(["good", "doubtful"])])
    exclude = set(frame.article_key) - usable
    dates = {k: d for k, d in zip(frame.article_key, frame.published_at) if d}
    groups = cn.story_groups(list(frame.article_key), title, dates,
                             {p: v for p, v in pairs.items() if p[0] in usable and p[1] in usable},
                             exclude=exclude)
    frame["story_id"] = [uid("story", "wikipedia_cited", groups[k][0]) for k in frame.article_key]
    frame["story_join"] = [groups[k][1] for k in frame.article_key]
    frame["story_size"] = frame.groupby("story_id").article_key.transform("size")
    # One primary per story: the best text, then the longest.
    rank = frame.text_quality.map({"good": 0, "doubtful": 1, "unusable": 2, "none": 3})
    order = frame.assign(_r=rank, _w=-frame.words).sort_values(["story_id", "_r", "_w",
                                                                "article_key"])
    frame["story_primary"] = frame.index.isin(order.groupby("story_id").head(1).index)

    cites_new = cites_new.assign(
        textref_uid=cites_new.article_key.map(dict(zip(frame.article_key, frame.textref_uid))))
    return frame, cites_new, xref


# ── report ───────────────────────────────────────────────────────────────────
def _pct(n: float) -> str:
    return f"{n:.0%}"


def _count_table(series: pd.Series, name: str) -> str:
    counts = series.value_counts()
    return pd.DataFrame({name: counts.index, "articles": counts.values,
                         "share": [_pct(v / counts.sum()) for v in counts.values]}
                        ).to_markdown(index=False)


def write_report(frame: pd.DataFrame, cites: pd.DataFrame, xref: pd.DataFrame) -> None:
    text = frame[frame.words > 0]
    usable = frame[frame.text_quality.isin(["good", "doubtful"])]
    reasons = Counter(r for rs in frame.quality_reasons for r in rs.split("|") if r)
    stories = usable.story_id.nunique()
    multi = usable.groupby("story_id").size()
    quality = pd.crosstab(frame.outlet_type, frame.text_quality).reindex(
        columns=["good", "doubtful", "unusable", "none"], fill_value=0)
    quality["total"] = quality.sum(axis=1)
    hint = frame.event_date_hint_level.value_counts()
    timed = frame[frame.days_after_event.notna()]
    lag = pd.cut(timed.days_after_event, [-10_000, -1, 0, 1, 7, 30, 365, 100_000],
                 labels=["before the event", "same day", "next day", "2–7 days",
                         "8–30 days", "31–365 days", "over a year"])
    lines = [
        "# News articles cited by Wikipedia",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by "
        "`scripts/26_wikipedia_cited_news.py`.",
        "",
        f"The tornado pages cite **{len(frame) + len(xref):,} distinct news articles**. "
        f"**{len(xref):,}** are already in LexisNexis (strong match, stage 24) and get no "
        f"second copy: they are listed in `{LEXIS_XREF_CSV.relative_to(config.REPO_ROOT)}` "
        f"with the LexisNexis `textref_uid`. The other **{len(frame):,}** are new text "
        f"records (`collection = {COLLECTION}`), "
        f"**{len(text):,} with text** ({text.words.sum():,} words, median "
        f"{int(text.words.median())}), and **{len(frame[frame.text_quality == 'good']):,} "
        "with text that checks out as the cited article**.",
        "",
        "Text bodies stay in `data/processed/wikipedia_cited_news.jsonl` (gitignored): news "
        "is copyrighted. The CSV carries metadata and a "
        f"{SNIPPET_WORDS}-word snippet.",
        "",
        "## Is the text the article?",
        "",
        _count_table(frame.text_quality, "text_quality"),
        "",
        "- **good**: most of the cited headline's words appear near the top of the "
        f"text (≥ {cn.TITLE_IN_TEXT_MIN:.0%}), or in the page's own title "
        f"(≥ {cn.TITLE_MATCH_MIN:.0%}), and none of the problems below.",
        "- **doubtful**: the headline is not found (often the same story under a later "
        "headline: archive copies of live pages), the page is mostly navigation with the "
        "headline missing, or a differently titled citation on the same site returned "
        "nearly the same text.",
        "- **unusable**: a video page, a consent wall or a site front (\"Before you "
        "continue to YouTube\", a TV station's homepage), exactly the same text came "
        "back for differently titled citations, or the headline is missing and the text "
        "never mentions a storm (another article altogether).",
        "- **none**: no text was retrieved (reasons below).",
        "",
        pd.DataFrame({"reason": list(reasons), "articles": list(reasons.values())})
        .sort_values("articles", ascending=False).to_markdown(index=False),
        "",
        f"{(~frame.mentions_storm & (frame.words > 0)).sum():,} texts never mention a "
        "tornado or storm. Wikipedia cites some articles for context (power outages, "
        "relief efforts, a building's history), so this is not a quality flag; a "
        "relevance label (as for Media Cloud and LexisNexis, stages 18/19) is the "
        "next step.",
        "",
        "### By outlet type",
        "",
        quality.reset_index().to_markdown(index=False),
        "",
        "### Why there is no text",
        "",
        _count_table(frame.loc[frame.words == 0, "retrieval_status"], "retrieval_status"),
        "",
        "## Retrieval route",
        "",
        _count_table(text.retrieval_via, "via"),
        "",
        "An archive.org copy is the capture nearest the publication date (mid-year of the "
        "event year for undated citations), but the capture time itself was not recorded. A live page captured later shows up as a headline "
        "mismatch (doubtful), which is the main risk.",
        "",
        "## Stories across outlets",
        "",
        f"The {len(usable):,} usable texts form **{stories:,} stories**; "
        f"{(multi > 1).sum():,} stories have more than one copy (largest: {multi.max()}). "
        "Copies are joined by the same headline (five words or more) on the same day, or "
        f"when at least {cn.STORY_OVERLAP:.0%} of the shorter text's 8-word shingles are in "
        f"the longer one within {cn.STORY_DAYS} days. `story_primary` marks one copy per "
        "story (best quality, then longest).",
        "",
        _count_table(usable.story_join.replace("", "single copy"), "joined by"),
        "",
        "## Citation context",
        "",
        f"{len(cites):,} (article, citing passage) pairs in "
        f"`{CITATIONS_CSV.relative_to(config.REPO_ROOT)}`. " +
        (f"{(frame.n_citing_passages > 0).sum():,} articles are cited from at least one "
         "stage 25 passage; the rest are cited only from tables or sections that are not "
         "passages (confirmed-tornado tables, references to other events)."
         if (frame.n_citing_passages == 0).any() else
         "Every article is cited from at least one stage 25 passage."),
        "",
        pd.DataFrame({"event date taken from": hint.index, "articles": hint.values})
        .to_markdown(index=False),
        "",
        f"{(frame.n_ncei_ids > 0).sum():,} articles are cited by a passage that also cites "
        "NCEI event ids: a candidate hazard for the linker, to be confirmed by date and "
        "place since a passage can cite several.",
        "",
        "### Publication relative to the event",
        "",
        f"For the {len(timed):,} articles with a day-precise date and an event date:",
        "",
        pd.DataFrame({"published": lag.value_counts(sort=False).index.astype(str),
                      "articles": lag.value_counts(sort=False).values}).to_markdown(index=False),
        "",
        "\"Before the event\" is mostly forecasts and outlooks, and some passage dates "
        "that are the start of a multi-day outbreak.",
        "",
        "## Independence axes",
        "",
        f"Rule `{TIER_RULE}`: none of these outlets is the surveying organisation; the "
        "timing axis uses the event date of the citing passage and, with no survey time "
        "yet, never says post-survey (tiering's conservative default). The linker "
        "replaces both with the DAT hazard's begin time and survey date.",
        "",
        _count_table(frame.temporal_class, "temporal_class"),
        "",
        "## Caveats",
        "",
        "1. **A curated sample, not a census.** Editors cite what they find online, for "
        "the tornadoes notable enough to have an article: national, wire and TV-station "
        "sites over small papers, recent years over early ones.",
        "2. **LexisNexis overlap is excluded at stage 24's precision.** The title tiers "
        "were 100% right in the hand-check and the content tier 95%, so about 10 of the "
        f"{len(xref)} excluded articles may not be in LexisNexis after all.",
        "3. **The title check misses** an article quoted under a different headline and "
        "can pass a site front that happens to contain the headline in a list of links; "
        "see the examples in stage 24's hand-check.",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    frame, cites, xref = build()
    NEWS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with NEWS_JSONL.open("w", encoding="utf-8") as fh:
        for row in frame.to_dict("records"):
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    frame.drop(columns=["text"]).to_csv(TEXTREFS_CSV, index=False)
    cites.to_csv(CITATIONS_CSV, index=False)
    xref.to_csv(LEXIS_XREF_CSV, index=False)
    write_report(frame, cites, xref)
    write_manifest(config.PROCESSED_DIR / "manifest_wikipedia_cited_news.json",
                   "26_wikipedia_cited_news",
                   counts={"records": len(frame), "in_lexisnexis": len(xref),
                           "with_text": int((frame.words > 0).sum()),
                           **{f"quality_{k}": int(v) for k, v in
                              frame.text_quality.value_counts().items()},
                           "stories": int(frame.story_id.nunique()),
                           "citations": len(cites)},
                   outputs=[NEWS_JSONL, TEXTREFS_CSV, CITATIONS_CSV, LEXIS_XREF_CSV])
    print(frame.text_quality.value_counts().to_string())
    print(f"wrote {NEWS_JSONL.name}, {TEXTREFS_CSV.name}, {CITATIONS_CSV.name}, "
          f"{LEXIS_XREF_CSV.name}, {REPORT.name}")


if __name__ == "__main__":
    main()
