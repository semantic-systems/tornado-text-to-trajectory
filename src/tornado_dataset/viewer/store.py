"""In-memory store behind the viewer: articles, links, events, geometry.

Everything is loaded once at start-up and indexed by uid. The corpus is ~130 MB
of body text and the tables another ~40 MB, which is a few hundred MB resident —
fine for a single-user local tool and far simpler than a database.

The store owns two jobs beyond lookup:

* it derives the same ``textref_uid`` the linker used, by importing the shared
  helper rather than recomputing it, so the viewer and the pipeline cannot
  disagree about which article is which;
* it serves each episode's tracks as WGS84 GeoJSON, simplified and rounded, so the
  browser can draw them on an OpenStreetMap basemap and the reader can see which
  streets a tornado crossed rather than an abstract shape.
"""

from __future__ import annotations

import datetime as dt
import json
import math
from collections import defaultdict
from typing import Any

import pandas as pd

from shapely.geometry import mapping

from .. import config, viz
from ..dat import episode_table
from ..dat.geometry import to_shapely
from ..text.lexisnexis import textref_uid

# Columns of the link table that are evidence rather than bookkeeping; shown in
# the article view so a judgement can be made on what the linker actually used.
EVIDENCE_COLUMNS = [
    "link_score", "toponym_score", "corroboration_score", "matched_names",
    "n_matches", "has_specific_match", "has_prominent_match", "best_match_weight",
    "corroboration_signals", "corroboration_agree", "sig_ef_match",
    "sig_fatalities_match", "sig_date_match", "sig_source_locality",
    "day_offset", "from_retrospective_pass", "from_year_only_pass",
    "link_rank", "hazard_score", "hazard_margin",
]


# ~20 m at mid-latitudes. Below the width of the damage paths being drawn, so the
# shape is unchanged at any zoom the basemap supports.
SIMPLIFY_DEGREES = 0.0002
COORDINATE_PRECISION = 5          # ~1 m; more digits is payload, not information


def _round_coords(node: Any) -> Any:
    if isinstance(node, (int, float)):
        return round(float(node), COORDINATE_PRECISION)
    if isinstance(node, (list, tuple)):
        return [_round_coords(child) for child in node]
    return node


def _round_geometry(geometry: dict) -> dict:
    """Trim coordinate precision — GeoJSON at 15 decimals is 90% noise."""
    if geometry.get("type") == "GeometryCollection":
        return {"type": "GeometryCollection",
                "geometries": [_round_geometry(g) for g in geometry.get("geometries", [])]}
    return {"type": geometry.get("type"),
            "coordinates": _round_coords(geometry.get("coordinates"))}


