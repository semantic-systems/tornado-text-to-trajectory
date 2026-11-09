#!/usr/bin/env python
"""Stage 51 — compare ways of grouping tornadoes into episodes.

Runs the former convective-day rule and the space-time alternatives from the
literature on the same tornadoes, and scores each against NCEI Storm Events
episodes (stage 14). Read-only with respect to the pipeline: this is the
evidence behind the rule stage 15 publishes (space-time 400 km / 6 h on SPC
tracks), and the check that stage 15 publishes exactly that rule.

    python scripts/51_compare_episodes.py                 # group DAT hazards
    python scripts/51_compare_episodes.py --anchor spc    # group SPC whole tracks
    python scripts/51_compare_episodes.py --methods kde space_time   # a subset

``--anchor spc`` groups SPC's complete tornado list instead of the surveyed
subset in DAT, which is thin before ~2020: missing tornadoes can no longer cut
an outbreak in two. Its episodes are then carried to DAT hazards through the
stage 14 SPC ↔ DAT links and scored there as well — the design the dataset
would use if episodes were built on SPC. Outputs get an ``_spc`` suffix, and
one more is written: ``episode_counts_spc.csv``, per method and episode its SPC
tornadoes (all, EF1+, unrated) and DAT hazards — the counts an outbreak
threshold filters on (``episodes.episode_counts``).

With stage 50's watch systems present, every method is scored against them;
with its ``no-motion`` variant present as well (``50_watch_systems.py link
--no-motion-check``), against that too, and the report shows whether any
conclusion depends on the motion check (``--watch-variant`` names another).

Methods and their sources are described in :mod:`tornado_dataset.dat.episodes`.
Needs ``scripts/14_match_references.py`` for the reference; without it the
descriptive columns are still produced and the scores are left empty.
"""

from __future__ import annotations

import argparse
import time

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config
from tornado_dataset.dat import episode_table
from tornado_dataset.dat import episodes as ep
from tornado_dataset.dat import storm_events as se
from tornado_dataset.http import utcnow_iso

SPC_TRACKS = config.INTERIM_DIR / "spc_tornadoes.csv"
PERIODS = [(2010, 2015), (2016, 2020), (2021, 2025)]
BASELINE = ep.BASELINE      # the former rule; always runs

REFERENCES = [
    "SPC storm reports, organised 1200–1159 UTC: "
    "<https://www.spc.noaa.gov/climo/reports/210126_rpts.html>",
    "Fuhrmann, C. M., et al. (2014). Ranking of tornado outbreaks across the United "
    "States and their climatological characteristics. *Weather and Forecasting* 29(3), "
    "684–701, doi:10.1175/WAF-D-13-00128.1. Outbreak definition as in the authors' "
    "2012 abstract: <https://ams.confex.com/ams/26SLS/webprogram/Paper212025.html>",
    "Birant, D., & Kut, A. (2007). ST-DBSCAN: An algorithm for clustering "
    "spatial–temporal data. *Data & Knowledge Engineering* 60(1), 208–221, "
    "doi:10.1016/j.datak.2006.01.013",
    "Shafer, C. M., & Doswell, C. A. (2011). Using kernel density estimation to "
    "identify, rank, and classify severe weather outbreak events. *EJSSM* 6(2): "
    "<https://ejssm.com/ojs/index.php/site/article/view/29>",
    "Shafer, C. M., Grondin, N. S., & Doswell, C. A. (2015). Extensions to ranking and "
    "classifying severe weather outbreaks using kernel density estimation. 16th Conf. "
    "on Mesoscale Processes: <https://ams.confex.com/ams/16Meso/webprogram/Paper274887.html>",
]


def outputs(anchor: str) -> tuple:
    suffix = "" if anchor == "dat" else f"_{anchor}"
    return (config.INTERIM_DIR / f"episode_comparison_metrics{suffix}.csv",
            config.INTERIM_DIR / f"episode_comparison_assignments{suffix}.csv",
            config.OUTPUT_DIR / f"episode_comparison{suffix}_report.md",
            config.INTERIM_DIR / f"episode_counts{suffix}.csv")


