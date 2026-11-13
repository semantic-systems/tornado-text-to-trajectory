"""Viewer for the silver links (stage 44): a tornado, its path, and the texts linked to it.

One tornado at a time: its path on a map — DAT's damage polygon and track
line, SPC's straight start–end track, Storm Events' county segments — and every
Wikipedia passage and news article stage 44 linked to it, with its URL and
full text. The tornado's counties and the places a passage's heading names are
highlighted in each text, which is what the link rests on.

    python scripts/viewer.py --corpus silver          # http://127.0.0.1:8799

Read-only. Strengths and checks are hidden at first ("blind"), so that browsing
does not bias the hand check of stage 44's sheet; one click shows them. Links
the checks rejected are not part of the silver set: they are shown apart, with
the reason, in every mode. A hand-check row id (``s012``) in the search finds
that row's tornado.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, jsonify, render_template, request

from .. import config
from ..dat import references as refs
from ..text import silver
from ..text import wikifacts as wf

SILVER_CSV = config.PROCESSED_DIR / "wikipedia_silver_links.csv"
PASSAGES_JSONL = config.PROCESSED_DIR / "wikipedia_passages.jsonl"
NEWS_JSONL = config.PROCESSED_DIR / "wikipedia_cited_news.jsonl"
LEXIS_JSONL = config.OUTPUT_DIR / "lexisnexis_articles.jsonl"
SHEET_KEY = config.INTERIM_DIR / "wikipedia_silver_handcheck_key.csv"
NCEI_EVENT_URL = "https://www.ncdc.noaa.gov/stormevents/eventdetails.jsp?id={}"
STRENGTH_ORDER = {s: i for i, s in enumerate(silver.STRENGTHS)}
GEOMETRIES = ("dat_polygon", "dat_line", "spc_track", "none")
KIND_ORDER = {"wikipedia_passage": 0, "cited_news": 1, "lexisnexis": 2}


def _clean(value: Any) -> Any:
    """JSON-safe scalars: NaN and "" become None, numpy types Python ones."""
    if value is None or (isinstance(value, str) and value == ""):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value.item() if hasattr(value, "item") else value


def _split(value) -> list[str]:
    return [v for v in str(value or "").split("|") if v and v != "nan"]


def _bool(value) -> bool | None:
    s = str(value).strip().lower()
    return True if s == "true" else False if s == "false" else None


def _features(path, wanted: set[str]) -> dict[str, list[dict]]:
    """The GeoJSON geometries of hazards ``wanted``, a GeometryCollection split
    into its parts so each can be drawn in its own style."""
    out: dict[str, list[dict]] = {}
    if not wanted or not path.exists():
        return out
    with path.open(encoding="utf-8") as fh:
        for f in json.load(fh)["features"]:
            uid = f["properties"].get("hazard_uid")
            if uid not in wanted or not f.get("geometry"):
                continue
            g = f["geometry"]
            parts = g["geometries"] if g["type"] == "GeometryCollection" else [g]
            out.setdefault(uid, []).extend(parts)
    return out


class SilverStore:
    def __init__(self, tag: str | None = None):
        self.tag = tag or f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
        config.require_data(SILVER_CSV, PASSAGES_JSONL, NEWS_JSONL, refs.SE_TORNADOES)
        print("loading the silver links, Storm Events, geometries and texts…")
        links = pd.read_csv(SILVER_CSV, keep_default_na=False, low_memory=False)
        self.links = links[links.link_level == "hazard"].copy()
        keys = set(self.links.tornado_key)

        se = pd.read_csv(refs.SE_TORNADOES, low_memory=False)
        se = se[se.TORNADO_KEY.isin(keys)]
        self.tornadoes = silver.tornadoes(se)
        self.segments = {k: g.sort_values("begin_utc") for k, g in se.groupby("TORNADO_KEY")}

        dat = {u for v in self.links.dat_hazard_uids for u in _split(v)}
        own = {u for v in self.links.get("spc_hazard_uids", pd.Series(dtype=str)) for u in _split(v)}
        self.dat_geoms = _features(config.PROCESSED_DIR / f"hazards_{self.tag}.geojson", dat)
        self.spc_geoms = _features(config.PROCESSED_DIR / f"spc_hazards_{self.tag}.geojson", own)

        uids = set(self.links.text_uid) | {p for v in self.links.get("citing_passages", [])
                                           for p in _split(v)}
        self.passages = {r["textref_uid"]: r for r in map(json.loads, PASSAGES_JSONL.open(encoding="utf-8"))
                         if r["textref_uid"] in uids}
        self.news = {r["textref_uid"]: r for r in map(json.loads, NEWS_JSONL.open(encoding="utf-8"))
                     if r["textref_uid"] in uids}
        self.lexis = self._lexis(set(self.links.text_uid[self.links.text_kind == "lexisnexis"]))

        self.sheet: dict[str, dict] = {}       # text_uid → {row_id, tornado_key}
        if SHEET_KEY.exists():
            for r in pd.read_csv(SHEET_KEY, keep_default_na=False).itertuples():
                self.sheet[r.text_uid] = {"row_id": r.row_id, "tornado_key": r.tornado_key}

        self.index = [self._summary(k, g) for k, g in self.links.groupby("tornado_key")]
        self.index.sort(key=lambda t: (t["date"], t["name"]))
        print(f"  {len(self.index)} tornadoes, {len(self.links):,} linked texts "
              f"({len(self.passages)} passages, {len(self.news)} cited news, {len(self.lexis)} LexisNexis)")

    @staticmethod
    def _lexis(uids: set[str]) -> dict[str, dict]:
        from ..text.lexisnexis import textref_uid
        out = {}
        if uids and LEXIS_JSONL.exists():
            for line in LEXIS_JSONL.open(encoding="utf-8"):
                r = json.loads(line)
                if (u := textref_uid(r)) in uids:
                    out[u] = r
        return out

    # ── list ────────────────────────────────────────────────────────────────
    def _name(self, g: pd.DataFrame) -> str:
        """The tornado's name: a dedicated article's title, else a section heading
        (a rejected passage is about another tornado, so never its name)."""
        p = g[g.text_kind == "wikipedia_passage"]
        p = p[p.strength != "rejected"] if (p.strength != "rejected").any() else p
        arts = p[p.unit_kind == "tornado_article"]
        if len(arts):
            return arts.title.iloc[0]
        heads = [h for h in p.heading if h]
        return heads[0] if heads else (p.title.iloc[0] if len(p) else g.title.iloc[0])

    def _summary(self, key: str, g: pd.DataFrame) -> dict:
        t = self.tornadoes[key]
        kept = g[g.strength != "rejected"]
        p = kept[kept.text_kind == "wikipedia_passage"]
        sheet_rows = sorted(self.sheet[u]["row_id"] for u in g.text_uid
                            if u in self.sheet and self.sheet[u]["tornado_key"] == key)
        best = min((STRENGTH_ORDER[s] for s in p.strength if s in STRENGTH_ORDER), default=3)
        names = " ".join([self._name(g), *g.title, *g.page_title, *t["counties"], *t["states"],
                          *sheet_rows])
        return {
            "key": key, "name": self._name(g), "date": t["date"], "year": t["date"][:4],
            "rating": t["rating"], "states": sorted(t["states"]),
            "n_passages": int(len(p)), "n_news": int((kept.text_kind != "wikipedia_passage").sum()),
            "n_lexis": int((kept.text_kind == "lexisnexis").sum()),
            "n_rejected": int((g.strength == "rejected").sum()),
            "geometry": g.geometry.iloc[0] or "none",
            "strengths": sorted(set(g.strength), key=lambda s: STRENGTH_ORDER.get(s, 9)),
            "passage_strength": silver.STRENGTHS[best],
            "sheet_rows": sheet_rows, "deaths": t["deaths"],
            "_hay": wf.fold(names),
        }

    def facets(self) -> dict:
        return {"total": len(self.index), "n_texts": len(self.links),
                "years": sorted({t["year"] for t in self.index}),
                "strengths": list(silver.STRENGTHS), "geometries": list(GEOMETRIES),
                "has_sheet": bool(self.sheet)}

    def search(self, a: dict) -> dict:
        q = wf.fold(a.get("q", ""))
        rows = []
        for t in self.index:
            if q and not all(w in t["_hay"] for w in q.split()):
                continue
            if a.get("year") and t["year"] != a["year"]:
                continue
            if a.get("geometry") and t["geometry"] != a["geometry"]:
                continue
            if a.get("strength") and a["strength"] not in t["strengths"]:
                continue
            if a.get("has") == "lexis" and not t["n_lexis"]:
                continue
            if a.get("has") == "news" and not t["n_news"]:
                continue
            if a.get("has") == "sheet" and not t["sheet_rows"]:
                continue
            rows.append({k: v for k, v in t.items() if not k.startswith("_")})
        order = a.get("sort", "date")
        if order == "news":
            rows.sort(key=lambda t: -t["n_news"])
        elif order == "deaths":
            rows.sort(key=lambda t: -t["deaths"])
        return {"total": len(rows), "rows": rows}

    # ── one tornado ─────────────────────────────────────────────────────────
    def _map(self, key: str, g: pd.DataFrame) -> dict:
        feats = []
        for uid in sorted({u for v in g.dat_hazard_uids for u in _split(v)}):
            for geom in self.dat_geoms.get(uid, []):
                role = "dat_polygon" if "Polygon" in geom["type"] else "dat_line"
                feats.append({"type": "Feature", "geometry": geom,
                              "properties": {"role": role, "hazard_uid": uid}})
        for uid in sorted({u for v in g.get("spc_hazard_uids", []) for u in _split(v)}):
            for geom in self.spc_geoms.get(uid, []):
                feats.append({"type": "Feature", "geometry": geom,
                              "properties": {"role": "spc_track", "hazard_uid": uid}})
        for r in self.segments[key].itertuples():
            pts = [[r.BEGIN_LON, r.BEGIN_LAT], [r.END_LON, r.END_LAT]]
            pts = [p for p in pts if pd.notna(p[0]) and pd.notna(p[1]) and p != [0, 0]]
            if not pts:
                continue
            geom = ({"type": "LineString", "coordinates": pts} if len(pts) == 2 and pts[0] != pts[1]
                    else {"type": "Point", "coordinates": pts[0]})
            feats.append({"type": "Feature", "geometry": geom,
                          "properties": {"role": "se_segment", "event_id": int(r.EVENT_ID),
                                         "county": f"{str(r.CZ_NAME).title()}, {str(r.STATE).title()}",
                                         "rating": r.TOR_F_SCALE,
                                         "length_mi": _clean(r.TOR_LENGTH),
                                         "width_yd": _clean(r.TOR_WIDTH)}})
        return {"type": "FeatureCollection", "features": feats}

    def _text(self, r) -> dict:
        kind = r.text_kind
        base = {
            "uid": r.text_uid, "kind": kind, "title": r.title, "url": _clean(r.url),
            "published": _clean(r.published_at), "strength": r.strength, "how": r.how,
            "evidence": _clean(r.evidence),
            "reject_reason": _clean(getattr(r, "reject_reason", "")),
            "mediacloud": {"n": len(_split(getattr(r, "mediacloud_ids", ""))),
                           "tier": _clean(getattr(r, "mediacloud_tier", "")),
                           "label": _clean(getattr(r, "mediacloud_label", ""))},
            "checks": {k: _bool(getattr(r, k, "")) for k in ("date_ok", "state_ok", "place_ok", "rating_ok")},
            "days_after_event": _clean(pd.to_numeric(getattr(r, "days_after_event", ""), errors="coerce")),
            "sheet_row": self.sheet.get(r.text_uid, {}).get("row_id"),
        }
        if kind == "wikipedia_passage":
            p = self.passages.get(r.text_uid, {})
            base.update({"page_title": p.get("page_title"), "heading": p.get("heading"),
                         "unit_kind": p.get("unit_kind"), "event_date": p.get("event_date"),
                         "event_date_basis": p.get("event_date_basis"),
                         "source": "Wikipedia", "text": p.get("text") or "",
                         "ncei_ids": _split(getattr(r, "cited_ncei_ids", "")),
                         "table_match": _clean(getattr(r, "table_match", "")),
                         "n_tornadoes_cited": _clean(pd.to_numeric(getattr(r, "n_tornadoes_cited", ""),
                                                                   errors="coerce")),
                         "places": wf.place_names(p.get("heading") or p.get("title") or "")})
        elif kind == "cited_news":
            n = self.news.get(r.text_uid, {})
            base.update({"source": n.get("source_name") or n.get("domain"),
                         "text": n.get("text") or "", "text_quality": n.get("text_quality"),
                         "archive_url": n.get("wikipedia_archive_url") or n.get("wayback_snapshot_url"),
                         "story_primary": _bool(getattr(r, "story_primary", ""))})
        else:
            x = self.lexis.get(r.text_uid, {})
            base.update({"source": x.get("source") or "LexisNexis", "text": x.get("body") or "",
                         "text_quality": "lexisnexis", "byline": x.get("byline")})
        if kind != "wikipedia_passage":
            base["citing"] = [{"uid": u, "title": self.passages.get(u, {}).get("title") or u,
                               "url": self.passages.get(u, {}).get("url")}
                              for u in _split(getattr(r, "citing_passages", ""))]
        return base

    def tornado(self, key: str) -> dict | None:
        if key not in self.tornadoes:
            return None
        g = self.links[self.links.tornado_key == key]
        t = self.tornadoes[key]
        texts = [self._text(r) for r in g.itertuples()]
        texts.sort(key=lambda x: (KIND_ORDER.get(x["kind"], 9), x["published"] or "9999", x["title"] or ""))
        segs = self.segments[key]
        places = sorted({p for x in texts for p in x.get("places", [])})
        first = g.iloc[0]
        return {
            "key": key, "name": self._name(g), "date": t["date"], "rating": t["rating"],
            "states": sorted(t["states"]), "counties": sorted(c.title() for c in t["counties"]),
            "length_mi": t["length_mi"], "deaths": t["deaths"],
            "injuries": int(pd.to_numeric(segs.INJURIES_DIRECT, errors="coerce").fillna(0).sum())
            if "INJURIES_DIRECT" in segs else None,
            "event_ids": t["event_ids"], "ncei_url": NCEI_EVENT_URL,
            "narratives": [{"event_id": int(r.EVENT_ID), "county": str(r.CZ_NAME).title(),
                            "text": r.EVENT_NARRATIVE} for r in segs.itertuples()
                           if isinstance(r.EVENT_NARRATIVE, str) and r.EVENT_NARRATIVE.strip()],
            "geometry": first.geometry or "none", "dat_via": _clean(first.get("dat_via")),
            "dat_hazard_uids": _split(first.dat_hazard_uids),
            "spc_ids": _split(first.get("spc_ids")), "episode_uids": _split(first.get("episode_uids")),
            "terms": sorted({*(c for c in t["counties"] if len(c) > 3), *places}, key=len, reverse=True),
            "map": self._map(key, g), "texts": texts,
        }


def create_silver_app(tag: str | None = None) -> Flask:
    app = Flask(__name__)
    store = SilverStore(tag)

    static = Path(app.static_folder)

    @app.get("/")
    def index():
        # The files' mtimes as a version, so an edited script is never served stale.
        version = int(max((static / f).stat().st_mtime for f in ("silver.js", "silver.css")))
        return render_template("silver.html", facets=store.facets(), v=version)

    @app.get("/api/tornadoes")
    def api_tornadoes():
        return jsonify(store.search(request.args.to_dict()))

    @app.get("/api/tornado/<key>")
    def api_tornado(key: str):
        t = store.tornado(key)
        return (jsonify(t), 200) if t else (jsonify({"error": "unknown tornado"}), 404)

    return app
