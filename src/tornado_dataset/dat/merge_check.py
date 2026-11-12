"""Hand check of stage 12's merges: does a hazard built from several DAT lines
join tornadoes that should stay apart? (stage 17 ``merges``).

Stage 12 joins DAT lines by union-find (:func:`hazards.merge_lines`): a shared
polygon, the same ``event_id`` on the same date, or an endpoint within a few km on
the same convective day. Chains of such unions can join neighbouring tornadoes.
The candidates are the multi-line hazards that stage 14 links to two or more SPC
tracks: SPC sees more than one tornado there, either because the hazard joins
several (an over-merge) or because SPC records one tornado in pieces.

The sample is stratified by the rules that made the hazard (``STRATA``), so each
rule's error rate can be read off; the check weights the strata back to the
population. What the annotator sees (``merge_sheet.csv`` and the map
``merge_review.html``) holds the DAT lines and SPC tracks; the measures that might
predict an over-merge (simultaneous SPC tracks, the largest gap between lines,
the spread of start times) go to ``merge_key.csv``, for the check to test.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.ops import unary_union

from .. import config, handcheck
from . import episode_table
from . import references as refs
from .geometry import to_equal_area, to_shapely
from .spc_tornadoes import track_geometries

ANNOTATION = handcheck.ANNOTATION
PREFIX = "M"
SHEET_SEED = 20261112
LABELS = ("one_tornado", "several_tornadoes", "cannot_tell")
# Stage 12's rules behind a hazard, and how many of each the sheet draws.
STRATA = {"endpoint_gap": 30, "event_id": 20, "polygon": 15, "mixed": 10}
# An SPC hazard (a tornado with no DAT link) this close to a candidate's lines on
# its day is shown: the merge may have swallowed its ground without its record.
NEARBY_M = 1_000.0


def stratum(merge_evidence: str) -> str:
    """The stage 12 rules behind a hazard, as one of ``STRATA``."""
    rules = set(str(merge_evidence or "").split(";")) - {""}
    if rules == {"endpoint_gap"}:
        return "endpoint_gap"
    if rules == {"event_id+date"}:
        return "event_id"
    if rules and rules <= {"spatial_link", "path_guid"}:
        return "polygon"
    return "mixed"


def paths() -> dict[str, Path]:
    return {"sheet": ANNOTATION / "merge_sheet.csv", "key": ANNOTATION / "merge_key.csv",
            "map": ANNOTATION / "merge_review.html",
            "how_to": ANNOTATION / "HOW_TO_ANNOTATE_merges.txt",
            "manifest": ANNOTATION / "manifest_annotation_merges.json"}


def _features(path: Path) -> dict[str, dict]:
    """DAT features by ``objectid`` (as text)."""
    features = json.loads(path.read_text(encoding="utf-8"))["features"]
    return {str(f["properties"].get("objectid")): f for f in features}


def candidates(tag: str) -> tuple[pd.DataFrame, dict[str, dict]]:
    """Every multi-line DAT hazard on two or more SPC tracks, with what the sheet,
    the key and the map need (the last by ``hazard_uid``)."""
    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv", low_memory=False)
    links = pd.read_csv(refs.spc_links_path(tag))
    tracks = pd.read_csv(refs.SPC_TRACKS, low_memory=False)
    member = episode_table.membership(tag)
    lines = _features(config.INTERIM_DIR / f"dat_lines_{tag}.geojson")
    polygons = _features(config.INTERIM_DIR / f"dat_polygons_{tag}.geojson")

    n_spc = links.groupby("hazard_uid").spc_id.nunique()
    hazards["n_spc"] = hazards.hazard_uid.map(n_spc).fillna(0).astype(int)
    pop = hazards[(hazards.n_lines > 1) & (hazards.n_spc >= 2)].copy()
    pop["stratum"] = pop.merge_evidence.map(stratum)

    t = tracks.set_index("spc_id")
    t_geo = dict(zip(tracks.spc_id, track_geometries(tracks, lambda g: g)))
    t["t0"] = pd.to_datetime(t.begin_utc, utc=True, errors="coerce")
    t["t1"] = pd.to_datetime(t.end_utc, utc=True, errors="coerce").fillna(t.t0)
    own = member[member.hazard_source == "spc"].set_index("spc_id").hazard_uid
    own_day = t.t0.dt.date[t.index.isin(own.index)]
    by_hazard = links.groupby("hazard_uid").spc_id.agg(lambda s: sorted(set(s)))

    rows, shapes = [], {}
    for h in pop.itertuples():
        feats = [lines[o] for o in str(h.line_objectids).split(";") if o in lines]
        feats.sort(key=lambda f: str(f["properties"].get("starttime") or ""))
        geoms = [to_shapely(f["geometry"]) for f in feats]
        proj = [to_equal_area(g) for g in geoms]
        line_text = []
        for k, f in enumerate(feats, 1):
            p = f["properties"]
            length = p.get("length")
            line_text.append(
                f"L{k}: {handcheck.iso_hm(p.get('starttime'))}–{handcheck.iso_hm(p.get('endtime'))[11:]} UTC, "
                f"{p.get('efscale') or '?'}, "
                f"{length if isinstance(length, (int, float)) and length >= 0 else '?'} mi"
                + (f", {p['wfo']}" if p.get("wfo") else "")
                + (f", event_id {p['event_id']}" if str(p.get("event_id") or "").strip() else ""))
        gaps = [min(a.distance(b) for j, b in enumerate(proj) if j != i)
                for i, a in enumerate(proj)] if len(proj) > 1 else [0.0]
        starts = pd.to_datetime([f["properties"].get("starttime") for f in feats],
                                utc=True, errors="coerce").dropna()

        ids = [s for s in by_hazard.get(h.hazard_uid, []) if s in t.index]
        ids.sort(key=lambda s: (t.t0.get(s), s))
        spc_text = [f"S{k}: {handcheck.iso_hm(t.t0[s])}–{handcheck.iso_hm(t.t1[s])[11:]} UTC, "
                    f"{'EF' + str(int(t.mag[s])) if t.mag[s] >= 0 else 'EFU'}, "
                    f"{t.len[s]} mi, {t.st[s]}, {int(t.fat[s])} deaths ({s})"
                    for k, s in enumerate(ids, 1)]
        spans = sorted((t.t0[s], t.t1[s]) for s in ids if pd.notna(t.t0[s]))
        simultaneous = any(b0 < a1 for (a0, a1), (b0, b1) in zip(spans, spans[1:]))

        day = dt.date.fromisoformat(h.convective_day) if isinstance(h.convective_day, str) else None
        near = []
        if day is not None and proj:
            union = unary_union(proj)
            one = dt.timedelta(days=1)
            for s in own_day.index[(own_day >= day - one) & (own_day <= day + one)]:
                g = t_geo.get(s)
                if g is not None and to_equal_area(g).distance(union) <= NEARBY_M:
                    near.append(s)
        near_text = [f"{handcheck.iso_hm(t.t0[s])} UTC, "
                     f"{'EF' + str(int(t.mag[s])) if t.mag[s] >= 0 else 'EFU'}, {t.len[s]} mi ({s})"
                     for s in near]

        polys = [to_shapely(polygons[o]["geometry"])
                 for o in str(h.polygon_objectids or "").split(";") if o in polygons]
        map_layers = [x for g in polys for x in handcheck.layers(g, "area")]
        map_layers += [x for s in near for x in handcheck.layers(t_geo.get(s), "grey")]
        map_layers += [x for k, s in enumerate(ids, 1)
                       for x in handcheck.layers(t_geo.get(s), "spc", f"S{k}")]
        map_layers += [x for k, g in enumerate(geoms)
                       for x in handcheck.layers(g, f"c{k}", f"L{k + 1}")]
        shapes[h.hazard_uid] = {
            "layers": map_layers, "line_text": line_text, "spc_text": spc_text,
            "near_text": near_text}
        rows.append({
            "hazard_uid": h.hazard_uid, "stratum": h.stratum,
            "merge_evidence": h.merge_evidence, "convective_day": h.convective_day,
            "states": ";".join(sorted({str(t.st[s]) for s in ids})), "wfo_all": h.wfo_all,
            "efscale": h.efscale, "n_lines": int(h.n_lines), "n_spc": len(ids),
            "dat_lines": " | ".join(line_text), "spc_tracks": " | ".join(spc_text),
            "spc_hazards_on_lines": " | ".join(near_text),
            "spc_simultaneous": simultaneous, "max_line_gap_m": round(max(gaps), 1),
            "line_start_spread_h": (round((starts.max() - starts.min()).total_seconds() / 3600, 2)
                                    if len(starts) > 1 else 0.0),
            "n_spc_hazards_on_lines": len(near)})
    return pd.DataFrame(rows), shapes


def draw(pop: pd.DataFrame, rng: np.random.Generator,
         sizes: dict[str, int] = STRATA) -> pd.DataFrame:
    """A stratified sample, in random order, with each case's weight."""
    return handcheck.draw(pop, rng, sizes, "M")


