"""Hand check of stage 20's official-text links (stage 35 ``links``).

Two questions, one sheet:

* **Precision.** Is the hazard a report or survey section is linked to the one
  it is about? LSRs are drawn by how their best match was found
  (``lsr_assignment``: ``sole``, ``clear``, ``time``, ``touching``, ``unclear``);
  survey sections (``primary_survey_of``) by how far their stated endpoints lie
  from the track (``pns_near`` within ``PNS_NEAR_M``, ``pns_far`` beyond).
* **Recall at the time margin** (``lsr_missed``). Tornado LSRs that stage 20
  left unlinked although a track lies within ``config.LSR_MATCH_RADIUS_M``,
  because its time is more than ``config.LSR_TIME_MARGIN_MIN`` and at most
  ``MISSED_MAX_H`` hours away: is that hazard the one reported?

Every case shows the report (a red point; a survey section's start and end)
and the hazards around it, numbered H1, H2, … in random order, so that the
linked one is not singled out. The annotator names the H the text is about, or
``none``. The key maps the numbers to hazards and says which one stage 20
chose (``linked_h``) or, for a missed LSR, which one lay near in space
(``near_h``).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import MultiPoint, Point
from shapely.strtree import STRtree

from .. import config, handcheck
from ..dat.geometry import to_equal_area
from . import iem, official, tiering

PREFIX = "T"
SHEET_SEED = 20261114
LABELS = tuple(f"h{k}" for k in range(1, 10)) + ("none", "cannot_tell")
STRATA = {"sole": 15, "clear": 10, "time": 10, "touching": 10, "unclear": 20,
          "lsr_missed": 25, "pns_near": 8, "pns_far": 12}
PNS_NEAR_M = 500.0
MISSED_MAX_H = 72
SHOW_RADIUS_M = 20_000.0
SHOW_MAX = 6


def paths() -> dict[str, Path]:
    a = handcheck.ANNOTATION
    return {"sheet": a / "textlink_sheet.csv", "key": a / "textlink_key.csv",
            "map": a / "textlink_review.html", "how_to": a / "HOW_TO_ANNOTATE_textlinks.txt",
            "manifest": a / "manifest_annotation_textlinks.json"}


def _interval(h) -> tuple[dt.datetime, dt.datetime | None] | None:
    """The hazard's begin-end, or its convective day without a time (as stage 20)."""
    begin = tiering._as_datetime(h.begin_utc) if isinstance(h.begin_utc, str) else None
    if begin:
        end = tiering._as_datetime(h.end_utc) if isinstance(h.end_utc, str) else None
        return begin, end
    if not isinstance(h.convective_day, str):
        return None
    start = dt.datetime.fromisoformat(h.convective_day).replace(
        hour=config.CONVECTIVE_DAY_START_HOUR, tzinfo=dt.timezone.utc)
    return start, start + dt.timedelta(days=1)


def _key(valid: str | None, lat: float, lon: float) -> tuple:
    t = pd.Timestamp(valid) if valid else None
    return (None if t is None else t.isoformat(), round(float(lat), 3), round(float(lon), 3))


def missed_lsrs(hz: pd.DataFrame, tree: STRtree, linked: set) -> pd.DataFrame:
    """Tornado LSRs stage 20 left unlinked with a track within the radius whose
    time is more than the margin and at most ``MISSED_MAX_H`` away."""
    years = sorted({int(d[:4]) for d in hz.convective_day.dropna()})
    rows = []
    for year in years:
        lsrs = iem.fetch_lsr_year(year, cache_dir=config.RAW_DIR / "iem" / "lsr", offline=True)
        for r in lsrs or []:
            if str(r["typetext"]).strip().upper() != "TORNADO" or not r["valid_utc"]:
                continue
            if _key(r["valid_utc"], r["lat"], r["lon"]) in linked:
                continue
            point = to_equal_area(Point(r["lon"], r["lat"]))
            valid = tiering._as_datetime(r["valid_utc"])
            best = None
            for i in tree.query(point.buffer(config.LSR_MATCH_RADIUS_M)):
                h = hz.iloc[i]
                distance = h.proj.distance(point)
                iv = _interval(h)
                if distance > config.LSR_MATCH_RADIUS_M or iv is None:
                    continue
                gap = iem.lsr_time_gap_min(valid, *iv)
                if best is None or gap < best[0]:
                    best = (gap, distance, h.hazard_uid)
            if best and config.LSR_TIME_MARGIN_MIN < best[0] <= MISSED_MAX_H * 60:
                rows.append({"stratum": "lsr_missed", "valid_utc": r["valid_utc"],
                             "lat": r["lat"], "lon": r["lon"],
                             "place": f"{r['city']}, {r['county']} County, {r['state']}",
                             "text": r["remark"], "source": r["source"], "wfo": r["wfo"],
                             "hazard_uid": best[2], "distance_m": round(best[1], 1),
                             "gap_min": round(best[0], 1), "textref_uid": None})
    return pd.DataFrame(rows)