def se_links_path(tag: str, anchor: str):
    name = "storm_events_links" if anchor == "dat" else "spc_storm_events_links"
    return config.PROCESSED_DIR / f"{name}_{tag}.csv"


def reference_for(frame: pd.DataFrame, tag: str, anchor: str = "dat",
                  via_spc: bool = True) -> pd.DataFrame | None:
    """Storm Events reference per item; for DAT, extended through SPC tracks.

    A DAT hazard without its own Storm Events match — usually one whose DAT time
    is off by hours — takes the episode of its SPC track's Storm Events row
    (``via_spc``; ``--dat-reference direct`` turns this off). The counts and the
    agreement of both routes are kept in ``attrs["sources"]``.
    """
    path = se_links_path(tag, anchor)
    if not path.exists():
        print(f"no {path.name} — scores will be empty; run scripts/14_match_references.py")
        return None
    links = pd.read_csv(path)
    if anchor == "spc":
        links = links.rename(columns={"spc_id": "hazard_uid"})
    ref = se.hazard_episode_reference(links)
    ref = frame[["hazard_uid"]].merge(ref, on="hazard_uid", how="left").set_index(frame.index)
    spc_links = config.PROCESSED_DIR / f"spc_tornado_links_{tag}.csv"
    spc_se = se_links_path(tag, "spc")
    if anchor != "dat" or not via_spc:
        return ref
    if not spc_links.exists() or not spc_se.exists():
        print("no SPC links — DAT reference from direct Storm Events matches only")
        return ref
    via = ep.reference_via_spc(frame.hazard_uid, pd.read_csv(spc_links), pd.read_csv(spc_se))
    ref, stats = ep.combine_references(ref, via)
    ref.attrs["sources"] = stats
    print(f"DAT reference: {stats['direct']:,} direct, +{stats['via_spc_only']:,} through SPC "
          f"tracks; both routes name the same episode for {stats['agree_episode']:.1%} "
          f"of {stats['both']:,} with both")
    return ref


def watch_systems_for(uids: pd.Series, tag: str, anchor: str,
                      variant: str = "") -> pd.DataFrame | None:
    """Each item's SPC watch system and sequence (stage 50); missing when unwatched.

    SPC tracks carry them directly. A DAT hazard takes those of its closest
    SPC track (stage 14 links), as SPC-built episodes are carried to DAT.
    ``variant`` reads a stage 50 output variant (``link --variant``).
    """
    path = config.PROCESSED_DIR / f"spc_watch_systems_{tag}{'_' + variant if variant else ''}.csv"
    if not path.exists():
        print(f"no {path.name} — " + (
            f"no comparison with watch variant {variant!r}; run scripts/50_watch_systems.py "
            + ("link --no-motion-check" if variant == "no-motion" else f"link --variant {variant}")
            if variant else
            "watch scores will be empty; run scripts/50_watch_systems.py link"))
        return None
    ws = pd.read_csv(path).set_index("spc_id")
    if "sequence_id" not in ws.columns:
        raise SystemExit(f"{path.name} predates watch sequences — rerun scripts/50_watch_systems.py link")
    key = uids
    if anchor == "dat":
        links = pd.read_csv(config.PROCESSED_DIR / f"spc_tornado_links_{tag}.csv")
        best = links[links.rank_for_hazard == 1].drop_duplicates("hazard_uid")
        key = uids.map(best.set_index("hazard_uid").spc_id)
    return pd.DataFrame({c: key.map(ws[c]).to_numpy() for c in ("system_id", "sequence_id")},
                        index=uids.index)


def watch_scores(lab: pd.Series, watch: pd.DataFrame | None, wfo: pd.Series | None,
                 prefix: str = "") -> dict:
    """Against systems (the upper bound: ``watch_``) and sequences (the lower bound: ``seq_``)."""
    if watch is None:
        return {}
    out = {f"{prefix}watch_{k}": v for k, v in ep.score_watch(lab, watch.system_id, wfo).items()}
    out |= {f"{prefix}seq_{k}": v for k, v in ep.score_watch(lab, watch.sequence_id, wfo).items()}
    return out


