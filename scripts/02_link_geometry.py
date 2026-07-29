"""Stage 2 — link DAT damage lines to damage polygons.

Emits every candidate pair with the evidence used to judge it, plus the reduced
"best line per polygon" table. Linkage uses geometry and time only; ``path_guid``
and ``event_id`` ride along as independent columns so stage 4 can score the
linker against them.

    python scripts/02_link_geometry.py
    python scripts/02_link_geometry.py --tag march2025
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config
from tornado_dataset.dat import link
from tornado_dataset.ids import write_manifest


def load_features(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["features"]


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--search-radius-m", type=float, default=config.LINK_SEARCH_RADIUS_M,
                        help="candidate generation radius (wider than the accepted threshold)")
    parser.add_argument("--gap-threshold-m", type=float, default=config.LINK_GAP_THRESHOLD_M,
                        help="accepted-link gap threshold; also the confidence scale")
    parser.add_argument("--buffer-m", type=float, default=config.LINK_BUFFER_M)
    parser.add_argument("--max-date-delta-days", type=int,
                        default=config.LINK_MAX_DATE_DELTA_DAYS)
    args = parser.parse_args()

    lines_path = config.INTERIM_DIR / f"dat_lines_{args.tag}.geojson"
    polygons_path = config.INTERIM_DIR / f"dat_polygons_{args.tag}.geojson"
    for path in (lines_path, polygons_path):
        if not path.exists():
            raise SystemExit(f"missing {path} — run scripts/01_fetch_dat.py first")

    raw_lines = load_features(lines_path)
    raw_polygons = load_features(polygons_path)
    lines = link.prepare(raw_lines)
    polygons = link.prepare(raw_polygons)
    print(f"lines: {len(lines)}/{len(raw_lines)} usable, "
          f"polygons: {len(polygons)}/{len(raw_polygons)} usable "
          f"(the rest carry attributes but no drawn geometry in DAT)")

    records = link.link_lines_to_polygons(
        lines, polygons,
        search_radius_m=args.search_radius_m,
        confidence_scale_m=args.gap_threshold_m,
        buffer_m=args.buffer_m)
    kept = link.accepted(records, gap_threshold_m=args.gap_threshold_m,
                         max_date_delta_days=args.max_date_delta_days)

    candidates = pd.DataFrame(records)
    best = pd.DataFrame(link.best_line_per_polygon(kept))

    candidates_path = config.INTERIM_DIR / f"dat_links_{args.tag}.csv"
    best_path = config.INTERIM_DIR / f"dat_links_best_{args.tag}.csv"
    candidates.to_csv(candidates_path, index=False)
    best.to_csv(best_path, index=False)

    linked_polygons = int(best.shape[0])
    counts = {
        "lines_total": len(raw_lines), "lines_usable": len(lines),
        "polygons_total": len(raw_polygons), "polygons_usable": len(polygons),
        "candidate_pairs": int(candidates.shape[0]),
        "accepted_links": len(kept),
        "polygons_with_a_link": linked_polygons,
        "polygons_without_a_link": len(polygons) - linked_polygons,
        "lines_with_a_link": int(best["line_oid"].nunique()) if len(best) else 0,
        "parameters": {"search_radius_m": args.search_radius_m,
                       "gap_threshold_m": args.gap_threshold_m,
                       "buffer_m": args.buffer_m,
                       "max_date_delta_days": args.max_date_delta_days},
    }
    write_manifest(config.INTERIM_DIR / f"manifest_link_{args.tag}.json", "02_link_geometry",
                   counts=counts, outputs=[candidates_path, best_path])

    print(f"\n{counts['candidate_pairs']} candidate pairs, {len(kept)} accepted; "
          f"{linked_polygons}/{len(polygons)} polygons matched to a line "
          f"({linked_polygons / max(1, len(polygons)):.1%})")
    if len(best):
        print(f"  touching their line (gap = 0 m): {(best.gap_m == 0).mean():.1%}")
        print(f"  shared_event_id agreement:       {best.shared_event_id.mean():.1%}")
        print(f"  path_guid available on best row: {best.path_guid_match.sum()}")
    print(f"wrote {candidates_path.name}, {best_path.name}")


if __name__ == "__main__":
    main()
