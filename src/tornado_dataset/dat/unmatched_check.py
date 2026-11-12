"""Hand check of the DAT hazards with no SPC track (stage 17 ``unmatched``).

357 DAT hazards have no SPC track, so they are in no episode and keep DAT's own
values. Stage 15 gives each a ``spc_match_status`` from where the nearest SPC
track is: on it at another time (``time_mismatch``), on a track another DAT
hazard holds (``probable_duplicate``), 5–20 km away (``spc_far``), nothing
within 20 km and 72 h (``no_spc_nearby``), or no time to search with
(``untimed_no_spc``). What each really is decides whether it stays a hazard of
its own, joins an SPC track, or goes: a tornado SPC's database lacks, the same
tornado as an SPC track (DAT's time or place wrong), a duplicate of another DAT
hazard, or not a tornado.

The sample is stratified by status. The annotator sees the DAT hazard, the SPC
tracks within ``SPC_NEAR_M`` and ``DAYS`` (S1, S2, … by distance), the other DAT
hazards within ``DAT_NEAR_M`` (D1, …), DAT's own comment and the reports linked
to it (stage 20); the key maps S and D to IDs and holds the measures.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd
from shapely.strtree import STRtree

from .. import config, handcheck
from . import episode_table
from . import references as refs
from .geometry import to_equal_area
from .spc_tornadoes import track_geometries

PREFIX = "U"
SHEET_SEED = 20261113
LABELS = ("real_tornado", "same_as_spc", "duplicate_dat", "not_a_tornado", "cannot_tell")
STRATA = {"no_spc_nearby": 20, "untimed_no_spc": 12, "spc_far": 12,
          "probable_duplicate": 12, "time_mismatch": 14}
SPC_NEAR_M = 20_000.0
DAT_NEAR_M = 5_000.0
DAYS = 3
MAX_SHOWN = 6


def paths() -> dict[str, Path]:
    a = handcheck.ANNOTATION
    return {"sheet": a / "unmatched_sheet.csv", "key": a / "unmatched_key.csv",
            "map": a / "unmatched_review.html", "how_to": a / "HOW_TO_ANNOTATE_unmatched.txt",
            "manifest": a / "manifest_annotation_unmatched.json"}


def _day(value) -> dt.date | None:
    return dt.date.fromisoformat(value[:10]) if isinstance(value, str) else None


def candidates(tag: str) -> tuple[pd.DataFrame, dict[str, dict]]:
    """Every DAT hazard with no SPC track, with what the sheet, key and map need."""
    member = episode_table.membership(tag)
    dat = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv", low_memory=False
                      ).set_index("hazard_uid")
    hz = handcheck.load_hazards(tag).set_index("hazard_uid")
    tracks = pd.read_csv(refs.SPC_TRACKS, low_memory=False)
    tracks["geom"] = track_geometries(tracks, lambda g: g)
    tracks = tracks[tracks.geom.notna()].reset_index(drop=True)
    tracks["proj"] = [to_equal_area(g) for g in tracks.geom]
    tracks["day"] = pd.to_datetime(tracks.begin_utc, utc=True).dt.date
    spc_tree = STRtree(list(tracks.proj))
    dat_hz = hz[hz.hazard_source == "dat"]
    dat_ids = list(dat_hz.index)
    dat_tree = STRtree(list(dat_hz.proj))
    texts = _linked_texts(tag)
    se = pd.read_csv(config.PROCESSED_DIR / f"storm_events_links_{tag}.csv",
                     usecols=["EVENT_ID", "hazard_uid"])
    se_of = se.groupby("hazard_uid").EVENT_ID.agg(lambda s: sorted(set(s)))

    pop = member[(member.hazard_source == "dat") & member.episode_uid.isna()].copy()
    pop["stratum"] = pop.spc_match_status
    rows, shapes = [], {}
    for m in pop.itertuples():
        h = hz.loc[m.hazard_uid]
        d = dat.loc[m.hazard_uid]
        day = _day(h.convective_day) or _day(d.convective_day)
        lo, hi = ((day - dt.timedelta(days=DAYS), day + dt.timedelta(days=DAYS))
                  if day else (None, None))
        near_spc = []
        for i in spc_tree.query(h.proj.buffer(SPC_NEAR_M)):
            t = tracks.iloc[i]
            dist = t.proj.distance(h.proj)
            if dist <= SPC_NEAR_M and (day is None or lo <= t.day <= hi):
                near_spc.append((dist, t))
        near_spc = sorted(near_spc, key=lambda x: (x[0], x[1].spc_id))[:MAX_SHOWN]
        near_dat = []
        for i in dat_tree.query(h.proj.buffer(DAT_NEAR_M)):
            uid = dat_ids[i]
            o = dat_hz.loc[uid]
            if uid == m.hazard_uid:
                continue
            od = _day(o.convective_day)
            dist = o.proj.distance(h.proj)
            if dist <= DAT_NEAR_M and (day is None or od is None or lo <= od <= hi):
                near_dat.append((dist, uid, o))
        near_dat = sorted(near_dat, key=lambda x: (x[0], x[1]))[:MAX_SHOWN]

        spc_text = [f"S{k}: {handcheck.iso_hm(t.begin_utc)}–{handcheck.iso_hm(t.end_utc)[11:]} "
                    f"UTC, {'EF' + str(int(t.mag)) if t.mag >= 0 else 'EFU'}, {t.len} mi, {t.st}, "
                    f"{dist / 1000:.1f} km away"
                    for k, (dist, t) in enumerate(near_spc, 1)]
        dat_text = [f"D{k}: " + handcheck.describe_hazard(o, dist)
                    for k, (dist, _, o) in enumerate(near_dat, 1)]
        own = handcheck.describe_hazard(h)
        extra = [f"DAT office {d.wfo}" if isinstance(d.wfo, str) else None,
                 f"event_id {d.dat_event_ids}" if isinstance(d.dat_event_ids, str) else None,
                 f"{int(d.n_lines)} line(s), {int(d.n_polygons)} polygon(s)",
                 f"Storm Events {';'.join(map(str, se_of[m.hazard_uid]))}"
                 if m.hazard_uid in se_of.index else "no Storm Events match"]
        linked = texts.get(m.hazard_uid, [])
        map_layers = [x for k, (_, uid, o) in enumerate(near_dat, 1)
                      for x in handcheck.layers(o.geom, "grey", f"D{k}")]
        map_layers += [x for k, (_, t) in enumerate(near_spc, 1)
                       for x in handcheck.layers(t.geom, "spc", f"S{k}")]
        map_layers += handcheck.layers(h.geom, "c0", "DAT")
        shapes[m.hazard_uid] = {
            "own": own, "extra": [e for e in extra if e], "spc_text": spc_text,
            "dat_text": dat_text, "texts": linked, "comment": d.oracle_text
            if isinstance(d.oracle_text, str) else None, "layers": map_layers}
        nearest = near_spc[0] if near_spc else None
        rows.append({
            "hazard_uid": m.hazard_uid, "stratum": m.stratum,
            "convective_day": day.isoformat() if day else "",
            "dat_hazard": own + "; " + "; ".join(e for e in extra if e),
            "spc_nearby": " | ".join(spc_text), "dat_nearby": " | ".join(dat_text),
            "n_texts": len(linked),
            "dat_comment": (d.oracle_text[:300] if isinstance(d.oracle_text, str) else ""),
            "spc_ids": json.dumps({f"S{k}": t.spc_id for k, (_, t) in enumerate(near_spc, 1)}),
            "dat_ids": json.dumps({f"D{k}": uid for k, (_, uid, _) in enumerate(near_dat, 1)}),
            "nearest_spc_km": round(nearest[0] / 1000, 2) if nearest else None,
            "nearest_spc_offset_h": m.spc_nearest_offset_h,
            "has_storm_events": m.hazard_uid in se_of.index,
            "has_time": isinstance(h.begin_utc, str),
            "efscale": d.efscale, "n_lines": int(d.n_lines)})
    return pd.DataFrame(rows), shapes


def _linked_texts(tag: str) -> dict[str, list[str]]:
    """Each hazard's linked LSRs (best match) and survey sections, one line each."""
    from ..text import official

    refs_path = config.PROCESSED_DIR / f"textrefs_nws_{tag}.csv"
    links_path = config.PROCESSED_DIR / f"textlinks_nws_{tag}.csv"
    if not (refs_path.exists() and links_path.exists()):
        return {}
    links = pd.read_csv(links_path, low_memory=False)
    keep = pd.concat([official.best_lsr_links(links),
                      links[links.link_relation == "primary_survey_of"]])
    texts = pd.read_csv(refs_path, usecols=["textref_uid", "source_type", "published_at",
                                            "title", "body"], low_memory=False
                        ).set_index("textref_uid")
    out: dict[str, list[str]] = {}
    for uid, ref in zip(keep.target_uid, keep.textref_uid):
        t = texts.loc[ref]
        body = " ".join(str(t.body).split())
        line = (f"LSR {handcheck.iso_hm(t.published_at)} UTC: {t.title} — {body[:200]}"
                if t.source_type == "lsr" else
                f"Survey statement issued {handcheck.iso_hm(t.published_at)} UTC: {t.title}")
        out.setdefault(uid, []).append(line)
    return out