def load_frame(tag: str, anchor: str) -> pd.DataFrame:
    if anchor == "dat":
        return ep.load_hazard_frame(tag)
    if not SPC_TRACKS.exists():
        raise SystemExit(f"no {SPC_TRACKS.name} — run scripts/13_fetch_references.py and "
                         "scripts/14_match_references.py")
    links = se_links_path(tag, "spc")
    return ep.load_spc_frame(SPC_TRACKS, links if links.exists() else None)


class Projection:
    """SPC-built episodes carried to DAT hazards, and the DAT-side references."""

    def __init__(self, tag: str, via_spc: bool = True):
        hz = episode_table.hazards_with_episodes(
            tag, ["hazard_uid", "episode_uid", "time_begin_utc"])
        self.dat = hz
        self.year = pd.to_datetime(hz.time_begin_utc, utc=True, errors="coerce").dt.year
        self.published = pd.Series(pd.factorize(hz.episode_uid)[0], index=hz.index)
        path = config.PROCESSED_DIR / f"spc_tornado_links_{tag}.csv"
        if not path.exists():
            raise SystemExit(f"no {path.name} — run scripts/14_match_references.py")
        self.links = pd.read_csv(path)
        best = self.links[self.links.rank_for_hazard == 1].drop_duplicates("hazard_uid")
        self.spc_id = hz.hazard_uid.map(best.set_index("hazard_uid").spc_id)
        self.reference = reference_for(hz, tag, "dat", via_spc)
        self.watch = watch_systems_for(hz.hazard_uid, tag, "dat")

    def score(self, labels: pd.Series, frame: pd.DataFrame) -> dict:
        lab, matched = ep.project_labels(labels, frame.hazard_uid, self.dat.hazard_uid,
                                         self.links)
        out = {"dat_matched_share": float(matched.mean()),
               "dat_episodes": int(lab.nunique()),
               "dat_ari_vs_published": ep.adjusted_rand(lab, self.published)}
        if self.reference is not None:
            s = ep.score(lab, self.reference)
            out |= {"dat_recall": s["recall"], "dat_office_precision": s["office_precision"],
                    "dat_se_split": s["se_episodes_split"]}
            if "LINKED_EPISODE" in self.reference.columns:
                out["dat_recall_linked"] = ep.score(lab, self.reference,
                                                    "LINKED_EPISODE")["recall"]
            for lo, hi in PERIODS:
                part = self.reference[self.year.between(lo, hi)]
                out[f"dat_recall_{lo}_{hi}"] = ep.score(lab, part)["recall"]
        out |= watch_scores(lab, self.watch,
                            None if self.reference is None else self.reference.WFO, "dat_")
        return out