def candidates(tag: str):
    """Every linked LSR (best match), survey section and missed LSR; the shapes
    are built for the sampled cases only (a function of the sample)."""
    P = config.PROCESSED_DIR
    links = pd.read_csv(P / f"textlinks_nws_{tag}.csv", low_memory=False)
    texts = pd.read_csv(P / f"textrefs_nws_{tag}.csv", low_memory=False).set_index("textref_uid")
    hz = handcheck.load_hazards(tag)
    tree = STRtree(list(hz.proj))

    lsr = official.best_lsr_links(links)
    t = texts.loc[lsr.textref_uid]
    lsr_pop = pd.DataFrame({
        "stratum": lsr.lsr_assignment.to_numpy(), "textref_uid": lsr.textref_uid.to_numpy(),
        "hazard_uid": lsr.target_uid.to_numpy(), "valid_utc": t.published_at.to_numpy(),
        "lat": t.lat.to_numpy(), "lon": t.lon.to_numpy(), "place": t.title.to_numpy(),
        "text": t.body.to_numpy(), "source": t.lsr_source.to_numpy(),
        "distance_m": lsr.distance_m.to_numpy(), "gap_min": lsr.lsr_time_gap_min.to_numpy()})
    pns = links[links.link_relation == "primary_survey_of"]
    t = texts.loc[pns.textref_uid]
    pns_pop = pd.DataFrame({
        "stratum": np.where(pns.distance_m <= PNS_NEAR_M, "pns_near", "pns_far"),
        "textref_uid": pns.textref_uid.to_numpy(), "hazard_uid": pns.target_uid.to_numpy(),
        "valid_utc": t.published_at.to_numpy(), "lat": np.nan, "lon": np.nan,
        "place": t.title.to_numpy(), "text": t.body.to_numpy(), "source": "survey statement",
        "distance_m": pns.distance_m.to_numpy(), "gap_min": np.nan})
    linked = {_key(v, a, b) for v, a, b in zip(texts.published_at, texts.lat, texts.lon)
              if pd.notna(a) and pd.notna(b)}
    pop = pd.concat([lsr_pop, pns_pop, missed_lsrs(hz, tree, linked)], ignore_index=True)
    return pop, lambda sample: _shapes(sample, hz, tree, links)


def _section(body: str, hz_row) -> tuple[dict | None, list]:
    """The survey section whose stated endpoints lie nearest the hazard's track."""
    best, best_d = None, None
    for seg in iem.parse_survey_segments(body):
        pts = [p for p in (iem.stated_point(seg["start_lat"], seg["start_lon"]),
                           iem.stated_point(seg["end_lat"], seg["end_lon"])) if p]
        if not pts:
            continue
        d = max(to_equal_area(Point(lon, lat)).distance(hz_row.proj) for lat, lon in pts)
        if best_d is None or d < best_d:
            best, best_d = seg, d
    if best is None:
        return None, []
    pts = [p for p in (iem.stated_point(best["start_lat"], best["start_lon"]),
                       iem.stated_point(best["end_lat"], best["end_lon"])) if p]
    return best, [Point(lon, lat) for lat, lon in pts]


def _shapes(sample: pd.DataFrame, hz: pd.DataFrame, tree: STRtree,
            links: pd.DataFrame) -> dict:
    rng = np.random.default_rng(SHEET_SEED + 1)
    by_uid = hz.set_index("hazard_uid")
    candidates_of = (links[links.link_relation == "describes"]
                     .groupby("textref_uid").target_uid.agg(list))
    out = {}
    for s in sample.itertuples():
        own = by_uid.loc[s.hazard_uid]
        section = None
        if s.stratum.startswith("pns"):
            section, points = _section(s.text, own)
            report = MultiPoint(points) if points else None
            text = section["text"] if section else s.text
        else:
            report = Point(s.lon, s.lat)
            text = s.text
        anchor = to_equal_area(report) if report is not None else own.proj
        days = 3 if s.stratum == "lsr_missed" else 1
        ref_day = (dt.date.fromisoformat(own.convective_day)
                   if s.stratum.startswith("pns") and isinstance(own.convective_day, str)
                   else pd.Timestamp(s.valid_utc).date() if isinstance(s.valid_utc, str)
                   else None)
        near = []
        for i in tree.query(anchor.buffer(SHOW_RADIUS_M)):
            h = hz.iloc[i]
            d = h.proj.distance(anchor)
            hd = dt.date.fromisoformat(h.convective_day) if isinstance(h.convective_day, str) \
                else None
            if d <= SHOW_RADIUS_M and (ref_day is None or hd is None
                                       or abs((hd - ref_day).days) <= days):
                near.append((d, h.hazard_uid))
        near.sort()
        must = {s.hazard_uid} | set(candidates_of.get(s.textref_uid, []) if s.textref_uid else [])
        shown = [u for _, u in near if u in must] + [u for _, u in near if u not in must]
        shown = list(dict.fromkeys(shown + [u for u in must if u in by_uid.index]))
        shown = shown[:max(SHOW_MAX, len(must))]
        order = list(rng.permutation(len(shown)))
        hmap = {f"H{k + 1}": shown[i] for k, i in enumerate(order)}
        dist = dict((u, d) for d, u in near)
        items, layers = [], []
        for k, (h_label, uid) in enumerate(hmap.items()):
            h = by_uid.loc[uid]
            items.append((f"{h_label}: " + handcheck.describe_hazard(h, dist.get(uid)), k))
            layers += handcheck.layers(h.geom, f"c{k}", h_label)
        if report is not None:
            layers += handcheck.layers(report, "report", "report" if not section else "section")
        lsr_cands = candidates_of.get(s.textref_uid, []) if s.textref_uid else []
        out[s.case_id] = {
            "hmap": hmap, "items": items, "layers": layers, "text": text,
            "section_title": section["title"] if section else None,
            "linked_h": next((k for k, u in hmap.items() if u == s.hazard_uid), None),
            "n_candidates": len(lsr_cands)}
    return out


