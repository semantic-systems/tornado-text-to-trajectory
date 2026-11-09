#!/usr/bin/env python
"""Stage 14 — match the official tornado records to DAT hazards.

Storm Events is the NWS's own tornado record, filed by each forecast office as
*Storm Data*. It is used here as a reference for DAT — how complete DAT is in
each year, and how forecasters grouped tornadoes into episodes — and its
``EVENT_ID``/``EPISODE_ID`` become external keys on our hazards. See
:mod:`tornado_dataset.dat.storm_events` for the three properties that shape
every use of it (county segments, local standard time, per-office episodes).

SPC's tornado database is matched alongside: one reviewed record per whole track
(:mod:`tornado_dataset.dat.spc_tornadoes`). It is the tornado-level reference —
completeness of DAT counted in tornadoes — and the check on how well Storm
Events' county segments were chained into tornadoes.

    python scripts/14_match_references.py      # offline; needs stage 13's downloads

``--from-dir`` and ``--spc-file`` read files from elsewhere, e.g. ones
downloaded by hand. Without an SPC file only the Storm Events part runs. The
coverage report is part of stage 17's events report.
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
from tornado_dataset.dat import references as refs
from tornado_dataset.dat import spc_tornadoes as spc
from tornado_dataset.dat import storm_events as se
from tornado_dataset.ids import write_manifest

def load_tornadoes(args) -> pd.DataFrame:
    directory = Path(args.from_dir).expanduser() if args.from_dir else refs.RAW_SE
    paths = se.details_paths(directory)
    wanted = [paths[y] for y in refs.years() if y in paths]
    if not wanted:
        raise SystemExit(f"no StormEvents_details-*.csv.gz in {directory} — run scripts/13_fetch_references.py")
    absent = [y for y in refs.years() if y not in paths]
    print(f"details files: {len(wanted)} years from {directory}"
          + (f" (missing {absent})" if absent else ""))
    return se.load_tornadoes(wanted)


def match(args) -> None:
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
    tornadoes.to_csv(refs.SE_TORNADOES, index=False)
    out = refs.se_links_path(args.tag)
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
                   outputs=[refs.SE_TORNADOES, out])
    print(f"wrote {refs.SE_TORNADOES}\nwrote {out}")
    join_spc(args, tornadoes, geoms, hazards, project=lambda g: transform(to_m.transform, g))


def join_spc(args, se_rows, se_geoms, hazards, project) -> None:
    """SPC whole tracks against DAT, and against the Storm Events chains."""
    path = Path(args.spc_file).expanduser() if args.spc_file else spc.local_file(refs.RAW_SPC)
    if path is None or not path.exists():
        print("\nno SPC actual_tornadoes file — skipping the SPC part "
              "(run scripts/13_fetch_references.py)")
        return
    tracks, notes = spc.load(path, refs.years())
    print(f"\nSPC {path.name}: {notes['kept']:,} whole tracks in the window "
          f"(dropped: {notes['dropped_not_whole_track']:,} non-whole-track, "
          f"{notes['dropped_unknown_tz']:,} unknown time zone)")
    geoms = spc.track_geometries(tracks, project)
    links = spc.join_hazards(tracks, geoms, hazards, max_distance_m=args.max_distance_m,
                             max_gap_s=args.max_gap_s)
    strict_hz = links[links.link_method == "spatial_temporal_join"].hazard_uid.nunique()
    dated_hz = links[links.link_method == "date_only"].hazard_uid.nunique()
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
    links["hazards_on_track"] = spc.hazards_per_track(links)
    unmatched = spc.nearest_unlinked(tracks, geoms, hazards, links)
    se_links = spc.join_storm_events(se_rows, se_geoms, tracks, geoms,
                                     max_distance_m=args.max_distance_m,
                                     max_gap_s=args.max_gap_s)
    check = spc.crosscheck_chains(se_links, se_rows)
    tracks.to_csv(refs.SPC_TRACKS, index=False)
    links.to_csv(refs.spc_links_path(args.tag), index=False)
    se_links.to_csv(refs.spc_se_links_path(args.tag), index=False)
    unmatched.to_csv(refs.spc_unmatched_path(args.tag), index=False)
    refs.crosscheck_path(args.tag).write_text(json.dumps(
        {**notes, **check, "time_repair": repair}, indent=2, default=float))
    print(f"matched: {links.spc_id.nunique():,}/{len(tracks):,} SPC tornadoes, "
          f"{links.hazard_uid.nunique():,}/{len(hazards):,} DAT hazards "
          f"({strict_hz:,} by the strict rule, {dated_hz:,} by date for hazards with no "
          f"time); {links[links.hazards_on_track > 1].spc_id.nunique():,} SPC tracks are the "
          "closest of more than one DAT hazard")
    print(f"Storm Events chains agreeing 1:1 with an SPC track: "
          f"{check['chains_one_to_one']:,}/{check['se_chains_matched']:,} "
          f"({check['share_one_to_one']:.1%}); split over several SPC tracks "
          f"{check['chains_split_over_spc']:,}; SPC tracks with several chains "
          f"{check['spc_with_several_chains']:,}")
    print(f"wrote {refs.SPC_TRACKS}\nwrote {refs.spc_links_path(args.tag)}\n"
          f"wrote {refs.spc_se_links_path(args.tag)}\nwrote {refs.crosscheck_path(args.tag)}\n"
          f"wrote {refs.spc_unmatched_path(args.tag)}")


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tag", default=default_tag)
    p.add_argument("--from-dir", default=None,
                   help="read details files from here instead of data/raw/storm_events")
    p.add_argument("--spc-file", default=None,
                   help="SPC *_actual_tornadoes.csv to use instead of data/raw/spc")
    p.add_argument("--max-distance-m", type=float, default=se.MATCH_DISTANCE_M)
    p.add_argument("--max-gap-s", type=float, default=se.MATCH_GAP_S)
    p.add_argument("--no-time-repair", action="store_true",
                   help="SPC: skip the second pass for whole-hour DAT time errors")
    p.add_argument("--repair-max-residual-min", type=float,
                   default=spc.REPAIR_MAX_RESIDUAL_MIN,
                   help="SPC second pass: how far from a whole hour the offset may be")
    p.add_argument("--repair-max-offset-h", type=int, default=spc.REPAIR_MAX_OFFSET_H,
                   help="SPC second pass: largest offset tried, in hours")
    match(p.parse_args())


if __name__ == "__main__":
    main()
