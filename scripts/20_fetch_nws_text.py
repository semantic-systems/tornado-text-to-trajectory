"""Stage 20 — collect NWS text (LSRs and storm-survey PNS) and attach it to hazards.

Produces the two same-org text streams:

* ``official_timely`` — Local Storm Reports, matched to a hazard by distance from
  the track and time within its begin-end. An LSR within reach of several hazards
  is linked to each, and ``is_best_match`` marks the one it is about; counts use
  that one only.
* ``oracle`` — the per-tornado section of a Public Information Statement storm
  survey, matched to a hazard by the coordinates the section itself states.

Both are US-government works, so the text is stored in full. Every link carries
the evidence it rests on (distance, time offset), and the survey section's own
rating / path length are kept beside DAT's, since the two are independent
descriptions of the same survey and their disagreements are worth measuring.

Hazards are stage 15's: DAT hazards and SPC tornadoes without a DAT survey
(their straight SPC line or point), with stage 16's offices and places. Text is
matched on each hazard's time and convective day, which for a DAT hazard whose
clock stage 14 found wrong or missing is its SPC track's
(:func:`episode_table.event_times`).

    python scripts/20_fetch_nws_text.py --cache-only          # what a run would fetch
    python scripts/20_fetch_nws_text.py                       # full window
    python scripts/20_fetch_nws_text.py --tag march2025
    python scripts/20_fetch_nws_text.py --sample-days 30      # cost pilot

``--cache-only`` reads nothing from the network: it builds from the IEM cache,
reports what is missing, and writes its tables with the suffix ``_cacheonly``
unless nothing was missing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
from collections import Counter, defaultdict

import _bootstrap  # noqa: F401

import pandas as pd
from shapely import STRtree
from shapely.geometry import LineString, Point

from tornado_dataset import config
from tornado_dataset.dat import episode_table
from tornado_dataset.dat.geometry import to_equal_area, to_shapely
from tornado_dataset.ids import uid, write_manifest
from tornado_dataset.text import iem, tiering


def load_hazards(tag: str) -> list[dict]:
    """DAT and SPC hazards with projected geometry, matching time and geography."""
    features = []
    for path, stage in ((config.PROCESSED_DIR / f"hazards_{tag}.geojson", "12_build_hazards"),
                        (episode_table.spc_hazards_path(tag, "geojson"), "15_build_episodes")):
        if not path.exists():
            raise SystemExit(f"no {path.name} — run scripts/{stage}.py")
        features += json.loads(path.read_text(encoding="utf-8"))["features"]
    # Times as stage 15 wrote them (episode_table.event_times): the begin, the
    # end where one is known or repaired, the day, and whose they are.
    member = episode_table.membership(tag)
    if "end_utc" not in member.columns:
        raise SystemExit("hazard_episodes has no hazard times — run scripts/15_build_episodes.py")
    times = (member[["hazard_uid", "begin_utc", "end_utc", "convective_day", "time_source"]]
             .set_index("hazard_uid").to_dict("index"))
    source = dict(zip(member.hazard_uid, member.hazard_source))
    episode_of = episode_table.episode_of(tag)
    geography = (episode_table.geography(tag, ("dat", "spc"))
                 .set_index("hazard_uid").to_dict("index"))

    hazards = []
    for feature in features:
        props = feature["properties"]
        geom = to_shapely(feature.get("geometry"))
        if geom is None:
            continue
        time = times.get(props["hazard_uid"])
        if time is None:
            raise SystemExit(f"{props['hazard_uid']} is not in hazard_episodes — "
                             "rerun scripts/15_build_episodes.py")
        info = geography.get(props["hazard_uid"], {})
        # Every office of every source (stage 16); older tables had two columns.
        wfos = {w for col in ("wfo_all", "wfo_dat", "wfo_spatial")
                for w in str(info.get(col) or "").split(";") if w and w != "nan"}
        names = {n.strip() for n in str(info.get("places") or "").split(";") if len(n.strip()) > 3}
        names |= {c.split(",")[0].strip() for c in str(info.get("counties") or "").split(";")
                  if len(c.split(",")[0].strip()) > 3}
        hazards.append({
            "uid": props["hazard_uid"],
            "source": source[props["hazard_uid"]],
            "episode_uid": episode_of.get(props["hazard_uid"]),
            "day": time["convective_day"] if isinstance(time["convective_day"], str) else None,
            "begin": time["begin_utc"] if isinstance(time["begin_utc"], str) else None,
            "end": time["end_utc"] if isinstance(time["end_utc"], str) else None,
            "time_source": time["time_source"],
            "efscale": props.get("efscale"),
            "path_length_mi": props.get("path_length_mi"),
            "fatalities": props.get("fatalities"),
            "wfos": sorted(wfos),
            "names": sorted(names),
            "proj": to_equal_area(geom),
        })
    return hazards


# ── Local Storm Reports ──────────────────────────────────────────────────────
def lsr_interval(hazard: dict) -> tuple[dt.datetime, dt.datetime | None] | None:
    """The time an LSR is held against: the hazard's begin-end, or its
    convective day when it has no time. ``None`` without either."""
    begin = tiering._as_datetime(hazard["begin"])
    if begin:
        return begin, tiering._as_datetime(hazard["end"])
    if not hazard["day"]:
        return None
    start = dt.datetime.fromisoformat(hazard["day"]).replace(
        hour=config.CONVECTIVE_DAY_START_HOUR, tzinfo=dt.timezone.utc)
    return start, start + dt.timedelta(days=1)


def collect_lsrs(hazards: list[dict], *, refresh: bool = False, offline: bool = False,
                 missing: Counter | None = None) -> list[dict]:
    """Match tornado LSRs to hazards by distance from the track and time.

    A hazard's candidates are the LSRs within ``LSR_MATCH_RADIUS_M`` of its track
    whose time lies within ``LSR_TIME_MARGIN_MIN`` of its begin-end (its
    convective day when it has no time). An LSR within reach of several hazards
    is linked to each, and one of them is its best match (:func:`iem.assign_lsr`).
    """
    cache_dir = config.RAW_DIR / "iem" / "lsr"
    margin = dt.timedelta(minutes=config.LSR_TIME_MARGIN_MIN)
    intervals = {h["uid"]: lsr_interval(h) for h in hazards}
    years = sorted({y for iv in intervals.values() if iv
                    for y in range((iv[0] - margin).year, ((iv[1] or iv[0]) + margin).year + 1)})
    by_year: dict[int, list[dict]] = {}
    for year in years:
        rows = iem.fetch_lsr_year(year, cache_dir=cache_dir, refresh=refresh, offline=offline)
        if rows is None:
            if missing is not None:
                missing["lsr_years"] += 1
            print(f"  LSRs {year}: not cached")
            continue
        by_year[year] = rows
        print(f"  LSRs {year}: {len(rows)}")

    prepared = {}
    for year, rows in by_year.items():
        points = [to_equal_area(Point(r["lon"], r["lat"])) for r in rows]
        valid = [tiering._as_datetime(r["valid_utc"]) for r in rows]
        prepared[year] = (rows, points, valid, STRtree(points) if points else None)

    matches = []
    for hazard in hazards:
        interval = intervals[hazard["uid"]]
        if interval is None:
            continue
        begin, end = interval
        last = max(begin, end or begin)
        for year in range((begin - margin).year, (last + margin).year + 1):
            rows, points, valid, tree = prepared.get(year, ([], [], [], None))
            if tree is None:
                continue
            for index in tree.query(hazard["proj"].buffer(config.LSR_MATCH_RADIUS_M)):
                distance = hazard["proj"].distance(points[index])
                if distance > config.LSR_MATCH_RADIUS_M or valid[index] is None:
                    continue
                gap = iem.lsr_time_gap_min(valid[index], begin, end)
                if gap > config.LSR_TIME_MARGIN_MIN:
                    continue
                offset = ((valid[index] - tiering._as_datetime(hazard["begin"])).total_seconds()
                          / 3600 if hazard["begin"] else None)
                matches.append({"hazard": hazard, "row": rows[index], "lsr": (year, index),
                                "distance_m": round(distance, 1), "gap_min": round(gap, 1),
                                "offset_hours": None if offset is None else round(offset, 2)})

    # One best match per LSR, among every hazard it is within reach of.
    proj = {h["uid"]: h["proj"] for h in hazards}
    by_lsr: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for match in matches:
        by_lsr[match["lsr"]].append(match)
    for group in by_lsr.values():
        best, basis = iem.assign_lsr(
            [{"uid": m["hazard"]["uid"], "distance_m": m["distance_m"], "gap_min": m["gap_min"]}
             for m in group],
            lambda a, b: proj[a].distance(proj[b]))
        for match in group:
            match.update(is_best_match=match["hazard"]["uid"] == best,
                         lsr_candidates=len(group), lsr_assignment=basis)
    return matches


# ── storm-survey PNS ─────────────────────────────────────────────────────────
def collect_pns(hazards: list[dict], *, window_days: int, refresh: bool = False,
                verbose: bool = True, offline: bool = False,
                missing: Counter | None = None) -> tuple[list[dict], dict]:
    """Find storm-survey sections and match them to hazards by coordinates."""
    list_cache = config.RAW_DIR / "iem" / "pns_lists"
    text_cache = config.RAW_DIR / "iem" / "products"

    hazards_by_day: dict[str, list[dict]] = defaultdict(list)
    for hazard in hazards:
        if hazard["day"]:
            hazards_by_day[hazard["day"]].append(hazard)

    # Which (date, WFO) combinations could hold a survey for one of our hazards?
    wanted: dict[dt.date, set[str]] = defaultdict(set)
    for day, group in hazards_by_day.items():
        day_date = dt.date.fromisoformat(day)
        offices = {w for hazard in group for w in hazard["wfos"]}
        for offset in range(window_days + 1):
            wanted[day_date + dt.timedelta(days=offset)] |= offices

    stats = Counter()
    stats["dates_listed"] = len(wanted)
    matches, seen_products = [], set()

    for i, (date, offices) in enumerate(sorted(wanted.items()), 1):
        products = iem.list_pns_products(date, cache_dir=list_cache, refresh=refresh,
                                         offline=offline)
        if products is None:
            if missing is not None:
                missing["pns_lists"] += 1
            continue
        stats["products_listed"] += len(products)
        for product in products:
            product_id = product.get("product_id")
            if not product_id or product_id in seen_products:
                continue
            if iem.product_wfo(product_id) not in offices:
                continue
            seen_products.add(product_id)
            text = iem.fetch_product_text(product_id, cache_dir=text_cache, refresh=refresh,
                                          offline=offline)
            if text is None:
                if missing is not None:
                    missing["pns_products"] += 1
                continue
            stats["products_downloaded"] += 1
            if not text:
                continue
            verdict = iem.classify_pns(text)
            if not verdict["is_tornado_survey"]:
                stats["not_a_tornado_survey"] += 1
                continue
            stats["tornado_surveys"] += 1
            issued = iem.parse_product_time(product_id)
            segments = iem.parse_survey_segments(text)
            if segments:
                stats["structured_surveys"] += 1
                for segment in segments:
                    stats["survey_segments"] += 1
                    for la, lo in (("start_lat", "start_lon"), ("end_lat", "end_lon")):
                        if segment[la] is not None and segment[lo] is not None:
                            point = iem.stated_point(segment[la], segment[lo])
                            stats["endpoints_sign_restored"] += bool(
                                point and point[1] != segment[lo])
                            stats["endpoints_unusable"] += point is None
                    matched = match_segment(segment, hazards_by_day, date)
                    stats["segments_matched"] += bool(matched)
                    for hazard, distance, is_best in matched:
                        matches.append({
                            "hazard": hazard, "segment": segment, "product_id": product_id,
                            "wfo": iem.product_wfo(product_id),
                            "issued": issued, "distance_m": round(distance, 1),
                            "is_best_match": is_best, "survey_format": "structured",
                            "matched_name": None,
                        })
                continue

            # Legacy free-text survey: no sections, no coordinates. Matched by
            # office and date *and* a place name from the hazard appearing in the
            # product, so the link rests on stated evidence rather than on the
            # office having surveyed something that week.
            stats["legacy_surveys"] += 1
            attributes = iem.parse_legacy_survey(text)
            upper = text.upper()
            for offset in range(window_days + 1):
                day = (date - dt.timedelta(days=offset)).isoformat()
                for hazard in hazards_by_day.get(day, []):
                    if iem.product_wfo(product_id) not in hazard["wfos"]:
                        continue
                    # Two independent name hits, not one. A single common
                    # toponym ("Madison", "Central") matches products about
                    # entirely different tornadoes the same office surveyed that
                    # week; requiring corroboration cuts those loose.
                    hits = [n for n in hazard["names"] if n.upper() in upper]
                    if len(hits) < config.PNS_LEGACY_MIN_NAME_HITS:
                        stats["legacy_rejected_weak_names"] += 1
                        continue
                    hit = "+".join(hits[:3])
                    stats["legacy_matched"] += 1
                    matches.append({
                        "hazard": hazard, "product_id": product_id,
                        "wfo": iem.product_wfo(product_id), "issued": issued,
                        "distance_m": None, "is_best_match": False,
                        "survey_format": "legacy_unstructured", "matched_name": hit,
                        "segment": {"title": f"{hit} storm survey (legacy format)",
                                    "text": text, "summary": "",
                                    "ef_rating": attributes["ef_rating"],
                                    "path_length_mi": attributes["path_length_mi"],
                                    "path_width_yd": None, "fatalities": None,
                                    "start_location": None, "end_location": None},
                    })
        if verbose and i % 50 == 0:
            print(f"  PNS dates {i}/{len(wanted)} — {stats['products_downloaded']} products, "
                  f"{stats['tornado_surveys']} surveys, {len(matches)} segment links",
                  end="\r", flush=True)
    if verbose:
        print(f"  PNS dates {len(wanted)}/{len(wanted)} — {stats['products_downloaded']} products, "
              f"{stats['tornado_surveys']} surveys, {len(matches)} segment links")
    return matches, dict(stats)


def match_segment(segment: dict, hazards_by_day: dict[str, list[dict]],
                  issue_date: dt.date) -> list[tuple[dict, float, bool]]:
    """Hazards a survey section describes, by its own start/end coordinates.

    A section states where the tornado began and ended, so matching is geometric
    rather than name-based. DAT sometimes draws as one line what the survey
    splits into several sections (and vice versa), so all hazards within the
    tolerance are returned with their distance and the closest flagged.
    """
    start = iem.stated_point(segment["start_lat"], segment["start_lon"])
    if start is None:
        return []
    points = [start]
    end = iem.stated_point(segment["end_lat"], segment["end_lon"])
    if end is not None:
        points.append(end)
    # Both endpoints must sit near the track, not just the segment as a whole.
    # DAT sometimes draws one 80-mile line where the survey lists several
    # tornadoes, and a neighbouring tornado's path crosses such a line at zero
    # distance — measuring the connecting line would match it as if it were the
    # same storm. Requiring both ends near the track rules that out.
    projected_points = [to_equal_area(Point(lon, lat)) for lat, lon in points]

    # The section's own start date is authoritative; fall back to a window before
    # the issue date, since a survey is always published after the event.
    days = []
    if segment.get("start_date"):
        try:
            stamp = dt.datetime.strptime(segment["start_date"].strip(), "%m/%d/%Y").date()
            days = [stamp, stamp - dt.timedelta(days=1)]
        except ValueError:
            days = []
    if not days:
        days = [issue_date - dt.timedelta(days=offset)
                for offset in range(config.PNS_SURVEY_WINDOW_DAYS + 1)]

    candidates = []
    for day in days:
        for hazard in hazards_by_day.get(day.isoformat(), []):
            distance = max(point.distance(hazard["proj"]) for point in projected_points)
            if distance <= config.PNS_MATCH_RADIUS_M:
                candidates.append((hazard, distance))
    if not candidates:
        return []
    best = min(candidates, key=lambda c: c[1])[0]["uid"]
    return [(hazard, distance, hazard["uid"] == best) for hazard, distance in candidates]


# ── assembly ─────────────────────────────────────────────────────────────────
def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--window-days", type=int, default=config.PNS_SURVEY_WINDOW_DAYS)
    parser.add_argument("--sample-days", type=int, default=None,
                        help="restrict to N randomly sampled convective days (cost pilot)")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--skip-pns", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--cache-only", action="store_true",
                        help="no network: build from the IEM cache and report what is missing")
    args = parser.parse_args()
    if args.cache_only and args.refresh:
        parser.error("--cache-only and --refresh exclude each other")
    missing: Counter = Counter()

    hazards = load_hazards(args.tag)
    if args.sample_days:
        days = sorted({h["day"] for h in hazards if h["day"]})
        random.Random(args.seed).shuffle(days)
        keep = set(days[:args.sample_days])
        hazards = [h for h in hazards if h["day"] in keep]
        print(f"pilot: {len(keep)} convective days, {len(hazards)} hazards")
    print(f"{len(hazards)} hazards with usable geometry: "
          f"{dict(Counter(h['source'] for h in hazards))}; matched on the time of "
          f"{dict(Counter(h['time_source'] for h in hazards))}")

    print("\nLocal Storm Reports")
    lsr_matches = collect_lsrs(hazards, refresh=args.refresh, offline=args.cache_only,
                               missing=missing)
    print(f"  {len(lsr_matches)} LSR-hazard matches")

    pns_matches, pns_stats = ([], {})
    if not args.skip_pns:
        print("\nStorm-survey PNS")
        pns_matches, pns_stats = collect_pns(hazards, window_days=args.window_days,
                                             refresh=args.refresh, offline=args.cache_only,
                                             missing=missing)

    # The survey time per hazard is what makes temporal_class meaningful: it is
    # the moment after which any text is downstream of the survey. The *first*
    # survey publication is the boundary, even if later revisions follow.
    survey_time: dict[str, dt.datetime] = {}
    for match in pns_matches:
        if match["issued"] is None:
            continue
        current = survey_time.get(match["hazard"]["uid"])
        if current is None or match["issued"] < current:
            survey_time[match["hazard"]["uid"]] = match["issued"]

    # Offices re-issue a survey as it is refined, so one tornado can appear in
    # several products with changing ratings and path lengths. All versions are
    # kept — the revision history is data — but the latest is flagged, since an
    # experiment wanting "the" oracle text needs the definitive one.
    latest_issue: dict[tuple[str, str], dt.datetime] = {}
    for match in pns_matches:
        key = (match["hazard"]["uid"], match["segment"]["title"].strip().lower())
        if match["issued"] and (key not in latest_issue or match["issued"] > latest_issue[key]):
            latest_issue[key] = match["issued"]

    # Which section is *the* survey of this hazard, as opposed to a section about
    # a neighbouring tornado that happens to pass the distance test? Decided on
    # geometry plus agreement with DAT's own path length — two independent
    # descriptions of the same tornado should agree on how long it was.
    best_per_hazard: dict[str, tuple[float, float, str]] = {}
    for match in pns_matches:
        hazard, segment = match["hazard"], match["segment"]
        # A legacy product matched only by office, date and place name is weaker
        # evidence than a section whose stated coordinates land on the track, so
        # it starts from a lower base and can be outranked by any structured match.
        score = (1 - min(1.0, match["distance_m"] / config.PNS_MATCH_RADIUS_M)
                 if match["distance_m"] is not None else 0.4)
        dat_length, survey_length = hazard.get("path_length_mi"), segment.get("path_length_mi")
        if dat_length and survey_length:
            agreement = 1 - abs(survey_length - dat_length) / max(survey_length, dat_length)
            score = 0.6 * score + 0.4 * agreement
        # Revisions of the same section score identically, so ties go to the most
        # recent issue — the survey as the office finally left it.
        issued = match["issued"].timestamp() if match["issued"] else 0.0
        ref_key = uid("textref", "pns", match["product_id"], segment["title"])
        current = best_per_hazard.get(hazard["uid"])
        # Scores are compared at 0.1% granularity: a revision that changes a path
        # length from 81.80 to 81.77 miles is not evidence of a better match, so
        # recency should decide instead of that rounding noise.
        if current is None or (round(score, 3), issued) > (round(current[0], 3), current[1]):
            best_per_hazard[hazard["uid"]] = (score, issued, ref_key)

    textrefs, textlinks = [], []

    for match in lsr_matches:
        hazard, row = match["hazard"], match["row"]
        ref_uid = uid("textref", "lsr", row["valid_utc"], row["lat"], row["lon"],
                      row["typetext"], row["remark"][:60])
        classification = tiering.derive(
            author_org=f"NWS {row['wfo']}", source_type="lsr",
            published_at=row["valid_utc"], event_begin=hazard["begin"],
            survey_at=survey_time.get(hazard["uid"]))
        textrefs.append({
            "textref_uid": ref_uid, "source_type": "lsr",
            "source_name": f"NWS Local Storm Report ({row['wfo']})",
            "author_org": f"NWS {row['wfo']}", "language": "en",
            "published_at": row["valid_utc"],
            "title": f"{row['typetext']} — {row['city']}, {row['county']} County, {row['state']}",
            "body": row["remark"], "body_is_public_domain": True,
            "url": None, "lat": row["lat"], "lon": row["lon"],
            "lsr_source": row["source"], **classification,
        })
        textlinks.append({
            "textref_uid": ref_uid, "target_uid": hazard["uid"], "link_level": "hazard",
            "link_relation": "describes", "linker": "auto",
            "distance_m": match["distance_m"], "time_offset_hours": match["offset_hours"],
            "link_evidence": "lsr_point_within_radius_and_window",
            "link_confidence": round(max(0.0, 1 - match["distance_m"] / config.LSR_MATCH_RADIUS_M), 3),
            "is_best_match": match["is_best_match"], "lsr_candidates": match["lsr_candidates"],
            "lsr_assignment": match["lsr_assignment"], "lsr_time_gap_min": match["gap_min"],
        })

    for match in pns_matches:
        hazard, segment = match["hazard"], match["segment"]
        ref_uid = uid("textref", "pns", match["product_id"], segment["title"])
        published = match["issued"].isoformat() if match["issued"] else None
        classification = tiering.derive(
            author_org=f"NWS {match['wfo']}", source_type="pns",
            published_at=published, event_begin=hazard["begin"],
            survey_at=survey_time.get(hazard["uid"]))
        textrefs.append({
            "textref_uid": ref_uid, "source_type": "pns",
            "source_name": f"NWS Public Information Statement ({match['wfo']})",
            "author_org": f"NWS {match['wfo']}", "language": "en",
            "published_at": published,
            "title": segment["title"], "body": segment["text"],
            "body_is_public_domain": True,
            "url": f"{config.IEM_BASE}/p.php?pid={match['product_id']}",
            "product_id": match["product_id"],
            # The survey's own numbers, kept so they can be compared with DAT's.
            "survey_ef_rating": segment["ef_rating"],
            "survey_path_length_mi": segment["path_length_mi"],
            "survey_path_width_yd": segment["path_width_yd"],
            "survey_fatalities": segment["fatalities"],
            "survey_start_location": segment["start_location"],
            "survey_end_location": segment["end_location"],
            "survey_format": match["survey_format"],
            **classification,
        })
        key = (hazard["uid"], segment["title"].strip().lower())
        # Only the best-scoring section is this hazard's survey; the others are
        # sections about nearby tornadoes and are recorded as mentions, so the
        # oracle text of a hazard is never another tornado's write-up.
        #
        # Legacy free-text products can never be primary. Measured on the April
        # 2011 outbreak, their rating agreed with DAT on 40% of links against 97%
        # for coordinate-matched sections: office+date+place-name cannot pick the
        # right tornado out of a product covering dozens. The text is kept and
        # linked as a mention — it is genuine survey prose about that outbreak —
        # but calling it this hazard's oracle would overstate what we know.
        is_primary = (match["survey_format"] == "structured"
                      and best_per_hazard.get(hazard["uid"], (0, 0, None))[2] == ref_uid)
        textlinks.append({
            "textref_uid": ref_uid, "target_uid": hazard["uid"], "link_level": "hazard",
            "link_relation": "primary_survey_of" if is_primary else "mentions",
            "linker": "auto",
            "distance_m": match["distance_m"], "time_offset_hours": classification["time_offset_hours"],
            "link_evidence": ("survey_segment_endpoints_near_track"
                              if match["distance_m"] is not None
                              else f"legacy_pns_wfo_date_placename:{match['matched_name']}"),
            "is_best_match": match["is_best_match"],
            "is_latest_survey": bool(match["issued"] and latest_issue.get(key) == match["issued"]),
            "link_confidence": (round(max(0.0, 1 - match["distance_m"] / config.PNS_MATCH_RADIUS_M), 3)
                                if match["distance_m"] is not None else 0.4),
        })

    refs = pd.DataFrame(textrefs).drop_duplicates(subset="textref_uid")
    links = pd.DataFrame(textlinks).drop_duplicates(subset=["textref_uid", "target_uid"])

    suffix = f"{args.tag}" + (f"_pilot{args.sample_days}" if args.sample_days else "")
    if args.cache_only and missing:
        suffix += "_cacheonly"      # incomplete: never overwrite the real tables
    refs_path = config.PROCESSED_DIR / f"textrefs_nws_{suffix}.csv"
    links_path = config.PROCESSED_DIR / f"textlinks_nws_{suffix}.csv"
    refs.to_csv(refs_path, index=False)
    links.to_csv(links_path, index=False)

    source_of = {h["uid"]: h["source"] for h in hazards}

    def per_source(uids) -> dict[str, int]:
        return dict(Counter(source_of.get(u, "unknown") for u in set(uids)))

    # "Has oracle text" means a survey section identified as *this* tornado's,
    # not merely any survey product that mentioned the area.
    primary = set(links.target_uid[links.link_relation == "primary_survey_of"]) if len(links) else set()
    mentioned = set(links.target_uid[links.link_relation == "mentions"]) if len(links) else set()
    lsr_links = (links[(links.link_relation == "describes") & (links.is_best_match == True)]  # noqa: E712
                 if len(links) else pd.DataFrame(columns=["target_uid", "textref_uid"]))
    with_lsr = set(lsr_links.target_uid)
    counts = {
        "hazards_considered": len(hazards),
        "hazards_by_source": dict(Counter(h["source"] for h in hazards)),
        "matched_on_time_of": dict(Counter(h["time_source"] for h in hazards)),
        "textrefs": len(refs),
        "textlinks": len(links),
        "by_source_type": refs.source_type.value_counts().to_dict() if len(refs) else {},
        "by_text_role": refs.text_role.value_counts().to_dict() if len(refs) else {},
        "hazards_with_any_nws_text": per_source(
            (set(links.target_uid[links.link_relation != "describes"]) | with_lsr)
            if len(links) else []),
        "hazards_with_lsr": per_source(with_lsr),
        "lsrs_by_assignment": (lsr_links.lsr_assignment.value_counts().to_dict()
                               if len(lsr_links) else {}),
        "lsr_links_not_best": int(((links.link_relation == "describes")
                                   & (links.is_best_match != True)).sum())  # noqa: E712
                              if len(links) else 0,
        "hazards_with_oracle_survey": per_source(primary),
        "hazards_with_survey_mention_only": per_source(mentioned - primary),
        "by_survey_format": (refs[refs.source_type == "pns"].survey_format.value_counts().to_dict()
                             if len(refs) and "survey_format" in refs else {}),
        "pns": pns_stats,
        "not_cached": dict(missing) if args.cache_only else None,
        "parameters": {"window_days": args.window_days,
                       "lsr_radius_m": config.LSR_MATCH_RADIUS_M,
                       "lsr_time_margin_min": config.LSR_TIME_MARGIN_MIN,
                       "lsr_near_factor": config.LSR_NEAR_FACTOR,
                       "lsr_near_floor_m": config.LSR_NEAR_FLOOR_M,
                       "lsr_touch_m": config.LSR_TOUCH_M,
                       "pns_radius_m": config.PNS_MATCH_RADIUS_M,
                       "tier_rule_version": tiering.TIER_RULE_VERSION},
    }
    write_manifest(config.PROCESSED_DIR / f"manifest_nws_text_{suffix}.json",
                   "20_fetch_nws_text", counts=counts, outputs=[refs_path, links_path])

    print(f"\n{len(refs)} text references, {len(links)} links")
    print(f"  by role: {counts['by_text_role']}")
    print(f"  hazards with any NWS text: {counts['hazards_with_any_nws_text']}")
    print(f"  hazards with an oracle survey section: {counts['hazards_with_oracle_survey']}")
    print(f"wrote {refs_path.name}, {links_path.name}")
    if args.cache_only:
        if missing:
            print(f"\nnot cached, so left out: {dict(missing)}. A run without --cache-only "
                  "fetches them (about 0.5 s each); the PNS products of uncached lists are "
                  "only known once the lists are fetched.")
        else:
            print("\neverything was cached: the tables are complete.")


if __name__ == "__main__":
    main()
