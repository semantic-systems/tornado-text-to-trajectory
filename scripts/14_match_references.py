#!/usr/bin/env python
"""Stage 14 — NCEI Storm Events and SPC tornadoes: download, match to DAT, report.

Storm Events is the NWS's own tornado record, filed by each forecast office as
*Storm Data*. It is used here as a reference for DAT — how complete DAT is in
each year, and how forecasters grouped tornadoes into episodes — and its
``EVENT_ID``/``EPISODE_ID`` become external keys on our hazards. See
:mod:`tornado_dataset.dat.storm_events` for the three properties that shape
every use of it (county segments, local standard time, per-office episodes).

SPC's tornado database is fetched and matched alongside: one reviewed record per
whole track (:mod:`tornado_dataset.dat.spc_tornadoes`). It is the tornado-level
reference — completeness of DAT counted in tornadoes — and the check on how
well Storm Events' county segments were chained into tornadoes.

    python scripts/14_match_references.py fetch          # ~16 Storm Events files + 1 SPC file
    python scripts/14_match_references.py join           # match rows to DAT hazards
    python scripts/14_match_references.py report         # coverage per year
    python scripts/14_match_references.py run            # all three

``fetch`` needs the network (ncei.noaa.gov, spc.noaa.gov) and skips files
already present; ``join`` and ``report`` are offline. ``--from-dir`` and
``--spc-file`` point ``join`` at files elsewhere, e.g. ones downloaded by hand.
Without an SPC file, ``join`` and ``report`` do the Storm Events part only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401

import pandas as pd
from pyproj import Transformer
from shapely.ops import transform

from tornado_dataset import config
from tornado_dataset.dat import episodes as ep
from tornado_dataset.dat import spc_tornadoes as spc
from tornado_dataset.dat import storm_events as se
from tornado_dataset.dat.evaluate import wilson_interval
from tornado_dataset.http import utcnow_iso
from tornado_dataset.ids import write_manifest

RAW = config.RAW_DIR / "storm_events"
TORNADOES = config.INTERIM_DIR / "storm_events_tornadoes.csv"
REPORT = config.OUTPUT_DIR / "storm_events_report.md"
RAW_SPC = config.RAW_DIR / "spc"
SPC_TORNADOES = config.INTERIM_DIR / "spc_tornadoes.csv"


def links_path(tag: str) -> Path:
    return config.PROCESSED_DIR / f"storm_events_links_{tag}.csv"


def spc_links_path(tag: str) -> Path:
    return config.PROCESSED_DIR / f"spc_tornado_links_{tag}.csv"


def spc_se_links_path(tag: str) -> Path:
    return config.PROCESSED_DIR / f"spc_storm_events_links_{tag}.csv"


def spc_unmatched_path(tag: str) -> Path:
    return config.INTERIM_DIR / f"spc_unmatched_dat_{tag}.csv"


def crosscheck_path(tag: str) -> Path:
    return config.INTERIM_DIR / f"spc_chain_crosscheck_{tag}.json"


def years() -> list[int]:
    return list(range(config.WINDOW_START.year, config.WINDOW_END.year + 1))


def cmd_fetch(args) -> None:
    records = se.download(years(), RAW)
    for r in records:
        print(f"  {r['year']}  {r['status']:<14} {r.get('file') or ''}")
    log = RAW / "provenance.jsonl"
    with log.open("a", encoding="utf-8") as fh:
        for r in records:
            if r["status"] == "downloaded":
                fh.write(json.dumps(r) + "\n")
    missing = [r["year"] for r in records if r["status"] == "not_published"]
    if missing:
        print(f"\nnot yet published by NCEI: {missing} — the database lags by months.")
    record = spc.download(RAW_SPC)
    print(f"  SPC   {record['status']:<14} {record.get('file') or ''}")
    if record["status"] == "downloaded":
        with (RAW_SPC / "provenance.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")


def load_tornadoes(args) -> pd.DataFrame:
    directory = Path(args.from_dir).expanduser() if args.from_dir else RAW
    paths = se.details_paths(directory)
    wanted = [paths[y] for y in years() if y in paths]
    if not wanted:
        raise SystemExit(f"no StormEvents_details-*.csv.gz in {directory} — run `fetch`")
    absent = [y for y in years() if y not in paths]
    print(f"details files: {len(wanted)} years from {directory}"
          + (f" (missing {absent})" if absent else ""))
    return se.load_tornadoes(wanted)


def cmd_join(args) -> None:
    tornadoes = load_tornadoes(args)
    print(f"Storm Events tornado rows: {len(tornadoes):,} -> "
          f"{tornadoes.TORNADO_KEY.nunique():,} tornadoes after chaining county segments; "
          f"{tornadoes.EPISODE_ID.nunique():,} episodes -> "
          f"{tornadoes.LINKED_EPISODE.nunique():,} linked")
    frame = ep.load_hazard_frame(args.tag)
    hazards = frame.assign(geom=frame.track)
    to_m = Transformer.from_crs(config.CRS_WGS84, config.CRS_EQUAL_AREA, always_xy=True)
    geoms = se.row_geometries(tornadoes, lambda g: transform(to_m.transform, g))
    links = se.join_hazards(tornadoes, geoms, hazards,
                            max_distance_m=args.max_distance_m, max_gap_s=args.max_gap_s)

    config.INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    tornadoes.to_csv(TORNADOES, index=False)
    out = links_path(args.tag)
    out.parent.mkdir(parents=True, exist_ok=True)
    links.to_csv(out, index=False)
    rows, hz = links.EVENT_ID.nunique(), links.hazard_uid.nunique()
    print(f"matched: {rows:,}/{len(tornadoes):,} Storm Events rows, "
          f"{hz:,}/{len(hazards):,} DAT hazards "
          f"(≤{args.max_distance_m/1000:g} km, ≤{args.max_gap_s/60:g} min)")
    write_manifest(config.PROCESSED_DIR / f"manifest_storm_events_{args.tag}.json",
                   "14_match_references", counts={
                       "se_tornado_rows": len(tornadoes),
                       "se_tornadoes": int(tornadoes.TORNADO_KEY.nunique()),
                       "se_episodes": int(tornadoes.EPISODE_ID.nunique()),
                       "se_linked_episodes": int(tornadoes.LINKED_EPISODE.nunique()),
                       "se_rows_matched": rows, "dat_hazards": len(hazards),
                       "dat_hazards_matched": hz,
                       "max_distance_m": args.max_distance_m, "max_gap_s": args.max_gap_s},
                   outputs=[TORNADOES, out])
    print(f"wrote {TORNADOES}\nwrote {out}")
    join_spc(args, tornadoes, geoms, hazards, project=lambda g: transform(to_m.transform, g))


def join_spc(args, se_rows, se_geoms, hazards, project) -> None:
    """SPC whole tracks against DAT, and against the Storm Events chains."""
    path = Path(args.spc_file).expanduser() if args.spc_file else spc.local_file(RAW_SPC)
    if path is None or not path.exists():
        print("\nno SPC actual_tornadoes file — skipping the SPC part (run `fetch`)")
        return
    tracks, notes = spc.load(path, years())
    print(f"\nSPC {path.name}: {notes['kept']:,} whole tracks in the window "
          f"(dropped: {notes['dropped_not_whole_track']:,} non-whole-track, "
          f"{notes['dropped_unknown_tz']:,} unknown time zone)")
    geoms = spc.track_geometries(tracks, project)
    links = spc.join_hazards(tracks, geoms, hazards, max_distance_m=args.max_distance_m,
                             max_gap_s=args.max_gap_s)
    strict_hz = links.hazard_uid.nunique()
    links = spc.with_first_pass_columns(links, tracks, hazards)
    repair = {"enabled": not args.no_time_repair,
              "ef_chance": spc.chance_ef_agreement(tracks, hazards)}
    if not args.no_time_repair:
        repaired, stats = spc.repair_time_links(
            tracks, geoms, hazards, links, max_distance_m=args.max_distance_m,
            max_offset_h=args.repair_max_offset_h,
            max_residual_min=args.repair_max_residual_min)
        links = pd.concat([links, repaired], ignore_index=True)
        repair |= stats
        print(f"time-repaired pass: {repaired.hazard_uid.nunique():,} more DAT hazards "
              f"(whole-hour offsets 1–{args.repair_max_offset_h} h, ±"
              f"{args.repair_max_residual_min:g} min, ≤{args.max_distance_m/1000:g} km)")
    links["id_date"] = spc.event_id_date_check(links, tracks, hazards)
    unmatched = spc.nearest_unlinked(tracks, geoms, hazards, links)
    se_links = spc.join_storm_events(se_rows, se_geoms, tracks, geoms,
                                     max_distance_m=args.max_distance_m,
                                     max_gap_s=args.max_gap_s)
    check = spc.crosscheck_chains(se_links, se_rows)
    tracks.to_csv(SPC_TORNADOES, index=False)
    links.to_csv(spc_links_path(args.tag), index=False)
    se_links.to_csv(spc_se_links_path(args.tag), index=False)
    unmatched.to_csv(spc_unmatched_path(args.tag), index=False)
    crosscheck_path(args.tag).write_text(json.dumps(
        {**notes, **check, "time_repair": repair}, indent=2, default=float))
    print(f"matched: {links.spc_id.nunique():,}/{len(tracks):,} SPC tornadoes, "
          f"{links.hazard_uid.nunique():,}/{len(hazards):,} DAT hazards "
          f"({strict_hz:,} by the strict rule)")
    print(f"Storm Events chains agreeing 1:1 with an SPC track: "
          f"{check['chains_one_to_one']:,}/{check['se_chains_matched']:,} "
          f"({check['share_one_to_one']:.1%}); split over several SPC tracks "
          f"{check['chains_split_over_spc']:,}; SPC tracks with several chains "
          f"{check['spc_with_several_chains']:,}")
    print(f"wrote {SPC_TORNADOES}\nwrote {spc_links_path(args.tag)}\n"
          f"wrote {spc_se_links_path(args.tag)}\nwrote {crosscheck_path(args.tag)}\n"
          f"wrote {spc_unmatched_path(args.tag)}")


def cmd_report(args) -> None:
    if not TORNADOES.exists() or not links_path(args.tag).exists():
        raise SystemExit("run `join` first")
    tornadoes = pd.read_csv(TORNADOES, low_memory=False)
    tornadoes["begin_utc"] = pd.to_datetime(tornadoes.begin_utc, utc=True)
    links = pd.read_csv(links_path(args.tag))
    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{args.tag}.csv", low_memory=False)
    hazards["t0"] = pd.to_datetime(hazards.time_begin_utc, utc=True, errors="coerce")
    cov = se.coverage_by_year(tornadoes, hazards, links)

    def ci(k, n):
        if not n:
            return "—"
        lo, hi = wilson_interval(int(k), int(n))
        return f"{k/n:.0%} [{lo:.0%}, {hi:.0%}]"

    best = links[links.rank_for_hazard == 1]
    per_ep_wfo = tornadoes.groupby("EPISODE_ID").WFO.nunique().max()
    linked_wfo = tornadoes.groupby("LINKED_EPISODE").WFO.nunique()
    pointers = int(tornadoes.TOR_OTHER_WFO.notna().sum())
    cross = int((tornadoes.TOR_OTHER_WFO.notna()
                 & (tornadoes.TOR_OTHER_WFO != tornadoes.WFO)).sum())
    lines = [
        "# NCEI Storm Events against DAT — Stage 14", "",
        f"Generated {utcnow_iso()}. Storm Events rows matched to DAT hazards when "
        "within the `join` tolerances (default "
        f"{se.MATCH_DISTANCE_M/1000:g} km and {se.MATCH_GAP_S/60:g} min, in UTC converted "
        "from Storm Data's local standard time).",
        "",
        "> Storm Events has one row per tornado **per county**. Rows are chained into "
        "whole tornadoes through their `TOR_OTHER_*` pointers (`TORNADO_KEY`), and the "
        "tornado counts below are what compare with DAT hazards; the row counts are "
        "county segments.", "",
        "## Coverage by year", "",
        "| year | SE rows | SE tornadoes | DAT hazards | SE tornadoes found in DAT | "
        "DAT hazards found in SE |", "|---|---:|---:|---:|---|---|",
    ]
    for r in cov.itertuples():
        lines.append(f"| {r.year} | {r.se_rows:,} | {int(r.se_tornadoes or 0):,} | "
                     f"{r.dat_hazards:,} | "
                     f"{ci(r.se_tornadoes_matched, int(r.se_tornadoes or 0))} | "
                     f"{ci(r.dat_hazards_matched, r.dat_hazards)} |")
    lines += [
        "", "The fifth column is **DAT completeness**: the share of officially "
        "recorded tornadoes that have a DAT survey. DAT was adopted unevenly "
        "by the offices, so it is low in the early years; every figure built on DAT "
        "geometry inherits that.",
        "The sixth is the share of DAT hazards with an official record. A DAT hazard "
        "without one is usually a timing or location disagreement beyond the "
        "tolerances, occasionally a survey Storm Data never received.", "",
        "## Episodes", "",
        f"- {tornadoes.EPISODE_ID.nunique():,} Storm Events episodes hold tornadoes; "
        f"the most offices any one spans is **{per_ep_wfo}**. Episodes are filed per "
        "office, so a multi-state outbreak is many episodes.",
        f"- **Linked episodes.** {pointers:,} rows point to a continuation county, "
        f"{cross:,} of them in another office. Joining episodes that share a tornado "
        f"turns {tornadoes.EPISODE_ID.nunique():,} episodes into "
        f"{tornadoes.LINKED_EPISODE.nunique():,} (`LINKED_EPISODE`), "
        f"{int((linked_wfo > 1).sum()):,} of which span more than one office (at most "
        f"{int(linked_wfo.max())}). Offices whose parts of an outbreak share no "
        "crossing tornado stay separate, so large outbreaks remain several episodes.",
        f"- {best.EPISODE_ID.nunique():,} episodes are matched to at least one DAT "
        "hazard; `scripts/51_compare_episodes.py` scores grouping methods against both "
        "`EPISODE_ID` and `LINKED_EPISODE`.", "",
    ] + spc_section(args, hazards, ci) + [
        "## Notes", "",
        "- NCEI revises each year's file in place and publishes the current year with "
        "a lag of months; `fetch` always takes the newest revision.",
        "- `EVENT_ID` and `EPISODE_ID` are joined to hazards by space and time, not by "
        "key: DAT's own `event_id` is free text and does not reliably equal either.",
        "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(cov.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(f"\nwrote {REPORT}")


def spc_section(args, hazards: pd.DataFrame, ci) -> list[str]:
    """Report lines for the SPC comparison; empty when it was not run."""
    if not SPC_TORNADOES.exists() or not spc_links_path(args.tag).exists():
        return []
    tracks = pd.read_csv(SPC_TORNADOES, low_memory=False)
    links = pd.read_csv(spc_links_path(args.tag))
    check = json.loads(crosscheck_path(args.tag).read_text()) \
        if crosscheck_path(args.tag).exists() else {}
    hz_year = hazards.t0.dt.year
    method = links.get("link_method", pd.Series("spatial_temporal_join", index=links.index))
    strict = links[method == "spatial_temporal_join"]
    lines = ["## SPC whole tracks", "",
             "SPC's database holds one reviewed record per tornado — the official "
             "version of the chaining above. Same matching rule; the last column adds "
             "the time-repaired second pass (next section).", "",
             "| year | SPC tornadoes | DAT hazards | SPC tornadoes found in DAT | "
             "DAT hazards found in SPC | … with time repair |", "|---|---:|---:|---|---|---|"]
    found_spc, found_hz = set(strict.spc_id), set(strict.hazard_uid)
    found_all = set(links.hazard_uid)
    for y in sorted(tracks.yr.unique()):
        t = tracks[tracks.yr == y]
        h = hazards[hz_year == y]
        k1 = int(t.spc_id.isin(found_spc).sum())
        k2 = int(h.hazard_uid.isin(found_hz).sum())
        k3 = int(h.hazard_uid.isin(found_all).sum())
        lines.append(f"| {y} | {len(t):,} | {len(h):,} | {ci(k1, len(t))} | "
                     f"{ci(k2, len(h))} | {ci(k3, len(h))} |")
    if check:
        lines += ["", f"- **Chaining check.** Of {check['se_chains_matched']:,} Storm "
                  "Events tornadoes (chained county segments) matched to an SPC track, "
                  f"**{check['share_one_to_one']:.1%}** correspond one-to-one. "
                  f"{check['chains_split_over_spc']:,} chains spread over several SPC "
                  "tracks (over-chained, or SPC keeps them apart); "
                  f"{check['spc_with_several_chains']:,} SPC tracks hold several chains "
                  "(a `TOR_OTHER_*` pointer that did not resolve).",
                  f"- Records dropped on loading: {check.get('dropped_not_whole_track', 0):,} "
                  f"not whole-track, {check.get('dropped_unknown_tz', 0):,} with an unknown "
                  "time zone."]
    return lines + [""] + repair_section(args, links, hazards, check.get("time_repair", {}))


def implied_false(first: pd.DataFrame, fixed: pd.DataFrame, chance) -> str:
    """The share of wrong second-pass links that the rating agreement implies.

    If a share f of them pair different tornadoes, they agree at
    (1 − f)·a₁ + f·a₀, with a₁ the first pass's rate and a₀ chance's.
    """
    a1 = first.ef_agrees.dropna().astype(bool).mean()
    a2 = fixed.ef_agrees.dropna().astype(bool).mean()
    if chance is None or not (a1 > chance) or pd.isna(a2):
        return ""
    f = min(max((a1 - a2) / (a1 - chance), 0.0), 1.0)
    return (f"; solving (1 − f)·{a1:.3f} + f·{chance:.3f} = {a2:.3f} puts the share of "
            f"wrong pairs at **≈ {f:.1%}**")


def repair_section(args, links: pd.DataFrame, hazards: pd.DataFrame, repair: dict) -> list[str]:
    """What the time-repaired second pass found, and the checks on it."""
    if "time_offset_h" not in links.columns:
        return []
    best = links[links.rank_for_hazard == 1].drop_duplicates("hazard_uid")
    first = best[best.link_method == "spatial_temporal_join"]
    fixed = best[best.link_method == "time_repaired"]
    total = len(hazards)
    lines = ["## Time-repaired matches (second pass)", ""]
    if not repair.get("enabled", False):
        return lines + ["Not run (`--no-time-repair`).", ""]

    def agree(frame):
        known = frame.ef_agrees.dropna()
        return f"{known.astype(bool).mean():.0%}" if len(known) else "—"

    chance = repair.get("candidates_residual_20_30", 0) / 10 * repair["max_residual_min"]
    kept = repair.get("candidates_residual_le_tol", 0)
    lines += [
        f"The strict rule leaves {total - len(first):,} of {total:,} DAT hazards without "
        "an SPC track. Most have one within metres whose start differs by a **whole "
        "number of hours, to the minute** — the DAT time was saved in the wrong zone or on "
        "the wrong date. The second pass links a hazard to an SPC track within "
        f"{repair['max_distance_m']/1000:g} km whose start is k hours away, "
        f"1 ≤ |k| ≤ {repair['max_offset_h']}, to within ±{repair['max_residual_min']:g} min. "
        "DAT's times are never changed; the offset is kept on the link "
        "(`link_method = time_repaired`, `time_offset_h`, `offset_class`).", "",
        f"**{len(fixed):,} more hazards** are linked "
        f"({len(first) / total:.1%} → {(len(first) + len(fixed)) / total:.1%} of DAT).", "",
        "Three checks that do not rest on the time field:", "",
        f"- **The offsets pile up on the hour.** Of {repair.get('candidates', 0):,} "
        "candidate pairs within the distance, "
        f"{repair.get('candidates_residual_le_2', 0):,} are within 2 min of a whole hour. "
        "Pairs that are not one tornado fall anywhere in the hour; their density 20–30 "
        f"min from it puts chance at ≈ {chance:.0f} of the {kept:,} candidates kept "
        f"({chance / max(kept, 1):.0%}, an upper bound — it counts candidates, and most "
        "hazards with a chance candidate also have a real one).",
        f"- **Ratings agree as often as in the first pass.** EF ratings match on "
        f"{agree(fixed)} of second-pass links, {agree(first)} of first-pass links, and "
        f"{repair.get('ef_chance', float('nan')):.0%} for ratings drawn at random"
        + implied_false(first, fixed, repair.get("ef_chance")) + ".",
    ]
    ids = fixed.id_date.value_counts() if "id_date" in fixed.columns else pd.Series(dtype=int)
    dated = fixed[fixed.offset_class.str.contains("date", na=False)]
    did = dated.id_date.value_counts() if "id_date" in dated.columns else pd.Series(dtype=int)
    lines.append(
        f"- **DAT's own `event_id` sides with SPC.** Where it holds a legible date "
        f"({int(ids.sum()):,} links), it is SPC's local date and not DAT's for "
        f"{int(ids.get('spc', 0)):,}, DAT's and not SPC's for {int(ids.get('dat', 0)):,}. "
        f"For the date repairs alone ({int(did.sum()):,} with a date): SPC "
        f"{int(did.get('spc', 0)):,}, DAT {int(did.get('dat', 0)):,}.")
    lines += ["", "| cause | hazards | EF agrees | SPC track also has a first-pass "
              "hazard |", "|---|---:|---:|---:|"]
    # date+1, date-2 … are one cause, a wrong date; the day count is on each link.
    family = fixed.offset_class.str.replace(r"date[+-]\d+", "date", regex=True)
    for name, g in fixed.groupby(family):
        lines.append(f"| `{name}` | {len(g):,} | {agree(g)} | "
                     f"{int(g.spc_already_linked.astype(bool).sum()):,} |")
    by_year = fixed.groupby(pd.to_datetime(
        fixed.hazard_uid.map(hazards.set_index("hazard_uid").time_begin_utc),
        utc=True).dt.year).offset_class.agg(lambda c: c.value_counts().index[0])
    counts = fixed.groupby(pd.to_datetime(
        fixed.hazard_uid.map(hazards.set_index("hazard_uid").time_begin_utc),
        utc=True).dt.year).size()
    lines += ["", "Most common class per year (repaired hazards): "
              + ", ".join(f"{int(y)} {by_year[y]} ({counts[y]})" for y in counts.index) + ".",
              "",
              "- `local_as_utc` (+4…+7 h): the local clock saved as if it were UTC, so "
              "DAT is early by the zone's offset — 5 h for CDT, 6 h for CST.",
              "- `dst` (±1 h): daylight saving applied or missed. `date±n`: the "
              "date wrong by n days; combined with an hour part when both are wrong.",
              "- `unexplained`: a whole-hour offset no clock error accounts for; "
              "kept, but filter on `offset_class` to drop them.",
              "- A hazard whose SPC track already has a first-pass hazard is probably "
              "a second survey of the same tornado in DAT.", ""]
    path = spc_unmatched_path(args.tag)
    if path.exists():
        left = pd.read_csv(path)
        near = left.nearest_distance_km.notna()
        lines += ["### Still without an SPC track", "",
                  f"{len(left):,} DAT hazards ({len(left) / total:.1%}). "
                  f"{int(near.sum()):,} have an SPC track within 20 km and 72 h (listed "
                  "with its distance and offset), "
                  f"**{int((~near).sum()):,} have none** — candidates for tornadoes not in "
                  "the official record (reclassified, never submitted, a duplicate or a "
                  f"test entry). One row each in `data/interim/{path.name}`, for a "
                  "hand check.", ""]
    return lines


def cmd_run(args) -> None:
    cmd_fetch(args)
    cmd_join(args)
    cmd_report(args)


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    for name, fn, helptext in [("fetch", cmd_fetch, "download the newest file per year"),
                               ("join", cmd_join, "match Storm Events rows to DAT hazards"),
                               ("report", cmd_report, "coverage per year"),
                               ("run", cmd_run, "fetch, join and report")]:
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("--tag", default=default_tag)
        sp.add_argument("--from-dir", default=None,
                        help="read details files from here instead of data/raw/storm_events")
        sp.add_argument("--spc-file", default=None,
                        help="SPC *_actual_tornadoes.csv to use instead of data/raw/spc")
        sp.add_argument("--max-distance-m", type=float, default=se.MATCH_DISTANCE_M)
        sp.add_argument("--max-gap-s", type=float, default=se.MATCH_GAP_S)
        sp.add_argument("--no-time-repair", action="store_true",
                        help="SPC: skip the second pass for whole-hour DAT time errors")
        sp.add_argument("--repair-max-residual-min", type=float,
                        default=spc.REPAIR_MAX_RESIDUAL_MIN,
                        help="SPC second pass: how far from a whole hour the offset may be")
        sp.add_argument("--repair-max-offset-h", type=int, default=spc.REPAIR_MAX_OFFSET_H,
                        help="SPC second pass: largest offset tried, in hours")
        sp.set_defaults(func=fn)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