def _clean(value: Any) -> Any:
    """JSON-safe scalar: NaN/NaT become None, numpy types become Python ones."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if value is pd.NaT:
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, (dt.date, dt.datetime, pd.Timestamp)):
        return str(value)
    return value


class Store:
    def __init__(self, tag: str | None = None) -> None:
        self.tag = tag or f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
        self._load()

    # ── loading ──────────────────────────────────────────────────────────────
    def _load(self) -> None:
        processed = config.PROCESSED_DIR
        print("viewer: loading corpus …", flush=True)
        articles = pd.read_json(config.OUTPUT_DIR / "lexisnexis_articles.jsonl", lines=True)
        articles["textref_uid"] = [textref_uid(row) for row in articles.to_dict("records")]
        # Byte-identical rows are the same article exported twice; keep one.
        articles = articles.drop_duplicates(subset="textref_uid", keep="first")
        articles["published"] = pd.to_datetime(articles.pub_date, errors="coerce")
        articles["year"] = articles.published.dt.year
        self.articles = articles.set_index("textref_uid", drop=False)

        print("viewer: loading links and events …", flush=True)
        links = pd.read_csv(processed / f"article_links_{self.tag}.csv")
        self.links_by_article: dict[str, list[dict]] = defaultdict(list)
        for row in links[links.corpus == "lexisnexis"].to_dict("records"):
            self.links_by_article[row["textref_uid"]].append(row)
        for records in self.links_by_article.values():
            records.sort(key=lambda r: -(r.get("link_score") or 0))

        status = pd.read_csv(processed / f"article_status_{self.tag}.csv")
        self.status = status.drop_duplicates(subset="textref_uid").set_index("textref_uid")

        self.episodes = pd.read_csv(processed / f"episodes_{self.tag}.csv").set_index("episode_uid")
        hazards = episode_table.hazards_with_episodes(self.tag)
        self.hazards = hazards.set_index("hazard_uid")
        self.hazards_by_episode: dict[str, list[str]] = defaultdict(list)
        for row in hazards.itertuples():
            if isinstance(row.episode_uid, str):
                self.hazards_by_episode[row.episode_uid].append(row.hazard_uid)

        geography = pd.read_csv(processed / f"hazard_geography_{self.tag}.csv")
        self.geography = geography.set_index("hazard_uid")

        print("viewer: preparing geometry …", flush=True)
        # Kept in WGS84 and handed to Leaflet as GeoJSON: the browser needs real
        # coordinates to put a track on a basemap, and the map library does the
        # Web Mercator projection itself. Geometry is simplified to roughly 20 m
        # first — the difference is invisible against street-level tiles and it
        # keeps an 80-tornado outbreak's payload small.
        features = json.loads(
            (processed / f"hazards_{self.tag}.geojson").read_text())["features"]
        self.hazard_geometry: dict[str, dict] = {}
        self.hazard_bounds: dict[str, tuple[float, float, float, float]] = {}
        for feature in features:
            geom = to_shapely(feature.get("geometry"))
            if geom is None or geom.is_empty:
                continue
            hazard_uid = feature["properties"]["hazard_uid"]
            simplified = geom.simplify(SIMPLIFY_DEGREES, preserve_topology=False)
            if simplified.is_empty:
                simplified = geom
            self.hazard_geometry[hazard_uid] = _round_geometry(mapping(simplified))
            self.hazard_bounds[hazard_uid] = simplified.bounds

        # A compact index the list view can filter without touching bodies.
        self.index = self._build_index()
        print(f"viewer: ready — {len(self.articles):,} articles, "
              f"{sum(len(v) for v in self.links_by_article.values()):,} links", flush=True)

    def _build_index(self) -> pd.DataFrame:
        rows = []
        for row in self.articles.itertuples():
            links = self.links_by_article.get(row.textref_uid, [])
            best = links[0] if links else None
            status = (self.status.loc[row.textref_uid]
                      if row.textref_uid in self.status.index else None)
            rows.append({
                "textref_uid": row.textref_uid,
                "headline": row.headline,
                "source": row.source,
                "date": None if pd.isna(row.published) else row.published.date().isoformat(),
                "year": None if pd.isna(row.year) else int(row.year),
                "n_words": row.n_words,
                "is_duplicate": bool(row.is_duplicate),
                "n_links": len(links),
                "link_status": (status.link_status if status is not None else "unknown"),
                "scope": (status.scope if status is not None else "unknown"),
                "best_score": round(best["link_score"], 3) if best else None,
                "best_relation": best["link_relation"] if best else None,
                "best_event_day": best["event_day"] if best else None,
            })
        return pd.DataFrame(rows)

    # ── queries ──────────────────────────────────────────────────────────────
    def search(self, *, query: str = "", year: int | None = None, status: str = "",
               source: str = "", relation: str = "", min_score: float | None = None,
               has_links: str = "", offset: int = 0, limit: int = 50) -> dict[str, Any]:
        frame = self.index
        if query:
            needle = query.lower()
            frame = frame[frame.headline.str.lower().str.contains(needle, na=False, regex=False)
                          | frame.source.str.lower().str.contains(needle, na=False, regex=False)]
        if year:
            frame = frame[frame.year == year]
        if status:
            frame = frame[frame.link_status == status]
        if source:
            frame = frame[frame.source == source]
        if relation:
            frame = frame[frame.best_relation == relation]
        if min_score is not None:
            frame = frame[frame.best_score.fillna(-1) >= min_score]
        if has_links == "yes":
            frame = frame[frame.n_links > 0]
        elif has_links == "no":
            frame = frame[frame.n_links == 0]

        total = len(frame)
        page = frame.sort_values(["date", "headline"], ascending=[False, True]) \
                    .iloc[offset:offset + limit]
        return {"total": total, "offset": offset, "limit": limit,
                "rows": [{k: _clean(v) for k, v in row.items()}
                         for row in page.to_dict("records")]}

    def facets(self) -> dict[str, Any]:
        """Values the filter controls offer, from the data rather than hard-coded."""
        return {
            "years": sorted(int(y) for y in self.index.year.dropna().unique()),
            "statuses": sorted(self.index.link_status.dropna().unique().tolist()),
            "relations": sorted(self.index.best_relation.dropna().unique().tolist()),
            "sources": self.index.source.value_counts().head(60).index.tolist(),
            "total": len(self.index),
        }

    def article(self, uid: str) -> dict[str, Any] | None:
        if uid not in self.articles.index:
            return None
        row = self.articles.loc[uid]
        fields = {k: _clean(v) for k, v in row.items()
                  if k not in ("body", "published", "textref_uid")}
        status = self.status.loc[uid] if uid in self.status.index else None
        links = [self._link_payload(record) for record in self.links_by_article.get(uid, [])]
        # Every distinct name the linker matched, so the body can highlight what
        # the score was actually built from.
        highlights = sorted({part.split("(")[0]
                             for record in self.links_by_article.get(uid, [])
                             for part in str(record.get("matched_names") or "").split(";")
                             if part.strip()}, key=len, reverse=True)
        return {
            "textref_uid": uid,
            "headline": row.headline,
            "source": row.source,
            "date": None if pd.isna(row.published) else row.published.date().isoformat(),
            "body": row.body,
            "paragraphs": str(row.body or "").split("\n\n"),
            "fields": fields,
            "link_status": _clean(status.link_status) if status is not None else None,
            "scope": _clean(status.scope) if status is not None else None,
            "n_candidate_episodes": _clean(status.n_candidate_episodes) if status is not None else None,
            "links": links,
            "highlights": highlights,
        }

    def _link_payload(self, record: dict) -> dict[str, Any]:
        episode_uid = record.get("episode_uid")
        payload = {
            "episode_uid": episode_uid,
            "hazard_uid": _clean(record.get("hazard_uid")),
            "link_relation": record.get("link_relation"),
            "link_level": record.get("link_level"),
            "evidence": {k: _clean(record.get(k)) for k in EVIDENCE_COLUMNS if k in record},
            "event": self.episode_summary(episode_uid) if episode_uid else None,
        }
        return payload

    def episode_summary(self, episode_uid: str) -> dict[str, Any] | None:
        if episode_uid not in self.episodes.index:
            return None
        row = self.episodes.loc[episode_uid]
        hazard_uids = self.hazards_by_episode.get(episode_uid, [])
        places, counties, states = [], [], set()
        for hazard_uid in hazard_uids:
            if hazard_uid not in self.geography.index:
                continue
            info = self.geography.loc[hazard_uid]
            places += [p for p in str(info.places or "").split(";") if p][:4]
            counties += [c for c in str(info.counties or "").split(";") if c]
            states |= {s for s in str(info.states or "").split(";") if s}
        return {
            "episode_uid": episode_uid,
            "convective_day": _clean(row.convective_day),
            "time_begin_utc": _clean(row.time_begin_utc),
            "n_hazards": _clean(row.n_hazards),
            "max_efscale": _clean(row.max_efscale),
            "fatalities": _clean(row.fatalities),
            "injuries": _clean(row.injuries),
            "wfos": _clean(row.wfos),
            "states": sorted(states),
            "counties": sorted(set(counties))[:12],
            "places": sorted(set(places))[:16],
        }

    def episode_detail(self, episode_uid: str) -> dict[str, Any] | None:
        """Episode summary plus its tornado tracks as GeoJSON for the map.

        One feature per hazard, carrying the attributes a popup needs, so the
        browser can render and label them without a second request.
        """
        summary = self.episode_summary(episode_uid)
        if summary is None:
            return None

        features: list[dict[str, Any]] = []
        bounds: list[tuple[float, float, float, float]] = []
        for hazard_uid in self.hazards_by_episode.get(episode_uid, []):
            geometry = self.hazard_geometry.get(hazard_uid)
            if geometry is None:
                continue
            hazard = self.hazards.loc[hazard_uid] if hazard_uid in self.hazards.index else None
            info = (self.geography.loc[hazard_uid]
                    if hazard_uid in self.geography.index else None)
            ef = viz.ef_class(hazard.efscale) if hazard is not None else viz.UNRATED
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "hazard_uid": hazard_uid,
                    "ef": ef,
                    "colour": viz.ef_colour(ef),
                    "efscale": _clean(hazard.efscale) if hazard is not None else None,
                    "path_length_mi": _clean(hazard.path_length_mi) if hazard is not None else None,
                    "path_width_yd": _clean(hazard.path_width_yd) if hazard is not None else None,
                    "fatalities": _clean(hazard.fatalities) if hazard is not None else None,
                    "injuries": _clean(hazard.injuries) if hazard is not None else None,
                    "time_begin_utc": _clean(hazard.time_begin_utc) if hazard is not None else None,
                    "wfo": _clean(hazard.wfo) if hazard is not None else None,
                    "has_polygon": bool(hazard.has_polygon) if hazard is not None else False,
                    "nearest_place": _clean(info.nearest_place) if info is not None else None,
                    "counties": _clean(info.counties) if info is not None else None,
                },
            })
            if hazard_uid in self.hazard_bounds:
                bounds.append(self.hazard_bounds[hazard_uid])

        bbox = None
        if bounds:
            bbox = [min(b[0] for b in bounds), min(b[1] for b in bounds),
                    max(b[2] for b in bounds), max(b[3] for b in bounds)]
        return {**summary,
                "geojson": {"type": "FeatureCollection", "features": features},
                "bbox": bbox, "n_features": len(features)}