SHEET_COLUMNS = ["case_id", "convective_day", "dat_hazard", "spc_nearby", "dat_nearby",
                 "n_texts", "dat_comment", "spc_reports", "label", "notes"]
KEY_COLUMNS = ["case_id", "hazard_uid", "stratum", "weight", "spc_ids", "dat_ids",
               "nearest_spc_km", "nearest_spc_offset_h", "has_storm_events", "has_time",
               "efscale", "n_lines"]


def sheet_and_key(sample: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sheet = sample.assign(
        spc_reports=[f"https://www.spc.noaa.gov/climo/reports/{pd.Timestamp(d):%y%m%d}_rpts.html"
                     if d else "" for d in sample.convective_day],
        label="", notes="")
    return sheet[SHEET_COLUMNS], sample[KEY_COLUMNS]


def review_map(sample: pd.DataFrame, sheet: pd.DataFrame, shapes: dict[str, dict]) -> str:
    cases = []
    for s, r in zip(sample.itertuples(), sheet.itertuples()):
        sh = shapes[s.hazard_uid]
        cases.append(handcheck.case(
            s.case_id, s.convective_day or "no date",
            [("The DAT hazard (blue)", [(sh["own"], 0)] + sh["extra"]),
             (f"SPC tornadoes within {SPC_NEAR_M / 1000:g} km and {DAYS} days (dashed black)",
              sh["spc_text"] or ["none"]),
             (f"Other DAT hazards within {DAT_NEAR_M / 1000:g} km and {DAYS} days (dashed grey)",
              sh["dat_text"]),
             ("Reports and survey statements linked to it (stage 20)", sh["texts"])],
            sh["layers"], [("SPC reports of the day", r.spc_reports)],
            text=sh["comment"], text_heading="DAT's comment"))
    return handcheck.review_map(
        "DAT hazards with no SPC track", cases,
        "Label in unmatched_sheet.csv: " + ", ".join(LABELS) + ".")


HOW_TO = f"""How to check the DAT hazards with no SPC track (stage 17)
==========================================================

Each case is a DAT hazard that no SPC tornado was matched to. Question: what is
it?

1. Open the map: python -m http.server 8792 --directory outputs/annotation
   then http://127.0.0.1:8792/unmatched_review.html  (n / p: next / previous).
2. On the map: the DAT hazard in blue; SPC tornadoes within {SPC_NEAR_M / 1000:g} km and
   {DAYS} days dashed black (S1, S2, ... nearest first); other DAT hazards within
   {DAT_NEAR_M / 1000:g} km dashed grey (D1, ...). The panel gives times, ratings,
   lengths, DAT's comment, and the reports and survey statements linked to it.
3. Decide, in unmatched_sheet.csv:
   real_tornado   a tornado that SPC's database lacks: no SPC tornado matches it
                  in place and rating, and something (comment, reports, Storm
                  Events) says it happened
   same_as_spc    the same tornado as an SPC track: same path and rating, but
                  DAT's time or date or place is off. Put the S number in notes
   duplicate_dat  the same tornado as another DAT hazard. Put the D number in notes
   not_a_tornado  not a tornado: a test or training entry, wind damage, a
                  misfiled feature
   cannot_tell    the evidence does not settle it
   The SPC report page (spc_reports) and NCEI Storm Events can help.
4. Do not open unmatched_key.csv before you are done.

When done:  python scripts/17_qa_events.py unmatched-check
"""
