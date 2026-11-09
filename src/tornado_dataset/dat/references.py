"""The official tornado records DAT is checked against: NCEI Storm Events and SPC.

Paths shared by stage 13 (download), stage 14 (matching) and stage 17 (the
events report), and the report section on them. The matching itself lives in
:mod:`.storm_events` and :mod:`.spc_tornadoes`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .. import config
from . import spc_tornadoes as spc
from . import storm_events as se
from .evaluate import wilson_interval

RAW_SE = config.RAW_DIR / "storm_events"
RAW_SPC = config.RAW_DIR / "spc"
SE_TORNADOES = config.INTERIM_DIR / "storm_events_tornadoes.csv"
SPC_TRACKS = config.INTERIM_DIR / "spc_tornadoes.csv"


def years() -> list[int]:
    return list(range(config.WINDOW_START.year, config.WINDOW_END.year + 1))


def se_links_path(tag: str) -> Path:
    return config.PROCESSED_DIR / f"storm_events_links_{tag}.csv"


def spc_links_path(tag: str) -> Path:
    return config.PROCESSED_DIR / f"spc_tornado_links_{tag}.csv"


def spc_se_links_path(tag: str) -> Path:
    return config.PROCESSED_DIR / f"spc_storm_events_links_{tag}.csv"


def spc_unmatched_path(tag: str) -> Path:
    return config.INTERIM_DIR / f"spc_unmatched_dat_{tag}.csv"


def crosscheck_path(tag: str) -> Path:
    return config.INTERIM_DIR / f"spc_chain_crosscheck_{tag}.json"


def download() -> tuple[list[dict], dict]:
    """The newest Storm Events details file per year and SPC's tornado file.

    Skips files already present; appends what was downloaded to each source's
    ``provenance.jsonl``.
    """
    records = se.download(years(), RAW_SE)
    with (RAW_SE / "provenance.jsonl").open("a", encoding="utf-8") as fh:
        for r in records:
            if r["status"] == "downloaded":
                fh.write(json.dumps(r) + "\n")
    record = spc.download(RAW_SPC)
    if record["status"] == "downloaded":
        with (RAW_SPC / "provenance.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    return records, record


# ── report section (stage 17) ───────────────────────────────────────────────
def report_lines(tag: str) -> list[str] | None:
    """The reference part of stage 17's report; ``None`` until stage 14 has run.

    Headings start at ``###``, to sit under one section of the events report.
    """
    if not SE_TORNADOES.exists() or not se_links_path(tag).exists():
        return None
    tornadoes = pd.read_csv(SE_TORNADOES, low_memory=False)
    tornadoes["begin_utc"] = pd.to_datetime(tornadoes.begin_utc, utc=True)
    links = pd.read_csv(se_links_path(tag))
    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv", low_memory=False)
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
        "Storm Events rows are matched to DAT hazards (stage 14) when within "
        f"{se.MATCH_DISTANCE_M/1000:g} km and {se.MATCH_GAP_S/60:g} min, in UTC converted "
        "from Storm Data's local standard time.",
        "",
        "> Storm Events has one row per tornado **per county**. Rows are chained into "
        "whole tornadoes through their `TOR_OTHER_*` pointers (`TORNADO_KEY`), and the "
        "tornado counts below are what compare with DAT hazards; the row counts are "
        "county segments.", "",
        "### Coverage by year", "",
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
        "### Episodes", "",
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
    ] + spc_section(tag, hazards, ci) + [
        "### Notes", "",
        "- NCEI revises each year's file in place and publishes the current year with "
        "a lag of months; stage 13 always takes the newest revision.",
        "- `EVENT_ID` and `EPISODE_ID` are joined to hazards by space and time, not by "
        "key: DAT's own `event_id` is free text and does not reliably equal either.",
        "",
    ]
    return lines


def spc_section(tag: str, hazards: pd.DataFrame, ci) -> list[str]:
    """Report lines for the SPC comparison; empty when it was not run."""
    if not SPC_TRACKS.exists() or not spc_links_path(tag).exists():
        return []
    tracks = pd.read_csv(SPC_TRACKS, low_memory=False)
    links = pd.read_csv(spc_links_path(tag))
    check = json.loads(crosscheck_path(tag).read_text()) \
        if crosscheck_path(tag).exists() else {}
    hz_year = hazards.t0.dt.year.fillna(
        pd.to_datetime(hazards.convective_day, errors="coerce").dt.year)
    method = links.get("link_method", pd.Series("spatial_temporal_join", index=links.index))
    strict = links[method == "spatial_temporal_join"]
    lines = ["### SPC whole tracks", "",
             "SPC's database holds one reviewed record per tornado — the official "
             "version of the chaining above. Same matching rule; the last column adds "
             "the time-repaired second pass (next section) and, for hazards whose DAT "
             "survey gives only a date, a match by date within a day.", "",
             "| year | SPC tornadoes | DAT hazards | SPC tornadoes found in DAT | "
             "DAT hazards found in SPC | … all passes |", "|---|---:|---:|---|---|---|"]
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
    lines += [""] + geometry_source_lines(links, hazards)
    return lines + [""] + repair_section(tag, links, hazards, check.get("time_repair", {}))


def geometry_source_lines(links: pd.DataFrame, hazards: pd.DataFrame) -> list[str]:
    """SPC match by what a hazard's geometry rests on, and SPC tracks DAT holds twice."""
    if "geometry_source" not in hazards.columns:
        return []
    best = links[links.rank_for_hazard == 1].drop_duplicates("hazard_uid").set_index("hazard_uid")
    how = hazards.hazard_uid.map(best.link_method).fillna("none")
    t = pd.crosstab(hazards.geometry_source, how)
    cols = [c for c in ("spatial_temporal_join", "time_repaired", "date_only", "none") if c in t]
    names = {"spatial_temporal_join": "strict", "time_repaired": "time repaired",
             "date_only": "by date", "none": "no SPC track"}
    lines = ["#### By geometry source", "",
             "Hazards from damage polygons alone (stage 12: tornadoes DAT surveyed "
             "without drawing a track) are matched by their polygons; most carry a time, "
             "those with only a date are matched by date.", "",
             "| geometry | hazards | " + " | ".join(names[c] for c in cols) + " |",
             "|---|---:|" + "---:|" * len(cols)]
    for src, row in t.iterrows():
        n = int(row.sum())
        lines.append(f"| {src} | {n:,} | " + " | ".join(
            f"{int(row[c]):,} ({row[c] / n:.0%})" for c in cols) + " |")
    if "hazards_on_track" in best.columns:
        shared = best[best.hazards_on_track > 1]
        src = hazards.set_index("hazard_uid").geometry_source
        kinds = shared.assign(s=shared.index.map(src)).groupby("spc_id").s.agg(
            lambda s: "with a polygon-only hazard" if (s == "polygon").any() else "lines only")
        lines += ["", f"- **{shared.spc_id.nunique():,} SPC tracks are the closest of more than "
                  f"one DAT hazard** ({shared.index.nunique():,} hazards; "
                  f"{int((kinds != 'lines only').sum()):,} involve a polygon-only hazard). One "
                  "tornado in DAT twice: a polygon beyond stage 11's linking distance from its "
                  "own line, pieces of one track drawn apart, or a second survey. Kept as they "
                  "are and flagged on the links (`hazards_on_track`): merging them needs the "
                  "SPC track, which stage 12, building hazards from DAT alone, does not use."]
    return lines


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


def repair_section(tag: str, links: pd.DataFrame, hazards: pd.DataFrame, repair: dict) -> list[str]:
    """What the time-repaired second pass found, and the checks on it."""
    if "time_offset_h" not in links.columns:
        return []
    best = links[links.rank_for_hazard == 1].drop_duplicates("hazard_uid")
    first = best[best.link_method == "spatial_temporal_join"]
    fixed = best[best.link_method == "time_repaired"]
    total = len(hazards)
    lines = ["### Time-repaired matches (second pass)", ""]
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
    path = spc_unmatched_path(tag)
    if path.exists():
        left = pd.read_csv(path)
        near = left.nearest_distance_km.notna()
        lines += ["#### Still without an SPC track", "",
                  f"{len(left):,} DAT hazards ({len(left) / total:.1%}). "
                  f"{int(near.sum()):,} have an SPC track within 20 km and 72 h (listed "
                  "with its distance and offset), "
                  f"**{int((~near).sum()):,} have none** — candidates for tornadoes not in "
                  "the official record (reclassified, never submitted, a duplicate or a "
                  f"test entry). One row each in `data/interim/{path.name}`, for a "
                  "hand check.", ""]
    return lines
