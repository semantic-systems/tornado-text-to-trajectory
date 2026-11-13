#!/usr/bin/env python
"""Stage 15 — build episodes (outbreaks) on SPC tracks, and the hazards in them.

Groups SPC's complete tornado list by single linkage within
``config.EPISODE_MAX_DISTANCE_M`` (400 km) and ``config.EPISODE_MAX_GAP_H`` (6 h),
with no day boundary, and publishes every group, ``has_dat`` flagging those with
a DAT survey. Each DAT hazard takes the episode of its closest SPC track (stage
14); an SPC tornado with no DAT link becomes a hazard of its own (``spc_hazards``,
straight SPC line). A DAT hazard with no SPC track is in no episode and gets a
``spc_match_status``. See :mod:`tornado_dataset.dat.episode_table`; stage 51 has
the comparison behind the rule.

Each hazard's times are written with its episode: ``begin_utc``, ``end_utc``,
``convective_day``, with ``time_source`` (``dat``, ``spc``, or ``spc_track`` where
stage 14 found DAT's time wrong or missing) and ``end_repaired`` (a DAT end with a
mistyped date, its clock time kept; an end that cannot be repaired, or that DAT
lacks, is empty; :func:`episode_table.event_times`). Stage 12's ``time_begin_utc`` and
``time_end_utc`` stay as DAT entered them.

Each hazard's ``rating``, ``deaths`` and ``injuries`` are written with it too:
SPC's where the hazard has an SPC track (each track counted on one hazard), DAT's
where it has none (``values_source``). DAT's and SPC's own values stay beside
them (``dat_*``, ``spc_*``), with ``rating_differs``, ``deaths_differ`` and
``injuries_differ`` where the two were compared (``values_compare``;
:func:`episode_table.hazard_values`).

    python scripts/15_build_episodes.py

Offline. Needs stage 12's hazards and stage 14's SPC tracks and links, and stops
if they are missing. Writes, in ``data/processed/``, ``episodes_<tag>.csv``,
``hazard_episodes_<tag>.csv`` (one row per DAT and SPC hazard) and
``spc_hazards_<tag>.csv``/``.geojson``; and ``data/interim/spc_episodes_<tag>.csv``
(every SPC track, its episode and role).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config
from tornado_dataset.dat import episode_table as et
from tornado_dataset.dat import episodes as ep
from tornado_dataset.dat import references as refs
from tornado_dataset.ids import write_manifest


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tag", default=default_tag)
    args = p.parse_args()

    hazards_path = config.PROCESSED_DIR / f"hazards_{args.tag}.csv"
    needed = {hazards_path: "scripts/12_build_hazards.py",
              refs.SPC_TRACKS: "scripts/13_fetch_references.py and 14_match_references.py",
              refs.spc_links_path(args.tag): "scripts/14_match_references.py"}
    for path, stage in needed.items():
        if not path.exists():
            raise SystemExit(f"no {path.name} — run {stage}")

    tracks = pd.read_csv(refs.SPC_TRACKS, low_memory=False)
    frame = ep.load_spc_frame(refs.SPC_TRACKS)
    labels = et.group_spc(frame)
    hazards = pd.read_csv(hazards_path, low_memory=False)
    links = pd.read_csv(refs.spc_links_path(args.tag))
    optional = {name: (pd.read_csv(path) if path.exists() else None) for name, path in
                (("unmatched", refs.spc_unmatched_path(args.tag)),
                 ("spc_se_links", refs.spc_se_links_path(args.tag)))}
    for name, frame_ in optional.items():
        if frame_ is None:
            print(f"note: no {name} table from stage 14 — "
                  + ("statuses stay 'unmatched'" if name == "unmatched" else "offices from DAT only"))
    episodes, member, grouping, spc_hazards = et.build(frame, labels, tracks, hazards, links,
                                                       **optional)
    time_cols = ["hazard_uid", "time_begin_utc", "time_end_utc", "convective_day"]
    table = pd.concat([hazards[time_cols].assign(hazard_source="dat"),
                       spc_hazards[time_cols].assign(hazard_source="spc")], ignore_index=True)
    member = member.merge(et.event_times(table, member, tracks), on="hazard_uid", how="left")
    member = member.merge(et.hazard_values(member, hazards, tracks, links), on="hazard_uid",
                          how="left")
    counted = member.spc_ids_counted.dropna().str.split(";").explode()
    if counted.duplicated().any() or set(counted) != set(tracks.spc_id):
        raise SystemExit("SPC tracks counted twice or not at all in the hazards' values")

    out = {"episodes": et.episodes_path(args.tag), "membership": et.membership_path(args.tag),
           "spc_hazards": et.spc_hazards_path(args.tag),
           "spc_hazards_geojson": et.spc_hazards_path(args.tag, "geojson"),
           "spc": et.spc_episodes_path(args.tag)}
    for path in out.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    episodes.to_csv(out["episodes"], index=False)
    member.to_csv(out["membership"], index=False)
    spc_hazards.to_csv(out["spc_hazards"], index=False)
    features = et.spc_hazard_features(spc_hazards, tracks)
    out["spc_hazards_geojson"].write_text(json.dumps(
        {"type": "FeatureCollection", "features": features}), encoding="utf-8")
    grouping.to_csv(out["spc"], index=False)

    dat = member[member.hazard_source == "dat"]
    counts = {
        "method": et.METHOD,
        "max_distance_m": config.EPISODE_MAX_DISTANCE_M, "max_gap_h": config.EPISODE_MAX_GAP_H,
        "spc_tracks": len(frame), "spc_track_roles": grouping.role.value_counts().to_dict(),
        "episodes": len(episodes), "episodes_with_dat": int(episodes.has_dat.sum()),
        "episodes_without_hazards": int((episodes.n_hazards == 0).sum()),
        "multi_day_episodes": int((episodes.convective_days.str.count(";") > 0).sum()),
        "episodes_6plus_ef1": int((episodes.n_spc_ef1plus >= 6).sum()),
        "hazards": len(member), "dat_hazards": len(dat), "spc_hazards": len(spc_hazards),
        "dat_hazards_in_episodes": int(dat.episode_uid.notna().sum()),
        "dat_link_method": dat.spc_link_method.value_counts().to_dict(),
        "dat_match_status": dat.spc_match_status.value_counts().to_dict(),
        "time_source": member.time_source.value_counts().to_dict(),
        "dat_end_repaired": int(member.end_repaired.sum()),
        "dat_end_unknown": int((dat.begin_utc.notna() & dat.end_utc.isna()).sum()),
        "dat_untimed": int((dat.begin_utc.isna()).sum()),
        "values_source": member.values_source.value_counts().to_dict(),
        "values_compare": member.values_compare.value_counts().to_dict(),
        "values_differ": {
            field: {"compared": int(member[flag].notna().sum()),
                    "differ": int(member[flag].fillna(False).sum())}
            for field, flag in (("rating", "rating_differs"), ("deaths", "deaths_differ"),
                                ("injuries", "injuries_differ"))},
        "deaths": {"hazards": int(member.deaths.sum()), "spc_tracks": int(tracks.fat.sum()),
                   "dat_only": int(member.deaths[member.values_source == "dat"].sum())},
        "spc_hazard_geometry": dict(Counter(f["properties"]["geometry_source"] or "none"
                                            for f in features)),
    }
    write_manifest(config.PROCESSED_DIR / f"manifest_episodes_{args.tag}.json",
                   "15_build_episodes", counts=counts, outputs=list(out.values()))
    print(f"{len(frame):,} SPC tracks -> {len(episodes):,} episodes, "
          f"{counts['episodes_with_dat']:,} with a DAT hazard; "
          f"{counts['multi_day_episodes']:,} span several convective days, "
          f"{counts['episodes_6plus_ef1']:,} hold ≥6 EF1+ tornadoes")
    roles = counts["spc_track_roles"]
    print(f"SPC tracks: {roles.get('dat_closest', 0):,} closest track of a DAT hazard, "
          f"{roles.get('dat_secondary', 0):,} linked to one otherwise, "
          f"{roles.get('spc_hazard', 0):,} hazards of their own")
    print(f"hazards: {len(dat):,} DAT ({counts['dat_hazards_in_episodes']:,} in an episode) "
          f"+ {len(spc_hazards):,} SPC")
    d = counts["deaths"]
    print(f"values: {d['hazards']:,} deaths over hazards = SPC's {d['spc_tracks']:,} "
          f"+ {d['dat_only']:,} on DAT hazards with no SPC track; DAT and SPC differ on "
          + ", ".join(f"{k} {v['differ']:,} of {v['compared']:,}"
                      for k, v in counts["values_differ"].items()))
    print("DAT hazards without an SPC track: " + ", ".join(
        f"{k} {v:,}" for k, v in counts["dat_match_status"].items() if k != "linked"))
    for path in out.values():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