SHEET_COLUMNS = ["case_id", "convective_day", "states", "wfo_all", "efscale", "n_lines",
                 "dat_lines", "n_spc", "spc_tracks", "spc_hazards_on_lines", "spc_reports",
                 "label", "notes"]
KEY_COLUMNS = ["case_id", "hazard_uid", "stratum", "weight", "merge_evidence",
               "spc_simultaneous", "max_line_gap_m", "line_start_spread_h",
               "n_spc_hazards_on_lines"]


def sheet_and_key(sample: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sheet = sample.assign(
        spc_reports=[f"https://www.spc.noaa.gov/climo/reports/{pd.Timestamp(d):%y%m%d}_rpts.html"
                     if isinstance(d, str) else "" for d in sample.convective_day],
        label="", notes="")
    return sheet[SHEET_COLUMNS], sample[KEY_COLUMNS]


read_sheet = handcheck.read_sheet


HOW_TO = """How to check stage 12's merges (stage 17)
=========================================

Each case is one hazard that stage 12 built from several DAT lines, where SPC's
database has two or more tornadoes. Question: is it ONE tornado, or did the
merge join SEVERAL that should be separate hazards?

1. Open the map: python -m http.server 8792 --directory outputs/annotation
   then http://127.0.0.1:8792/merge_review.html  (the basemap tiles need the
   server; the map works without them). Keys: n / p for next / previous case.
2. On the map: DAT lines in colour, numbered L1, L2, ... in order of start time
   (as in the sheet); DAT damage polygons shaded; SPC's tornadoes as dashed black
   start-end lines S1, S2, ...; SPC tornadoes with no DAT survey that lie on the
   lines dashed grey. The panel lists each line's and track's time, rating,
   length and office.
3. Decide, in merge_sheet.csv:
   one_tornado        the lines continue one track (end of one near the start
                      of the next, times in sequence, one parent storm); SPC
                      splitting it (at a state or office line) is fine
   several_tornadoes  at least one line is a separate tornado: side by side
                      (parallel tracks), at overlapping times, or a gap in
                      space and time that a single tornado would not leave
   cannot_tell        the map and the times do not settle it
   In notes, say which lines belong apart (e.g. "L3 separate, parallel to L1").
   The SPC report page (spc_reports) and the NWS event pages can help.
4. Do not open merge_key.csv before you are done.

When done:  python scripts/17_qa_events.py merges-check
"""


# ── the map ─────────────────────────────────────────────────────────────────
def review_map(sample: pd.DataFrame, sheet: pd.DataFrame, shapes: dict[str, dict]) -> str:
    """One self-contained page showing every sampled case."""
    cases = []
    for s, r in zip(sample.itertuples(), sheet.itertuples()):
        shape = shapes[s.hazard_uid]
        cases.append(handcheck.case(
            s.case_id, f"{s.convective_day} · {s.states}",
            [("DAT lines (colour)", [(x, k) for k, x in enumerate(shape["line_text"])]),
             ("SPC tornadoes linked to this hazard (dashed black)", shape["spc_text"]),
             ("SPC tornadoes without DAT survey on the lines (dashed grey)",
              shape["near_text"])],
            shape["layers"], [("SPC reports of the day", r.spc_reports)]))
    return handcheck.review_map("Stage 12 merge check", cases,
                                "Label in merge_sheet.csv: one_tornado, several_tornadoes, "
                                "cannot_tell.")
