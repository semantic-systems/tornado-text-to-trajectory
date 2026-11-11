#!/usr/bin/env python
"""Stage 25 — which official texts of one tornado are edits of the same account.

For every hazard, compares its official texts pairwise — the survey statement
(PNS section, ``primary_survey_of``), the Storm Events narratives
(``narrative_of``), the DAT comments (``comment_of``) and the LSRs
(``describes``) — by shared verbatim wording, and groups the texts that go back
to one account. The method, and why it needs no hand labels, is in
:mod:`tornado_dataset.text.same_source`; in short:

1. **wording specific to the tornado**: 5-token runs found in the texts of at
   most one hazard besides the pair's own; anything more common is a phrase or
   an office formula;
2. **link**: two texts of a hazard share at least ``m`` tokens of such wording;
   ``m`` is the smallest value from 10 at which at most 0.1% of other-episode
   pairs and 1% of same-episode, other-hazard pairs would link (the two
   comparison sets bound the share of false links from below and above);
3. **recall**: on edited copies of real texts (truncation, excerpt, sentence
   changes, changed numbers, rewording) and, where the hand-saved SPC daily
   reports are present, on SPC's copies of LSR remarks;
4. **groups**: connected texts of one hazard; ``contained_in`` and the
   representative are observations, not a claim about which text came first;
5. **sensitivity**: the whole method rerun with other run lengths and cut-offs.

    python scripts/25_find_same_source_edits.py
    python scripts/25_find_same_source_edits.py --no-sensitivity
    python scripts/25_find_same_source_edits.py samples      # a page to check by eye

Offline: half a minute, three with the sensitivity runs. Needs stage 15
(hazards and episodes), stage 20 (PNS and LSR) and stage 24 (narratives, DAT
comments). Writes ``data/processed/same_source_edits_<tag>.csv`` (one row per
hazard and text), ``data/interim/same_source_pairs_<tag>.csv`` (every compared
pair), a manifest and ``outputs/same_source_edits_report.md``.

``samples`` reruns the method (half a minute) and writes only
``outputs/same_source_samples_<tag>.html``: stratified samples (random hazards,
links just over and pairs just under the rule, low-coverage links, survey
statement and narrative left apart, bridged groups, real-time LSRs in a survey
account, comparison pairs that linked), the counted wording highlighted, with a
verdict per sample kept in the browser and exported as CSV
(:mod:`tornado_dataset.text.same_source_view`). ``--per-stratum`` and ``--seed``
set the size and the draw.
"""

from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

import _bootstrap  # noqa: F401

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tornado_dataset import config
from tornado_dataset.dat import episode_table
from tornado_dataset.ids import uid, write_manifest
from tornado_dataset.text import same_source as ss
from tornado_dataset.text import same_source_view

HAZARD_RELATIONS = {"primary_survey_of", "describes", "narrative_of", "comment_of"}
ORACLE_TYPES = {"pns", "storm_events_narrative", "dat_comment"}
SHORT = {"pns": "PNS", "storm_events_narrative": "narrative", "dat_comment": "DAT comment",
         "lsr": "LSR"}
SCOPES = ("other_episode", "same_episode")
WORDS = {0: "no", 1: "one", 2: "two", 3: "three"}


# ── loading ────────────────────────────────────────────────────────────────

