"""Map-based review of the stage 26 hand checks.

The two worksheets ``scripts/26_watch_systems.py sheets`` writes are hard to
judge from text alone: whether a grouping cuts an outbreak the way the official
summaries do, or whether a watch the motion check kept apart really belongs to
another system, is a question about places and times. This app shows both on a
map with a time slider and writes the labels straight back into the worksheet
CSVs, so ``check`` reads them unchanged.

* **Outbreaks.** Every SPC track of a named outbreak, coloured by group under
  grouping A–I (switch with the keys a–i), with a timeline of the groups below
  the map. The groupings stay blinded: the browser receives letters and
  per-outbreak group numbers, never the method or the raw group ids, and the
  key files are read only here on the server.
* **Compare.** After the blind labels: one outbreak under a few named
  groupings side by side (four synced maps, one shared time slider), with
  each grouping's blind label. Colours follow a reference grouping — a group
  takes the colour of the reference group it shares most tracks with — so a
  split or a merge shows as a change of colour. Read-only; it opens only once
  every outbreak row is labelled.
* **Watch pairs.** Watch A and B — polygons, the counties each covered and when
  (the linking rules work on these), A's storm motion, the other watches in
  effect around them and the tornadoes of the period — plus both SEL texts.
  The distances that made the motion check reject the pair stay in the key.

Labels go to the ``label`` and ``notes`` columns only, written atomically. Do
not keep the CSVs open in a spreadsheet program while labelling here.

    python scripts/26_watch_systems.py review          # http://127.0.0.1:8800
"""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

from .. import config
from ..dat import episodes as ep
from ..dat import spc_watches as sw

_WRITE_LOCK = threading.Lock()
OUTSIDE_DAYS = 3            # members of a group this far outside an outbreak window are shown
PAIR_PAD = pd.Timedelta(hours=3)
SIMPLIFY_DEG = 0.01         # ~1 km; for drawing only


def _clean(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _iso(ts) -> str | None:
    return None if ts is None or pd.isna(ts) else pd.Timestamp(ts).isoformat()


def _geojson(geom) -> dict | None:
    from shapely.geometry import mapping
    if geom is None or geom.is_empty:
        return None
    return mapping(geom.simplify(SIMPLIFY_DEG, preserve_topology=True))


def _write_label(path: Path, id_col: str, item_id: str, label: str | None, notes: str) -> None:
    """Set one row's label and notes, writing to a temporary file and renaming it."""
    with _WRITE_LOCK:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        hit = df[id_col] == item_id
        if hit.sum() != 1:
            raise KeyError(item_id)
        df.loc[hit, "label"] = label or ""
        df.loc[hit, "notes"] = notes or ""
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".csv.part")
        os.close(fd)
        df.to_csv(tmp, index=False)
        os.replace(tmp, path)


