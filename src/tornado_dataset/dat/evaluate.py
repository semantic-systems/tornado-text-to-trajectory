"""Evaluate the spatial line->polygon linker against DAT's own foreign key.

Some damage polygons carry ``path_guid``, a reference to the parent line's
``globalid``. The linker never reads that column, so those polygons form a gold
standard for measuring how well geometry alone recovers the intended link.

The usable gold set is far smaller than the field's population rate suggests:
across 2010-2025, 3,467 of 9,989 polygons hold the all-zero placeholder GUID and
only **289 hold a real reference** — which is why ``link.real_path_guid`` filters
the placeholder rather than testing for a non-empty string.

Three things this module is careful about:

* **The gold set is small and not a random sample.** The 289 usable rows fall in
  2017 and 2020-2025 only, reflecting DAT editing practice rather than any
  property of the tornadoes. Metrics are therefore reported *conditional* on that
  subpopulation, alongside the per-year and per-WFO population rates and a
  stratified breakdown, so a reader can judge how far they generalise.
* **Coverage and correctness are separate questions.** A polygon whose true line
  is absent from the candidate set is a recall failure of the *candidate search*;
  a polygon assigned the wrong line is an error of the *ranking*. They are
  counted separately.
* **Confidence has to mean something.** The reliability table compares the
  published ``link_confidence`` against the observed accuracy in each bin.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from .link import real_path_guid


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval — well behaved for proportions near 0 or 1."""
    if total == 0:
        return (float("nan"), float("nan"))
    phat = successes / total
    denominator = 1 + z * z / total
    centre = (phat + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(phat * (1 - phat) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def gold_polygons(polygons: list[dict[str, Any]], line_globalids: set[str]) -> pd.DataFrame:
    """Polygons carrying a real ``path_guid``, flagged by whether it resolves.

    A GUID pointing at a line outside the study window (or since deleted) cannot
    be scored; it is kept with ``resolvable=False`` and counted rather than
    dropped, so the report can state how much of the key was unusable.
    """
    rows = []
    for feature in polygons:
        props = feature.get("properties", {})
        guid = real_path_guid(props.get("path_guid"))
        if guid is None:
            continue
        rows.append({
            "polygon_oid": props.get("objectid"),
            "true_line_globalid": guid,
            "resolvable": guid in line_globalids,
            "stormdate": props.get("stormdate"),
            "efscale": props.get("efscale"),
        })
    return pd.DataFrame(rows)


def score_assignment(best: pd.DataFrame, gold: pd.DataFrame,
                     candidates: pd.DataFrame | None = None) -> dict[str, Any]:
    """Score the best-line-per-polygon assignment against the gold set.

    Returns counts and rates for: assignment accuracy (of the polygons that were
    assigned a line at all), candidate-set recall (was the true line even among
    the candidates?), and the two failure modes.
    """
    scored = gold[gold.resolvable].merge(
        best[["polygon_oid", "line_globalid", "line_wfo", "link_confidence", "gap_m",
              "frac_line_in_polygon", "shared_event_id"]],
        on="polygon_oid", how="left")
    scored["assigned"] = scored.line_globalid.notna()
    scored["correct"] = scored.assigned & (scored.line_globalid == scored.true_line_globalid)

    result: dict[str, Any] = {
        "gold_polygons_total": int(len(gold)),
        "gold_unresolvable": int((~gold.resolvable).sum()),
        "gold_scored": int(len(scored)),
        "assigned": int(scored.assigned.sum()),
        "correct": int(scored.correct.sum()),
        "wrong_line": int((scored.assigned & ~scored.correct).sum()),
        "not_assigned": int((~scored.assigned).sum()),
    }
    result["precision"] = result["correct"] / result["assigned"] if result["assigned"] else float("nan")
    result["recall"] = result["correct"] / result["gold_scored"] if result["gold_scored"] else float("nan")
    if result["precision"] + result["recall"] > 0:
        result["f1"] = (2 * result["precision"] * result["recall"]
                        / (result["precision"] + result["recall"]))
    else:
        result["f1"] = float("nan")
    result["precision_ci"] = wilson_interval(result["correct"], result["assigned"])
    result["recall_ci"] = wilson_interval(result["correct"], result["gold_scored"])

    if candidates is not None and len(candidates):
        pairs = set(zip(candidates.polygon_oid, candidates.line_globalid))
        scored["true_line_in_candidates"] = [
            (row.polygon_oid, row.true_line_globalid) in pairs for row in scored.itertuples()]
        found = scored.true_line_in_candidates
        result["true_line_in_candidates"] = int(found.sum())
        result["candidate_recall"] = found.mean() if len(scored) else float("nan")
        # Three distinct ways to miss, kept apart because they call for different
        # fixes: a wider search, a looser acceptance threshold, or better ranking.
        result["search_misses"] = int((~found).sum())
        result["threshold_exclusions"] = int((found & ~scored.assigned).sum())
        result["ranking_errors"] = int((found & scored.assigned & ~scored.correct).sum())

    result["_scored"] = scored
    return result


def threshold_sweep(candidates: pd.DataFrame, gold: pd.DataFrame,
                    gaps: list[float], date_deltas: list[int]) -> pd.DataFrame:
    """Precision/recall over a grid of (gap threshold, date guard) operating points.

    Re-runs the *ranking* on filtered candidate sets, which is why candidate
    generation uses a wider radius than any point in this grid. Reported in full
    rather than only at the chosen point, so the choice is inspectable.
    """
    truth = dict(zip(gold[gold.resolvable].polygon_oid,
                     gold[gold.resolvable].true_line_globalid))
    rows = []
    for gap in gaps:
        for delta in date_deltas:
            subset = candidates[(candidates.gap_m <= gap)
                                & (candidates.date_delta_days.isna()
                                   | (candidates.date_delta_days <= delta))]
            assigned = correct = 0
            if not subset.empty:
                ordered = subset.sort_values(["frac_line_in_polygon", "gap_m"],
                                             ascending=[False, True])
                picked = ordered.groupby("polygon_oid").first()
                scoreable = picked[picked.index.isin(truth)]
                assigned = len(scoreable)
                correct = sum(1 for oid, row in scoreable.iterrows()
                              if row.line_globalid == truth[oid])
            rows.append({
                "gap_threshold_m": gap, "max_date_delta_days": delta,
                "polygons_linked": int(subset.polygon_oid.nunique()) if not subset.empty else 0,
                "gold_assigned": int(assigned), "gold_correct": int(correct),
                "precision": correct / assigned if assigned else float("nan"),
                "recall": correct / len(truth) if truth else float("nan"),
            })
    return pd.DataFrame(rows)


def diagnose_unlinked(lines: list[dict[str, Any]], polygons: list[dict[str, Any]],
                      linked_oids: set[Any]) -> pd.DataFrame:
    """For every polygon with no accepted link, how far away is the nearest line?

    Distinguishes a *linker* limitation (a track exists just beyond the
    threshold) from a *data* property (the polygon was drawn without any track
    line, which is common for damage surveyed as an area rather than a path).
    Distances are reported both ignoring the date and restricted to the same day.
    """
    from shapely import STRtree

    if not lines:
        return pd.DataFrame()
    tree = STRtree([line["proj"] for line in lines])
    by_date: dict[Any, list[int]] = {}
    for i, line in enumerate(lines):
        by_date.setdefault(line["date"], []).append(i)

    rows = []
    for polygon in polygons:
        if polygon["objectid"] in linked_oids:
            continue
        nearest = tree.nearest(polygon["proj"])
        distance = polygon["proj"].distance(lines[nearest]["proj"])
        same_day = [i for i in by_date.get(polygon["date"], [])]
        same_day_distance = min(
            (polygon["proj"].distance(lines[i]["proj"]) for i in same_day), default=None)
        rows.append({
            "polygon_oid": polygon["objectid"],
            "stormdate": polygon["properties"].get("stormdate"),
            "nearest_line_m": round(distance, 1),
            "nearest_same_day_line_m": (round(same_day_distance, 1)
                                        if same_day_distance is not None else None),
            "any_line_that_day": bool(same_day),
        })
    return pd.DataFrame(rows)


def calibration(scored: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    """Observed accuracy per link_confidence bin (reliability table)."""
    assigned = scored[scored.assigned].copy()
    if assigned.empty:
        return pd.DataFrame()
    assigned["bin"] = pd.cut(assigned.link_confidence, bins=[i / bins for i in range(bins + 1)],
                             include_lowest=True)
    grouped = assigned.groupby("bin", observed=True).agg(
        n=("correct", "size"),
        mean_confidence=("link_confidence", "mean"),
        observed_accuracy=("correct", "mean"))
    grouped[["ci_low", "ci_high"]] = [
        wilson_interval(int(round(row.observed_accuracy * row.n)), int(row.n))
        for row in grouped.itertuples()]
    return grouped.reset_index()


def stratify(scored: pd.DataFrame, by: str) -> pd.DataFrame:
    """Accuracy within strata (year or WFO) — does the estimate hold up?"""
    frame = scored.copy()
    if by == "year":
        frame["stratum"] = frame.stormdate.astype(str).str[:4]
    else:
        frame["stratum"] = frame[by].fillna("(missing)")
    grouped = frame.groupby("stratum", dropna=False).agg(
        n=("correct", "size"), correct=("correct", "sum"), assigned=("assigned", "sum"))
    grouped["accuracy"] = grouped.correct / grouped.n
    return grouped.reset_index()


def population_rates(polygons: list[dict[str, Any]], by: str = "year") -> pd.DataFrame:
    """How often the key fields are populated per year — is the gold set typical?

    Counts the placeholder GUID separately from a real reference, because the two
    look identical to a SQL ``IS NOT NULL`` test and differ completely in value.
    The polygon layer has no ``wfo`` column, so WFO strata come from the linked
    line instead (see :func:`stratify`).
    """
    rows = []
    for feature in polygons:
        props = feature.get("properties", {})
        raw = str(props.get("path_guid") or "").strip()
        rows.append({
            "year": str(props.get("stormdate") or "")[:4] or "(missing)",
            "real_path_guid": real_path_guid(raw) is not None,
            "placeholder_guid": bool(raw) and real_path_guid(raw) is None,
            "has_event_id": bool(str(props.get("event_id") or "").strip()),
            "has_comments": bool(str(props.get("comments") or "").strip()),
        })
    frame = pd.DataFrame(rows)
    grouped = frame.groupby(by).agg(n=("real_path_guid", "size"),
                                    real_path_guid=("real_path_guid", "sum"),
                                    placeholder_guid=("placeholder_guid", "sum"),
                                    with_event_id=("has_event_id", "sum"),
                                    with_comments=("has_comments", "sum"))
    grouped["path_guid_rate"] = grouped.real_path_guid / grouped.n
    grouped["event_id_rate"] = grouped.with_event_id / grouped.n
    grouped["comments_rate"] = grouped.with_comments / grouped.n
    return grouped.reset_index()
