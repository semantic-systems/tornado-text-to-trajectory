#!/usr/bin/env python
"""Stage 26 — SPC watch systems as a cross-office episode reference.

Plan: ``docs/plan_watch_linking.md`` (steps 0–4; step 5, the third reference in
stage 25, is separate).

    python scripts/26_watch_systems.py probe     # step 0: feasibility, on a sample
    python scripts/26_watch_systems.py fetch     # step 1: ~225 cached IEM requests + county boundaries
    python scripts/26_watch_systems.py link      # steps 2–4, offline; report and sensitivity
    python scripts/26_watch_systems.py run       # fetch + link
    python scripts/26_watch_systems.py link --no-motion-check   # variant, own files
    python scripts/26_watch_systems.py sheets    # hand-check worksheets → outputs/annotation/
    python scripts/26_watch_systems.py review    # label them on a map → http://127.0.0.1:8800
    python scripts/26_watch_systems.py check     # score them once filled in

``link`` builds watch systems by three rules (plan, step 3): watches in force
in the same county at the same time; explicit "replaces watch N"; and inferred
succession — B starts within ``--gap-h`` of A's end, within ``--edge-km`` of A's
counties at the hand-over (county edge to county edge, Census 2020 boundaries),
and not upstream of A's storm motion by more than a tolerance calibrated on the
"replaces" links (``--motion-slack-km`` sets it by hand). Each SPC
tornado then takes the system of the watch its county was under (step 4).

A ``link`` with ``--variant NAME`` writes every output with a ``_NAME`` suffix
and leaves the main ones alone; ``--no-motion-check`` implies ``--variant
no-motion``. Stage 25 scores against the main systems and, where present, the
``no-motion`` variant, to show whether a conclusion depends on the check.

``probe`` answers the questions the plan leaves open before any linking is
built, on a small sample (about 25 requests to the IEM archive, cached under
``data/raw/spc_watches/probe/``):

1. From which year are county-level watch records complete?
2. Do county records carry the watch number and type, so they join the watch
   attributes (storm motion, PDS)?
3. How do counties' own end times differ from the watch's nominal expiry —
   how much does county-level timing matter?
4. For SPC tornadoes, do the official counties and the polygons put the same
   tornadoes in the same watches?
5. How often do the watch texts state succession ("replaces watch N"), and does
   it parse?

Writes ``outputs/watch_probe_report.md``. Needs stage 24's SPC tracks
(``data/interim/spc_tornadoes.csv``) for question 4.
"""

from __future__ import annotations

import argparse
import json

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config
from tornado_dataset.dat import episodes as ep
from tornado_dataset.dat import spc_watches as sw
from tornado_dataset.dat import storm_events as se
from tornado_dataset.http import utcnow_iso
from tornado_dataset.ids import write_manifest

RAW = config.RAW_DIR / "spc_watches"
PROBE_DIR = RAW / "probe"
SPC_TRACKS = config.INTERIM_DIR / "spc_tornadoes.csv"
PROBE_REPORT = config.OUTPUT_DIR / "watch_probe_report.md"
PROBE_JSON = config.INTERIM_DIR / "watch_probe.json"
RAW_CENSUS = config.RAW_DIR / "census"
REPORT = config.OUTPUT_DIR / "watch_systems_report.md"
GRID_GAP_H = (1, 3, 6)
GRID_EDGE_KM = (0, 50, 150)
# Validation 3 of the plan: well-documented outbreaks, read against NWS and SPC
# event summaries by hand. Dates are convective days (12 UTC to 12 UTC).
# Well-documented outbreaks with official summaries, spread over years, seasons
# and storm types: multi-day sequences (Apr 2011, Dec 2015, May 2019), cool-season
# and overnight events (Nov 2013, Jan 2017, Dec 2021), early spring (Mar 2012).
NAMED_OUTBREAKS = [("2011-04-25", "2011-04-28"), ("2012-03-02", "2012-03-03"),
                   ("2013-11-17", "2013-11-17"), ("2015-12-23", "2015-12-28"),
                   ("2017-01-21", "2017-01-23"), ("2019-05-27", "2019-05-29"),
                   ("2020-04-12", "2020-04-13"), ("2021-12-10", "2021-12-11"),
                   ("2023-03-31", "2023-04-01"), ("2024-04-26", "2024-04-28")]


def tag_default() -> str:
    return f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"


def years() -> list[int]:
    return list(range(config.WINDOW_START.year, config.WINDOW_END.year + 1))


def out_paths(tag: str, variant: str = "") -> dict:
    """Outputs of ``link``; a variant's carry its name, so the main ones stay."""
    v = f"_{variant}" if variant else ""
    return {"watches": config.INTERIM_DIR / f"spc_watches_{tag}{v}.csv",
            "links": config.INTERIM_DIR / f"spc_watch_links_{tag}{v}.csv",
            "review": config.INTERIM_DIR / f"spc_watch_review_{tag}{v}.csv",
            "sensitivity": config.INTERIM_DIR / f"spc_watch_sensitivity_{tag}{v}.csv",
            "tornadoes": config.PROCESSED_DIR / f"spc_watch_systems_{tag}{v}.csv"}


def report_path(variant: str = ""):
    return config.OUTPUT_DIR / (f"watch_systems_{variant}_report.md" if variant
                                else "watch_systems_report.md")


def variant_of(args) -> str:
    """``--variant`` as given; else ``no-motion`` for ``--no-motion-check``, else main."""
    if args.variant is not None:
        return args.variant
    return "no-motion" if args.no_motion_check else ""


