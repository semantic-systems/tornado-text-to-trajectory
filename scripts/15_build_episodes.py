#!/usr/bin/env python
"""Stage 15 — build episodes (outbreaks) on SPC tracks and carry them to DAT hazards.

Groups SPC's complete tornado list by single linkage within
``config.EPISODE_MAX_DISTANCE_M`` (400 km) and ``config.EPISODE_MAX_GAP_H`` (6 h),
with no day boundary, and gives each DAT hazard the episode of its closest SPC
track (stage 14). A hazard with no SPC track is an episode of its own
(``in_spc`` false). Episodes without a DAT hazard are not published, but every
count includes their tornadoes. See :mod:`tornado_dataset.dat.episode_table`;
stage 51 has the comparison behind the choice.

    python scripts/15_build_episodes.py

Offline. Needs stage 12's hazards and stage 14's SPC tracks and links, and stops
if they are missing: episodes built on DAT alone would differ without notice.
Writes ``data/processed/episodes_<tag>.csv``, ``data/processed/hazard_episodes_<tag>.csv``
(one row per hazard) and ``data/interim/spc_episodes_<tag>.csv`` (every SPC track).
"""

from __future__ import annotations

import argparse

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
    episodes, member, grouping = et.build(frame, labels, tracks, hazards, links)

    out = {"episodes": et.episodes_path(args.tag), "membership": et.membership_path(args.tag),
           "spc": et.spc_episodes_path(args.tag)}
    for path in out.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    episodes.to_csv(out["episodes"], index=False)
    member.to_csv(out["membership"], index=False)
    grouping.to_csv(out["spc"], index=False)

    spc_eps = episodes[episodes.in_spc]
    counts = {
        "method": et.METHOD,
        "max_distance_m": config.EPISODE_MAX_DISTANCE_M, "max_gap_h": config.EPISODE_MAX_GAP_H,
        "spc_tracks": len(frame), "spc_episodes": int(grouping.episode_uid.nunique()),
        "spc_episodes_with_dat": int(grouping[grouping.has_dat].episode_uid.nunique()),
        "hazards": len(member), "hazards_in_spc": int(member.in_spc.sum()),
        "hazards_by_link_method": member.spc_link_method.value_counts().to_dict(),
        "episodes": len(episodes), "episodes_from_spc": len(spc_eps),
        "episodes_dat_only": int((~episodes.in_spc).sum()),
        "multi_day_episodes": int((episodes.convective_days.str.count(";") > 0).sum()),
        "episodes_6plus_ef1": int((episodes.n_spc_ef1plus >= 6).sum()),
    }
    write_manifest(config.PROCESSED_DIR / f"manifest_episodes_{args.tag}.json",
                   "15_build_episodes", counts=counts, outputs=list(out.values()))
    print(f"{len(frame):,} SPC tracks -> {counts['spc_episodes']:,} episodes, "
          f"{counts['spc_episodes_with_dat']:,} with a DAT hazard")
    print(f"{len(member):,} DAT hazards: {counts['hazards_in_spc']:,} through an SPC track, "
          f"{len(member) - counts['hazards_in_spc']:,} on their own")
    print(f"published: {len(episodes):,} episodes ({len(spc_eps):,} from SPC, "
          f"{counts['episodes_dat_only']:,} single DAT hazards); "
          f"{counts['multi_day_episodes']:,} span several convective days; "
          f"{counts['episodes_6plus_ef1']:,} hold ≥6 EF1+ SPC tornadoes")
    for path in out.values():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