class WatchReviewStore:
    def __init__(self, tag: str, sheets: dict, raw_dir: Path, census_zip: Path,
                 outbreak_labels: tuple, review_labels: tuple, compare: tuple = ()):
        self.tag, self.paths, self.raw_dir, self.census_zip = tag, sheets, raw_dir, census_zip
        self.compare_names = list(compare)
        self.labels = {"outbreak": list(outbreak_labels), "review": list(review_labels)}
        for k in ("outbreak", "outbreak_key", "review", "review_key"):
            if not sheets[k].exists():
                raise SystemExit(f"no {sheets[k].name} — run `python scripts/26_watch_systems.py "
                                 "sheets` first")
        print("loading SPC tracks, groupings and watches …")
        t = pd.read_csv(config.INTERIM_DIR / "spc_tornadoes.csv", low_memory=False)
        t = t.rename(columns={"wid": "width_yd", "len": "length_mi"})
        t["t0"] = pd.to_datetime(t.begin_utc, utc=True)
        t["t1"] = pd.to_datetime(t.end_utc, utc=True)
        ws = pd.read_csv(config.PROCESSED_DIR / f"spc_watch_systems_{tag}.csv",
                         usecols=["spc_id", "watches", "system_id", "sequence_id"])
        asg = pd.read_csv(config.INTERIM_DIR / "episode_comparison_assignments_spc.csv"
                          ).rename(columns=ep.LEGACY_NAMES)
        self.tracks = (t.merge(ws, on="spc_id", how="left")
                       .merge(asg.rename(columns={"hazard_uid": "spc_id"}), on="spc_id",
                              how="left").sort_values("t0").reset_index(drop=True))
        w = pd.read_csv(config.INTERIM_DIR / f"spc_watches_{tag}.csv")
        for c in ("first_start", "last_end", "issue", "expire"):
            w[c] = pd.to_datetime(w[c], utc=True, errors="coerce")
        self.watches = w.set_index("wid", drop=False)
        self._years: dict[int, dict] = {}
        self._counties = None
        self._county_names = None

    # ── lazily loaded raw material ──────────────────────────────────────────
    def year(self, year: int) -> dict:
        """Polygons, cleaned county records and SEL texts of one year, cached."""
        if year not in self._years:
            records, polygons, _ = sw.load_year(year, self.raw_dir)
            records, _ = sw.clean_county_records(records, polygons)
            records["wid"] = [sw.watch_id(y, n) for y, n in zip(records.year, records.num)]
            polygons["wid"] = [sw.watch_id(y, n) for y, n in zip(polygons.year, polygons.num)]
            texts = {}
            for f in sorted((self.raw_dir / str(year)).glob("sel_*.txt")):
                for product in sw.split_products(f.read_text(encoding="utf-8")):
                    p = sw.parse_watch_text(product)
                    if p["num"] is not None and not p["cancellation"]:
                        texts.setdefault(sw.watch_id(year, p["num"]), product)
            self._years[year] = {"records": records,
                                 "polygons": polygons.drop_duplicates("wid").set_index("wid"),
                                 "texts": texts}
        return self._years[year]

    def counties(self) -> dict:
        """``ugc`` → simplified WGS84 county outline, and ``ugc`` → "Name, ST"."""
        if self._counties is None:
            import shapely
            from pyogrio import raw
            print("loading county outlines …")
            member = sw.COUNTY_BOUNDARIES.rsplit("/", 1)[1].replace(".zip", ".shp")
            meta, _, wkb, fields = raw.read(f"/vsizip/{self.census_zip}/{member}")
            cols = {n.upper(): v for n, v in zip(meta["fields"], fields)}
            usps = pd.Series(cols["STUSPS"]).astype(str)
            ugc = usps + "C" + pd.Series(cols["COUNTYFP"]).astype(str).str.zfill(3)
            geoms = shapely.simplify(shapely.from_wkb(wkb), SIMPLIFY_DEG, preserve_topology=True)
            self._counties = dict(zip(ugc, geoms))
            self._county_names = dict(zip(ugc, pd.Series(cols["NAME"]).astype(str) + ", " + usps))
        return self._counties

    def county_name(self, st, fips) -> str | None:
        if self._county_names is None:
            self.counties()
        if pd.isna(st) or pd.isna(fips) or int(fips) == 0:
            return None
        return self._county_names.get(f"{st}C{int(fips):03d}")

    def polygon(self, wid: str) -> pd.Series | None:
        year = int(wid.split("_")[0])
        polys = self.year(year)["polygons"]
        return polys.loc[wid] if wid in polys.index else None

    # ── sheets ──────────────────────────────────────────────────────────────
    def sheet(self, kind: str) -> pd.DataFrame:
        return pd.read_csv(self.paths[kind], dtype=str, keep_default_na=False)

    def state(self) -> dict:
        o = self.sheet("outbreak")
        outbreaks = []
        for code, g in o.groupby(o.row_id.str[:3], sort=True):
            outbreaks.append({
                "id": code, "title": g.outbreak.iat[0],
                "tornadoes": int(g.tornadoes_in_window.iat[0]),
                "reports": g.spc_reports.iat[0].split(),
                "rows": [{"row_id": r.row_id, "letter": r.row_id[-1], "label": r.label,
                          "notes": r.notes, "n_groups": int(r.n_groups_3plus)}
                         for r in g.itertuples()]})
        r = self.sheet("review")
        pairs = [{"pair_id": x.pair_id, "a": x.watch_a, "b": x.watch_b,
                  "a_type": x.watch_a_type, "b_type": x.watch_b_type,
                  "label": x.label, "notes": x.notes} for x in r.itertuples()]
        ready = self.compare_ready()
        return {"outbreaks": outbreaks, "pairs": pairs, "labels": self.labels, "tag": self.tag,
                "compare": {"ready": ready, "n": len(self.compare_names),
                            "names": self.compare_names if ready else []}}

    def save(self, kind: str, item_id: str, label: str | None, notes: str) -> None:
        if label and label not in self.labels[kind]:
            raise ValueError(f"label must be one of {self.labels[kind]}")
        id_col = "row_id" if kind == "outbreak" else "pair_id"
        _write_label(self.paths[kind], id_col, item_id, label, notes)

    # ── payloads ────────────────────────────────────────────────────────────
    def _track(self, r, extra: dict) -> dict:
        start = [r.slat, r.slon]
        known = pd.notna(r.elat) and pd.notna(r.elon) and r.elat != 0 and r.elon != 0
        end = [r.elat, r.elon] if known and (r.elat, r.elon) != (r.slat, r.slon) else None
        return {"id": r.spc_id, "t0": _iso(r.t0), "t1": _iso(r.t1),
                "coords": [start] + ([end] if end else []), "mag": _clean(r.mag),
                "st": r.st, "county": self.county_name(r.st, r.f1),
                "length_mi": _clean(r.length_mi), "width_yd": _clean(r.width_yd),
                "inj": _clean(r.inj), "fat": _clean(r.fat),
                "watches": [] if pd.isna(r.watches) else str(r.watches).split(";"), **extra}

    def _watch_shapes(self, lo, hi, exclude=()) -> list[dict]:
        w = self.watches
        sel = w[(w.first_start <= hi) & (w.last_end >= lo) & ~w.wid.isin(exclude)]
        out = []
        for x in sel.itertuples():
            p = self.polygon(x.wid)
            out.append({"wid": x.wid, "type": x.type, "start": _iso(x.first_start),
                        "end": _iso(x.last_end), "pds": bool(x.is_pds) if pd.notna(x.is_pds)
                        else False, "offices": x.wfos,
                        "geometry": _geojson(p.geometry) if p is not None else None})
        return out

    def _outbreak_rows(self, code: str):
        """The sheet rows of one outbreak and its window, 12Z first day to 12Z after the last."""
        o = self.sheet("outbreak")
        rows = o[o.row_id.str[:3] == code]
        if rows.empty:
            return None, None, None
        days = [d.strip() for d in rows.outbreak.iat[0].split("–")]
        lo = pd.Timestamp(days[0], tz="UTC") + pd.Timedelta(hours=12)
        hi = pd.Timestamp(days[-1], tz="UTC") + pd.Timedelta(hours=36)
        return rows, lo, hi

    def _grouped(self, lo, hi, cols: dict) -> dict:
        """Tracks of the window, plus members of their groups within OUTSIDE_DAYS, under
        each grouping in ``cols`` (key → assignment column). Groups are numbered per key
        from 0 by their tornado count inside the window, so raw ids never leave here."""
        t = self.tracks
        inside = (t.t0 >= lo) & (t.t0 < hi)
        near = (t.t0 >= lo - pd.Timedelta(days=OUTSIDE_DAYS)) & \
               (t.t0 < hi + pd.Timedelta(days=OUTSIDE_DAYS))
        show = inside.copy()
        for col in cols.values():
            ids = set(t.loc[inside, col].dropna())
            show |= near & t[col].isin(ids)
        shown = t[show]
        groupings, local = {}, {}
        for name, col in cols.items():
            counts = shown.loc[inside[show], col].value_counts()
            order = {gid: k for k, gid in enumerate(counts.index)}
            local[name] = shown[col].map(order)
            groups = []
            for gid, k in order.items():
                members = t[t[col] == gid]
                n_in = int(counts[gid])
                groups.append({
                    "g": k, "n": len(members), "n_inside": n_in, "small": n_in < 3,
                    "outside": len(members) - n_in, "start": _iso(members.t0.min()),
                    "end": _iso(members.t0.max()),
                    "max_ef": int(members.mag.max()) if members.mag.max() >= 0 else None,
                    "states": members.st.value_counts().index[:8].tolist()})
            groupings[name] = {"groups": groups,
                               "not_grouped": int(shown.loc[inside[show], col].isna().sum())}
        tracks = []
        for i, r in enumerate(shown.itertuples()):
            g = {k: (None if pd.isna(local[k].iat[i]) else int(local[k].iat[i])) for k in local}
            tracks.append(self._track(r, {"inside": bool(inside[show].iat[i]), "g": g}))
        return {"window": [_iso(lo), _iso(hi)],
                "extent": [_iso(shown.t0.min()), _iso(shown.t1.max())],
                "groupings": groupings, "tracks": tracks, "watches": self._watch_shapes(lo, hi)}

    def outbreak(self, code: str) -> dict | None:
        rows, lo, hi = self._outbreak_rows(code)
        if rows is None:
            return None
        key = pd.read_csv(self.paths["outbreak_key"]).set_index("row_id")
        cols = {r.row_id[-1]: key.loc[r.row_id, "column"] for r in rows.itertuples()}
        return {"id": code, "title": rows.outbreak.iat[0],
                "reports": rows.spc_reports.iat[0].split(),
                **self._grouped(lo, hi, dict(sorted(cols.items())))}

    def compare_ready(self) -> bool:
        """The compare view names the groupings, so it opens only once every outbreak row
        carries a label: the blind labels are then fixed."""
        return bool((self.sheet("outbreak").label != "").all())

    def compare(self, code: str) -> dict | None:
        """One outbreak under the groupings in ``self.compare_names``, unblinded, with the
        blind label and notes each got on this outbreak."""
        rows, lo, hi = self._outbreak_rows(code)
        if rows is None:
            return None
        key = pd.read_csv(self.paths["outbreak_key"])
        key = key[key.row_id.str[:3] == code].set_index("grouping_name")
        names = [n for n in self.compare_names if n in key.index]
        cols = {n: key.loc[n, "column"] for n in names}
        sheet = rows.set_index("row_id")
        panels = [{"name": n, "letter": key.loc[n, "row_id"][-1],
                   "label": sheet.loc[key.loc[n, "row_id"], "label"],
                   "notes": sheet.loc[key.loc[n, "row_id"], "notes"]} for n in names]
        return {"id": code, "title": rows.outbreak.iat[0],
                "reports": rows.spc_reports.iat[0].split(), "panels": panels,
                **self._grouped(lo, hi, cols)}

    def _watch_detail(self, wid: str) -> dict:
        x = self.watches.loc[wid]
        year = int(wid.split("_")[0])
        y = self.year(year)
        p = self.polygon(wid)
        rec = y["records"][y["records"].wid == wid]
        rec = rec.groupby("ugc", as_index=False).agg(start=("start", "min"), end=("end", "max"),
                                                    wfo=("wfo", "first"))
        shapes = self.counties()
        counties = [{"ugc": c.ugc, "name": self._county_names.get(c.ugc, c.ugc),
                     "start": _iso(c.start), "end": _iso(c.end), "wfo": c.wfo,
                     "geometry": _geojson(shapes.get(c.ugc))} for c in rec.itertuples()]
        num = int(wid.split("_")[1])
        return {"wid": wid, "num": num, "type": x.type, "start": _iso(x.first_start),
                "end": _iso(x.last_end), "issue": _iso(x.issue), "expire": _iso(x.expire),
                "offices": x.wfos, "pds": bool(x.is_pds) if pd.notna(x.is_pds) else False,
                "motion_from_deg": _clean(x.mv_drct), "motion_kt": _clean(x.mv_sknt),
                "replaces": x.replaces if isinstance(x.replaces, str) else "",
                "url": f"https://www.spc.noaa.gov/products/watch/{year}/ww{num:04d}.html",
                "geometry": _geojson(p.geometry) if p is not None else None,
                "counties": counties, "text": y["texts"].get(wid)}

    def pair(self, pair_id: str) -> dict | None:
        r = self.sheet("review")
        row = r[r.pair_id == pair_id]
        if row.empty:
            return None
        a, b = row.watch_a.iat[0], row.watch_b.iat[0]
        wa, wb = self._watch_detail(a), self._watch_detail(b)
        lo = min(self.watches.loc[a].first_start, self.watches.loc[b].first_start) - PAIR_PAD
        hi = max(self.watches.loc[a].last_end, self.watches.loc[b].last_end) + PAIR_PAD
        context = self._watch_shapes(lo, hi, exclude=(a, b))
        from shapely.geometry import shape
        from shapely.ops import unary_union
        parts = [shape(g) for g in (wa["geometry"], wb["geometry"]) if g] + \
                [shape(c["geometry"]) for w in (wa, wb) for c in w["counties"] if c["geometry"]]
        area = unary_union(parts).buffer(3.0) if parts else None
        if area is not None:
            context = [c for c in context if c["geometry"] and shape(c["geometry"]).intersects(area)]
        t = self.tracks
        sel = t[(t.t0 >= lo) & (t.t0 <= hi)]
        if area is not None:
            minx, miny, maxx, maxy = area.bounds
            sel = sel[(sel.slon >= minx) & (sel.slon <= maxx) & (sel.slat >= miny) & (sel.slat <= maxy)]
        tracks = [self._track(x, {}) for x in sel.itertuples()]
        return {"pair_id": pair_id, "a": wa, "b": wb, "window": [_iso(lo), _iso(hi)],
                "gap_min": int(row.b_starts_minutes_after_a_ends.iat[0]),
                "context": context, "tracks": tracks}


