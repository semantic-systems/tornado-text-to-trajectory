"""Stage 21 — collect independent news coverage per episode from GDELT.

One query per episode (an outbreak), built from the place names its tornadoes
passed through. GDELT enforces one request per five seconds, so a full sweep runs
for hours; every response is cached, which makes the run resumable and lets a
rerun work offline.

Articles are stored as links and metadata only — never bodies — and each is
classified on the two independence axes against the episode's onset and the time
its first NWS survey was published.

    python scripts/21_fetch_gdelt.py --limit 20            # pilot
    python scripts/21_fetch_gdelt.py --tag march2025
    python scripts/21_fetch_gdelt.py                       # full sweep (hours)
"""

from __future__ import annotations

import argparse
import datetime as dt
from collections import Counter, defaultdict

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config
from tornado_dataset.dat import episode_table
from tornado_dataset.ids import uid, write_manifest
from tornado_dataset.text import gdelt, tiering


def survey_times(tag: str) -> dict[str, dt.datetime]:
    """First primary-survey publication per episode, if Stage 20 has run."""
    refs_path = config.PROCESSED_DIR / f"textrefs_nws_{tag}.csv"
    links_path = config.PROCESSED_DIR / f"textlinks_nws_{tag}.csv"
    hazards_path = config.PROCESSED_DIR / f"hazards_{tag}.csv"
    if not (refs_path.exists() and links_path.exists()):
        return {}
    refs = pd.read_csv(refs_path)
    links = pd.read_csv(links_path)
    hazards = episode_table.hazards_with_episodes(tag, ["hazard_uid", "episode_uid"])
    surveys = (links[links.link_relation == "primary_survey_of"]
               .merge(refs[["textref_uid", "published_at", "source_type"]], on="textref_uid")
               .merge(hazards, left_on="target_uid", right_on="hazard_uid"))
    out: dict[str, dt.datetime] = {}
    for row in surveys.itertuples():
        moment = tiering._as_datetime(row.published_at)
        if moment and (row.episode_uid not in out or moment < out[row.episode_uid]):
            out[row.episode_uid] = moment
    return out


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--limit", type=int, default=None,
                        help="only the N largest eligible episodes (pilot)")
    parser.add_argument("--days-after", type=int, default=config.GDELT_WINDOW_DAYS_AFTER)
    parser.add_argument("--wayback", action="store_true",
                        help="capture Internet Archive snapshots for kept articles")
    parser.add_argument("--wayback-per-episode", type=int, default=10)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--cache-only", action="store_true",
                        help="rebuild the tables from data/raw/gdelt/ without any "
                             "network access. Queries never fetched are skipped and "
                             "counted separately from failures, so partial coverage "
                             "stays visible in the manifest instead of looking like "
                             "a complete sweep.")
    args = parser.parse_args()

    episodes = pd.read_csv(config.PROCESSED_DIR / f"episodes_{args.tag}.csv")
    geography = pd.read_csv(config.PROCESSED_DIR / f"hazard_geography_{args.tag}.csv")
    hazards = episode_table.hazards_with_episodes(args.tag)

    # Toponyms are ranked by the severity of the tornado that passed them: an
    # outbreak's news coverage names the places its strongest tornadoes hit, and
    # a query has room for only about a dozen terms. Ranking by raw frequency
    # instead surfaces whichever hamlets happen to recur, which is not what
    # reporting keys on.
    from tornado_dataset.dat.hazards import ef_rank

    places_by_episode: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
    counties_by_episode: dict[str, list[tuple[float, str]]] = defaultdict(list)
    merged = geography.merge(hazards[["hazard_uid", "episode_uid", "efscale", "fatalities"]],
                             on="hazard_uid", suffixes=("_geo", ""))
    for row in merged.itertuples():
        severity = ef_rank(row.efscale) + (2 if (row.fatalities or 0) > 0 else 0)
        for order, name in enumerate(str(row.places or "").split(";")):
            if name:
                # nearest place of the worst tornado first
                places_by_episode[row.episode_uid].append((-severity, order, name))
        for name in str(row.counties or "").split(";"):
            if name:
                counties_by_episode[row.episode_uid].append((-severity, name.split(",")[0].strip()))

    coverage_start = config.GDELT_COVERAGE_START.isoformat()
    eligible = episodes[episodes.convective_day >= coverage_start].copy()
    skipped = len(episodes) - len(eligible)
    eligible = eligible.sort_values("n_hazards", ascending=False)
    if args.limit:
        eligible = eligible.head(args.limit)

    print(f"{len(episodes)} episodes; {skipped} predate GDELT coverage "
          f"({coverage_start}) and are flagged, {len(eligible)} to query")
    surveys = survey_times(args.tag)
    if surveys:
        print(f"  survey times known for {len(surveys)} episodes (from Stage 20)")

    cache_dir = config.RAW_DIR / "gdelt"
    wayback_dir = config.RAW_DIR / "wayback"
    textrefs, textlinks = [], []
    stats = Counter()

    # The window is queried in slices because a response is capped at 250 and
    # filled newest-first: one 8-day query would return only the follow-up
    # coverage and drop the breaking reports the dataset is built around.
    slices = [(0, 1), (1, 3), (3, args.days_after)]

    for i, episode in enumerate(eligible.itertuples(), 1):
        # Place names first (news names towns), counties as a fallback for
        # hazards whose track passed nowhere populated.
        ranked = [name for _, _, name in sorted(places_by_episode.get(episode.episode_uid, []))]
        if not ranked:
            ranked = [name for _, name in sorted(counties_by_episode.get(episode.episode_uid, []))]
        query = gdelt.build_query(ranked)
        if not query:
            stats["episodes_without_toponyms"] += 1
            continue

        day = dt.date.fromisoformat(episode.convective_day)
        articles, capped, failed_slices, uncached_slices = [], False, 0, 0
        for offset_start, offset_end in slices:
            if offset_start >= offset_end:
                continue
            batch = gdelt.query_articles(
                query, day + dt.timedelta(days=offset_start),
                day + dt.timedelta(days=offset_end),
                cache_dir=cache_dir, refresh=args.refresh,
                cache_only=args.cache_only)
            if batch is gdelt.NOT_CACHED:   # never fetched; not a failure either
                uncached_slices += 1
                stats["uncached_queries"] += 1
                continue
            if batch is None:          # the request failed; not an empty window
                failed_slices += 1
                stats["failed_queries"] += 1
                continue
            capped = capped or len(batch) >= config.GDELT_MAX_RECORDS
            articles.extend(batch)
        if failed_slices:
            stats["episodes_with_a_failed_slice"] += 1
            stats["episodes_fully_failed"] += int(failed_slices == len(slices))
        if uncached_slices:
            # Coverage for this episode is partial by construction, so it must be
            # visible in the manifest rather than looking like a complete sweep.
            stats["episodes_with_an_uncached_slice"] += 1
            stats["episodes_fully_uncached"] += int(uncached_slices == len(slices))
        seen_urls = set()
        articles = [a for a in articles
                    if a.get("url") and not (a["url"] in seen_urls or seen_urls.add(a["url"]))]
        stats["episodes_queried"] += 1
        stats["episodes_hit_record_cap"] += bool(capped)
        stats["articles_returned"] += len(articles)
        kept = [a for a in articles if gdelt.is_relevant(a)]
        stats["articles_relevant"] += len(kept)

        for rank, article in enumerate(kept):
            published = gdelt.parse_seendate(article.get("seendate", ""))
            classification = tiering.derive(
                author_org=article.get("domain"), source_type="news",
                published_at=published, event_begin=episode.time_begin_utc,
                survey_at=surveys.get(episode.episode_uid))
            snapshot = None
            if args.wayback and rank < args.wayback_per_episode:
                snapshot = gdelt.wayback_snapshot(
                    article["url"], (published or "")[:10].replace("-", "") or
                    day.strftime("%Y%m%d"), cache_dir=wayback_dir)
                stats["wayback_attempted"] += 1
                stats["wayback_found"] += bool(snapshot)

            ref_uid = uid("textref", "news", article["url"])
            textrefs.append({
                "textref_uid": ref_uid, "source_type": "news",
                "source_name": article.get("domain"), "author_org": article.get("domain"),
                "language": article.get("language"), "published_at": published,
                "title": article.get("title"), "url": article["url"],
                "sourcecountry": article.get("sourcecountry"),
                "wayback_snapshot_url": snapshot,
                "body_is_public_domain": False,   # links + metadata only
                **classification,
            })
            textlinks.append({
                "textref_uid": ref_uid, "target_uid": episode.episode_uid,
                "link_level": "episode", "link_relation": "describes", "linker": "auto",
                "time_offset_hours": classification["time_offset_hours"],
                "link_evidence": "gdelt_toponym_query",
                # Retrieval by place name is weak evidence on its own; Stage C
                # tightens this with per-article matching, so the confidence
                # stays deliberately modest here.
                "link_confidence": 0.5,
                "query": query,
                "hit_record_cap": capped,
                # An episode whose slices were rate-limited away is *undersampled*,
                # not quiet; anything counting articles per episode must exclude it.
                "failed_slices": failed_slices,
            })

        if i % 10 == 0 or i == len(eligible):
            print(f"  {i}/{len(eligible)} episodes — {stats['articles_relevant']} relevant "
                  f"articles kept of {stats['articles_returned']} returned", end="\r", flush=True)
    print()

    if args.cache_only and stats["uncached_queries"]:
        print(f"\ncache-only: {stats['uncached_queries']:,} queries were never "
              f"fetched and are absent from this rebuild "
              f"({stats['episodes_fully_uncached']:,} episodes have no cached slice "
              "at all). Coverage figures from these tables are a lower bound.")

    refs = pd.DataFrame(textrefs).drop_duplicates(subset="textref_uid")
    links = pd.DataFrame(textlinks).drop_duplicates(subset=["textref_uid", "target_uid"])

    suffix = args.tag + (f"_top{args.limit}" if args.limit else "")
    refs_path = config.PROCESSED_DIR / f"textrefs_news_{suffix}.csv"
    links_path = config.PROCESSED_DIR / f"textlinks_news_{suffix}.csv"
    refs.to_csv(refs_path, index=False)
    links.to_csv(links_path, index=False)

    counts = {
        "episodes_total": len(episodes),
        "episodes_before_gdelt_coverage": int(skipped),
        "episodes_queried": stats["episodes_queried"],
        "episodes_without_toponyms": stats["episodes_without_toponyms"],
        "episodes_hit_record_cap": stats["episodes_hit_record_cap"],
        "failed_queries": stats["failed_queries"],
        "episodes_with_a_failed_slice": stats["episodes_with_a_failed_slice"],
        "episodes_fully_failed": stats["episodes_fully_failed"],
        "cache_only": bool(args.cache_only),
        "uncached_queries": stats["uncached_queries"],
        "episodes_with_an_uncached_slice": stats["episodes_with_an_uncached_slice"],
        "episodes_fully_uncached": stats["episodes_fully_uncached"],
        "window_slices_days": slices,
        "articles_returned": stats["articles_returned"],
        "articles_relevant": stats["articles_relevant"],
        "unique_articles": len(refs),
        "episodes_with_articles": int(links.target_uid.nunique()) if len(links) else 0,
        "by_text_role": refs.text_role.value_counts().to_dict() if len(refs) else {},
        "wayback": {"attempted": stats["wayback_attempted"], "found": stats["wayback_found"]},
        "parameters": {"days_after": args.days_after,
                       "max_records": config.GDELT_MAX_RECORDS,
                       "coverage_start": coverage_start,
                       "tier_rule_version": tiering.TIER_RULE_VERSION},
    }
    write_manifest(config.PROCESSED_DIR / f"manifest_news_{suffix}.json",
                   "21_fetch_gdelt", counts=counts, outputs=[refs_path, links_path])

    print(f"{len(refs)} unique articles across {counts['episodes_with_articles']} episodes")
    print(f"  roles: {counts['by_text_role']}")
    if stats["failed_queries"]:
        total_queries = stats["episodes_queried"] * len(slices)
        print(f"  ⚠ {stats['failed_queries']}/{total_queries} queries FAILED "
              f"({stats['failed_queries'] / max(1, total_queries):.0%}, mostly rate limiting); "
              f"{stats['episodes_fully_failed']} episodes got nothing at all.")
        print(f"    Re-run this script to retry only those — cached responses are skipped.")
    if args.wayback:
        print(f"  wayback: {stats['wayback_found']}/{stats['wayback_attempted']} archived")
    print(f"wrote {refs_path.name}, {links_path.name}")


if __name__ == "__main__":
    main()
