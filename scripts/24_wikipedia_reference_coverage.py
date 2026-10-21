#!/usr/bin/env python
"""Stage 24 — what share of the news Wikipedia cites about US tornadoes do we hold?

Reads the pinned revisions stage 23 stored, extracts every reference with the
section it is cited from, keeps the news ones, and matches them against the
LexisNexis export in the tiers defined in :mod:`tornado_dataset.text.refcoverage`.

Subcommands, in order::

    python scripts/24_wikipedia_reference_coverage.py extract   # refs from wikitext (seconds)
    python scripts/24_wikipedia_reference_coverage.py fetch     # cited-article text (hours, resumable)
    python scripts/24_wikipedia_reference_coverage.py status    # what the fetch store holds
    python scripts/24_wikipedia_reference_coverage.py match     # tiers, report, hand-check sheet

``match`` runs on whatever ``fetch`` has stored so far, so it can be run before
the fetch finishes; the report states how many cited articles had text, and the
content tier is a lower bound until that reaches the ceiling.

``fetch`` uses the stage 21 crawler: robots.txt honoured, the publisher first,
the Wayback Machine copy nearest the citation date as fallback, behind the
global archive.org throttle. Text is kept locally for matching and never
published (see the legal note in :mod:`tornado_dataset.text.fulltext`).

LexisNexis input is ``outputs/lexisnexis_articles.jsonl``, written by
``python -m tornado_dataset.text.lexisnexis`` from the RTF export.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone

import pandas as pd
from tqdm import tqdm

import _bootstrap  # noqa: F401

from tornado_dataset import config
from tornado_dataset.dat.evaluate import wilson_interval
from tornado_dataset.ids import write_manifest
from tornado_dataset.text import fulltext
from tornado_dataset.text import refcoverage as rc
from tornado_dataset.text import wikipedia as wp
from tornado_dataset.text.lexisnexis import textref_uid

PAGES_CSV = config.INTERIM_DIR / "wikipedia_pages.csv"
REFS_CSV = config.INTERIM_DIR / "wikipedia_refs.csv"
ARTICLES_CSV = config.INTERIM_DIR / "wikipedia_news_articles.csv"
MATCHES_CSV = config.INTERIM_DIR / "wikipedia_ref_matches.csv"
HANDCHECK_CSV = config.OUTPUT_DIR / "annotation" / "wikipedia_ref_handcheck.csv"
HANDCHECK_KEY = config.INTERIM_DIR / "wikipedia_ref_handcheck_key.csv"   # tier per row
STORE = config.RAW_DIR / "wikipedia" / "ref_fulltext.jsonl"
LEXIS_JSONL = config.OUTPUT_DIR / "lexisnexis_articles.jsonl"
REPORT = config.OUTPUT_DIR / "wikipedia_reference_coverage_report.md"


# ── extract ──────────────────────────────────────────────────────────────────
def extract(args) -> None:
    config.require_data(PAGES_CSV)
    pages = pd.read_csv(PAGES_CSV)
    pages = pages[pages.scope == "in_scope"]
    rows = []
    for page in tqdm(pages.itertuples(), total=len(pages), desc="pages", unit="page"):
        text = json.loads(wp.store_path(page.pageid, page.revid).read_text("utf-8"))["wikitext"]
        for ref in wp.extract_references(text):
            rows.append({"pageid": page.pageid, "revid": page.revid,
                         "page_title": page.title, "page_kind": page.kind,
                         "page_year": page.year, **ref,
                         "ref_class": wp.classify_reference(ref)})
    refs = pd.DataFrame(rows)
    refs["passage"] = refs.page_title + " § " + refs.sections
    articles = rc.news_articles(refs)
    articles["outlet_type"] = [rc.outlet_type(d, a) for d, a in
                               zip(articles.domain, articles.agency)]
    config.INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    refs.to_csv(REFS_CSV, index=False)
    articles.to_csv(ARTICLES_CSV, index=False)
    print(f"{len(refs):,} references on {refs.pageid.nunique()} pages "
          f"→ {refs.ref_class.value_counts().to_dict()}")
    print(f"{len(articles):,} distinct cited news articles; wrote {REFS_CSV.name}, "
          f"{ARTICLES_CSV.name}")


# ── fetch ────────────────────────────────────────────────────────────────────
def _items() -> list[dict]:
    config.require_data(ARTICLES_CSV)
    articles = pd.read_csv(ARTICLES_CSV, keep_default_na=False)
    articles = articles[articles.url != ""]
    return [{"url": a.url,
             "publish_date": a.pub_date or (a.page_years.split("|")[0] + "-06-01")}
            for a in articles.itertuples()]


def fetch(args) -> None:
    items = _items()
    store = fulltext.load_store(STORE)
    todo = fulltext.pending(items, store, retry_failed=args.retry_failed)
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(items):,} cited URLs, {len(store):,} already in the store, "
          f"{len(todo):,} to fetch")
    print(f"resumable: outcomes append to {STORE} as they happen.")
    with tqdm(total=len(todo), unit="url") as bar:
        fulltext.retrieve_many(todo, workers=args.workers, progress=bar.update,
                               store_path=STORE)


def status(args) -> None:
    items = _items()
    store = fulltext.load_store(STORE)
    seen = [store[i["url"]] for i in items if i["url"] in store]
    counts = Counter(r.get("status") for r in seen)
    print(f"{len(items):,} cited URLs; {len(seen):,} attempted")
    for name, n in counts.most_common():
        print(f"  {name:28s} {n:6,}")
    print(f"  pending                      {len(fulltext.pending(items, store)):6,}")
    print(f"  retryable                    "
          f"{len(fulltext.pending(items, store, retry_failed=True)) - len(fulltext.pending(items, store)):6,}")


# ── match ────────────────────────────────────────────────────────────────────
def load_lexis() -> pd.DataFrame:
    config.require_data(LEXIS_JSONL)
    lexis = pd.read_json(LEXIS_JSONL, lines=True)
    # Hashed exactly as stage 19 hashes it — before any type conversion — so
    # the ids here are the ids in lexisnexis_article_labels.csv.
    lexis["textref_uid"] = [textref_uid(r) for r in lexis.to_dict("records")]
    lexis["pub_date"] = pd.to_datetime(lexis.pub_date, errors="coerce").dt.date.astype(str)
    return lexis.drop_duplicates("textref_uid").reset_index(drop=True)


def match(args) -> None:
    articles = pd.read_csv(ARTICLES_CSV, keep_default_na=False)
    refs = pd.read_csv(REFS_CSV, keep_default_na=False)
    print("loading LexisNexis …")
    lexis = load_lexis()
    outlets = rc.OutletIndex(lexis)
    articles["lexis_sources"] = [
        "|".join(sorted(outlets.sources_for(a.domain, [a.work, a.publisher, a.agency, a.via])))
        for a in articles.itertuples()]
    articles["in_universe"] = articles.lexis_sources != ""

    print("title tiers …")
    titled = rc.title_matches(articles, lexis, outlets)

    store = fulltext.load_store(STORE)
    texts = {url: r.get("text", "") for url, r in store.items() if r.get("status") == "ok"}
    articles["text_retrieved"] = articles.url.isin(texts)
    print(f"content tier on {articles.text_retrieved.sum():,} retrieved texts …")
    index = rc.ShingleIndex(lexis)
    content = rc.content_matches(articles, texts, index)

    matches = pd.concat([titled, content[content.tier.notna()]
                         if len(content) else content], ignore_index=True)
    matches.to_csv(MATCHES_CSV, index=False)
    for tier in rc.TIERS:
        hit = set(matches.loc[matches.tier == tier, "article_key"])
        articles[tier] = articles.article_key.isin(hit)
    articles["matched_strong"] = articles[list(rc.STRONG_TIERS)].any(axis=1)
    articles["matched_any"] = articles[list(rc.TIERS)].any(axis=1)
    if len(content):
        best = content.set_index("article_key")
        articles["content_containment"] = articles.article_key.map(best.containment)
        articles["content_textref"] = articles.article_key.map(best.get("textref_uid"))
    else:
        articles["content_containment"] = pd.NA
        articles["content_textref"] = pd.NA
    articles.to_csv(ARTICLES_CSV, index=False)

    write_handcheck(articles, matches, lexis, texts)
    write_report(articles, refs, matches, titled, content, lexis)
    write_manifest(config.PROCESSED_DIR / "manifest_wikipedia_reference_coverage.json",
                   "24_wikipedia_reference_coverage",
                   counts={"references": len(refs), "news_articles": len(articles),
                           "in_universe": int(articles.in_universe.sum()),
                           "text_retrieved": int(articles.text_retrieved.sum()),
                           **{t: int(articles[t].sum()) for t in rc.TIERS},
                           "matched_strong": int(articles.matched_strong.sum()),
                           "lexisnexis_articles": len(lexis)},
                   outputs=[REFS_CSV, ARTICLES_CSV, MATCHES_CSV])
    print(f"strong match: {articles.matched_strong.sum():,}/{len(articles):,} "
          f"({articles.matched_strong.mean():.1%}); in universe "
          f"{articles[articles.in_universe].matched_strong.mean():.1%}")
    print(f"wrote {MATCHES_CSV.name}, {HANDCHECK_CSV.name}, {REPORT.name}")


def _lede(text: str, words: int = 80) -> str:
    return " ".join(str(text or "").split()[:words])


def _nearest(art, lexis: pd.DataFrame) -> pd.Series | None:
    """The same-outlet LexisNexis article with the closest headline within a
    week — the candidate a matcher miss would have to be."""
    sources = set(art.lexis_sources.split("|"))
    day = pd.Timestamp(art.pub_date)
    pool = lexis[lexis.source.isin(sources)
                 & ((pd.to_datetime(lexis.pub_date, errors="coerce") - day).abs()
                    <= pd.Timedelta(days=config.WIKI_REF_FUZZY_DATE_DAYS))]
    if pool.empty:
        return None
    scores = [rc.matching.title_similarity(art.title, h)["jaccard"] for h in pool.headline]
    return pool.iloc[max(range(len(scores)), key=scores.__getitem__)]


def write_handcheck(articles: pd.DataFrame, matches: pd.DataFrame,
                    lexis: pd.DataFrame, texts: dict[str, str]) -> None:
    """A blind sheet to measure the matcher.

    Up to 20 matched pairs per tier measure each tier's precision; 30 misses
    measure what the matcher leaves behind. The misses are drawn only from
    citations that *have* a same-outlet LexisNexis article within a week — the
    rest provably have nothing to match (see "Matcher or export?"). The tier
    is not on the sheet, so it cannot steer the label; it sits in a key file.

    Never overwrites a sheet that already carries labels.
    """
    if HANDCHECK_CSV.exists():
        prior = pd.read_csv(HANDCHECK_CSV, keep_default_na=False)
        if "label" in prior and (prior.label != "").any():
            print(f"  {HANDCHECK_CSV.name} already has labels — left untouched")
            return
    best = (matches.sort_values("jaccard", ascending=False, na_position="last")
                   .drop_duplicates(["article_key", "tier"]))
    parts = [best[best.tier == t].sample(min((best.tier == t).sum(), 20), random_state=24)
             for t in rc.TIERS]
    pairs = pd.concat(parts)[["article_key", "tier", "textref_uid", "jaccard", "containment"]]

    missed = articles[articles.in_universe & ~articles.matched_any
                      & (articles.date_precision == "day")]
    rows = []
    for art in missed.sample(frac=1, random_state=24).itertuples():
        cand = _nearest(art, lexis)
        if cand is not None:
            rows.append({"article_key": art.article_key, "tier": "unmatched",
                         "textref_uid": cand.textref_uid})
        if len(rows) == 30:
            break
    key = pd.concat([pairs, pd.DataFrame(rows)], ignore_index=True)
    key = key.sample(frac=1, random_state=24).reset_index(drop=True)
    key.insert(0, "row_id", [f"h{i + 1:03d}" for i in range(len(key))])

    cited = articles.set_index("article_key")
    lex = lexis.drop_duplicates("textref_uid").set_index("textref_uid")
    sheet = pd.DataFrame({
        "row_id": key.row_id,
        "cited_title": key.article_key.map(cited.title),
        "cited_outlet": key.article_key.map(cited.work.where(cited.work != "", cited.domain)),
        "cited_date": key.article_key.map(cited.pub_date),
        "cited_url": key.article_key.map(cited.url),
        "cited_lede": key.article_key.map(cited.url).map(lambda u: _lede(texts.get(u, ""))),
        "lexis_headline": key.textref_uid.map(lex.headline),
        "lexis_source": key.textref_uid.map(lex.source),
        "lexis_date": key.textref_uid.map(lex.pub_date),
        "lexis_lede": key.textref_uid.map(lex.body).map(_lede),
        "label": "",
        "notes": "",
    })
    HANDCHECK_CSV.parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(HANDCHECK_CSV, index=False)
    key.to_csv(HANDCHECK_KEY, index=False)


def _share(n: int, d: int) -> str:
    if not d:
        return "–"
    lo, hi = wilson_interval(n, d)
    return f"{n / d:.1%} ({lo:.1%}–{hi:.1%})"


def _table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def write_report(articles, refs, matches, titled, content, lexis) -> None:
    n = len(articles)
    uni = articles[articles.in_universe]
    lines = [
        "# Wikipedia reference coverage — LexisNexis",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by "
        "`scripts/24_wikipedia_reference_coverage.py match`.",
        "",
        "> **Question.** Of the news articles English Wikipedia cites about US "
        f"tornadoes ({config.WINDOW_START.year}–{config.WINDOW_END.year}), how many are in "
        f"our LexisNexis export ({len(lexis):,} distinct articles)? Wikipedia's editors "
        "chose these without reference to our corpus, so the share is a recall "
        "estimate the corpus cannot give about itself — recall on *what Wikipedia "
        "cites*, which leans to national, wire and online sources.",
        "",
        "## The references",
        "",
        f"{len(refs):,} distinct references on {refs.pageid.nunique()} pages "
        "(dedicated tornado articles and outbreak articles from stage 23):",
        "",
        _table(refs.ref_class.value_counts().rename_axis("class").reset_index(name="references")),
        "",
        f"Only `news` enters the denominator. The {refs[refs.ref_class == 'news'].shape[0]:,} "
        f"news references are **{n:,} distinct cited articles** (one URL cited from "
        f"several pages counts once); {(articles.date_precision != 'day').sum():,} "
        f"({(articles.date_precision != 'day').mean():.0%}) carry no day-precise date, "
        "and can only be matched within their outlet and the event year.",
        "",
        "## Coverage",
        "",
        f"**In universe:** {len(uni):,} of {n:,} cited articles "
        f"({len(uni) / n:.0%}) come from an outlet that appears in our LexisNexis export. "
        "The rest come from outlets LexisNexis either does not carry or that never "
        "matched the search; those cannot be told apart without LexisNexis's source list.",
        "",
    ]
    rows = []
    cumulative = pd.Series(False, index=articles.index)
    for tier in rc.TIERS:
        cumulative = cumulative | articles[tier]
        rows.append({
            "tier": f"`{tier}`",
            "this tier": int(articles[tier].sum()),
            "only this tier": int((articles[tier] & (articles[list(rc.TIERS)].sum(axis=1) == 1)).sum()),
            "cumulative — overall": _share(int(cumulative.sum()), n),
            "cumulative — in universe": _share(int(cumulative[articles.in_universe].sum()), len(uni)),
        })
    lines += [
        _table(pd.DataFrame(rows)),
        "",
        "Rows are cumulative in the order shown; 95% Wilson intervals in brackets. "
        f"**The headline figure is the third row** (`title_outlet` + "
        f"`title_syndicated` + `content`): **{_share(int(articles.matched_strong.sum()), n)} "
        f"overall, {_share(int(uni.matched_strong.sum()), len(uni))} in universe.** "
        "`title_fuzzy` is the weak tier and is reported, not counted, until the "
        "hand-check measures its precision.",
        "",
    ]
    retrieved = int(articles.text_retrieved.sum())
    with_url = int((articles.url != "").sum())
    lines += [
        "### The content tier",
        "",
        f"Text was retrieved for **{retrieved:,} of {with_url:,}** cited URLs "
        f"({retrieved / max(with_url, 1):.0%}). "
        + ("**The fetch has not finished, so the content tier is a lower bound.** "
           if retrieved < 0.8 * with_url else "")
        + "Where both a title match and text exist, the text is a check on the title:",
        "",
    ]
    if retrieved:
        check = []
        for tier in ("title_outlet", "title_syndicated", "title_fuzzy"):
            sub = articles[articles[tier] & articles.text_retrieved]
            confirmed = (sub.content_containment >= config.WIKI_REF_CONTENT_CONTAINMENT).sum()
            check.append({"title tier": f"`{tier}`", "with text": len(sub),
                          "text confirms": int(confirmed),
                          "confirmation rate": _share(int(confirmed), len(sub))})
        lines += [_table(pd.DataFrame(check)), "",
                  "A title match the text does not confirm is either a false positive or "
                  "a LexisNexis copy that differs from the web version (print edits, "
                  "updates); the hand-check separates the two.", ""]

    def breakdown(col: str, label: str) -> list[str]:
        g = articles.groupby(col)
        t = pd.DataFrame({
            label: list(g.groups),
            "cited": g.size().values,
            "in universe": g.in_universe.sum().astype(int).values,
            "matched (strong)": g.matched_strong.sum().astype(int).values,
        })
        t["recall — overall"] = [_share(m, c) for m, c in zip(t["matched (strong)"], t.cited)]
        t["recall — in universe"] = [
            _share(int(articles[(articles[col] == k) & articles.in_universe].matched_strong.sum()), u)
            for k, u in zip(t[label], t["in universe"])]
        return [_table(t), ""]

    articles["year"] = articles.pub_date.str[:4].where(articles.pub_date != "",
                                                       articles.page_years.str[:4])
    lines += ["### By year of the cited article", ""] + breakdown("year", "year")
    lines += ["### By outlet type", "",
              "Heuristic: wire = AP/Reuters/AFP/UPI or an agency credit; national = a "
              "fixed list of national outlets; local broadcast = a call-sign domain.", ""]
    lines += breakdown("outlet_type", "outlet type")

    # Event level: does each page / tornado section have at least one held article?
    exploded = articles.assign(passage=articles.sections.str.split(" \\| ")).explode("passage")
    per_page = articles.assign(page=articles.pages.str.split(" \\| ")).explode("page")
    page_cov = per_page.groupby("page").matched_strong.any()
    sec = exploded[exploded.passage.str.contains(" > ", na=False)]
    sec_cov = sec.groupby("passage").matched_strong.any()
    lines += [
        "## Coverage per event",
        "",
        f"- **Pages:** {page_cov.sum()} of {len(page_cov)} pages that cite news "
        f"({page_cov.mean():.0%}) have at least one cited article in LexisNexis.",
        f"- **Per-tornado sections:** {sec_cov.sum()} of {len(sec_cov)} outbreak sections "
        f"that cite news ({sec_cov.mean() if len(sec_cov) else 0:.0%}) do.",
        "",
    ]

    # Is a miss the matcher's fault or the export's? If LexisNexis holds nothing
    # from that outlet within ±3 days, no matcher could have found it.
    lex_days = lexis.assign(day=pd.to_datetime(lexis.pub_date, errors="coerce"))
    by_source = {s: g.day.dropna().values for s, g in lex_days.groupby("source")}
    missed = uni[~uni.matched_any & (uni.date_precision == "day")]
    window = pd.Timedelta(days=config.OVERLAP_DATE_TOLERANCE_DAYS)

    def any_nearby(row) -> bool:
        day = pd.Timestamp(row.pub_date)
        return any(((by_source.get(s, []) >= (day - window).to_datetime64())
                    & (by_source.get(s, []) <= (day + window).to_datetime64())).any()
                   for s in row.lexis_sources.split("|") if s in by_source)

    nearby = missed.apply(any_nearby, axis=1) if len(missed) else pd.Series(dtype=bool)
    lines += [
        "## Matcher or export?",
        "",
        f"Of the {len(missed)} dated in-universe citations with no match, "
        f"**{int((~nearby).sum())} ({(~nearby).mean() if len(nearby) else 0:.0%}) have no "
        "LexisNexis article at all from that outlet within "
        f"±{config.OVERLAP_DATE_TOLERANCE_DAYS} days.** For those, the export does not "
        "hold the outlet's coverage of that event, and no matcher could recover them. "
        f"The other {int(nearby.sum())} are where matcher misses can hide — a rewritten "
        "print headline, or a different story the same week — and the content tier and "
        "the hand-check are what resolve them.",
        "",
    ]
    lines += ["## Where the misses are", "",
              "### Outlets in universe, cited often, matched rarely", "",
              "Each is either a matcher failure (rewritten print headline, wrong date) "
              "or an outlet whose LexisNexis feed is partial. The hand-check sheet "
              "samples from these rows.", ""]
    miss = (uni.assign(outlet=uni.work.where(uni.work != "", uni.domain))
               .groupby("outlet").agg(cited=("article_key", "size"),
                                      matched=("matched_strong", "sum"),
                                      lexisnexis_names=("lexis_sources", "first"))
               .query("cited >= 3").sort_values("cited", ascending=False).head(25)
               .reset_index())
    miss["lexisnexis_names"] = miss.lexisnexis_names.str.slice(0, 80)
    lines += [_table(miss), ""]
    out = articles[~articles.in_universe]
    lines += ["### Most-cited outlets not in our export", "",
              "These decide the in-universe/overall gap. Looking them up in the "
              "LexisNexis source directory turns the proxy into a partly verified list: "
              "an outlet LexisNexis carries belongs in the universe, and its citations "
              "are misses of our search rather than of LexisNexis.", "",
              _table(out.assign(outlet=out.work.where(out.work != "", out.domain))
                        .groupby(["outlet", "domain"]).size().rename("cited")
                        .sort_values(ascending=False).head(30).reset_index()), ""]
    other = refs[refs.ref_class == "other_web"]
    lines += [f"### `other_web` references ({len(other)}), excluded from the denominator", "",
              "Cited without a publication name on a domain that is not NWS, government, "
              "social or reference. Many look like local news; if so, the classifier is "
              "conservative and the denominator slightly small.", "",
              ", ".join(f"{d} ({c})" for d, c in other.domain.value_counts().head(25).items()),
              ""]
    lines += [
        "## Validation",
        "",
        f"`{HANDCHECK_CSV.relative_to(config.REPO_ROOT) if HANDCHECK_CSV.is_relative_to(config.REPO_ROOT) else HANDCHECK_CSV}` "
        "is blind: each row pairs a cited article with one LexisNexis article, and the "
        "tier that proposed the pair is in `data/interim/wikipedia_ref_handcheck_key.csv`, "
        "not on the sheet. Up to 20 pairs per tier measure each tier's precision; 30 "
        "pairs are a miss with its nearest same-outlet candidate, which measures what "
        "the matcher leaves behind. Labels: `same_article`, `same_article_edited` (the "
        "same piece in another version — print edit, update, trimmed wire copy), "
        "`different_article`, `unsure`.",
        "",
        "## Limitations",
        "",
        "1. **Recall on what Wikipedia cites**, not on tornado news. Editors cite "
        "online, national and wire sources; local print is under-represented.",
        "2. **The universe is a proxy** (outlets present in our export), which makes "
        "in-universe recall optimistic. Overall recall is the conservative figure.",
        "3. **Undated citations** are matched within their outlet and event year only, "
        "and cannot reach the syndicated tier.",
        "4. **Outlet identity is inferred** from names and domains. A Wikipedia "
        "citation of a Gannett paper may be held in LexisNexis under a different "
        "masthead; the content tier is what catches those.",
        "5. **Nothing here is validated against humans until the hand-check is filled.**",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("extract")
    f = sub.add_parser("fetch")
    f.add_argument("--workers", type=int, default=12)
    f.add_argument("--retry-failed", action="store_true",
                   help="re-attempt transient failures (rate limits, connection errors)")
    f.add_argument("--limit", type=int, default=None, help="fetch at most N URLs this run")
    sub.add_parser("status")
    sub.add_parser("match")
    args = ap.parse_args()
    {"extract": extract, "fetch": fetch, "status": status, "match": match}[args.cmd](args)


if __name__ == "__main__":
    main()
