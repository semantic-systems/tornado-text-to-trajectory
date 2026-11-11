#!/usr/bin/env python
"""Stage 24 — the text that comes with the official records, as TextRefs.

Turns two texts already on disk into TextRefs and TextLinks, in the schema of
stage 20's NWS text (:mod:`tornado_dataset.text.records`):

* NCEI Storm Events narratives (stage 13): each tornado row's
  ``EVENT_NARRATIVE``, linked to its DAT or SPC hazard (stage 14's links,
  stage 15's hazards), and each Storm Events episode's ``EPISODE_NARRATIVE``,
  linked to the stage 15 episodes its rows fall in.
* DAT comments (stages 10 and 12): one TextRef per distinct comment of a hazard.

All are ``oracle`` text: written by the surveying office from its survey. Texts
are not merged or deduplicated here; how they overlap with each other and with
the survey statements is stage 25.

    python scripts/24_import_record_text.py

Offline. Needs stages 12-15. Writes ``data/processed/textrefs_records_<tag>.csv``
and ``textlinks_records_<tag>.csv`` (the bodies are US government works, public
domain) and a manifest.
"""

from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config
from tornado_dataset.dat import episode_table
from tornado_dataset.dat import references as refs
from tornado_dataset.ids import write_manifest
from tornado_dataset.text import records


def load_dat_features(tag: str) -> dict[str, dict[str, dict]]:
    out = {}
    for role, name in (("line", "dat_lines"), ("polygon", "dat_polygons")):
        path = config.INTERIM_DIR / f"{name}_{tag}.geojson"
        if not path.exists():
            raise SystemExit(f"no {path.name} — run scripts/10_fetch_dat.py")
        features = json.loads(path.read_text(encoding="utf-8"))["features"]
        out[role] = {str(f["properties"].get("objectid")): f["properties"] for f in features}
    return out


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tag", default=default_tag)
    args = parser.parse_args()
    tag = args.tag

    needed = {refs.SE_TORNADOES: "scripts/13_fetch_references.py",
              refs.se_links_path(tag): "scripts/14_match_references.py",
              refs.spc_se_links_path(tag): "scripts/14_match_references.py",
              episode_table.membership_path(tag): "scripts/15_build_episodes.py",
              episode_table.spc_episodes_path(tag): "scripts/15_build_episodes.py"}
    for path, stage in needed.items():
        if not path.exists():
            raise SystemExit(f"no {path.name} — run {stage}")

    se = pd.read_csv(refs.SE_TORNADOES, low_memory=False,
                     usecols=["EVENT_ID", "EPISODE_ID", "WFO", "STATE", "CZ_NAME", "begin_utc",
                              "BEGIN_LAT", "BEGIN_LON", "EVENT_NARRATIVE", "EPISODE_NARRATIVE"])
    membership = episode_table.membership(tag)
    targets = records.event_targets(pd.read_csv(refs.se_links_path(tag)),
                                    pd.read_csv(refs.spc_se_links_path(tag)), membership,
                                    pd.read_csv(episode_table.spc_episodes_path(tag)))
    se_refs, se_links = records.storm_events_refs(se, targets)

    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv", low_memory=False)
    dat_refs, dat_links = records.dat_comment_refs(hazards, load_dat_features(tag))

    ref_frame, link_frame = records.frames(se_refs + dat_refs, se_links + dat_links)
    out_refs = config.PROCESSED_DIR / f"textrefs_records_{tag}.csv"
    out_links = config.PROCESSED_DIR / f"textlinks_records_{tag}.csv"
    ref_frame.to_csv(out_refs, index=False)
    link_frame.to_csv(out_links, index=False)

    hazard_links = link_frame[link_frame.link_level == "hazard"]
    source_of = membership.set_index("hazard_uid").hazard_source
    covered = hazard_links.assign(source=hazard_links.target_uid.map(source_of))
    raw_files = sorted(p.name for p in (config.RAW_DIR / "storm_events").glob("StormEvents_details*"))
    counts = {
        "textrefs": ref_frame.source_type.value_counts().to_dict(),
        "roles": ref_frame.text_role.value_counts().to_dict(),
        "mentions_track": ref_frame.groupby("source_type").mentions_track.mean().round(3).to_dict(),
        "words_median": ref_frame.groupby("source_type").n_words.median().to_dict(),
        "storm_event_rows": len(se),
        "event_link_routes": pd.Series([t[0] for t in targets.values()]).value_counts().to_dict(),
        "event_narratives_unlinked": int(
            (~ref_frame.textref_uid[ref_frame.source_type == "storm_events_narrative"]
             .isin(link_frame.textref_uid)).sum()),
        "hazards_with_narrative": covered[covered.link_relation == "narrative_of"]
        .groupby("source").target_uid.nunique().to_dict(),
        "hazards_with_dat_comment": int(
            hazard_links[hazard_links.link_relation == "comment_of"].target_uid.nunique()),
        "episodes_with_episode_narrative": int(
            link_frame[link_frame.link_relation == "episode_narrative_of"].target_uid.nunique()),
        "hazards": membership.hazard_source.value_counts().to_dict(),
        "storm_events_files": raw_files,
    }
    write_manifest(config.PROCESSED_DIR / f"manifest_records_text_{tag}.json",
                   "24_import_record_text", counts=counts, outputs=[out_refs, out_links])
    for key in ("textrefs", "roles", "event_link_routes", "hazards_with_narrative",
                "hazards_with_dat_comment", "episodes_with_episode_narrative",
                "mentions_track", "words_median"):
        print(f"{key}: {counts[key]}")
    print(f"wrote {out_refs.name}, {out_links.name}")


if __name__ == "__main__":
    main()