def create_watch_review_app(tag: str, sheets: dict, raw_dir: Path, census_zip: Path,
                            outbreak_labels: tuple, review_labels: tuple,
                            compare: tuple = ()) -> Flask:
    app = Flask(__name__)
    store = WatchReviewStore(tag, sheets, raw_dir, census_zip, outbreak_labels, review_labels,
                             compare)

    @app.get("/")
    def index():
        return render_template("watch_review.html", tag=tag)

    @app.get("/api/state")
    def api_state():
        return jsonify(store.state())

    @app.get("/api/outbreak/<code>")
    def api_outbreak(code: str):
        out = store.outbreak(code)
        return (jsonify(out), 200) if out else (jsonify({"error": "unknown outbreak"}), 404)

    @app.get("/api/compare/<code>")
    def api_compare(code: str):
        if not store.compare_ready():
            return jsonify({"error": "label every outbreak grouping first — the compare view "
                                     "names the groupings"}), 409
        out = store.compare(code)
        return (jsonify(out), 200) if out else (jsonify({"error": "unknown outbreak"}), 404)

    @app.get("/api/pair/<pair_id>")
    def api_pair(pair_id: str):
        out = store.pair(pair_id)
        return (jsonify(out), 200) if out else (jsonify({"error": "unknown pair"}), 404)

    @app.post("/api/label")
    def api_label():
        body = request.get_json(force=True) or {}
        kind = body.get("kind")
        if kind not in ("outbreak", "review"):
            return jsonify({"error": "kind must be outbreak or review"}), 400
        try:
            store.save(kind, str(body.get("id", "")), body.get("label") or None,
                       str(body.get("notes") or ""))
        except (ValueError, KeyError) as e:
            return jsonify({"error": str(e)}), 400
        return jsonify({"ok": True})

    return app
