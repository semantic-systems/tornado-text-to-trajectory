"""Stage 11 — link news articles to the tornado or outbreak they describe.

Runs the pipeline in docs/stage_c_plan.md: a date window to build a shortlist, IDF-
weighted toponym matching to decide, corroborating signals to break ties, and a
descent to the individual tornado only where the evidence supports it.

Handles both text sources, which differ in what they give us: LexisNexis articles
have full bodies, GDELT records have a headline and nothing else. They are scored
by the same code and reported separately, because their precision is not
comparable.

    python scripts/11_link_articles.py                    # both sources
    python scripts/11_link_articles.py --skip-gdelt
    python scripts/11_link_articles.py --news-suffix march2025
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config
from tornado_dataset.dat.hazards import ef_rank
from tornado_dataset.ids import uid, write_manifest
from tornado_dataset.text import lexisnexis, linking, tiering


# Out-of-scope classes. The dataset covers US tornadoes NWS surveyed, so an
# article about an Ontario tornado or a preparedness explainer is not a linking
# failure — it has no answer to find. Reporting coverage against all articles
# mixes those in and understates what the linker achieves; these heuristics let
# the report give both denominators. They classify, they never filter.
FOREIGN_RE = re.compile(
    r"\b(canada|canadian|ontario|quebec|alberta|manitoba|saskatchewan|"
    r"british columbia|india|bangladesh|china|europe|german|france|french|italy|"
    r"poland|czech|netherlands|britain|england|scotland|ireland|wales|"
    r"australia|new zealand|japan|brazil|argentina|philippines|indonesia)\b",
    re.IGNORECASE)
NO_EVENT_RE = re.compile(
    r"\b(how to prepare|how to survive|what to do|preparedness|safety tips|"
    r"tornado season|seasonal outlook|explainer|insurance|legislation|"
    r"introduce[sd]? the|donat\w+|grant\w*|fundraiser|drill|climate change|"
    r"study finds|new research|anniversary)\b", re.IGNORECASE)


def load_gate_labels(path) -> dict[str, str] | None:
    """Read stage 19's per-article relevance labels, or ``None`` if not gating.

    The regex heuristics above are *superseded* by these labels but deliberately
    kept: they still populate the ``scope`` column, and their disagreement with
    the model is a free drift monitor — the same treatment stage 18 gave its cue
    regexes after measurement removed them from the decision.
    """
    if path is None:
        return None
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"missing {path} — run scripts/19_filter_lexisnexis.py apply first")
    frame = pd.read_csv(path, keep_default_na=False,
                        usecols=["textref_uid", "primary"])
    labels = dict(zip(frame.textref_uid, frame.primary))
    kept = sum(1 for v in labels.values() if v == "EVENT")
    print(f"gating on {path.name}: {len(labels):,} labelled articles, "
          f"{kept:,} EVENT will be linked, {len(labels) - kept:,} recorded and skipped")
    return labels


def classify_scope(headline: str, body: str, states_mentioned: bool) -> str:
    """Coarse in-scope / out-of-scope judgement for coverage reporting."""
    blob = f"{headline} {str(body)[:800]}"
    if FOREIGN_RE.search(blob) and not states_mentioned:
        return "out_of_scope_foreign"
    if NO_EVENT_RE.search(headline or ""):
        return "likely_no_event_article"
    return "in_scope"


def ef_numbers(values) -> set[int]:
    out = set()
    for value in values:
        rank = ef_rank(value)
        if rank >= 0:
            out.add(int(rank))
    return out


def load_events(tag: str):
    """Episode and hazard records, indexed by convective day."""
    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv")
    episodes = pd.read_csv(config.PROCESSED_DIR / f"episodes_{tag}.csv")
    geography = pd.read_csv(config.PROCESSED_DIR / f"hazard_geography_{tag}.csv")

    index = linking.ToponymIndex(geography.to_dict("records"))

    states_by_hazard = {row.hazard_uid: {s for s in str(row.states or "").split(";") if s}
                        for row in geography.itertuples()}
    hazard_events, hazards_by_episode = {}, defaultdict(list)
    for row in hazards.itertuples():
        day = None
        if isinstance(row.convective_day, str):
            day = dt.date.fromisoformat(row.convective_day)
        hazard_events[row.hazard_uid] = {
            "day": day, "ef_numbers": ef_numbers([row.efscale]),
            "fatalities": row.fatalities, "injuries": row.injuries,
            "states": states_by_hazard.get(row.hazard_uid, set()),
            "efscale": row.efscale, "path_length_mi": row.path_length_mi,
        }
        if isinstance(row.episode_uid, str):
            hazards_by_episode[row.episode_uid].append(row.hazard_uid)

    episode_events, episodes_by_day = {}, defaultdict(list)
    for row in episodes.itertuples():
        if not isinstance(row.convective_day, str):
            continue
        day = dt.date.fromisoformat(row.convective_day)
        members = hazards_by_episode.get(row.episode_uid, [])
        episode_events[row.episode_uid] = {
            "day": day,
            "ef_numbers": ef_numbers([hazard_events[h]["efscale"] for h in members]),
            "fatalities": row.fatalities, "injuries": row.injuries,
            "states": {s for h in members for s in hazard_events[h]["states"]},
            "n_hazards": row.n_hazards, "max_efscale": row.max_efscale,
        }
        episodes_by_day[day].append(row.episode_uid)

    return (index, episode_events, episodes_by_day, hazard_events,
            dict(hazards_by_episode))


def link_article(article: dict, index: linking.ToponymIndex, episode_events: dict,
                 episodes_by_day: dict, hazard_events: dict, hazards_by_episode: dict,
                 *, retrospective: bool) -> list[dict]:
    """Score one article against its candidate episodes and decide."""
    # Missing dates arrive as pandas NaT, which is truthy and whose .year is a
    # float — so it has to be normalised, not merely tested for.
    published: dt.date | None = linking.as_date(article["date"])
    text = linking.ArticleText(headline=article.get("headline", ""),
                               dateline=article.get("dateline", ""),
                               body=article.get("body", ""),
                               title_only=article.get("title_only", False))
    states = linking.source_states(article.get("source", ""), article.get("dateline", ""))

    candidates = linking.candidate_events(published, episodes_by_day) if published else []
    window_uids = {uid_ for uid_, _ in candidates}
    offsets = {uid_: offset for uid_, offset in candidates}

    # Second pass for anniversary and retrospective pieces, whose event lies far
    # outside the publication window: take the dates the article itself names and
    # add episodes on those days. Without this, ~4.5% of the corpus is unlinkable
    # by construction — and they are exactly the retrospective class the
    # experiments need.
    extra: list[str] = []
    year_only: set[str] = set()
    if retrospective and published:
        for named, granularity in linking.explicit_dates(text.full_text, published):
            if granularity == "year":
                # A bare year pins nothing by itself, so every outbreak day in it
                # becomes a candidate and the toponym score has to earn the link.
                # These are filtered again after scoring.
                for month in range(1, 13):
                    for day_number in range(1, 32):
                        try:
                            day = dt.date(named.year, month, day_number)
                        except ValueError:
                            continue
                        for uid_ in episodes_by_day.get(day, []):
                            if uid_ not in window_uids and uid_ not in extra:
                                extra.append(uid_)
                                year_only.add(uid_)
                                offsets[uid_] = (published - day).days
                continue
            if granularity == "month":
                # "May 2024" or "one year after" pins a month, not a day, so every
                # outbreak day in that month becomes a candidate. The toponym score
                # still has to pick one out.
                days = [named.replace(day=1) + dt.timedelta(days=k) for k in range(31)]
                days = [d for d in days if d.month == named.month]
            else:
                days = [named + dt.timedelta(days=k) for k in (-1, 0, 1)]
            for day in days:
                if abs((day - published).days) <= config.LINK_DAYS_AFTER_EVENT:
                    continue                      # already in the window
                for uid_ in episodes_by_day.get(day, []):
                    if uid_ not in window_uids and uid_ not in extra:
                        extra.append(uid_)
                        offsets[uid_] = (published - day).days
    for uid_ in extra:
        window_uids.add(uid_)

    scored = []
    for episode_uid in window_uids:
        event = episode_events.get(episode_uid)
        if not event:
            continue
        record = linking.score_pair(text, index.episode_names.get(episode_uid, {}),
                                   event, index, published=published,
                                   source_states=states)
        # A year-only candidate is admitted only on a strong place match; without
        # this a single "the 2011 tornado" would nominate every outbreak of 2011.
        if episode_uid in year_only and (
                record["toponym_score"] < config.LINK_YEAR_ONLY_MIN_TOPONYM
                or (config.LINK_YEAR_ONLY_REQUIRE_PROMINENT
                    and not record.get("has_prominent_match"))
                or record["corroboration_score"] < config.LINK_YEAR_ONLY_MIN_CORROBORATION):
            continue
        record.update({
            "episode_uid": episode_uid,
            "day_offset": offsets.get(episode_uid),
            "from_retrospective_pass": episode_uid in extra,
            "from_year_only_pass": episode_uid in year_only,
            "event_day": event["day"].isoformat(),
            "event_n_hazards": event["n_hazards"],
            "event_max_ef": event["max_efscale"],
            "event_fatalities": event["fatalities"],
        })
        scored.append(record)

    decided = linking.decide(scored)
    for record in decided:
        # Descend to a single tornado only when one clearly wins; most coverage of
        # a big outbreak is about the outbreak.
        best = linking.refine_to_hazard(
            text, hazards_by_episode.get(record["episode_uid"], []), index,
            hazard_events, published=published, source_states=states)
        record["link_level"] = "hazard" if best else "episode"
        record["hazard_uid"] = best["hazard_uid"] if best else None
        record["hazard_score"] = best["link_score"] if best else None
        record["hazard_margin"] = best.get("hazard_margin") if best else None
    return decided, len(window_uids)


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--news-suffix", default=None,
                        help="suffix of the GDELT textref file, if a pilot subset")
    parser.add_argument("--articles", type=Path,
                        default=config.OUTPUT_DIR / "lexisnexis_articles.jsonl")
    parser.add_argument("--labels", type=Path, default=None,
                        help="stage 19 relevance labels "
                             "(data/processed/lexisnexis_article_labels.csv). When "
                             "given, only EVENT articles are linked; the rest are "
                             "recorded with link_status=filtered_<primary>.")
    parser.add_argument("--skip-gdelt", action="store_true")
    parser.add_argument("--no-retrospective", action="store_true",
                        help="disable the text-date second pass")
    args = parser.parse_args()

    print("loading events and gazetteer …")
    (index, episode_events, episodes_by_day,
     hazard_events, hazards_by_episode) = load_events(args.tag)
    print(f"  {len(episode_events)} episodes, {len(hazard_events)} hazards, "
          f"{len(index.document_frequency):,} distinct place names")

    rows: list[dict] = []
    refs: list[dict] = []
    statuses: list[dict] = []
    stats = Counter()

    # ── LexisNexis: full text ──
    gate_labels = load_gate_labels(args.labels)
    lexis = pd.read_json(args.articles, lines=True)
    lexis["date"] = [linking.as_date(d) for d in
                     pd.to_datetime(lexis.pub_date, errors="coerce").dt.tz_localize(None)]
    undated = int(sum(1 for d in lexis.date if d is None))
    print(f"\nLexisNexis: {len(lexis)} articles "
          f"({int((~lexis.is_duplicate).sum())} unique)")
    if undated:
        # These cannot be windowed at all, so they are reported rather than
        # silently producing zero links.
        print(f"  {undated} article(s) carry no publication date and cannot be "
              f"date-windowed — they get no links")
    # The export contains the same file more than once where download batches
    # overlapped — 14% of rows are byte-identical copies. Scoring each copy would
    # write duplicate link rows, break the per-article cap and let one article be
    # drawn several times into an annotation sample, so each unique article is
    # linked once and the repeat count is recorded.
    seen_uids: set[str] = set()
    for i, row in enumerate(lexis.to_dict("records"), 1):
        ref_uid = lexisnexis.textref_uid(row)
        refs.append({
            "textref_uid": ref_uid, "source_type": "news_fulltext",
            "corpus": "lexisnexis", "file": row.get("file"),
            "source_name": row.get("source"),
            "headline": row.get("headline"), "published_at": row.get("pub_date"),
            "date": row["date"], "dateline": row.get("dateline"),
            "is_duplicate": bool(row.get("is_duplicate")),
            "dup_group": row.get("dup_group"), "n_words": row.get("n_words"),
            "body": row.get("body"),
        })
        if ref_uid in seen_uids:
            stats["exact_duplicate_rows"] += 1
            continue
        seen_uids.add(ref_uid)

        # Stage 19's relevance label, when supplied, gates the expensive part.
        # An article it did not judge is still linked rather than silently
        # dropped — a partial label file is a mismatch to report, not a licence
        # to shrink the corpus.
        gate = gate_labels.get(ref_uid) if gate_labels is not None else None
        if gate is None and gate_labels is not None:
            stats["unlabelled_by_stage19"] += 1
        filtered = gate is not None and gate != "EVENT"

        if filtered:
            stats[f"filtered_{gate.lower()}"] += 1
            decided, n_candidates = [], 0
        else:
            decided, n_candidates = link_article(
                {**row, "date": row["date"]}, index, episode_events, episodes_by_day,
                hazard_events, hazards_by_episode, retrospective=not args.no_retrospective)
            stats["lexis_candidates"] += n_candidates
            stats["lexis_linked"] += bool(decided)
            for record in decided:
                rows.append({**record, "textref_uid": ref_uid, "corpus": "lexisnexis"})

        # Per-article outcome, so "coverage" can be quoted against the population
        # that could have been linked rather than against everything downloaded.
        blob = f"{row.get('headline', '')} {str(row.get('body', ''))[:800]}"
        scope = classify_scope(row.get("headline", ""), row.get("body", ""),
                               states_mentioned=bool(linking.source_states(
                                   row.get("source", ""), row.get("dateline", ""))))
        if filtered:
            # Recorded, not dropped: article_status_*.csv is a complete census of
            # the corpus that the report and the viewer both read, and silently
            # shrinking it would break both.
            status = f"filtered_{gate.lower()}"
        elif decided:
            status = "linked"
        elif row["date"] is None:
            status = "no_publication_date"
        elif scope != "in_scope":
            status = scope
        elif n_candidates == 0:
            status = "no_surveyed_event_in_window"
        else:
            status = "no_link_above_floor"
        statuses.append({"textref_uid": ref_uid, "file": row.get("file"),
                         "headline": row.get("headline"), "date": row["date"],
                         "source": row.get("source"), "scope": scope,
                         "link_status": status, "n_candidate_episodes": n_candidates,
                         "n_links": len(decided)})
        if i % 200 == 0:
            print(f"  scored {i}/{len(lexis)}", end="\r", flush=True)
    print(f"  scored {len(lexis)}/{len(lexis)}")

    # ── GDELT: headline only ──
    news_tag = args.news_suffix or args.tag
    news_path = config.PROCESSED_DIR / f"textrefs_news_{news_tag}.csv"
    if not args.skip_gdelt and news_path.exists():
        news = pd.read_csv(news_path)
        news["date"] = [linking.as_date(d) for d in
                        pd.to_datetime(news.published_at, errors="coerce",
                                       format="ISO8601", utc=True).dt.tz_localize(None)]
        print(f"\nGDELT: {len(news)} articles (headline only)")
        for i, row in enumerate(news.to_dict("records"), 1):
            decided, n_candidates = link_article(
                {"date": row["date"], "headline": row.get("title") or "",
                 "dateline": "", "body": "", "source": row.get("source_name") or "",
                 "title_only": True},
                index, episode_events, episodes_by_day, hazard_events,
                hazards_by_episode, retrospective=False)
            stats["gdelt_candidates"] += n_candidates
            stats["gdelt_linked"] += bool(decided)
            for record in decided:
                rows.append({**record, "textref_uid": row["textref_uid"],
                             "corpus": "gdelt"})
            if i % 500 == 0:
                print(f"  scored {i}/{len(news)}", end="\r", flush=True)
        print(f"  scored {len(news)}/{len(news)}")
        stats["gdelt_articles"] = len(news)
    elif not args.skip_gdelt:
        print(f"\nGDELT: {news_path.name} not found — run scripts/07_fetch_gdelt.py "
              f"or pass --news-suffix")

    links = pd.DataFrame(rows)
    refs_frame = pd.DataFrame(refs)

    # Publishable links vs candidates: the split point is provisional until the
    # annotated sample sets it (docs/stage_c_plan.md §4), so both are written.
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    links_path = config.PROCESSED_DIR / f"article_links_{args.tag}.csv"
    refs_path = config.PROCESSED_DIR / f"textrefs_lexisnexis_{args.tag}.csv"
    links.to_csv(links_path, index=False)
    refs_frame.drop(columns=["body"]).to_csv(refs_path, index=False)
    status_frame = pd.DataFrame(statuses)
    status_path = config.PROCESSED_DIR / f"article_status_{args.tag}.csv"
    status_frame.to_csv(status_path, index=False)

    lexis_links = links[links.corpus == "lexisnexis"] if len(links) else links
    counts = {
        "lexis_rows_in_export": len(lexis),
        "lexis_exact_duplicate_rows": stats["exact_duplicate_rows"],
        "lexis_articles": len(seen_uids),
        "lexis_articles_without_a_date": undated,
        "lexis_articles_with_a_link": stats["lexis_linked"],
        "lexis_mean_candidate_episodes": round(
            stats["lexis_candidates"] / max(1, len(seen_uids)), 1),
        "lexis_links": len(lexis_links),
        "gdelt_articles": stats.get("gdelt_articles", 0),
        "gdelt_articles_with_a_link": stats["gdelt_linked"],
        "gdelt_links": int((links.corpus == "gdelt").sum()) if len(links) else 0,
        "by_relation": links.link_relation.value_counts().to_dict() if len(links) else {},
        "by_level": links.link_level.value_counts().to_dict() if len(links) else {},
        "from_retrospective_pass": int(links.from_retrospective_pass.sum()) if len(links) else 0,
        "parameters": {
            "days_before_event": config.LINK_DAYS_BEFORE_EVENT,
            "days_after_event": config.LINK_DAYS_AFTER_EVENT,
            "min_score": config.LINK_MIN_SCORE,
            "weight_toponym": config.LINK_WEIGHT_TOPONYM,
            "weight_corroboration": config.LINK_WEIGHT_CORROBORATION,
            "hazard_margin": config.LINK_HAZARD_MARGIN,
            "tier_rule_version": tiering.TIER_RULE_VERSION,
        },
    }
    in_scope = status_frame[status_frame.scope == "in_scope"] if len(status_frame) else status_frame
    counts["by_link_status"] = (status_frame.link_status.value_counts().to_dict()
                                if len(status_frame) else {})
    counts["in_scope_articles"] = len(in_scope)
    counts["in_scope_linked"] = int((in_scope.link_status == "linked").sum()) if len(in_scope) else 0
    write_manifest(config.PROCESSED_DIR / f"manifest_article_links_{args.tag}.json",
                   "11_link_articles", counts=counts,
                   outputs=[links_path, refs_path, status_path])

    print(f"\n{len(links)} candidate links written")
    print(f"  LexisNexis: {stats['lexis_linked']}/{len(seen_uids)} unique articles "
          f"({stats['lexis_linked'] / max(1, len(seen_uids)):.1%}); "
          f"{stats['exact_duplicate_rows']} exact duplicate rows skipped; "
          f"mean {counts['lexis_mean_candidate_episodes']} candidate episodes each")
    if stats.get("gdelt_articles"):
        print(f"  GDELT: {stats['gdelt_linked']}/{stats['gdelt_articles']} articles "
              f"({stats['gdelt_linked'] / max(1, stats['gdelt_articles']):.1%})")
    if counts["in_scope_articles"]:
        print(f"  in scope (excludes foreign / no-event articles): "
              f"{counts['in_scope_linked']}/{counts['in_scope_articles']} "
              f"({counts['in_scope_linked'] / counts['in_scope_articles']:.1%})")
        print(f"  status: {counts['by_link_status']}")
    print(f"  relations: {counts['by_relation']}  levels: {counts['by_level']}")
    print(f"  found only via the retrospective pass: {counts['from_retrospective_pass']}")
    print(f"wrote {links_path.name}, {refs_path.name}")


if __name__ == "__main__":
    main()