SHEET_COLUMNS = ["case_id", "kind", "time_utc", "place", "report_text", "hazards", "label",
                 "notes"]
KEY_COLUMNS = ["case_id", "stratum", "weight", "textref_uid", "hazard_uid", "linked_h",
               "near_h", "hmap", "distance_m", "gap_min", "n_candidates"]


def sheet_and_key(sample: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    shapes = sample.attrs["shapes"]           # the H numbers (handcheck.write_check)
    pns = sample.stratum.str.startswith("pns")
    sheet = pd.DataFrame({
        "case_id": sample.case_id,
        "kind": np.where(pns, "survey statement", "local storm report"),
        "time_utc": [handcheck.iso_hm(v) for v in sample.valid_utc],
        "place": [shapes[c]["section_title"] or p if pns_ else p
                  for c, p, pns_ in zip(sample.case_id, sample.place, pns)],
        "report_text": [" ".join(str(shapes[c]["text"]).split())[:400] for c in sample.case_id],
        "hazards": [" | ".join(x for x, _ in shapes[c]["items"]) for c in sample.case_id],
        "label": "", "notes": ""})
    linked = sample.stratum != "lsr_missed"
    key = sample.assign(
        linked_h=[shapes[c]["linked_h"] if l else None for c, l in zip(sample.case_id, linked)],
        near_h=[None if l else shapes[c]["linked_h"] for c, l in zip(sample.case_id, linked)],
        hmap=[json.dumps(shapes[c]["hmap"]) for c in sample.case_id],
        n_candidates=[shapes[c]["n_candidates"] for c in sample.case_id])
    return sheet, key[KEY_COLUMNS]


def review_map(sample: pd.DataFrame, sheet: pd.DataFrame, shapes: dict) -> str:
    cases = []
    for s, r in zip(sample.itertuples(), sheet.itertuples()):
        sh = shapes[s.case_id]
        about = [f"{r.kind}, {r.time_utc} UTC", str(r.place)]
        if not s.stratum.startswith("pns") and isinstance(s.source, str):
            about.append(f"source: {s.source}")
        cases.append(handcheck.case(
            s.case_id, f"{r.kind} · {r.time_utc}",
            [("The text (red: the report's place, or the section's start and end)", about),
             ("Hazards nearby (numbered at random)", sh["items"])],
            sh["layers"], text=sh["text"], text_heading="Text"))
    return handcheck.review_map("Official text links", cases,
                                "Label in textlink_sheet.csv: H1, H2, …, none, cannot_tell.")


HOW_TO = f"""How to check the official-text links (stage 35)
===============================================

Each case is a Local Storm Report (LSR) or a section of a storm-survey
statement, with the hazards (tornado tracks) around it numbered H1, H2, ... at
random. Question: which hazard is the text about?

1. Open the map: python -m http.server 8792 --directory outputs/annotation
   then http://127.0.0.1:8792/textlink_review.html  (n / p: next / previous).
2. On the map: the report's place as a red point (for a survey section, the
   start and end it states); the hazards in colour, H1, H2, ...; the panel
   gives each hazard's source (DAT survey or SPC record), time, rating, length
   and distance, and the full text.
3. Label, in textlink_sheet.csv:
   H1, H2, ...  the hazard the text describes: the place lies on or near the
                track and the time falls within it (an LSR may be minutes off
                and up to a few km from the track; a spotter's position, not
                the tornado's). For a survey section: the same start, end,
                rating and length.
   none         none of the hazards shown: another tornado, or no tornado
   cannot_tell  two hazards fit equally, or the text does not say enough
   In notes, say why where it was not obvious ("H2: same time, H1 an hour
   earlier").
4. Do not open textlink_key.csv before you are done.

When done:  python scripts/35_qa_text.py links-check
"""