def _month(ym: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.Timestamp(ym + "-01", tz="UTC")
    return start, start + pd.offsets.MonthBegin(1)


def cmd_probe(args) -> None:
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    result: dict = {"generated": utcnow_iso(), "season": [args.season_start, args.season_end]}

    # 1–2. Coverage per year: one month (April) of county records against polygons.
    print("coverage per year (April):")
    cov_rows = []
    for year in range(args.first_year, args.last_year + 1):
        sts, ets = _month(f"{year}-04")
        records = sw.parse_county_records(sw.fetch_county_records(sts, ets, PROBE_DIR))
        polygons = sw.parse_polygons(sw.fetch_polygons(sts, ets, PROBE_DIR))
        row = {"year": year, **sw.coverage(records, polygons), "county_rows": len(records)}
        cov_rows.append(row)
        print(f"  {year}  polygons {row['polygon_watches']:>4}  with county records "
              f"{row['with_county_records']:>4} ({row['share']:.0%})  "
              f"county rows {row['county_rows']:,}")
    result["coverage"] = cov_rows

    # 3–4. One season in detail.
    sts, ets = pd.Timestamp(args.season_start, tz="UTC"), pd.Timestamp(args.season_end, tz="UTC")
    records = sw.parse_county_records(sw.fetch_county_records(sts, ets, PROBE_DIR))
    polygons = sw.parse_polygons(sw.fetch_polygons(sts, ets, PROBE_DIR))
    result["season_coverage"] = sw.coverage(records, polygons)
    result["timing"] = sw.county_timing(records, polygons)
    print(f"\nseason {args.season_start}–{args.season_end}: {len(polygons):,} watches, "
          f"{len(records):,} county records; timing {result['timing']}")

    if SPC_TRACKS.exists():
        tracks = pd.read_csv(SPC_TRACKS, low_memory=False)
        t0 = pd.to_datetime(tracks.begin_utc, utc=True)
        tracks = tracks[(t0 >= sts) & (t0 < ets)].reset_index(drop=True)
        result["tornadoes"] = sw.summarise_hits(tracks, sw.county_hits(tracks, records),
                                                sw.polygon_hits(tracks, polygons))
        print(f"tornadoes: {result['tornadoes']}")
    else:
        print(f"no {SPC_TRACKS.name} — run scripts/24_storm_events.py join; "
              "skipping the tornado comparison")

    # 5. Watch texts: the season month by month (under IEM's per-request cap),
    # plus recent months, since the product format changed to mixed case.
    months = pd.date_range(sts, ets, freq="MS", inclusive="left").strftime("%Y-%m").tolist()
    texts = []
    for ym in months + args.text_months:
        a, b = _month(ym)
        parsed = sw.parse_watch_texts(sw.fetch_texts("SEL", a, b, PROBE_DIR))
        parsed["month"] = ym
        texts.append(parsed)
    texts = pd.concat(texts, ignore_index=True)
    result["texts"] = text_summary(texts)
    print(f"watch texts: {result['texts']['by_month']}")

    PROBE_JSON.parent.mkdir(parents=True, exist_ok=True)
    PROBE_JSON.write_text(json.dumps(result, indent=2, default=str))
    write_probe_report(result, texts)
    print(f"\nwrote {PROBE_JSON}\nwrote {PROBE_REPORT}")


def text_summary(texts: pd.DataFrame) -> dict:
    by_month = []
    for ym, g in texts.groupby("month"):
        watches = g[~g.cancellation & g.num.notna()]
        by_month.append({
            "month": ym, "products": len(g),
            "watches": int(watches.num.nunique()),
            "cancellations": int(g.cancellation.sum()),
            "unidentified": int(g.num.isna().sum()),
            "with_replaces": int((watches.replaces.str.len() > 0).sum()),
            "with_not_in_effect": int((watches.not_in_effect.str.len() > 0).sum()),
            "with_continue_list": int((watches.continues.str.len() > 0).sum()),
        })
    return {"by_month": by_month}


def write_probe_report(r: dict, texts: pd.DataFrame) -> None:
    def pct(v):
        return "—" if v is None or pd.isna(v) else f"{v:.0%}"

    lines = [
        "# SPC watch archive — feasibility probe (stage 26)", "",
        f"Generated {r['generated']}. Plan: `docs/plan_watch_linking.md`, step 0. "
        "Sources: IEM VTEC county records (`watchwarn.py`, TO.A/SV.A), IEM SPC watch "
        "polygons (`spc_watch.py`), SPC SEL watch texts (IEM text archive). Responses "
        "are cached under `data/raw/spc_watches/probe/`.", "",
        "## 1–2. County records per year (April)", "",
        "| year | watches (polygons) | with county records | type agrees | county rows |",
        "|---|---:|---:|---:|---:|",
    ]
    for c in r["coverage"]:
        lines.append(f"| {c['year']} | {c['polygon_watches']:,} | "
                     f"{c['with_county_records']:,} ({pct(c['share'])}) | "
                     f"{pct(c['type_agrees'])} | {c['county_rows']:,} |")
    sc, tm = r["season_coverage"], r["timing"]
    lines += [
        "", "Read: the first year at ~100% is where county records can be the primary "
        "source; earlier years need the polygon fallback.", "",
        f"## 3. County timing — season {r['season'][0]} to {r['season'][1]}", "",
        f"- {sc['polygon_watches']:,} watches, {pct(sc['share'])} with county records.",
        f"- Of {tm.get('county_records_joined', 0):,} county records joined to their "
        f"watch: **{pct(tm.get('cleared_early_share'))} ended more than 30 min before "
        f"the watch's expiry** (median {tm.get('median_minutes_early', 0):.0f} min early), "
        f"{pct(tm.get('extended_share'))} more than 30 min after it.",
        "", "Read: a large early share means polygons overstate where and when a watch "
        "was in force, and county timing matters.", "",
    ]
    t = r.get("tornadoes")
    if t:
        lines += [
            "## 4. Tornadoes: counties against polygons", "",
            f"{t['tornadoes']:,} SPC tracks in the season ({t['unknown_county']:,} without a "
            "county code in SPC's record, so not placeable by county).", "",
            "| | in a watch by polygon | not by polygon |", "|---|---:|---:|",
            f"| **in a watch by county** | {t['both']:,} | {t['county_only']:,} |",
            f"| **not by county** | {t['polygon_only']:,} | {t['neither']:,} |", "",
            f"- Of tornadoes in a watch both ways, **{pct(t['same_watch_share'])}** are in "
            "the same watch(es).",
            f"- {t['county_under_two_watches']:,} tornadoes' counties were under two watches "
            "at once (rule 1 of step 3 links those watches; expected rare).", "",
        ]
    lines += ["## 5. Watch texts (SEL)", "",
              "| month | products | watches | cancellations | unidentified | "
              "“replaces” | “will not be in effect” | “CONTINUE…WW” list |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for m in r["texts"]["by_month"]:
        lines.append(f"| {m['month']} | {m['products']:,} | {m['watches']:,} | "
                     f"{m['cancellations']:,} | {m['unidentified']:,} | "
                     f"{m['with_replaces']:,} | {m['with_not_in_effect']:,} | "
                     f"{m['with_continue_list']:,} |")
    examples = texts[texts.replace_snippet.notna()].head(10)
    lines += ["", "The “CONTINUE…WW” list names watches still in effect elsewhere — "
              "concurrency, not succession. Explicit succession is the “replaces” "
              "statement. *Unidentified* products have no recognisable watch number and "
              "should be read before trusting the counts.", ""]
    if len(examples):
        lines += ["Replacement statements found (NWS text, public domain), for a hand "
                  "check of the parse:", ""]
        for e in examples.itertuples():
            lines.append(f"- {e.type} {int(e.num) if pd.notna(e.num) else '?'} → replaces "
                         f"{e.replaces}: “…{e.replace_snippet}…”")
    else:
        lines.append("No replacement statements were found in the sampled texts.")
    lines += ["", "## What decides the design", "",
              "- County records complete from the first year of the window → primary "
              "source as planned; otherwise polygons for the years before.",
              "- Replacement statements present and parsing in ≥95% of a hand-checked "
              "sample → step 3 rule 2 is used; rare or unparseable → inferred succession "
              "only, and the plan says so.",
              "- Counties and polygons disagreeing for a material share of tornadoes → the "
              "county choice is justified by numbers, and validation 5 reports it.", ""]
    PROBE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PROBE_REPORT.write_text("\n".join(lines), encoding="utf-8")


# ── steps 1–4 ───────────────────────────────────────────────────────────────
def cmd_fetch(args) -> None:
    print(f"fetching {len(years())} years from IEM (cached under {RAW}) …")
    for y in years():
        r = sw.fetch_year(y, RAW, refresh=args.refresh)
        print(f"  {y}  county records {r['county_records']:>7,}  watches {r['watches']:>5,}  "
              f"SEL products {r['sel_products']:>5,}")
    g = sw.fetch_county_boundaries(RAW_CENSUS)
    print(f"  Census county boundaries  {g['status']:<10} {g['file']}")


def load_all() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    parts = [sw.load_year(y, RAW) for y in years()]
    return tuple(pd.concat(x, ignore_index=True) for x in zip(*parts))


def office_reference(tag: str) -> pd.DataFrame | None:
    path = config.PROCESSED_DIR / f"spc_storm_events_links_{tag}.csv"
    if not path.exists():
        return None
    links = pd.read_csv(path).rename(columns={"spc_id": "hazard_uid"})
    return se.hazard_episode_reference(links).rename(columns={"hazard_uid": "spc_id"})


def agreement(assign: pd.DataFrame, ref: pd.DataFrame | None) -> dict:
    """Validation 2: Storm Events episodes against watch systems, on watched tornadoes."""
    if ref is None:
        return {}
    m = assign[["spc_id", "system_id"]].merge(ref, on="spc_id", how="left")
    m.loc[m.system_id.isna(), ["EPISODE_ID", "LINKED_EPISODE"]] = None
    labels = pd.Series(pd.factorize(m.system_id.fillna("none"))[0], index=m.index)
    out = {f"office_{k}": v for k, v in ep.score(labels, m).items()}
    if "LINKED_EPISODE" in m.columns:
        out |= {f"linked_{k}": v for k, v in ep.score(labels, m, "LINKED_EPISODE").items()}
    return out


def explicit_recovered(watches, l1, l2, l3) -> float:
    """Share of SPC's own "replaces" links that rules 1 and 3 alone also produce."""
    if not len(l2):
        return float("nan")
    sid = dict(zip(watches.wid, sw.systems(watches, pd.concat([l1, l3]))))
    return float(sum(sid.get(a) == sid.get(b) for a, b in zip(l2.a, l2.b)) / len(l2))


def cmd_link(args) -> None:
    variant = variant_of(args)
    paths = out_paths(args.tag, variant)
    if variant:
        print(f"variant {variant!r}: outputs get a _{variant} suffix; the main ones are kept")
    print("loading cached watches …")
    records, polygons, texts = load_all()
    zip_path = RAW_CENSUS / sw.COUNTY_BOUNDARIES.rsplit("/", 1)[1]
    if not zip_path.exists():
        raise SystemExit(f"no {zip_path.name} — run `fetch`")
    geo = sw.load_counties(zip_path)
    records, cleaning = sw.clean_county_records(records, polygons)
    print(f"county records: {cleaning}")
    watches, counties = sw.build_watches(records, polygons, texts)
    no_boundary = float((~counties.ugc.isin(geo.ugc)).mean())
    print(f"{len(watches):,} watches, {len(counties):,} county spans "
          f"({no_boundary:.1%} without a county boundary)")

    fp = sw.Footprints(watches, counties, geo)
    l1 = sw.concurrent_links(counties)
    l2 = sw.explicit_links(watches)
    explicit = sw.measure_links(l2, fp)
    cal = sw.calibrate_motion_slack(explicit)
    by_hand = args.motion_slack_km is not None
    slack = args.motion_slack_km * 1000 if by_hand else cal["slack_m"]
    how = ("set" if by_hand else f"calibrated on {cal['n']} replaces links"
           if cal["calibrated"] else "fallback")
    print(f"rule 1 concurrent: {len(l1):,}   rule 2 replaces: {len(l2):,}   "
          f"upstream tolerance {slack / 1000:.0f} km ({how})   rule 3 candidates …")
    cand = sw.succession_candidates(watches, fp)
    l3, rejected = sw.inferred_links(cand, gap_s=args.gap_h * 3600, edge_m=args.edge_km * 1000,
                                     motion_check=not args.no_motion_check,
                                     motion_slack_m=slack)
    print(f"rule 3 succession: {len(l3):,} (rejected upstream: {len(rejected):,})")
    links = pd.concat([l1, l2, l3], ignore_index=True)
    watches["system_id"] = sw.systems(watches, links)
    watches["sequence_id"] = sw.systems(watches, sw.sequence_links(links), "wq_")
    system_of = dict(zip(watches.wid, watches.system_id))
    sequence_of = dict(zip(watches.wid, watches.sequence_id))

    tracks = pd.read_csv(SPC_TRACKS, low_memory=False)
    tracks = tracks[tracks.yr.isin(years())].reset_index(drop=True)
    assign = sw.assign_tornadoes(tracks, counties, polygons, system_of, sequence_of)
    ref = office_reference(args.tag)

    grid = []
    slacks = [("0", 0.0), ("calibrated", cal["slack_m"]), ("2× calibrated", 2 * cal["slack_m"]),
              ("off", None)]
    for gh in GRID_GAP_H:
        for dk in GRID_EDGE_KM:
            for label, sl in slacks:
                g3, _ = sw.inferred_links(cand, gap_s=gh * 3600, edge_m=dk * 1000,
                                          motion_check=sl is not None,
                                          motion_slack_m=sl or 0.0)
                gsys = dict(zip(watches.wid, sw.systems(watches, pd.concat([l1, l2, g3]))))
                ga = assign.assign(system_id=assign.watches.map(
                    lambda w: None if pd.isna(w) else gsys.get(w.split(";")[0])))
                sizes = ga.dropna(subset=["system_id"]).groupby("system_id").size()
                grid.append({"gap_h": gh, "edge_km": dk, "upstream_tolerance": label,
                             "upstream_tolerance_km": None if sl is None else sl / 1000,
                             "systems_with_tornadoes": len(sizes),
                             "largest_tornadoes": int(sizes.max()) if len(sizes) else 0,
                             "explicit_recovered": explicit_recovered(watches, l1, l2, g3),
                             **{k: v for k, v in agreement(ga, ref).items()
                                if k in ("office_recall", "office_se_episodes_split",
                                         "linked_recall")}})
    grid = pd.DataFrame(grid)

    for p in paths.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    watches.to_csv(paths["watches"], index=False)
    links.to_csv(paths["links"], index=False)
    rejected.to_csv(paths["review"], index=False)
    grid.to_csv(paths["sensitivity"], index=False)
    assign.to_csv(paths["tornadoes"], index=False)
    def beyond_speed(df):
        ok = df.speed_reach_m.notna() & df.centre_m.notna()
        return float((df.centre_m[ok] > df.speed_reach_m[ok]).mean()) if ok.any() else float("nan")

    summary = {
        "watches": len(watches), "county_spans": len(counties),
        "county_spans_without_boundary": no_boundary, "cleaning": cleaning,
        "calibration": cal, "upstream_tolerance_m": slack, "upstream_tolerance_set": by_hand,
        "rule3_beyond_speed": beyond_speed(l3), "rule2_beyond_speed": beyond_speed(explicit),
        "speed_split": {
            name: {"n": int(len(df)), "beyond": beyond_speed(df)}
            for name, df in (("rule3_overlapping", l3[l3.gap_s < 0]),
                             ("rule3_sequential", l3[l3.gap_s >= 0]),
                             ("rule2_overlapping", explicit[explicit.gap_s < 0]),
                             ("rule2_sequential", explicit[explicit.gap_s >= 0]))},
        "rule1_links": len(l1), "rule2_links": len(l2), "rule3_links": len(l3),
        "rule2_unmatched": l2.attrs.get("unmatched", 0),
        "rule3_rejected_upstream": len(rejected),
        "systems": int(watches.system_id.nunique()),
        "sequences": int(watches.sequence_id.nunique()),
        "extent": {"system": tornado_extent(assign, tracks, "system_id"),
                   "sequence": tornado_extent(assign, tracks, "sequence_id")},
        "explicit_recovered": explicit_recovered(watches, l1, l2, l3),
        "tornadoes": len(assign), "tornadoes_in_watch": int((assign.method != "none").sum()),
        "tornadoes_in_two_systems": int((assign.n_systems > 1).sum()),
        **agreement(assign, ref),
        "gap_h": args.gap_h, "edge_km": args.edge_km, "motion_check": not args.no_motion_check,
        "variant": variant,
    }
    report = report_path(variant)
    write_report(summary, watches, counties, assign, grid, ref is not None, report)
    suffix = f"_{variant}" if variant else ""
    write_manifest(config.PROCESSED_DIR / f"manifest_watch_systems_{args.tag}{suffix}.json",
                   "26_watch_systems", counts={k: v for k, v in summary.items()
                                               if isinstance(v, (int, float, bool))},
                   outputs=list(paths.values()))
    print(f"{summary['systems']:,} watch systems; {summary['tornadoes_in_watch']:,}/"
          f"{summary['tornadoes']:,} SPC tornadoes in a watch")
    for p in [*paths.values(), report]:
        print(f"wrote {p}")


def cmd_run(args) -> None:
    cmd_fetch(args)
    cmd_link(args)


def tornado_extent(assign: pd.DataFrame, tracks: pd.DataFrame, col: str) -> dict:
    """How far apart a group's tornadoes start, weighted by tornadoes (km)."""
    import numpy as np
    from pyproj import Transformer

    a = assign[["spc_id", col]].dropna().merge(tracks[["spc_id", "slat", "slon"]], on="spc_id")
    x, y = Transformer.from_crs(config.CRS_WGS84, config.CRS_EQUAL_AREA,
                                always_xy=True).transform(a.slon.to_numpy(), a.slat.to_numpy())
    g = a.assign(x=x / 1000, y=y / 1000).groupby(col).agg(
        n=("spc_id", "size"), x0=("x", "min"), x1=("x", "max"), y0=("y", "min"), y1=("y", "max"))
    g["e"] = np.hypot(g.x1 - g.x0, g.y1 - g.y0)
    w = np.repeat(g.e.to_numpy(), g.n.to_numpy())
    return {"groups": int(len(g)), "largest": int(g.n.max()) if len(g) else 0,
            "p50_km": float(np.percentile(w, 50)) if len(w) else float("nan"),
            "p90_km": float(np.percentile(w, 90)) if len(w) else float("nan"),
            "max_km": float(g.e.max()) if len(g) else float("nan")}


def system_table(watches: pd.DataFrame, counties: pd.DataFrame,
                 assign: pd.DataFrame) -> pd.DataFrame:
    """Per system: watches, tornadoes, offices, span in hours."""
    wfo = counties.assign(system_id=counties.wid.map(dict(zip(watches.wid, watches.system_id))))
    g = watches.groupby("system_id")
    t = assign.dropna(subset=["system_id"]).groupby("system_id").size()
    return pd.DataFrame({
        "watches": g.size(),
        "tor_watches": g.type.agg(lambda s: int((s == "TOR").sum())),
        "start": g.first_start.min(), "end": g.last_end.max(),
        "offices": wfo.groupby("system_id").wfo.nunique(),
    }).assign(hours=lambda d: (d.end - d.start).dt.total_seconds() / 3600,
              tornadoes=t).fillna({"tornadoes": 0})


def write_report(s: dict, watches, counties, assign, grid: pd.DataFrame, scored: bool,
                 path=REPORT) -> None:
    def pct(v):
        return "—" if v is None or pd.isna(v) else f"{v:.1%}"

    def f2(v):
        return "—" if v is None or pd.isna(v) else f"{v:.2f}"

    sys_t = system_table(watches, counties, assign)
    with_t = sys_t[sys_t.tornadoes > 0]
    yr = assign.yr
    lines = [
        "# SPC watch systems — Stage 26"
        + (f" (variant `{s['variant']}`)" if s.get("variant") else ""), "",
        f"Generated {utcnow_iso()}. Plan: `docs/plan_watch_linking.md`. Thresholds: "
        f"*Δt* = {s['gap_h']:g} h, *d* = {s['edge_km']:g} km (county edge to county edge), "
        + (f"upstream tolerance {s['upstream_tolerance_m'] / 1000:.0f} km"
           + (" (set by hand)" if s["upstream_tolerance_set"] else
              " (calibrated, below)" if s["calibration"]["calibrated"] else
              " (fallback: too few “replaces” links to calibrate)")
           if s["motion_check"] else "motion check off") + ".", "",
        "> A watch system is a connected sequence of SPC tornado and severe thunderstorm "
        "watches — how SPC organised the threat in real time, and the unit in which it "
        "was communicated. It is an operational grouping, not a physical one.", "",
        "## Watches and links", "",
        f"- {s['watches']:,} watches with county records, {s['county_spans']:,} county "
        f"spans ({pct(s['county_spans_without_boundary'])} without a Census county "
        "boundary, left out of distances).",
        f"- County records dropped before linking: {s['cleaning']['dropped_marine_zones']:,} "
        "marine zones (coastal and lake waters listed with the counties), "
        f"{s['cleaning']['dropped_outside_spc_area']:,} "
        "outside SPC's area (Honolulu numbers its own watches from 1, colliding with SPC's), "
        f"{s['cleaning']['dropped_before_issue']:,} starting before SPC issued the watch of that "
        f"number and {s['cleaning']['dropped_after_expiry']:,} after it expired (mistyped watch "
        f"numbers), of {s['cleaning']['county_records']:,}; "
        f"{s['cleaning']['kept_without_polygon']:,} kept although their number has no SPC polygon.",
        f"- Links: rule 1 (same county at the same time) **{s['rule1_links']:,}**, "
        f"rule 2 (“replaces”) **{s['rule2_links']:,}** ({s['rule2_unmatched']:,} statements "
        "naming no watch that ended within a day before, dropped), rule 3 (inferred succession) "
        f"**{s['rule3_links']:,}**; {s['rule3_rejected_upstream']:,} rule-3 candidates "
        "rejected only because they lie upstream of the storm motion "
        "(`spc_watch_review_<tag>.csv`, to read a sample).",
        f"- **{s['systems']:,} systems**, {len(with_t):,} with at least one SPC tornado.",
        f"- Rules 1 and 3 alone reproduce **{pct(s['explicit_recovered'])}** of SPC's own "
        "“replaces” links — the test of the inferred rule against forecaster-stated "
        "succession.", "",
        "| systems with tornadoes | median | p95 | max |", "|---|---:|---:|---:|",
    ]
    cal = s["calibration"]
    tail = []
    if cal.get("calibrated"):
        tail += [
            "", "## Upstream tolerance — calibrated on SPC's stated successions", "",
            f"For the {cal['n']:,} “replaces” links, the displacement of the successor's "
            "footprint centre along the storm motion (negative = upstream): 5th percentile "
            f"{cal['p5_m'] / 1000:+.0f} km, quartile {cal['p25_m'] / 1000:+.0f} km, median "
            f"{cal['median_m'] / 1000:+.0f} km; {pct(cal['upstream_share'])} lie upstream at "
            "all. The tolerance is set so that 95% of these forecaster-stated successions "
            f"pass: **{s['upstream_tolerance_m'] / 1000:.0f} km**. Upstream offsets of "
            "genuine successors come from footprint shape and sideways extension along a "
            "line, so this measures that noise rather than choosing it."]
    tail += [
        "", "## Speed limit (diagnostic)", "",
        "How often a link's footprint centres lie farther apart than storms at the watch's "
        "speed (`MV_SKNT`) travel in the gap plus the hand-over hour. Not a rule — the "
        "edge-distance condition already bounds distance — but a check that it does: "
        f"rule-3 links {pct(s['rule3_beyond_speed'])}, SPC's “replaces” links "
        f"{pct(s['rule2_beyond_speed'])}. Footprint centres move with the watch's shape as "
        "well as with the storms, so a share above zero is expected for both; a large "
        "difference between the two would mean rule 3 links watches SPC would not have.", "",
        "Split by whether the two watches overlap in time (the successor begins before "
        "its predecessor's last county ends: only the hand-over hour of storm travel is "
        "allowed) or follow in sequence:", "",
        "| links | overlapping | beyond speed | sequential | beyond speed |",
        "|---|---:|---:|---:|---:|"]
    sp = s["speed_split"]
    for name, key in (("rule 3 (inferred)", "rule3"), ("rule 2 (“replaces”)", "rule2")):
        o, q = sp[f"{key}_overlapping"], sp[f"{key}_sequential"]
        tail.append(f"| {name} | {o['n']:,} | {pct(o['beyond'])} | {q['n']:,} | "
                    f"{pct(q['beyond'])} |")
    tail += ["", "Read: if the gap between rule 3 and rule 2 sits in the overlapping "
             "column, rule 3 is joining side-by-side watches of one system (which SPC does "
             "not state as replacements), not successions SPC would reject."]
    for col, name in (("watches", "watches"), ("tornadoes", "tornadoes"),
                      ("offices", "offices"), ("hours", "hours")):
        v = with_t[col]
        lines.append(f"| {name} | {v.median():,.0f} | {v.quantile(.95):,.0f} | {v.max():,.0f} |")
    lines += tail

    ex = s["extent"]
    lines += ["", "## Two granularities: systems and sequences", "",
              "Most rule-3 links join watches in force *at the same time* whose counties "
              "touch — side-by-side watches along one front. Following them gives "
              "**systems**: connected watch coverage. Keeping only hand-overs in time "
              "(same county at once, “replaces”, or a successor starting after its "
              "predecessor ended) gives **sequences**: one chain of watches. Stage 25 uses "
              "systems as an upper bound on an event and sequences as a lower bound.", "",
              "| | groups with tornadoes | largest (tornadoes) | extent p50 | p90 | max |",
              "|---|---:|---:|---:|---:|---:|",
              f"| systems | {ex['system']['groups']:,} | {ex['system']['largest']:,} | "
              f"{ex['system']['p50_km']:,.0f} km | {ex['system']['p90_km']:,.0f} km | "
              f"{ex['system']['max_km']:,.0f} km |",
              f"| sequences | {ex['sequence']['groups']:,} | {ex['sequence']['largest']:,} | "
              f"{ex['sequence']['p50_km']:,.0f} km | {ex['sequence']['p90_km']:,.0f} km | "
              f"{ex['sequence']['max_km']:,.0f} km |", "",
              "Extent: distance across a group's tornado start points, weighted by tornadoes "
              "(the extent the typical tornado's group has).", ""]
    lines += ["", "## Tornadoes in watches", "",
              f"{s['tornadoes_in_watch']:,} of {s['tornadoes']:,} SPC tornadoes "
              f"({s['tornadoes_in_watch'] / max(s['tornadoes'], 1):.1%}) started in a county "
              f"under a watch (by polygon where SPC gives no county). "
              f"{s['tornadoes_in_two_systems']:,} fall in two systems at once (expected 0: "
              "rule 1 links such watches).", "",
              "| year | tornadoes | in a watch | EF0 | EF1 | EF2+ |", "|---|---:|---:|---:|---:|---:|"]
    watched = assign.method != "none"
    for y in sorted(yr.unique()):
        a = assign[yr == y]
        w = watched[yr == y]
        ef = lambda lo, hi: pct(w[a.mag.between(lo, hi)].mean()) if a.mag.between(lo, hi).any() else "—"
        lines.append(f"| {y} | {len(a):,} | {pct(w.mean())} | {ef(0, 0)} | {ef(1, 1)} | {ef(2, 5)} |")
    lines += ["", "Unwatched tornadoes are a known, non-random class (weak, quickly forming, "
              "QLCS and tropical-cyclone tornadoes); scores against watch systems are "
              "conditional on being watched.", ""]

    if scored:
        lines += [
            "## Agreement with the office episodes (validation 2)", "",
            "On watched SPC tornadoes with a Storm Events episode:", "",
            f"- **{f2(s.get('office_recall'))}** of tornado pairs one office put in one "
            "episode are in one watch system "
            f"(linked episodes: {f2(s.get('linked_recall'))}).",
            f"- {pct(s.get('office_se_episodes_split'))} of office episodes are split over "
            "two or more systems — cases to read: an office episode spanning two "
            "systems is either two systems SPC kept apart, or a gap in the watch chain.",
            "", ]
    lines += ["## Sensitivity (validation 4)", "",
              "| Δt h | d km | upstream tolerance | systems with tornadoes | largest (tornadoes) | "
              "“replaces” recovered | office recall | office episodes split | linked recall |",
              "|---:|---:|---|---:|---:|---:|---:|---:|---:|"]
    for r in grid.itertuples():
        tol = (r.upstream_tolerance if r.upstream_tolerance in ("0", "off")
               else f"{r.upstream_tolerance} ({r.upstream_tolerance_km:.0f} km)")
        lines.append(f"| {r.gap_h} | {r.edge_km} | {tol} | "
                     f"{r.systems_with_tornadoes:,} | {r.largest_tornadoes:,} | "
                     f"{pct(r.explicit_recovered)} | {f2(getattr(r, 'office_recall', None))} | "
                     f"{pct(getattr(r, 'office_se_episodes_split', None))} | "
                     f"{f2(getattr(r, 'linked_recall', None))} |")
    lines += ["", "A reference whose conclusions flip within this range is not a reference.", "",
              "## Named outbreaks (validation 3, for a hand check)", "",
              "Tornadoes from 12 UTC on the first day to 12 UTC after the last.", "",
              "| outbreak | tornadoes | in a watch | systems | largest: tornadoes · watches · "
              "offices · hours |", "|---|---:|---:|---:|---|"]
    t0 = pd.to_datetime(assign.begin_utc, utc=True)
    for a, b in NAMED_OUTBREAKS:
        lo = pd.Timestamp(a, tz="UTC") + pd.Timedelta(hours=12)
        hi = pd.Timestamp(b, tz="UTC") + pd.Timedelta(hours=36)
        part = assign[(t0 >= lo) & (t0 < hi)]
        ids = part.system_id.dropna().value_counts()
        big = sys_t.loc[ids.index[0]] if len(ids) else None
        lines.append(
            f"| {a}{'' if a == b else ' – ' + b} | {len(part):,} | "
            f"{pct((part.method != 'none').mean()) if len(part) else '—'} | {len(ids):,} | "
            + (f"{int(ids.iloc[0]):,} · {int(big.watches):,} · {int(big.offices):,} · "
               f"{big.hours:,.0f}" if big is not None else "—") + " |")
    lines += ["", "Check each against NWS office and SPC event summaries: one system, several, "
              "or merged with another event?", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


# ── hand checks (validation 3 and the motion-check review) ──────────────────
ANNOTATION = config.OUTPUT_DIR / "annotation"
SHEET_SEED = 20261105
REVIEW_SAMPLE = 50
OUTBREAK_LABELS = ("matches", "too_coarse", "too_fine", "cannot_tell")
REVIEW_LABELS = ("separate_systems", "should_link", "cannot_tell")
# Groupings compared on the named outbreaks, all on SPC tracks: SPC's own watch
# systems and sequences (stage 26), and from stage 25 --anchor spc stage 3's rule
# and its 400 km variant, the time-only outbreak sequence, the recommended
# space-time setting, and the three density variants.
OUTBREAK_GROUPINGS = {"watch systems": ("watch", "system_id"),
                      "watch sequences": ("watch", "sequence_id")}
OUTBREAK_GROUPINGS |= {name: ("method", name) for name in (
    "convective_day 200km (stage 3)",
    "convective_day 400km",
    ep.FUHRMANN_VARIANT,
    "space_time 400km 6h",
    "kde day bw=100km",
    "kde overlap 24h/12h bw=50km",
    "kde overlap 24h/12h bw=100km",
)}
_N_GROUPINGS = len(OUTBREAK_GROUPINGS)
# Shown side by side, unblinded, in the review app's Compare tab once every outbreak
# row is labelled: the two front-runners of the blind labels and the watch groupings.
COMPARE_GROUPINGS = ("space_time 400km 6h", ep.FUHRMANN_VARIANT,
                     "watch systems", "watch sequences")
_LAST = "ABCDEFGHIJ"[_N_GROUPINGS - 1]
HOW_TO = f"""How to do the watch hand checks (stage 26)
==========================================

Start the app:  python scripts/26_watch_systems.py review   (http://127.0.0.1:8800)
It saves every label into the two sheets below. Keep them closed in other
programs meanwhile. The same guide is in the app (button "Guide").
Do not open the *_key.csv files before you are done.

A. OUTBREAKS  (watch_outbreak_sheet.csv: {len(NAMED_OUTBREAKS)} outbreaks x {_N_GROUPINGS} groupings = {len(NAMED_OUTBREAKS) * _N_GROUPINGS} labels)
   Each outbreak is grouped {_N_GROUPINGS} ways, shown blind as A-{_LAST}. You label each grouping.

   1. Before looking at any grouping, write your event list. Open the SPC
      report pages and the Wikipedia search (links in the panel) and note the
      separate events the summaries describe, with region and time, e.g.
      "E1 26 Apr TX-AR evening; E2 27 Apr morning QLCS MS-AL; E3 27 Apr
      afternoon supercells AL-GA-TN". Put it in the notes of grouping A.
      An event = tornadoes from one storm system in one continuous period.
      Two parts are separate events if the summaries say so, or if activity
      stops for several hours and restarts with new storms elsewhere.
   2. For each grouping (keys a-{_LAST.lower()}), compare its coloured groups with your list.
      Grey (groups with < 3 tornadoes in the window, ungrouped tornadoes) does
      not count. Dashed tracks are outside the outbreak window: ignore them
      unless they make a group span two of your events.
   3. Label:
      1 matches     each event on your list is mainly one coloured group, and
                    no coloured group holds most of two events
      2 too_coarse  at least one coloured group holds two events of your list
      3 too_fine    at least one event is split into two or more coloured
                    groups (typical: cut at a 12Z line, or along the path)
      4 cannot_tell the summaries do not say whether the parts are one event
      Both errors at once: label the one affecting more tornadoes, note the other.
   4. Tools that help: the timeline (one row per group; 12Z = convective-day
      boundary) and the time window (e.g. +-3 h) with play, to see whether
      activity is continuous or stops and restarts.

B. WATCH PAIRS  (watch_review_sheet.csv: 50 pairs)
   The linking did not join watch B to watch A because B lies upstream of
   (behind) A's storm motion. Question: does B cover the same storms as A?

   1. The time starts at B's issue time; filled counties are those in effect at
      the selected time (blue A, orange B), arrows show 2 h of storm motion.
   2. Play through the pair (window +-1 h): do A's storms move into B, or do
      B's storms form separately behind or beside A's?
   3. Read both SEL texts (panel). "Replaces watch A" or "continues" points to
      the same threat; "new development", "second line", another region to a
      separate one.
   4. Label:
      1 separate_systems  B covers other storms (new development behind A's
                          line, a second line, another region): rejection right
      2 should_link       B covers A's storms (taken over or replaced): wrong
      3 cannot_tell       the map and texts do not settle it

When done:  python scripts/26_watch_systems.py check
"""


def _outbreak_window(a: str, b: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    return (pd.Timestamp(a, tz="UTC") + pd.Timedelta(hours=12),
            pd.Timestamp(b, tz="UTC") + pd.Timedelta(hours=36))


def _group_summary(members: pd.DataFrame) -> str:
    states = ",".join(members.st.value_counts().index[:6])
    more = "…" if members.st.nunique() > 6 else ""
    return (f"{len(members)} tornadoes, {members.t0.min():%d %b %H}Z–{members.t0.max():%d %b %H}Z, "
            f"max EF{int(members.mag.max()) if members.mag.max() >= 0 else '?'}, {states}{more}")


def outbreak_sheet(tag: str, rng) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per (named outbreak, grouping), groupings blinded as A–I."""
    tracks = pd.read_csv(SPC_TRACKS, low_memory=False, usecols=["spc_id", "st", "mag", "begin_utc"])
    tracks["t0"] = pd.to_datetime(tracks.begin_utc, utc=True)
    ws = pd.read_csv(config.PROCESSED_DIR / f"spc_watch_systems_{tag}.csv",
                     usecols=["spc_id", "system_id", "sequence_id"])
    asg = pd.read_csv(config.INTERIM_DIR / "episode_comparison_assignments_spc.csv"
                      ).rename(columns=ep.LEGACY_NAMES)
    t = tracks.merge(ws, on="spc_id", how="left").merge(
        asg.rename(columns={"hazard_uid": "spc_id"}), on="spc_id", how="left")
    sheet, key = [], []
    for i, (a, b) in enumerate(NAMED_OUTBREAKS, 1):
        lo, hi = _outbreak_window(a, b)
        days = pd.date_range(a, b, freq="D")
        reports = " ".join(f"https://www.spc.noaa.gov/climo/reports/{d:%y%m%d}_rpts.html" for d in days)
        inside = t[(t.t0 >= lo) & (t.t0 < hi)]
        names = list(OUTBREAK_GROUPINGS)
        letters = dict(zip(rng.permutation(names), "ABCDEFGHIJ"))
        for name in sorted(names, key=letters.get):
            kind, col = OUTBREAK_GROUPINGS[name]
            ids = inside[col].dropna().value_counts()
            big = ids[ids >= 3]
            groups = []
            for gid in big.index:
                members = t[t[col] == gid]            # the whole group, also outside the window
                outside = int((~members.spc_id.isin(inside.spc_id)).sum())
                groups.append(_group_summary(members)
                              + (f" (+{outside} outside the window)" if outside else ""))
            unassigned = int(inside[col].isna().sum())
            sheet.append({
                "row_id": f"O{i:02d}{letters[name]}", "outbreak": a if a == b else f"{a} – {b}",
                "tornadoes_in_window": len(inside), "grouping": f"grouping {letters[name]}",
                "n_groups_3plus": len(big), "n_smaller_groups": int((ids < 3).sum()),
                "not_grouped": unassigned, "groups": " | ".join(groups),
                "spc_reports": reports, "label": "", "notes": ""})
            key.append({"row_id": f"O{i:02d}{letters[name]}", "grouping_name": name,
                        "kind": kind, "column": col})
    return pd.DataFrame(sheet), pd.DataFrame(key)


def watch_url(wid: str) -> str:
    year, num = wid.split("_")
    return f"https://www.spc.noaa.gov/products/watch/{year}/ww{int(num):04d}.html"


def review_sheet(tag: str, rng) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A random sample of motion-check rejections; the measures go to the key."""
    p = out_paths(tag)
    review = pd.read_csv(p["review"])
    w = pd.read_csv(p["watches"]).set_index("wid")
    pick = review.iloc[rng.choice(len(review), size=min(REVIEW_SAMPLE, len(review)),
                                  replace=False)].reset_index(drop=True)
    sheet, key = [], []
    for k, r in enumerate(pick.itertuples(), 1):
        a, b = w.loc[r.a], w.loc[r.b]
        sheet.append({
            "pair_id": f"R{k:03d}",
            "watch_a": r.a, "watch_a_type": a.type, "watch_a_url": watch_url(r.a),
            "a_start_utc": a.first_start, "a_end_utc": a.last_end, "a_offices": a.wfos,
            "watch_b": r.b, "watch_b_type": b.type, "watch_b_url": watch_url(r.b),
            "b_start_utc": b.first_start, "b_end_utc": b.last_end, "b_offices": b.wfos,
            "b_starts_minutes_after_a_ends": round(r.gap_s / 60),
            "label": "", "notes": ""})
        key.append({"pair_id": f"R{k:03d}", "a": r.a, "b": r.b, "edge_m": r.edge_m,
                    "centre_m": r.centre_m, "along_m": r.along_m,
                    "speed_reach_m": r.speed_reach_m,
                    "system_a": a.system_id, "system_b": b.system_id})
    return pd.DataFrame(sheet), pd.DataFrame(key)


def read_sheet(path) -> pd.DataFrame:
    """A worksheet with its hand-entered columns as text (empty ones read as numbers)."""
    df = pd.read_csv(path, dtype={"label": str, "notes": str})
    df["label"] = df.label.str.strip().str.lower().replace("", None)
    return df


def sheet_paths() -> dict:
    return {"outbreak": ANNOTATION / "watch_outbreak_sheet.csv",
            "outbreak_key": ANNOTATION / "watch_outbreak_key.csv",
            "review": ANNOTATION / "watch_review_sheet.csv",
            "review_key": ANNOTATION / "watch_review_key.csv",
            "how_to": ANNOTATION / "HOW_TO_ANNOTATE_watches.txt"}


def cmd_sheets(args) -> None:
    import numpy as np

    paths = sheet_paths()
    filled = [p for k, p in paths.items() if k in ("outbreak", "review") and p.exists()
              and read_sheet(p).label.notna().any()]
    if filled and not args.force:
        raise SystemExit("labels already entered in " + ", ".join(p.name for p in filled)
                         + " — not overwriting (use --force to regenerate)")
    rng = np.random.default_rng(SHEET_SEED)
    o_sheet, o_key = outbreak_sheet(args.tag, rng)
    r_sheet, r_key = review_sheet(args.tag, rng)
    ANNOTATION.mkdir(parents=True, exist_ok=True)
    o_sheet.to_csv(paths["outbreak"], index=False)
    o_key.to_csv(paths["outbreak_key"], index=False)
    r_sheet.to_csv(paths["review"], index=False)
    r_key.to_csv(paths["review_key"], index=False)
    paths["how_to"].write_text(HOW_TO, encoding="utf-8")
    write_manifest(ANNOTATION / "manifest_annotation_watches.json", "26_watch_systems sheets",
                   counts={"outbreak_rows": len(o_sheet), "review_pairs": len(r_sheet),
                           "review_population": int(len(pd.read_csv(out_paths(args.tag)["review"]))),
                           "seed": SHEET_SEED},
                   outputs=list(paths.values()))
    for p in paths.values():
        print(f"wrote {p}")


def cmd_check(args) -> None:
    from tornado_dataset.dat.evaluate import wilson_interval

    paths = sheet_paths()
    o = read_sheet(paths["outbreak"]).merge(pd.read_csv(paths["outbreak_key"]), on="row_id")
    r = read_sheet(paths["review"]).merge(pd.read_csv(paths["review_key"]), on="pair_id")
    for name, df, allowed in (("outbreak", o, OUTBREAK_LABELS), ("review", r, REVIEW_LABELS)):
        bad = df.label.notna() & ~df.label.isin(allowed)
        if bad.any():
            raise SystemExit(f"{name} sheet: labels not in {allowed}: "
                             f"{sorted(df.label[bad].unique())}")
    lines = ["# Watch hand checks — Stage 26", "",
             f"Generated {utcnow_iso()} from `outputs/annotation/watch_*_sheet.csv`.", "",
             "## Named outbreaks: does each grouping cut them as the summaries do?", "",
             "| grouping | labelled | matches | too coarse | too fine | cannot tell |",
             "|---|---:|---:|---:|---:|---:|"]
    for name in OUTBREAK_GROUPINGS:
        g = o[o.grouping_name == name]
        c = g.label.value_counts()
        lines.append(f"| {name} | {int(g.label.notna().sum())}/{len(g)} | "
                     + " | ".join(str(int(c.get(x, 0))) for x in OUTBREAK_LABELS) + " |")
    c = r.label.value_counts()
    n = int(r.label.isin(("separate_systems", "should_link")).sum())
    k = int(c.get("should_link", 0))
    lines += ["", "## Motion-check rejections: was the rejection right?", "",
              f"{int(r.label.notna().sum())} of {len(r)} sampled pairs labelled: "
              f"{int(c.get('separate_systems', 0))} separate systems, {k} should have been "
              f"linked, {int(c.get('cannot_tell', 0))} cannot tell."]
    if n:
        lo, hi = wilson_interval(k, n)
        share = k / n
        lines += ["", f"Wrongly rejected: **{share:.0%}** [{lo:.0%}, {hi:.0%}] of decided pairs.",
                  "", "Read: above ~20%, the motion check rejects too many genuine "
                  "successions — prefer the setting without it (sensitivity grid, "
                  "`--no-motion-check`). Below, keep it."]
    out = config.OUTPUT_DIR / "watch_hand_checks_report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {out}")


def cmd_review(args) -> None:
    """The map-based review app for both worksheets; labels are written back into them."""
    from tornado_dataset.viewer.watch_review import create_watch_review_app

    zip_path = RAW_CENSUS / sw.COUNTY_BOUNDARIES.rsplit("/", 1)[1]
    app = create_watch_review_app(args.tag, sheet_paths(), RAW, zip_path,
                                  OUTBREAK_LABELS, REVIEW_LABELS, COMPARE_GROUPINGS)
    print(f"\n  watch hand checks → http://{args.host}:{args.port}\n")
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    sp = sub.add_parser("probe", help="feasibility check on a sample (step 0 of the plan)")
    sp.add_argument("--first-year", type=int, default=2004)
    sp.add_argument("--last-year", type=int, default=2012)
    sp.add_argument("--season-start", default="2011-03-01")
    sp.add_argument("--season-end", default="2011-07-01")
    sp.add_argument("--text-months", nargs="*", default=["2024-04"],
                    help="further months of watch texts, for the newer product format")
    sp.set_defaults(func=cmd_probe)
    for name, fn, helptext in [("fetch", cmd_fetch, "download watches 2010–2025 (cached)"),
                               ("link", cmd_link, "build watch systems and the report"),
                               ("run", cmd_run, "fetch and link")]:
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("--tag", default=tag_default())
        sp.add_argument("--refresh", action="store_true", help="re-download cached years")
        sp.add_argument("--gap-h", type=float, default=sw.DEFAULT_GAP_S / 3600)
        sp.add_argument("--edge-km", type=float, default=sw.DEFAULT_EDGE_M / 1000)
        sp.add_argument("--no-motion-check", action="store_true",
                        help="no upstream-motion check; implies --variant no-motion")
        sp.add_argument("--variant", default=None,
                        help="suffix for all outputs, so the main ones are kept "
                             "('' writes the main outputs)")
        sp.add_argument("--motion-slack-km", type=float, default=None,
                        help="upstream tolerance; default: calibrated on the “replaces” links")
        sp.set_defaults(func=fn)
    sp = sub.add_parser("sheets", help="write the hand-check worksheets (outputs/annotation/)")
    sp.add_argument("--tag", default=tag_default())
    sp.add_argument("--force", action="store_true", help="overwrite sheets that already hold labels")
    sp.set_defaults(func=cmd_sheets)
    sp = sub.add_parser("review", help="label the worksheets on a map (local web app)")
    sp.add_argument("--tag", default=tag_default())
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8800)
    sp.set_defaults(func=cmd_review)
    sp = sub.add_parser("check", help="score the filled-in worksheets")
    sp.set_defaults(func=cmd_check)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