def fmt(v, kind: str) -> str:
    if v is None or pd.isna(v):
        return "—"
    return {"pct": f"{v:.1%}", "int": f"{int(v):,}", "f1": f"{v:.0f}",
            "f2": f"{v:.2f}"}[kind]


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tag", default=default_tag)
    p.add_argument("--anchor", choices=["dat", "spc"], default="dat",
                   help="group DAT hazards (default) or SPC whole tracks (stage 14)")
    p.add_argument("--dat-reference", choices=["via_spc", "direct"], default="via_spc",
                   help="DAT hazards' Storm Events reference: their own match, extended "
                        "through their SPC track where they have none (default), or "
                        "their own match only (the behaviour before)")
    p.add_argument("--watch-variant", default="no-motion",
                   help="stage 50 output variant to score against as well, where present "
                        "(default: no-motion, from link --no-motion-check; '' for none)")
    p.add_argument("--methods", nargs="*", default=None,
                   help="run only methods whose name contains one of these strings "
                        "(the former convective-day rule always runs, as the baseline)")
    args = p.parse_args()

    metrics_path, assignments_path, report_path, counts_path = outputs(args.anchor)
    print(f"loading {'hazards' if args.anchor == 'dat' else 'SPC tracks'}…")
    frame = load_frame(args.tag, args.anchor)
    via_spc = args.dat_reference == "via_spc"
    reference = reference_for(frame, args.tag, args.anchor, via_spc)
    projection = Projection(args.tag, via_spc) if args.anchor == "spc" else None
    watch = watch_systems_for(frame.hazard_uid, args.tag, args.anchor)
    alt = (watch_systems_for(frame.hazard_uid, args.tag, args.anchor, args.watch_variant)
           if args.watch_variant and watch is not None else None)
    wfo = None if reference is None else reference.WFO
    year = frame.t0.dt.year

    grid = ep.method_grid()
    if args.methods:
        grid = {k: f for k, f in grid.items()
                if k == BASELINE or any(m in k for m in args.methods)}

    rows, labels, counts = [], {}, []
    for name, fn in grid.items():
        started = time.monotonic()
        lab = fn(frame)
        labels[name] = lab
        row = {"method": name, **ep.describe(lab, frame)}
        if reference is not None:
            row.update(ep.score(lab, reference))
            if "LINKED_EPISODE" in reference.columns:
                linked = ep.score(lab, reference, "LINKED_EPISODE")
                row["recall_linked"] = linked["recall"]
                row["se_split_linked"] = linked["se_episodes_split"]
            for lo, hi in PERIODS:
                part = reference[year.between(lo, hi)]
                row[f"recall_{lo}_{hi}"] = ep.score(lab, part)["recall"]
        row.update(watch_scores(lab, watch, wfo))
        row.update(watch_scores(lab, alt, wfo, "alt_"))
        if projection is not None:
            row.update(projection.score(lab, frame))
        if args.anchor == "spc":
            c = ep.episode_counts(lab, frame, projection.spc_id)
            counts.append(c.assign(method=name))
            row |= outbreak_counts(c)
        row["seconds"] = round(time.monotonic() - started, 1)
        rows.append(row)
        print(f"  {name:<44} {row['episodes']:>6,} episodes"
              + (f"  recall {row['recall']:.3f}  office precision "
                 f"{row['office_precision']:.3f}" if reference is not None else "")
              + (f"  within watch systems {row['watch_precision']:.3f}  sequences kept "
                 f"{row['seq_recall']:.3f}" if "watch_precision" in row else "")
              + f"  ({row['seconds']}s)")

    # Stage 15 must publish exactly this rule, carried to DAT hazards.
    agreement = None
    if projection is not None and ep.PUBLISHED in labels:
        lab, _ = ep.project_labels(labels[ep.PUBLISHED], frame.hazard_uid,
                                   projection.dat.hazard_uid, projection.links)
        agreement = ep.adjusted_rand(lab, projection.published)
        print(f"\n{ep.PUBLISHED} carried to DAT vs stage 15's episodes: ARI {agreement:.4f}")

    metrics = pd.DataFrame(rows)
    config.INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(metrics_path, index=False)
    pd.DataFrame({"hazard_uid": frame.hazard_uid, **{k: v for k, v in labels.items()}}
                 ).to_csv(assignments_path, index=False)
    written = [metrics_path, assignments_path, report_path]
    if counts:
        cols = ["method", "episode", "n_spc", "n_spc_ef1plus", "n_spc_unrated", "n_dat"]
        pd.concat(counts, ignore_index=True)[cols].to_csv(counts_path, index=False)
        written.append(counts_path)
    sources = (projection.reference if projection is not None else reference)
    sources = getattr(sources, "attrs", {}).get("sources") if sources is not None else None
    variant = None
    if alt is not None:
        variant = {"name": args.watch_variant,
                   **{f"{k}_{c}": int(w[c].nunique()) for k, w in (("main", watch), ("alt", alt))
                      for c in ("system_id", "sequence_id")}}
    write_report(report_path, metrics, reference, agreement, len(frame), args.anchor, sources,
                 variant)
    print("\n".join(f"wrote {p}" for p in written))