def load(tag: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """``(links, texts, dropped)``: one row per hazard and text; one per text."""
    P = config.PROCESSED_DIR
    needed = {P / f"textrefs_nws_{tag}.csv": "scripts/20_fetch_nws_text.py",
              P / f"textlinks_nws_{tag}.csv": "scripts/20_fetch_nws_text.py",
              P / f"textrefs_records_{tag}.csv": "scripts/24_import_record_text.py",
              P / f"textlinks_records_{tag}.csv": "scripts/24_import_record_text.py",
              episode_table.membership_path(tag): "scripts/15_build_episodes.py",
              episode_table.spc_hazards_path(tag): "scripts/15_build_episodes.py"}
    for path, stage in needed.items():
        if not path.exists():
            raise SystemExit(f"no {path.name} — run {stage}")
    cols = ["textref_uid", "source_type", "author_org", "body", "text_role"]
    nws = pd.read_csv(P / f"textrefs_nws_{tag}.csv", low_memory=False,
                      usecols=cols + ["lsr_source", "published_at", "lat", "lon"])
    rec = pd.read_csv(P / f"textrefs_records_{tag}.csv", low_memory=False, usecols=cols)
    texts = pd.concat([nws, rec], ignore_index=True).drop_duplicates("textref_uid")
    texts["office"] = texts.author_org.astype(str).str.replace("NWS", "", regex=False).str.strip()
    texts.loc[texts.office.isin(["", "nan", "None"]), "office"] = None
    lsr = texts.lsr_source.astype(str).str.upper()
    texts["lsr_class"] = np.where(texts.source_type != "lsr", None,
                                  np.where(lsr.str.contains("SURVEY"), "survey", "real_time"))

    links = pd.concat([pd.read_csv(P / f"textlinks_nws_{tag}.csv"),
                       pd.read_csv(P / f"textlinks_records_{tag}.csv")], ignore_index=True)
    links = links[(links.link_level == "hazard") & links.link_relation.isin(HAZARD_RELATIONS)]
    links = links[["textref_uid", "target_uid", "link_relation", "distance_m"]].rename(
        columns={"target_uid": "hazard_uid"}).drop_duplicates(["hazard_uid", "textref_uid"])

    membership = episode_table.membership(tag)[["hazard_uid", "hazard_source", "episode_uid"]]
    days = pd.concat([
        pd.read_csv(P / f"hazards_{tag}.csv", usecols=["hazard_uid", "convective_day"]),
        episode_table.spc_hazards(tag)[["hazard_uid", "convective_day"]]])
    membership = membership.merge(days, on="hazard_uid", how="left")
    known = links.hazard_uid.isin(membership.hazard_uid)
    dropped = {"links_to_hazards_not_in_stage_15": int((~known).sum()),
               "of_which_relation": links[~known].link_relation.value_counts().to_dict()}
    links = links[known].merge(membership, on="hazard_uid").merge(
        texts[["textref_uid", "source_type"]], on="textref_uid")
    # The 455 DAT hazards outside every episode are an episode of their own.
    links["episode_key"] = links.episode_uid.fillna(links.hazard_uid)
    links["year"] = links.convective_day.astype(str).str[:4]
    texts = texts[texts.textref_uid.isin(links.textref_uid)].reset_index(drop=True)
    return links, texts, dropped


# ── one run of the method ──────────────────────────────────────────────────

def run(links: pd.DataFrame, texts: pd.DataFrame, k: int, min_hazards: int | None,
        settings: dict) -> dict:
    """Profiles, within-hazard pairs, both comparison sets and the link rule."""
    floor = settings["min_shared_floor"]
    hazards = links.groupby("textref_uid").hazard_uid.agg(set).to_dict()
    episodes = links.groupby("textref_uid").episode_key.agg(set).to_dict()
    years = links.groupby("textref_uid").year.min().to_dict()
    bodies = dict(zip(texts.textref_uid, texts.body))
    toks = {u: ss.tokens(b) for u, b in bodies.items()}
    # Each text counts for one hazard: an LSR within reach of several for the
    # nearest, so that the same LSR does not count as several tornadoes.
    nearest = (links.sort_values(["distance_m", "hazard_uid"], na_position="last")
               .drop_duplicates("textref_uid").set_index("textref_uid").hazard_uid)
    counts = ss.hazard_counts((set(ss.runs(toks[u], k)), {nearest[u]}) for u in bodies)
    common = ss.common_runs(counts, min_hazards)
    prof = {u: ss.profile(b, k, common) for u, b in bodies.items()}
    # A comparison pair spans two hazards: one more is allowed, so that it meets
    # the same rule as a within-hazard pair (at most one hazard besides its own).
    common_pair = ss.common_runs(counts, None if min_hazards is None else min_hazards + 1)
    prof_pair = {u: ss.profile(b, k, common_pair) for u, b in bodies.items()}
    meta = {u: {"source_type": t, "office": o, "year": years[u], "episodes": episodes[u],
                "hazards": hazards[u], "body_key": hash(" ".join(toks[u])),
                "comparable": ss.comparable(prof[u], floor)}
            for u, t, o in zip(texts.textref_uid, texts.source_type, texts.office)}
    order = {u: ss.order_key(m["source_type"], prof[u].n_specific, u) for u, m in meta.items()}

    rows = []
    for hazard, g in links.groupby("hazard_uid", sort=True):
        members = sorted((u for u in g.textref_uid if meta[u]["comparable"]), key=order.get)
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                s = ss.compare(prof[a], prof[b])
                rows.append((hazard, a, b, meta[a]["source_type"], meta[b]["source_type"],
                             s.a_specific, s.b_specific, s.a_shared, s.b_shared,
                             s.a_in_b, s.b_in_a, s.shared))
    pairs = pd.DataFrame(rows, columns=["hazard_uid", "a_uid", "b_uid", "a_type", "b_type",
                                        "a_specific", "b_specific", "a_shared", "b_shared",
                                        "a_in_b", "b_in_a", "shared"])

    unique = sorted(set(zip(pairs.a_uid, pairs.b_uid)))
    comparison = {}
    for scope in SCOPES:
        rng = random.Random(f"{settings['seed']}-{scope}")
        out = []
        for kept, stand_in, replaced in ss.stand_ins(unique, meta, rng, scope):
            s = ss.compare(prof_pair[kept], prof_pair[stand_in])
            a, b = sorted((meta[kept]["source_type"], meta[replaced]["source_type"]),
                          key=lambda t: ss.order_key(t, 0, ""))
            out.append((a, b, s.shared, kept, stand_in))
        comparison[scope] = pd.DataFrame(out, columns=["a_type", "b_type", "shared",
                                                       "kept_uid", "stand_in_uid"])
    m, how = ss.choose_min_shared(comparison["other_episode"].shared,
                                  comparison["same_episode"].shared, floor,
                                  settings["target_other_episode"],
                                  settings["target_same_episode"])
    pairs["linked"] = pairs.shared >= m
    for c in comparison.values():
        c["linked"] = c.shared >= m
    return {"k": k, "min_hazards": min_hazards, "common": common, "profiles": prof,
            "profiles_pair": prof_pair,
            "meta": meta, "order": order, "pairs": pairs, "comparison": comparison,
            "min_shared": m, "min_shared_source": how, "common_runs": len(common)}


# ── groups ─────────────────────────────────────────────────────────────────

def group_rows(links: pd.DataFrame, texts: pd.DataFrame, r: dict, contained_share: float
               ) -> pd.DataFrame:
    prof, meta, order, pairs = r["profiles"], r["meta"], r["order"], r["pairs"]
    cov: dict[tuple[str, str, str], tuple[float, int]] = {}
    for p in pairs.itertuples():
        cov[(p.hazard_uid, p.a_uid, p.b_uid)] = (p.a_in_b, p.a_shared)
        cov[(p.hazard_uid, p.b_uid, p.a_uid)] = (p.b_in_a, p.b_shared)
    linked = pairs[pairs.linked]
    edges = {h: list(zip(g.a_uid, g.b_uid)) for h, g in linked.groupby("hazard_uid")}
    edge_set = set(zip(linked.hazard_uid, linked.a_uid, linked.b_uid))
    edge_set |= {(h, b, a) for h, a, b in edge_set}
    info = texts.set_index("textref_uid")

    out = []
    for hazard, g in links.groupby("hazard_uid", sort=True):
        members = sorted(g.textref_uid)
        number = ss.groups(members, edges.get(hazard, []))
        by_group: dict[int, list[str]] = {}
        for u, n in number.items():
            by_group.setdefault(n, []).append(u)
        for group in by_group.values():
            def covers(b: str) -> int:
                """Tokens of the other members that lie in runs shared with ``b``."""
                return sum(cov.get((hazard, a, b), (0, 0))[1] for a in group if a != b)
            rep = min(group, key=lambda b: (-covers(b), order[b]))
            bridged = len(group) > 2 and any(
                (hazard, a, b) not in edge_set for i, a in enumerate(group) for b in group[i + 1:])
            gid = uid("edit_group", hazard, rep)
            types = ";".join(sorted({meta[u]["source_type"] for u in group},
                                    key=lambda t: ss.order_key(t, 0, "")))
            for u in group:
                inside = [(cov[(hazard, u, b)][0], b) for b in group
                          if b != u and (hazard, u, b) in edge_set]
                best = min(inside, key=lambda x: (-x[0], order[x[1]])) if inside else None
                out.append({
                    "hazard_uid": hazard, "textref_uid": u,
                    "lsr_class": info.at[u, "lsr_class"], "text_role": info.at[u, "text_role"],
                    "n_tokens": prof[u].n_tokens, "n_specific": prof[u].n_specific,
                    "comparable": ss.comparable(prof[u], r["min_shared"]),
                    "edit_group": gid, "group_size": len(group), "group_source_types": types,
                    "is_representative": u == rep, "representative_uid": rep,
                    "coverage_by_representative": (1.0 if u == rep else
                                                   cov.get((hazard, u, rep), (np.nan,))[0]),
                    "contained_in": best[1] if best and best[0] >= contained_share else None,
                    "max_coverage": round(best[0], 3) if best else None,
                    "bridged": bridged,
                    "hazard_texts": len(members), "hazard_accounts": len(by_group),
                })
    rows = pd.DataFrame(out).merge(
        links[["hazard_uid", "textref_uid", "link_relation", "hazard_source", "episode_uid",
               "source_type"]], on=["hazard_uid", "textref_uid"])
    first = ["hazard_uid", "hazard_source", "episode_uid", "textref_uid", "source_type",
             "link_relation"]
    return rows[first + [c for c in rows.columns if c not in first]]


def co_grouped(key: pd.DataFrame, rows: pd.DataFrame) -> np.ndarray:
    group = dict(zip(zip(rows.hazard_uid, rows.textref_uid), rows.edit_group))
    return np.array([group[(h, a)] == group[(h, b)]
                     for h, a, b in zip(key.hazard_uid, key.a_uid, key.b_uid)], dtype=bool)


def false_link_bounds(pairs: pd.DataFrame, comparison: dict, by: list[str] | None) -> pd.DataFrame:
    """Within-hazard pairs and links, with the expected false links from each set."""
    def table(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        if not cols:
            return pd.DataFrame({"n": [len(df)], "rate": [df.linked.mean()]})
        return df.groupby(cols).linked.agg(n="size", rate="mean").reset_index()
    cols = by or []
    within = table(pairs, cols).rename(columns={"n": "pairs", "rate": "linked_share"})
    for scope, df in comparison.items():
        t = table(df, cols).rename(columns={"n": f"{scope}_n", "rate": f"{scope}_rate"})
        within = within.merge(t, on=cols, how="left") if cols else pd.concat([within, t], axis=1)
    within["links"] = (within.pairs * within.linked_share).round().astype(int)
    for scope in SCOPES:
        within[f"false_{scope}"] = within.pairs * within[f"{scope}_rate"]
    return within


# ── recall ─────────────────────────────────────────────────────────────────

def recall_derived(texts: pd.DataFrame, r: dict, per_type: int, seed: int) -> pd.DataFrame:
    """Whether edited copies of real texts would be linked to their original."""
    rng = random.Random(f"{seed}-recall")
    meta, prof, m = r["meta"], r["profiles"], r["min_shared"]
    bodies = dict(zip(texts.textref_uid, texts.body))
    pool = sorted(u for u, x in meta.items() if x["comparable"])
    vocabulary = sorted({t for u in pool[:5000] for t in ss.tokens(bodies[u])})
    rows = []
    for source_type in ss.SOURCE_ORDER:
        own = [u for u in pool if meta[u]["source_type"] == source_type]
        for u in rng.sample(own, min(per_type, len(own))):
            other = bodies[rng.choice(pool)]
            for kind in ss.DERIVATIONS:
                copy = ss.derive(bodies[u], kind, rng, other=other, vocabulary=vocabulary)
                if copy is None:
                    continue
                c = ss.profile(copy, r["k"], r["common"])
                s = ss.compare(c, prof[u])
                rows.append({"source_type": source_type, "edit": kind,
                             "comparable": ss.comparable(c, m), "shared": s.shared,
                             "coverage": s.a_in_b, "linked": s.shared >= m})
    return pd.DataFrame(rows)


def recall_spc(spc_dir: Path, texts: pd.DataFrame, r: dict) -> dict | None:
    """SPC's daily-report comments against the LSR they copy (same place and minute)."""
    files = sorted(spc_dir.glob("*_rpts_filtered_torn.csv")) if spc_dir.exists() else []
    if not files:
        return None
    m = r["min_shared"]
    lsr = texts[texts.source_type == "lsr"].copy()
    lsr["when"] = pd.to_datetime(lsr.published_at, utc=True, errors="coerce")
    rows = []
    for f in files:
        day = pd.Timestamp("20" + f.name[:6], tz="UTC")
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split(",", 7)      # the comment holds unquoted commas
            if len(parts) < 8 or not parts[0].strip().isdigit():
                continue
            hhmm = int(parts[0])
            when = day + pd.Timedelta(hours=hhmm // 100, minutes=hhmm % 100)
            if hhmm < 1200:                 # SPC's day runs 12 UTC to 12 UTC
                when += pd.Timedelta(days=1)
            lat, lon = float(parts[5]), float(parts[6])
            near = lsr[((lsr.when - when).abs() <= pd.Timedelta(minutes=2))
                       & ((lsr.lat - lat).abs() <= 0.02) & ((lsr.lon - lon).abs() <= 0.02)]
            row = {"file": f.name, "matched": bool(len(near))}
            if len(near):
                spc = ss.profile(parts[7], r["k"], r["common"])
                best = max((ss.compare(spc, r["profiles"][u]) for u in near.textref_uid),
                           key=lambda s: s.shared)
                row.update(comparable=ss.comparable(spc, m), shared=best.shared,
                           coverage=best.a_in_b, linked=best.shared >= m)
            rows.append(row)
    df = pd.DataFrame(rows)
    hit = df[df.matched].copy()
    out = {"files": [f.name for f in files], "reports": len(df), "matched_to_lsr": len(hit)}
    if len(hit):
        hit["comparable"] = hit.comparable.astype(bool)
        hit["linked"] = hit.linked.astype(bool)
        comp = hit[hit.comparable]
        out.update(too_short=int((~hit.comparable).sum()), comparable=len(comp),
                   linked=int(comp.linked.sum()),
                   recall_comparable=round(float(comp.linked.mean()), 3) if len(comp) else None,
                   coverage_median=round(float(hit.coverage.median()), 3))
    return out


# ── report ─────────────────────────────────────────────────────────────────

def label(a: str, b: str) -> str:
    return f"{SHORT.get(a, a)} – {SHORT.get(b, b)}"


def write_report(path: Path, tag: str, settings: dict, r: dict, rows: pd.DataFrame,
                 recall: pd.DataFrame, spc: dict | None, sensitivity: pd.DataFrame | None,
                 curve: pd.DataFrame, bounds: pd.DataFrame, overall: pd.Series,
                 dropped: dict, figure: Path) -> None:
    pairs, m = r["pairs"], r["min_shared"]
    co, cs = r["comparison"]["other_episode"], r["comparison"]["same_episode"]
    rule = (f"A shared run of {r['k']} tokens is *specific* when it occurs in the texts of at "
            f"most {WORDS.get(r['min_hazards'] - 2, r['min_hazards'] - 2)} hazard"
            f"{'' if r['min_hazards'] == 3 else 's'} besides the pair's own (each text counted "
            "for its nearest hazard)" if r["min_hazards"] else
            f"Every shared run of {r['k']} tokens counts (no filter for common runs)")
    L = [
        "# Same-source edits among the official texts",
        "",
        f"Tag `{tag}`. Generated by `scripts/25_find_same_source_edits.py`; the method is "
        "described in `src/tornado_dataset/text/same_source.py`.",
        "",
        "Which official texts of one hazard (survey statement, Storm Events narratives, DAT "
        "comments, LSRs) are edits of one account rather than independent descriptions. "
        + rule + f"; two texts are linked when at least **{m}** of their tokens lie in specific "
        "runs they share. Linked texts of a hazard form a group.",
        "",
        "## 1. Calibration",
        "",
        "Pairs that cannot be copies stand in for the false links, without hand labels: each "
        "text of a within-hazard pair is paired with a random text of the other's source type "
        "and office, either from **another episode** of the same year (no copy, no shared "
        "topic: a lower bound) or from **the same episode, another hazard** (same day, "
        "office and templates, but also some real copies between pieces of one tornado and "
        "through LSRs linked to the wrong tornado: an upper bound; identical texts excluded). "
        f"Rule: the smallest number of shared tokens from {settings['min_shared_floor']} at "
        f"which at most {settings['target_other_episode']:.1%} of the first and "
        f"{settings['target_same_episode']:.0%} of the second would link. Result: **{m}** "
        f"({r['min_shared_source']}).",
        "",
        "| shared tokens needed | other episode linked | same episode linked | "
        "within-hazard pairs linked |",
        "|---:|---:|---:|---:|",
    ]
    for c in curve.itertuples():
        mark = " ←" if c.min_shared == m else ""
        L.append(f"| {c.min_shared}{mark} | {c.other_episode:.3%} | {c.same_episode:.2%} | "
                 f"{c.within:.1%} |")
    L += [
        "",
        f"At {m}: {int(overall.links):,} of {int(overall.pairs):,} within-hazard pairs are linked. "
        f"Expected false links: {overall.false_other_episode:,.0f} by the other-episode set and "
        f"{overall.false_same_episode:,.0f} by the same-episode set, i.e. "
        f"**{overall.false_other_episode / overall.links:.1%} to "
        f"{overall.false_same_episode / overall.links:.1%} of the links**. Comparison pairs: "
        f"{len(co):,} and {len(cs):,}. Histogram: `figures/{figure.name}`.",
        "",
        "By source types:",
        "",
        "| source types | pairs | linked | expected false links (share of links) |",
        "|---|---:|---:|---:|",
    ]
    for b in bounds.itertuples():
        lo = b.false_other_episode / b.links if b.links else float("nan")
        hi = b.false_same_episode / b.links if b.links else float("nan")
        L.append(f"| {label(b.a_type, b.b_type)} | {b.pairs:,} | {b.linked_share:.1%} | "
                 f"{lo:.1%} – {hi:.1%} |")

    L += ["", "## 2. Recall", "",
          "Edited copies of a random sample of real texts, compared with their original. A "
          "copy is missed when the edit leaves fewer than "
          f"{m} tokens in shared specific runs. A copy whose own specific wording is shorter "
          "than that cannot be linked at all and is counted apart. Rising random rewording "
          "shows where verbatim reuse fades into paraphrase, which the method does not "
          "claim to detect.", "",
          "| edit | copies | too short | linked (of the rest) | median coverage |",
          "|---|---:|---:|---:|---:|"]
    for kind in ss.DERIVATIONS:
        g = recall[recall.edit == kind]
        if len(g):
            c = g[g.comparable]
            L.append(f"| {kind} | {len(g):,} | {(~g.comparable).mean():.1%} | "
                     f"{c.linked.mean():.1%} | {g.coverage.median():.2f} |")
    L += ["", "By source type of the original (all edits): " + ", ".join(
        f"{SHORT[t]} {g[g.comparable].linked.mean():.1%}"
        for t, g in recall.groupby("source_type")) + "."]
    if spc and spc.get("matched_to_lsr"):
        L += ["", f"**Real copies.** {spc['reports']} reports in the {len(spc['files'])} "
              f"hand-saved SPC daily files; {spc['matched_to_lsr']} match an LSR in stage 20 "
              "at the same place (0.02°) and minute (±2 min). SPC's comment is the LSR's "
              "remark, often cut at about 170 characters with the office appended, or an "
              f"earlier version of it. Too short to compare: {spc['too_short']}; linked: "
              f"**{spc['linked']} of {spc['comparable']} ({spc['recall_comparable']:.1%})**; "
              f"median coverage {spc['coverage_median']:.2f}."]
    else:
        L += ["", "Real copies: no SPC daily report files in `data/raw/spc_reports/`; the "
              "SPC–LSR check was skipped."]

    per_hazard = rows.drop_duplicates("hazard_uid")
    multi = per_hazard[per_hazard.hazard_texts >= 2]
    groups = rows.drop_duplicates(["hazard_uid", "edit_group"])
    shared = groups[groups.group_size >= 2]
    L += ["", "## 3. Groups", "",
          f"{len(rows):,} hazard–text rows over {len(per_hazard):,} hazards; "
          f"{(~rows.comparable).sum():,} texts have fewer than {m} specific tokens, "
          "cannot be linked and stay on their own.", "",
          f"- Hazards with two or more texts: {len(multi):,}, holding "
          f"{multi.hazard_texts.sum():,} texts in {multi.hazard_accounts.sum():,} accounts "
          f"(median {multi.hazard_texts.median():.0f} texts, "
          f"{multi.hazard_accounts.median():.0f} accounts).",
          f"- Groups of two or more texts: {len(shared):,}; bridged (some members not linked "
          f"directly): {shared.bridged.sum():,}.", "",
          "| source types in the group | groups |", "|---|---:|"]
    for comp, n in shared.group_source_types.value_counts().head(10).items():
        L.append(f"| {' + '.join(SHORT.get(x, x) for x in comp.split(';'))} | {n:,} |")

    container = rows.contained_in.map(dict(zip(rows.textref_uid, rows.source_type)))
    L += ["", f"Texts another member covers to at least {settings['contained_share']:.0%} "
          "(`contained_in`), by that member's source type:", "",
          "| text | texts | contained | in PNS | in narrative | in DAT comment | in LSR |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for st in ss.SOURCE_ORDER:
        g = rows[rows.source_type == st]
        c = container[g.index].value_counts()
        L.append(f"| {SHORT[st]} | {len(g):,} | {g.contained_in.notna().mean():.1%} | "
                 + " | ".join(f"{c.get(x, 0):,}" for x in ss.SOURCE_ORDER) + " |")
    reps = rows[rows.is_representative & (rows.group_size >= 2)].source_type.value_counts()
    L += ["", "Representatives of groups of two or more (the member covering most of the "
          "others' wording): " + ", ".join(f"{SHORT.get(k, k)} {v:,}" for k, v in reps.items())
          + "."]

    lsr = rows[rows.source_type == "lsr"]
    oracle_groups = set(rows.edit_group[rows.source_type.isin(ORACLE_TYPES)])
    L += ["", "LSRs grouped with a survey statement, narrative or DAT comment, by the LSR's "
          "source field. Stage 20 tiers every LSR `official_timely`, but those grouped with "
          "the survey's wording share it:", ""]
    for cls, g in lsr.groupby("lsr_class"):
        L.append(f"- {cls.replace('_', '-')}: {g.edit_group.isin(oracle_groups).mean():.1%} "
                 f"of {len(g):,}")

    if sensitivity is not None and len(sensitivity):
        L += ["", "## 4. Sensitivity", "",
              "The whole method rerun with one setting changed, the link rule recalibrated "
              "each time. Agreement: the share of the main run's within-hazard pairs whose "
              "\"same group\" status is unchanged.", "",
              "| run length | common from (hazards) | shared tokens needed | false links | "
              "pairs linked | groups ≥2 | agreement |",
              "|---:|---:|---:|---:|---:|---:|---:|"]
        for s in sensitivity.itertuples():
            L.append(f"| {s.k} | {s.min_hazards} | {s.min_shared} | {s.false_low:.1%} – "
                     f"{s.false_high:.1%} | {s.within_linked:.1%} | {s.groups:,} | "
                     f"{s.agreement:.1%} |")

    L += ["", "## 5. Scope and limits", "",
          "- Verbatim reuse only. A narrative that retells the survey in new words counts as "
          "a separate account; section 2 shows how detection fades with rewording.",
          "- No origin is inferred. Narratives and DAT comments carry no time, an LSR's time "
          "is the event's, and each hazard has one primary survey statement, so no pair has "
          "two publication times. `contained_in` and the representative are observations; "
          "the representative's tie-break (PNS, narrative, DAT comment, LSR) is a "
          "convention.",
          "- Groups are per hazard. A text linked to two hazards is grouped separately for "
          "each.",
          "- Each hazard's primary survey section is compared. Earlier revisions of it are "
          "stage 20 `mentions` and are not compared.",
          ]
    if dropped["links_to_hazards_not_in_stage_15"]:
        L.append("- Stage 20 or 24 predates the current hazards. Links to hazards no longer in "
                 f"stage 15 are left out: {dropped['links_to_hazards_not_in_stage_15']:,} "
                 f"({', '.join(f'{k} {v:,}' for k, v in dropped['of_which_relation'].items())});"
                 " rerun them.")
    L.append("")
    path.write_text("\n".join(L), encoding="utf-8")


def figure(path: Path, r: dict) -> None:
    bins = np.arange(0, 81, 2)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.hist(r["pairs"].shared.clip(upper=80), bins=bins, density=True, alpha=0.6,
            color="#2e6f95", label="texts of the same hazard")
    for scope, colour in (("same_episode", "#edae49"), ("other_episode", "#d1495b")):
        ax.hist(r["comparison"][scope].shared.clip(upper=80), bins=bins, density=True,
                alpha=0.5, color=colour, label=f"comparison: {scope.replace('_', ' ')}")
    ax.axvline(r["min_shared"], color="#333333", lw=1)
    ax.set_yscale("log")
    ax.set_xlabel("shared tokens of specific wording (clipped at 80)")
    ax.set_ylabel("density (log)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", nargs="?", default="run", choices=("run", "samples"),
                        help="run: tables and report (default); samples: the page to check by eye")
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--no-sensitivity", action="store_true",
                        help="skip the reruns with other run lengths and cut-offs")
    parser.add_argument("--per-stratum", type=int, default=25,
                        help="samples: samples per stratum (default 25)")
    parser.add_argument("--seed", type=int, default=None,
                        help="samples: draw another set (default config.EDIT_SEED)")
    args = parser.parse_args()
    tag = args.tag
    settings = {"k": config.EDIT_RUN_TOKENS, "min_hazards": config.EDIT_COMMON_HAZARDS,
                "min_shared_floor": config.EDIT_MIN_SHARED_FLOOR,
                "target_other_episode": config.EDIT_TARGET_OTHER_EPISODE,
                "target_same_episode": config.EDIT_TARGET_SAME_EPISODE,
                "contained_share": config.EDIT_CONTAINED_SHARE,
                "recall_texts_per_type": config.EDIT_RECALL_TEXTS, "seed": config.EDIT_SEED}
    started = time.time()

    links, texts, dropped = load(tag)
    print(f"{len(links):,} hazard–text links, {len(texts):,} texts, "
          f"{links.hazard_uid.nunique():,} hazards")
    r = run(links, texts, settings["k"], settings["min_hazards"], settings)
    pairs, comp = r["pairs"], r["comparison"]
    print(f"{len(pairs):,} within-hazard pairs; comparison pairs "
          + ", ".join(f"{s} {len(comp[s]):,}" for s in SCOPES)
          + f"; shared tokens needed: {r['min_shared']} ({r['min_shared_source']})")

    rows = group_rows(links, texts, r, settings["contained_share"])
    if args.action == "samples":
        seed = config.EDIT_SEED if args.seed is None else args.seed
        out = config.OUTPUT_DIR / f"same_source_samples_{tag}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(same_source_view.build(links, texts, rows, r, tag=tag,
                                              per_stratum=args.per_stratum, seed=seed),
                       encoding="utf-8")
        print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB); open it in a browser")
        return
    curve = pd.DataFrame([{"min_shared": n,
                           "other_episode": (comp["other_episode"].shared >= n).mean(),
                           "same_episode": (comp["same_episode"].shared >= n).mean(),
                           "within": (pairs.shared >= n).mean()}
                          for n in sorted({10, 12, 15, 20, 25, 30, r["min_shared"]})])
    bounds = false_link_bounds(pairs, comp, ["a_type", "b_type"])
    overall = false_link_bounds(pairs, comp, None).iloc[0]
    recall = recall_derived(texts, r, settings["recall_texts_per_type"], settings["seed"])
    spc = recall_spc(config.RAW_DIR / "spc_reports", texts, r)
    print(f"recall on edited copies: {recall[recall.comparable].linked.mean():.3f}; "
          f"SPC: {spc and spc.get('recall_comparable')}")

    sensitivity = None
    if not args.no_sensitivity:
        main_same = co_grouped(pairs, rows)
        variants = [(k, settings["min_hazards"]) for k in (4, 6, 8)]
        variants += [(settings["k"], d) for d in (2, 5, 10, None)]
        out = []
        for k, d in variants:
            v = run(links, texts, k, d, settings)
            v_rows = group_rows(links, texts, v, settings["contained_share"])
            o = false_link_bounds(v["pairs"], v["comparison"], None).iloc[0]
            groups = v_rows[v_rows.group_size >= 2].drop_duplicates(["hazard_uid", "edit_group"])
            out.append({"k": k, "min_hazards": "off" if d is None else d,
                        "min_shared": v["min_shared"],
                        "false_low": o.false_other_episode / max(o.links, 1),
                        "false_high": o.false_same_episode / max(o.links, 1),
                        "within_linked": v["pairs"].linked.mean(), "groups": len(groups),
                        "agreement": float((co_grouped(pairs, v_rows) == main_same).mean())})
            print(f"  sensitivity k={k} hazards={d}: needs {v['min_shared']}, "
                  f"agreement {out[-1]['agreement']:.3f}")
        sensitivity = pd.DataFrame(out)

    out_rows = config.PROCESSED_DIR / f"same_source_edits_{tag}.csv"
    out_pairs = config.INTERIM_DIR / f"same_source_pairs_{tag}.csv"
    out_pairs.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(out_rows, index=False)
    pairs.round(4).to_csv(out_pairs, index=False)

    fig_path = config.OUTPUT_DIR / "figures" / "same_source_shared_tokens.png"
    figure(fig_path, r)
    report = config.OUTPUT_DIR / "same_source_edits_report.md"
    write_report(report, tag, settings, r, rows, recall, spc, sensitivity, curve, bounds,
                 overall, dropped, fig_path)

    groups = rows.drop_duplicates(["hazard_uid", "edit_group"])
    multi = rows.drop_duplicates("hazard_uid").query("hazard_texts >= 2")
    counts = {
        "hazard_text_rows": len(rows), "texts": len(texts),
        "hazards": int(rows.hazard_uid.nunique()),
        "texts_by_type": texts.source_type.value_counts().to_dict(),
        "not_comparable": int((~rows.comparable).sum()),
        "common_runs": r["common_runs"],
        "min_shared": r["min_shared"], "min_shared_source": r["min_shared_source"],
        "within_pairs": len(pairs), "within_pairs_linked": int(pairs.linked.sum()),
        "comparison_pairs": {s: len(comp[s]) for s in SCOPES},
        "comparison_pairs_linked": {s: int(comp[s].linked.sum()) for s in SCOPES},
        "expected_false_links": {s: round(float(overall[f"false_{s}"]), 1) for s in SCOPES},
        "groups": len(groups), "groups_2plus": int((groups.group_size >= 2).sum()),
        "groups_bridged": int(groups.bridged.sum()),
        "hazards_with_2plus_texts": len(multi),
        "their_texts": int(multi.hazard_texts.sum()),
        "their_accounts": int(multi.hazard_accounts.sum()),
        "group_size": {int(k): int(v) for k, v in
                       groups.group_size.value_counts().sort_index().items()},
        "curve": curve.round(5).to_dict("records"),
        "recall_derived": recall[recall.comparable].groupby("edit").linked.mean()
        .round(3).to_dict(),
        "recall_derived_too_short": recall.groupby("edit").comparable
        .apply(lambda s: round(float(1 - s.mean()), 3)).to_dict(),
        "recall_spc": spc,
        "sensitivity": None if sensitivity is None else sensitivity.round(4).to_dict("records"),
        **dropped,
    }
    write_manifest(config.PROCESSED_DIR / f"manifest_same_source_{tag}.json",
                   "25_find_same_source_edits", counts=counts,
                   outputs=[out_rows, out_pairs, report], extra={"settings": settings})
    print(f"groups of 2+: {counts['groups_2plus']:,}; expected false links "
          f"{counts['expected_false_links']} of {counts['within_pairs_linked']:,}")
    print(f"wrote {out_rows.name}, {out_pairs.name}, {report.name} "
          f"({time.time() - started:.0f} s)")


if __name__ == "__main__":
    main()