def outbreak_counts(c: pd.DataFrame) -> dict:
    """What an outbreak threshold on the episode counts keeps, for the report."""
    n = c.n_spc.sum()
    big = c[c.n_spc_ef1plus >= 6]
    return {"episodes_6plus": int((c.n_spc >= 6).sum()),
            "episodes_6plus_ef1": len(big),
            "tornadoes_in_6plus_ef1": float(big.n_spc.sum() / n) if n else float("nan")}


def sources_note(s: dict | None) -> list[str]:
    """How the DAT hazards' Storm Events reference was reached."""
    if not s:
        return []
    return ["", f"> **DAT reference.** {s['direct']:,} DAT hazards match a Storm Events row "
            f"themselves; **{s['via_spc_only']:,} more** reach one through their SPC track "
            "(DAT hazard → SPC track → Storm Events row; mostly hazards whose DAT time is "
            "off by hours, stage 14). Where both routes exist "
            f"({s['both']:,} hazards), they name the same Storm Events episode for "
            f"**{s['agree_episode']:.1%}**. {s['neither']:,} have neither. "
            "`--dat-reference direct` scores against the hazards' own matches only."]


def write_report(path, m: pd.DataFrame, reference, agreement: float | None,
                 n_items: int, anchor: str = "dat", sources: dict | None = None,
                 variant: dict | None = None) -> None:
    scored = reference is not None
    n_ref = int(reference.EPISODE_ID.notna().sum()) if scored else 0
    unit = "DAT hazards" if anchor == "dat" else "SPC whole tracks"
    if agreement is None:
        check = ("The published episodes (stage 15) are built on SPC tracks; "
                 + ("this run groups DAT hazards, for comparison." if anchor == "dat" else
                    f"run with `{ep.PUBLISHED}` among the methods to check them."))
    else:
        check = (f"`{ep.PUBLISHED}`, carried to DAT hazards, reproduces stage 15's "
                 f"published episodes with ARI {agreement:.4f}"
                 + (" (exact)." if agreement > 0.9999 else " — **not exact: stage 15 and "
                    "this comparison disagree; check before reading on.**"))
    lines = [
        "# Episode definitions compared — Stage 51"
        + ("" if anchor == "dat" else " (SPC tracks)"), "",
        f"> **Scope:** all {n_items:,} {unit}, grouped by each method below. "
        + (f"Scores use the {n_ref:,} matched to an NCEI Storm Events row "
           "(stage 14), whose `EPISODE_ID` is the reference." if scored else
           "No Storm Events reference was available, so only the descriptive "
           "columns are filled.")
        + " This is the evidence behind the rule stage 15 publishes.", "",
        f"Generated {utcnow_iso()}. {check}",
    ] + (sources_note(sources) if anchor == "dat" else []) + [
        "", "## How to read the scores", "",
        "- **recall** — of hazard pairs one office put in one Storm Events episode, the "
        "share the method also groups. Below 1 means the method cuts a weather system "
        "a forecaster saw as one.",
        "- **office precision** — of hazard pairs the method groups *and* one office "
        "reported, the share that office also grouped. Below 1 suggests over-merging; "
        "it cannot see merges across offices, which Storm Events never makes.",
        "- **SE split** — share of Storm Events episodes (≥2 matched hazards) that the "
        "method spreads over more than one episode.",
        "- **linked** columns — the same against `LINKED_EPISODE`, where episodes of "
        "different offices that share a crossing tornado are one. Stricter: a method "
        "must also keep together what two offices jointly reported.",
        "- Extent and duration describe what an episode *is* under each method: a "
        "method can score perfect recall by merging a whole season.", "",
        "## Results", "",
        "| method | episodes | singletons | largest | p95 / max extent km | max h | "
        "multi-day | recall | recall linked | office precision | SE split | "
        "SE split linked |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in m.itertuples():
        lines.append(
            f"| {r.method} | {r.episodes:,} | {r.singleton_share:.0%} | {r.largest:,} | "
            f"{r.extent_km_p95:,.0f} / {r.extent_km_max:,.0f} | {r.duration_h_max:,.0f} | "
            f"{r.multi_day_episodes:,} | {fmt(getattr(r, 'recall', None), 'f2')} | "
            f"{fmt(getattr(r, 'recall_linked', None), 'f2')} | "
            f"{fmt(getattr(r, 'office_precision', None), 'f2')} | "
            f"{fmt(getattr(r, 'se_episodes_split', None), 'pct')} | "
            f"{fmt(getattr(r, 'se_split_linked', None), 'pct')} |")
    if scored:
        lines += ["", "### Recall by period", "",
                  ("DAT holds a small share of the official tornadoes before ~2020 "
                   "(stage 14), so early-period scores rest on fewer, possibly "
                   "unrepresentative, hazards." if anchor == "dat" else
                   "SPC tracks are complete in every period, so differences between "
                   "periods here are not a coverage effect."), "",
                  "| method | " + " | ".join(f"{lo}–{hi}" for lo, hi in PERIODS) + " |",
                  "|---|" + "---:|" * len(PERIODS)]
        for r in m.itertuples():
            lines.append(f"| {r.method} | " + " | ".join(
                fmt(getattr(r, f"recall_{lo}_{hi}"), "f2") for lo, hi in PERIODS) + " |")
    if "watch_precision" in m.columns:
        lines += watch_section(m, unit)
    if variant is not None and "alt_watch_precision" in m.columns:
        lines += variant_section(m, variant)
    if "episodes_6plus_ef1" in m.columns:
        lines += counts_section(m)
    if "dat_ari_vs_published" in m.columns:
        lines += projection_section(m, sources)
    lines += [
        "", "## Methods", "",
        "- **convective_day** — the former episode rule (200 km): same 1200–1159 UTC "
        "day, single linkage on track distance.",
        "- **space_time** — single linkage on track distance and the gap between time "
        "intervals; no day boundary.",
        "- **time-gap 6h, all ratings (Fuhrmann variant)** — after the outbreak-sequence "
        "rule of Fuhrmann et al.: consecutive tornadoes ≤6 h apart, with no distance "
        "limit. Unlike theirs, tornadoes of every rating chain (they used F/EF1+), the gap "
        "runs from one tornado's end to the next one's start (theirs from start to start), "
        "and no minimum count (their ≥6) applies; a count threshold is a filter on the "
        "episode counts. Their common synoptic-scale system has no objective test here, so "
        "this shows what the time rule alone does.",
        "- **st_dbscan** — Birant & Kut: a hazard needs `minpts` neighbours (itself "
        "included) to be a core point; only core points link clusters, so chains of "
        "isolated tornadoes do not bridge outbreaks. Noise points stay singletons.",
        "- **kde day** — Shafer & Doswell (2011): Gaussian kernel density of track "
        "midpoints per convective day on a 10 km grid; each connected region above "
        "half of one isolated tornado's peak is one episode.",
        "- **kde overlap 24h/12h** — the Shafer, Grondin & Doswell (2015) extension: "
        "24 h windows every 12 h, with regions that intersect in consecutive windows "
        "joined, so an outbreak is not cut at 12 UTC.",
        "",
        "Neither KDE variant replicates the papers: they clustered all severe reports "
        "and discarded sparse clusters to rank outbreaks, whereas here every tornado "
        "needs an episode. Bandwidths and the threshold are this project's choices.",
        "", "## Limitations", "",
        "1. **The reference is office-bounded.** Storm Events episodes never span two "
        "offices; linked episodes span offices only where a tornado crossed between "
        "them. Both test splitting well and merging only within one office.",
        "2. **Offices differ** in how finely they divide episodes; office precision "
        "mixes method behaviour with office practice.",
        "3. **Only matched tornadoes are scored** — for DAT hazards about nine in ten "
        "from 2020, fewer before; SPC tracks match Storm Events almost completely "
        "(stage 14 report).",
        "4. **The grid is coarse on purpose**: three distances × three gaps, two "
        "density settings. A finer search would overfit the one reference available.",
        "5. **SPC geometry is a straight start→end line**; distances between long, "
        "curved tracks are approximate under `--anchor spc`.",
        "6. **Watches are a forecast-made reference** (stage 50): they score only "
        "watched tornadoes, and they group what SPC expected to be one threat. They are "
        "the only reference here that spans offices; as bounds rather than a target, "
        "they flag over-merging (systems) and splitting (sequences). Conclusions should "
        "hold against both the office episodes and the watch bounds.",
        "", "## References", "",
    ] + [f"- {r}" for r in REFERENCES] + [""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def watch_section(m: pd.DataFrame, unit: str, prefix: str = "",
                  title: str = "Against SPC watches: upper and lower bounds") -> list[str]:
    """Scores against stage 50's watch systems and sequences — references that span offices."""
    n = int(m[prefix + "watch_scored"].iloc[0])
    lines = [
        "", f"## {title}", "",
        f"Scored on the {n:,} {unit} in a watch (stage 50; unwatched tornadoes — about a "
        "quarter, mostly weak — are left out). Watches are how SPC organised the threat "
        "in real time, across offices: an operational and communication unit, not a "
        "physical one. Stage 50 gives two granularities, and they bracket every method:", "",
        "- **Watch systems** (side-by-side watches joined; typically ~800 km across) are "
        "coarser than any method. Read as an **upper bound**: of pairs a method groups, the "
        "share inside one system — **within systems**, and its **cross-office** part. "
        "Below 1, the method merges what SPC never connected.",
        "- **Watch sequences** (one chain of hand-overs; typically ~300 km) are finer than "
        "any method. Read as a **lower bound**: of pairs SPC carried in one sequence, the "
        "share the method keeps together — **sequences kept**, and the share of sequences "
        "**split**. Below 1, the method cuts a chain SPC ran as one.",
        "", "A method consistent with SPC's operations scores near 1 on both. F1 against "
        "either alone is not reported here as a ranking: it measures how close a method's "
        "granularity is to that one definition, and the ranking flips between the two "
        "(the F1 columns are in the metrics CSV).", "",
        "| method | within systems | cross-office | sequences kept | sequences split |",
        "|---|---:|---:|---:|---:|"]
    for r in m.to_dict("records"):
        lines.append(
            f"| {r['method']} | {fmt(r.get(prefix + 'watch_precision'), 'f2')} | "
            f"{fmt(r.get(prefix + 'watch_cross_office_precision'), 'f2')} | "
            f"{fmt(r.get(prefix + 'seq_recall'), 'f2')} | "
            f"{fmt(r.get(prefix + 'seq_systems_split'), 'pct')} |")
    return lines


def variant_section(m: pd.DataFrame, v: dict) -> list[str]:
    """The watch scores against a stage 50 variant beside those against the main systems."""
    what = ("linked without the upstream-motion check (`link --no-motion-check`)"
            if v["name"] == "no-motion" else f"stage 50's `--variant {v['name']}`")
    lines = [
        "", f"## Against SPC watches: does it depend on the linking? (`{v['name']}`)", "",
        f"The same scores against watch systems {what}. Systems: "
        f"{v['main_system_id']:,} → {v['alt_system_id']:,} with a scored tornado; sequences: "
        f"{v['main_sequence_id']:,} → {v['alt_sequence_id']:,}. Each cell reads *main → "
        "variant*. A conclusion drawn from the watch bounds should hold in both columns; "
        "**Kendall τ** says whether the methods keep their order.", "",
        "| method | within systems | cross-office | sequences kept | sequences split |",
        "|---|---:|---:|---:|---:|"]
    cols = (("watch_precision", "f2", "within systems"),
            ("watch_cross_office_precision", "f2", "cross-office"),
            ("seq_recall", "f2", "sequences kept"),
            ("seq_systems_split", "pct", "sequences split"))
    for r in m.to_dict("records"):
        lines.append(f"| {r['method']} | " + " | ".join(
            f"{fmt(r.get(c), k)} → {fmt(r.get('alt_' + c), k)}" for c, k, _ in cols) + " |")
    lines.append("")
    for c, k, label in cols:
        a, b = m[c], m["alt_" + c]
        ok = a.notna() & b.notna()
        if ok.sum() >= 3:
            tau = a[ok].corr(b[ok], method="kendall")
            lines.append(f"- {label}: largest change {fmt((b[ok] - a[ok]).abs().max(), k)}, "
                         f"Kendall τ {tau:.2f}")
    return lines


def counts_section(m: pd.DataFrame) -> list[str]:
    """What an outbreak threshold on ``episode_counts_spc.csv`` keeps, per method."""
    lines = [
        "", "## Outbreak thresholds on the episode counts", "",
        "`episode_counts_spc.csv` holds, per method and episode, its SPC tornadoes "
        "(`n_spc`), those rated EF1+ (`n_spc_ef1plus`) and unrated (`n_spc_unrated`), and "
        "the DAT hazards carried into it (`n_dat`). A minimum size is a filter on these; "
        "the groupings themselves apply none. With ≥6 EF1+ (Fuhrmann et al.) the result "
        "is close to, not identical with, their outbreaks, since here EF0 tornadoes also "
        "chain an episode.", "",
        "| method | episodes ≥6 tornadoes | ≥6 EF1+ | tornadoes in ≥6 EF1+ |",
        "|---|---:|---:|---:|"]
    for r in m.to_dict("records"):
        lines.append(f"| {r['method']} | {fmt(r.get('episodes_6plus'), 'int')} | "
                     f"{fmt(r.get('episodes_6plus_ef1'), 'int')} | "
                     f"{fmt(r.get('tornadoes_in_6plus_ef1'), 'pct')} |")
    return lines


def projection_section(m: pd.DataFrame, sources: dict | None = None) -> list[str]:
    """Episodes built on SPC tracks, carried to DAT hazards and scored there."""
    share = m.dat_matched_share.iloc[0]
    lines = [
        "", "## Carried to DAT hazards", "",
        f"Each DAT hazard takes the episode of its closest SPC track (stage 14 links); "
        f"{share:.1%} have one. The other {1 - share:.1%} become their own episode, "
        "which costs recall where such a hazard belongs to an outbreak. Scores use the "
        "DAT hazards' own Storm Events reference, so they compare directly with "
        "`episode_comparison_report.md`; **ARI vs published** says how far each "
        "SPC-built grouping is from the episodes stage 15 publishes.",
    ] + sources_note(sources) + ["",
        "| method | DAT episodes | recall | recall linked | office precision | "
        "SE split | ARI vs published | " + " | ".join(f"{lo}–{hi}" for lo, hi in PERIODS)
        + " |", "|---|---:|---:|---:|---:|---:|---:|" + "---:|" * len(PERIODS)]
    for r in m.itertuples():
        lines.append(
            f"| {r.method} | {r.dat_episodes:,} | {fmt(getattr(r, 'dat_recall', None), 'f2')} | "
            f"{fmt(getattr(r, 'dat_recall_linked', None), 'f2')} | "
            f"{fmt(getattr(r, 'dat_office_precision', None), 'f2')} | "
            f"{fmt(getattr(r, 'dat_se_split', None), 'pct')} | "
            f"{fmt(r.dat_ari_vs_published, 'f2')} | " + " | ".join(
                fmt(getattr(r, f"dat_recall_{lo}_{hi}", None), "f2") for lo, hi in PERIODS)
            + " |")
    if "dat_watch_precision" in m.columns:
        lines += watch_section(m, "DAT hazards with an SPC track", "dat_",
                               "Carried to DAT hazards — against SPC watches")
    return lines


if __name__ == "__main__":
    main()
