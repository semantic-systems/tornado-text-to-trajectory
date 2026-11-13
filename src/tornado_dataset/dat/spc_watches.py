"""SPC tornado and severe thunderstorm watches, from the IEM archives.

Plan and rationale: ``docs/plan_watch_linking.md``. Three sources, all at the
Iowa Environmental Mesonet (IEM):

* **County records** — the official watch area. SPC lists the counties of a
  watch (WOU product); each forecast office then clears or extends its own
  (WCN product). IEM's VTEC archive holds one row per county per watch with
  that county's own start and end: ``watchwarn.py`` with phenomena ``TO``/``SV``
  and significance ``A``. Columns used: ``phenomena``, ``eventid`` (the watch
  number), ``ugc`` (``ALC089`` = Alabama county 089), ``gtype`` (``C`` county),
  ``utc_issue``, ``utc_expire``, ``status``, ``wfo``, ``vtec_year``.
* **Watch polygons** — the aviation parallelogram (SAW product), with the
  watch attributes: ``ISSUE``, ``EXPIRE``, ``NUM``, ``TYPE``, ``IS_PDS``,
  ``MV_DRCT``/``MV_SKNT`` (storm motion), probabilities. IEM: "not the official
  spatial bounds anymore". Used for attributes, and as a fallback.
* **Watch texts** — the public watch (SEL product). States other watches in
  effect ("OTHER WATCH INFORMATION...CONTINUE...WW 225...") and, sometimes,
  explicit succession ("replaces watch 123"). Cancellations are SEL products too.

A tornado's county comes from SPC's own record: state ``st`` and first-county
FIPS ``f1`` give the UGC code directly (``st`` + ``"C"`` + ``f1`` as three
digits), so no county shapes are needed.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd

IEM = "https://mesonet.agron.iastate.edu"
WATCHWARN = IEM + "/cgi-bin/request/gis/watchwarn.py"
SPC_WATCH = IEM + "/cgi-bin/request/gis/spc_watch.py"
AFOS = IEM + "/cgi-bin/afos/retrieve.py"
MIN_INTERVAL_S = 2.0           # between IEM requests; the archive is a shared service
AFOS_LIMIT = 9999              # IEM's maximum products per text request
COUNTY_TIMEOUT_S = 600         # a year of county records is ~60k rows, built on request

_TYPE = {"TO": "TOR", "SV": "SVR"}
_WATCH_TYPE = r"(TORNADO|SEVERE\s+THUNDERSTORM)"


def _iso(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%dT%H:%MZ")


def _type_code(text: str) -> str:
    return "TOR" if text.upper().startswith("TORNADO") else "SVR"


# ── fetching ────────────────────────────────────────────────────────────────
def fetch_county_records(sts, ets, cache_dir: Path, *, refresh: bool = False) -> str:
    from ..http import get_text
    params = {"sts": _iso(sts), "ets": _iso(ets), "phenomena": "TO,SV",
              "significance": "A,A", "limitps": "yes", "accept": "csv"}
    name = f"counties_{_iso(sts)[:10]}_{_iso(ets)[:10]}.csv"
    return get_text(WATCHWARN, params, cache_path=cache_dir / name, refresh=refresh,
                    min_interval=MIN_INTERVAL_S, timeout=COUNTY_TIMEOUT_S)


def fetch_polygons(sts, ets, cache_dir: Path, *, refresh: bool = False) -> dict:
    from ..http import get_json
    params = {"sts": _iso(sts), "ets": _iso(ets), "format": "geojson"}
    name = f"polygons_{_iso(sts)[:10]}_{_iso(ets)[:10]}.geojson"
    return get_json(SPC_WATCH, params, cache_path=cache_dir / name, refresh=refresh,
                    min_interval=MIN_INTERVAL_S)


def fetch_texts(pil: str, sts, ets, cache_dir: Path, *, refresh: bool = False) -> str:
    """All products whose ID starts with ``pil`` (``SEL`` = SEL0–SEL9), from SPC."""
    from ..http import get_text
    params = {"pil": pil, "sdate": _iso(sts), "edate": _iso(ets), "fmt": "text",
              "limit": AFOS_LIMIT, "order": "asc", "center": "KWNS"}
    name = f"{pil.lower()}_{_iso(sts)[:10]}_{_iso(ets)[:10]}.txt"
    return get_text(AFOS, params, cache_path=cache_dir / name, refresh=refresh,
                    min_interval=MIN_INTERVAL_S)


# ── parsing ─────────────────────────────────────────────────────────────────
def parse_county_records(csv_text: str) -> pd.DataFrame:
    """One row per county per watch: ``year``, ``num``, ``type``, ``ugc``, ``start``, ``end``."""
    cols = ["year", "num", "type", "ugc", "wfo", "status", "start", "end"]
    if not csv_text.strip():
        return pd.DataFrame(columns=cols)
    raw = pd.read_csv(io.StringIO(csv_text), dtype=str)
    raw.columns = [c.strip().lower() for c in raw.columns]
    need = {"phenomena", "significance", "eventid", "ugc", "utc_issue", "utc_expire"}
    missing = need - set(raw.columns)
    if missing:
        raise ValueError(f"county records lack {sorted(missing)}; columns are "
                         f"{list(raw.columns)} — IEM may have changed the format")
    raw = raw[raw.significance.str.strip() == "A"]
    raw = raw[raw.phenomena.str.strip().isin(_TYPE)]
    if "gtype" in raw.columns:
        raw = raw[raw.gtype.str.strip() == "C"]
    start = pd.to_datetime(raw.utc_issue, utc=True, errors="coerce")
    year = (pd.to_numeric(raw.vtec_year, errors="coerce") if "vtec_year" in raw.columns
            else start.dt.year)
    out = pd.DataFrame({
        "year": year.fillna(start.dt.year),
        "num": pd.to_numeric(raw.eventid, errors="coerce"),
        "type": raw.phenomena.str.strip().map(_TYPE),
        "ugc": raw.ugc.str.strip(),
        "wfo": raw.get("wfo", pd.Series(index=raw.index, dtype=str)),
        "status": raw.get("status", pd.Series(index=raw.index, dtype=str)),
        "start": start,
        "end": pd.to_datetime(raw.utc_expire, utc=True, errors="coerce"),
    })
    out = out.dropna(subset=["year", "num", "start", "end"])
    out[["year", "num"]] = out[["year", "num"]].astype(int)
    return out[cols].reset_index(drop=True)


def parse_polygons(geojson: dict) -> pd.DataFrame:
    """One row per watch: ``year``, ``num``, ``type``, ``issue``, ``expire``, motion, geometry (WGS84)."""
    from shapely.geometry import shape

    rows = []
    for f in geojson.get("features", []):
        p = {k.upper(): v for k, v in (f.get("properties") or {}).items()}
        rows.append({"num": p.get("NUM"), "type": str(p.get("TYPE") or "").strip().upper(),
                     "issue": p.get("ISSUE"), "expire": p.get("EXPIRE"),
                     "is_pds": p.get("IS_PDS"), "mv_drct": p.get("MV_DRCT"),
                     "mv_sknt": p.get("MV_SKNT"),
                     "geometry": shape(f["geometry"]) if f.get("geometry") else None})
    df = pd.DataFrame(rows, columns=["num", "type", "issue", "expire", "is_pds", "mv_drct",
                                     "mv_sknt", "geometry"])
    for c in ("issue", "expire"):
        df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    df["num"] = pd.to_numeric(df.num, errors="coerce")
    df = df.dropna(subset=["num", "issue"])
    df["num"] = df.num.astype(int)
    df["year"] = df.issue.dt.year
    return df.reset_index(drop=True)


_HEADER = re.compile(r"\n(?=\d{3}\s*\n[A-Z]{4}\d{2} [A-Z]{4} \d{6})")


def split_products(text: str) -> list[str]:
    """Separate a multi-product text response.

    NOAAPort frames products with SOH/ETX control characters; where those are
    absent, a product starts at a three-digit sequence line followed by a WMO
    header (``WWUS20 KWNS 271310``).
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x03", "")
    parts = text.split("\x01") if "\x01" in text else _HEADER.split(text)
    return [p.strip() for p in parts if p.strip()]


_NUMBER = re.compile(_WATCH_TYPE + r"\s+WATCH\s*-?\s*NUMBER\s+(\d+)", re.I)
_CANCEL = re.compile(r"CANCEL+ED\s+" + _WATCH_TYPE + r"\s+WATCH\s+(?:NUMBER\s+)?(\d+)", re.I)
# "REPLACES SEVERE THUNDERSTORM WATCH NUMBER 36...TORNADO WATCH NUMBER 37." — a
# watch can replace several, listed with "..." up to the first single full stop.
_REPLACES = re.compile(r"REPLACES?\s+(.*?)(?<!\.)\.(?!\.)", re.I)
_REPLACED_NUM = re.compile(r"(?:NUMBERS?|WW)\s*(\d+)", re.I)
# "WATCH NUMBER 36 37 WILL NOT BE IN EFFECT" — numbers separated by spaces, commas or "and".
_NOT_IN_EFFECT = re.compile(r"WATCH(?:ES)?\s+(?:NUMBERS?\s+)?((?:\d+(?:\s*,\s*|\s+AND\s+|\s+))+)"
                            r"WILL\s+NOT\s+BE\s+IN\s+EFFECT", re.I)
_CONTINUE = re.compile(r"CONTINUE\.\.\.((?:\s*WW\s*\d+\.*)+)", re.I)


def _numbers(s: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", s)]


def parse_watch_text(product: str) -> dict:
    """Watch number, type and the stated relations to other watches, from one SEL product."""
    flat = re.sub(r"\s+", " ", product)
    out = {"num": None, "type": None, "cancellation": False, "replaces": [],
           "not_in_effect": [], "continues": [], "replace_snippet": None}
    cancel = _CANCEL.search(flat)
    number = _NUMBER.search(flat)
    if cancel:
        out.update(cancellation=True, type=_type_code(cancel.group(1)),
                   num=int(cancel.group(2)))
    elif number:
        out.update(type=_type_code(number.group(1)), num=int(number.group(2)))
    for m in _REPLACES.finditer(flat):
        out["replaces"] += [int(n) for n in _REPLACED_NUM.findall(m.group(1))]
        if out["replace_snippet"] is None:
            out["replace_snippet"] = flat[max(m.start() - 80, 0):m.end() + 80]
    for m in _NOT_IN_EFFECT.finditer(flat):
        out["not_in_effect"] += _numbers(m.group(1))
    for m in _CONTINUE.finditer(flat):
        out["continues"] += _numbers(m.group(1))
    return out


def parse_watch_texts(text: str) -> pd.DataFrame:
    rows = [parse_watch_text(p) for p in split_products(text)]
    return pd.DataFrame(rows, columns=["num", "type", "cancellation", "replaces",
                                       "not_in_effect", "continues", "replace_snippet"])


# ── tornado → watch ─────────────────────────────────────────────────────────
def tornado_ugc(tracks: pd.DataFrame) -> pd.Series:
    """UGC county code of each SPC track's first county; missing when SPC has none (``f1`` 0)."""
    f1 = pd.to_numeric(tracks.f1, errors="coerce")
    ok = f1.notna() & (f1 > 0) & tracks.st.notna()
    code = tracks.st.astype(str).str.strip() + "C" + f1.fillna(0).astype(int).astype(str).str.zfill(3)
    return code.where(ok, None)


def county_hits(tracks: pd.DataFrame, records: pd.DataFrame) -> pd.DataFrame:
    """(spc_id, watch) pairs where the tornado's county was under the watch at its start."""
    t = pd.DataFrame({"spc_id": tracks.spc_id, "ugc": tornado_ugc(tracks),
                      "t0": pd.to_datetime(tracks.begin_utc, utc=True)}).dropna(subset=["ugc"])
    m = t.merge(records[["ugc", "year", "num", "type", "start", "end"]], on="ugc")
    m = m[(m.start <= m.t0) & (m.t0 < m.end)]
    return m[["spc_id", "year", "num", "type"]].drop_duplicates().reset_index(drop=True)


def polygon_hits(tracks: pd.DataFrame, polygons: pd.DataFrame) -> pd.DataFrame:
    """(spc_id, watch) pairs where the tornado started inside the polygon while it was valid."""
    from shapely import STRtree
    from shapely.geometry import Point

    poly = polygons[polygons.geometry.notna()].reset_index(drop=True)
    if poly.empty:
        return pd.DataFrame(columns=["spc_id", "year", "num", "type"])
    tree = STRtree(poly.geometry.to_list())
    t0 = pd.to_datetime(tracks.begin_utc, utc=True)
    rows = []
    for sid, lon, lat, t in zip(tracks.spc_id, tracks.slon, tracks.slat, t0):
        if pd.isna(lon) or pd.isna(lat) or pd.isna(t):
            continue
        pt = Point(lon, lat)
        for j in tree.query(pt, predicate="intersects"):
            w = poly.iloc[int(j)]
            if w.issue <= t and (pd.isna(w.expire) or t < w.expire):
                rows.append((sid, int(w.year), int(w.num), w.type))
    return pd.DataFrame(rows, columns=["spc_id", "year", "num", "type"]).drop_duplicates()


def county_timing(records: pd.DataFrame, polygons: pd.DataFrame,
                  tolerance_min: float = 30.0) -> dict[str, float]:
    """How a county's own end compares with its watch's nominal expiry."""
    m = records.merge(polygons[["year", "num", "expire"]], on=["year", "num"])
    if m.empty:
        return {"county_records_joined": 0}
    delta = (m.end - m.expire).dt.total_seconds() / 60
    return {
        "county_records_joined": len(m),
        "cleared_early_share": float((delta < -tolerance_min).mean()),
        "extended_share": float((delta > tolerance_min).mean()),
        "median_minutes_early": float(-delta[delta < -tolerance_min].median())
        if (delta < -tolerance_min).any() else 0.0,
    }


def summarise_hits(tracks: pd.DataFrame, by_county: pd.DataFrame,
                   by_polygon: pd.DataFrame) -> dict[str, float]:
    """Do the official counties and the polygons put the same tornadoes in the same watches?"""
    ids = set(tracks.spc_id)
    c, p = set(by_county.spc_id), set(by_polygon.spc_id)
    both = c & p
    def key(df):
        return {s: frozenset(zip(g.year, g.num)) for s, g in df.groupby("spc_id")}
    kc, kp = key(by_county), key(by_polygon)
    same = sum(1 for s in both if kc[s] == kp[s])
    per_tornado = by_county.groupby("spc_id").size()
    return {
        "tornadoes": len(ids),
        "unknown_county": int(tornado_ugc(tracks).isna().sum()),
        "in_watch_county": len(c), "in_watch_polygon": len(p),
        "both": len(both), "county_only": len(c - p), "polygon_only": len(p - c),
        "neither": len(ids - c - p),
        "same_watch_share": same / len(both) if both else float("nan"),
        "county_under_two_watches": int((per_tornado > 1).sum()),
    }


def coverage(records: pd.DataFrame, polygons: pd.DataFrame) -> dict[str, float]:
    """Share of polygon watches that have county records, and type agreement."""
    pw = polygons[["year", "num", "type"]].drop_duplicates(["year", "num"])
    cw = records[["year", "num", "type"]].drop_duplicates(["year", "num"])
    j = pw.merge(cw, on=["year", "num"], how="left", suffixes=("", "_county"))
    found = j.type_county.notna()
    return {
        "polygon_watches": len(pw), "county_watches": len(cw),
        "with_county_records": int(found.sum()),
        "share": float(found.mean()) if len(j) else float("nan"),
        "type_agrees": float((j.type[found] == j.type_county[found]).mean())
        if found.any() else float("nan"),
    }


# ── a year of watches ───────────────────────────────────────────────────────
def year_window(year: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    return pd.Timestamp(f"{year}-01-01", tz="UTC"), pd.Timestamp(f"{year + 1}-01-01", tz="UTC")


def fetch_year(year: int, raw_dir: Path, *, refresh: bool = False) -> dict:
    """County records, polygons and SEL texts for one year, cached under ``raw_dir/<year>/``.

    Texts are requested month by month to stay below IEM's per-request cap.
    """
    d = raw_dir / str(year)
    sts, ets = year_window(year)
    records = parse_county_records(fetch_county_records(sts, ets, d, refresh=refresh))
    polygons = parse_polygons(fetch_polygons(sts, ets, d, refresh=refresh))
    products = 0
    for start in pd.date_range(sts, ets, freq="MS", inclusive="left"):
        products += len(split_products(fetch_texts("SEL", start, start + pd.offsets.MonthBegin(1),
                                                   d, refresh=refresh)))
    return {"year": year, "county_records": len(records), "watches": len(polygons),
            "sel_products": products}


def load_year(year: int, raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """The cached year, parsed: county records, polygons, and texts (with ``year``)."""
    d = raw_dir / str(year)
    sts, ets = year_window(year)
    name = f"{_iso(sts)[:10]}_{_iso(ets)[:10]}"
    county_csv, poly_json = d / f"counties_{name}.csv", d / f"polygons_{name}.geojson"
    if not county_csv.exists() or not poly_json.exists():
        raise FileNotFoundError(f"{year}: no cached watches in {d} — run `fetch`")
    import json
    records = parse_county_records(county_csv.read_text(encoding="utf-8"))
    polygons = parse_polygons(json.loads(poly_json.read_text(encoding="utf-8")))
    texts = [parse_watch_texts(f.read_text(encoding="utf-8")) for f in sorted(d.glob("sel_*.txt"))]
    texts = pd.concat(texts, ignore_index=True) if texts else parse_watch_texts("")
    texts["year"] = year
    return records, polygons, texts


# ── county boundaries (Census cartographic boundary file) ──────────────────
COUNTY_BOUNDARIES = "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_county_500k.zip"
SIMPLIFY_M = 500.0             # far below any distance threshold; keeps distances fast
_FIPS_USPS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
    "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
    "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
    "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
    "55": "WI", "56": "WY", "60": "AS", "66": "GU", "69": "MP", "72": "PR", "78": "VI"}


def fetch_county_boundaries(dest: Path) -> dict:
    """The 2020 county boundary file (1:500,000); skipped if present.

    2020 rather than later: from 2022 the Census replaced Connecticut's counties
    with planning regions, while NWS county codes kept the old counties.
    """
    import json
    from ..http import _SESSION, utcnow_iso

    target = dest / COUNTY_BOUNDARIES.rsplit("/", 1)[1]
    if target.exists():
        return {"file": target.name, "status": "present"}
    dest.mkdir(parents=True, exist_ok=True)
    response = _SESSION.get(COUNTY_BOUNDARIES, timeout=300)
    response.raise_for_status()
    tmp = target.with_suffix(".part")
    tmp.write_bytes(response.content)
    tmp.rename(target)
    record = {"file": target.name, "status": "downloaded", "url": COUNTY_BOUNDARIES,
              "retrieved_at": utcnow_iso(), "bytes": len(response.content)}
    target.with_name(target.name + ".meta.json").write_text(json.dumps(record, indent=2))
    return record


def load_counties(zip_path: Path) -> pd.DataFrame:
    """``ugc`` → projected county polygon, its centroid (``x``, ``y``) and ``reach``.

    UGC county codes are the state's postal code, ``C`` and the three-digit
    county FIPS. Polygons are projected to EPSG:5070 and simplified to
    :data:`SIMPLIFY_M`. ``reach`` is the farthest boundary point from the
    centroid: centroid distance minus both reaches is a lower bound on the
    distance between two counties, used to skip pairs cheaply.
    """
    import shapely
    from pyogrio import raw
    from pyproj import Transformer

    from .. import config

    member = COUNTY_BOUNDARIES.rsplit("/", 1)[1].replace(".zip", ".shp")
    meta, _, wkb, fields = raw.read(f"/vsizip/{zip_path}/{member}")
    cols = {name.upper(): values for name, values in zip(meta["fields"], fields)}
    statefp = pd.Series(cols["STATEFP"]).astype(str).str.zfill(2)
    usps = (pd.Series(cols["STUSPS"]).astype(str) if "STUSPS" in cols
            else statefp.map(_FIPS_USPS))
    countyfp = pd.Series(cols["COUNTYFP"]).astype(str).str.zfill(3)
    to_m = Transformer.from_crs(config.CRS_WGS84, config.CRS_EQUAL_AREA, always_xy=True)
    geoms = shapely.transform(shapely.from_wkb(wkb),
                              lambda xy: np.column_stack(to_m.transform(xy[:, 0], xy[:, 1])))
    geoms = shapely.simplify(geoms, SIMPLIFY_M, preserve_topology=True)
    cent = shapely.centroid(geoms)
    x, y = shapely.get_x(cent), shapely.get_y(cent)
    reach = np.array([np.hypot(*(shapely.get_coordinates(g) - (cx, cy)).T).max()
                      for g, cx, cy in zip(geoms, x, y)])
    return pd.DataFrame({"ugc": usps + "C" + countyfp, "geometry": geoms,
                         "x": x, "y": y, "reach": reach})


# ── watches and their links ─────────────────────────────────────────────────
HANDOVER_S = 3600.0            # counties within an hour of a hand-over form its footprint
MOTION_SLACK_M = 50_000.0      # fallback upstream tolerance when too few "replaces" links calibrate it
DEFAULT_GAP_S = 3 * 3600.0     # plan default Δt
DEFAULT_EDGE_M = 50_000.0      # plan default d


def watch_id(year, num) -> str:
    return f"{int(year)}_{int(num):04d}"


# SPC watches cover the contiguous US. Honolulu (HFO) issues its own watches,
# numbered from 1 each year like SPC's, so its county records collide with
# SPC watch numbers; other offices occasionally mistype a watch number.
NON_SPC_STATES = {"HI", "AK", "PR", "VI", "GU", "AS", "MP"}
EARLY_TOLERANCE = pd.Timedelta(hours=2)
# Counties renamed since: NWS records keep the old code until the change.
UGC_RENAMED = {"SDC113": "SDC102"}     # Shannon → Oglala Lakota County, SD (2015)
LATE_TOLERANCE = pd.Timedelta(hours=1)


def clean_county_records(records: pd.DataFrame, polygons: pd.DataFrame
                         ) -> tuple[pd.DataFrame, dict]:
    """County records that belong to the SPC watch their number names.

    Dropped, and counted: marine zones (watches list coastal and lake waters
    alongside counties; ``ugc`` ``ANZ536`` rather than ``VAC001``); counties
    outside SPC's area; and records whose start
    lies more than :data:`EARLY_TOLERANCE` before SPC issued the watch of that
    number, or more than :data:`LATE_TOLERANCE` after it expired — a county
    cannot join a watch that has ended. Records whose number has no SPC polygon
    are kept (the polygon archive has a few gaps) and counted.
    """
    records = records.assign(ugc=records.ugc.replace(UGC_RENAMED))
    marine = records.ugc.str[2] != "C"
    records = records[~marine].reset_index(drop=True)
    outside = records.ugc.str[:2].isin(NON_SPC_STATES)
    m = records.merge(polygons.drop_duplicates(["year", "num"])[["year", "num", "issue", "expire"]],
                      on=["year", "num"], how="left")
    known = m.issue.notna().to_numpy()
    early = known & (m.start < m.issue - EARLY_TOLERANCE).to_numpy()
    late = known & (m.start > m.expire + LATE_TOLERANCE).to_numpy()
    keep = ~outside.to_numpy() & ~early & ~late
    notes = {"county_records": len(records) + int(marine.sum()),
             "dropped_marine_zones": int(marine.sum()),
             "dropped_outside_spc_area": int(outside.sum()),
             "dropped_before_issue": int((early & ~outside.to_numpy()).sum()),
             "dropped_after_expiry": int((late & ~outside.to_numpy()).sum()),
             "kept_without_polygon": int((keep & ~known).sum())}
    return records[keep].reset_index(drop=True), notes


def build_watches(records: pd.DataFrame, polygons: pd.DataFrame,
                  texts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per watch, and one row per (watch, county) with that county's span.

    Watch numbers run through tornado and severe thunderstorm watches together
    within a year, so ``year`` + ``num`` identify a watch and ``type`` is an
    attribute. Times come from the county records — the official ones — and
    storm motion, PDS and nominal issue/expiry from the polygon archive.
    """
    rec = records.assign(wid=[watch_id(y, n) for y, n in zip(records.year, records.num)])
    counties = (rec.groupby(["wid", "ugc"], as_index=False)
                .agg(start=("start", "min"), end=("end", "max"), wfo=("wfo", "first")))
    w = (rec.groupby("wid", as_index=False)
         .agg(year=("year", "first"), num=("num", "first"), type=("type", "first"),
              first_start=("start", "min"), last_end=("end", "max"),
              n_counties=("ugc", "nunique"),
              wfos=("wfo", lambda s: ";".join(sorted(set(s.dropna()))))))
    poly = polygons.assign(wid=[watch_id(y, n) for y, n in zip(polygons.year, polygons.num)])
    poly = poly.drop_duplicates("wid")[["wid", "issue", "expire", "is_pds", "mv_drct", "mv_sknt"]]
    w = w.merge(poly, on="wid", how="left")
    t = texts[~texts.cancellation.astype(bool) & texts.num.notna()]
    rep = {}
    for y, n, r in zip(t.year, t.num, t.replaces):
        rep.setdefault(watch_id(y, n), set()).update(r or [])
    w["replaces"] = [";".join(watch_id(y, n) for n in sorted(rep.get(wid, ())))
                     for wid, y in zip(w.wid, w.year)]
    return w.sort_values("first_start").reset_index(drop=True), counties


def concurrent_links(counties: pd.DataFrame) -> pd.DataFrame:
    """Rule 1: two watches in force in the same county at the same time."""
    rows = []
    for ugc, g in counties.sort_values("start").groupby("ugc", sort=False):
        if len(g) < 2:
            continue
        wid, st, en = g.wid.to_numpy(), g.start.to_numpy(), g.end.to_numpy()
        for i in range(len(g) - 1):
            j = i + 1 + np.nonzero(st[i + 1:] < en[i])[0]
            rows += [(wid[i], wid[k], ugc) for k in j if wid[k] != wid[i]]
    links = pd.DataFrame(rows, columns=["a", "b", "ugc"])
    return (links.groupby(["a", "b"], as_index=False).ugc.agg(lambda s: ";".join(sorted(set(s))))
            .assign(rule="concurrent"))


REPLACED_WITHIN = pd.Timedelta(hours=24)


def explicit_links(watches: pd.DataFrame) -> pd.DataFrame:
    """Rule 2: "this watch replaces watch N", where watch N fits in time.

    The text gives only the number, and numbers restart each January: a watch
    on 1 January replacing "watch 765" means last year's. So the replaced
    watch is looked up in the successor's year and the year before, and taken
    only if it ended no more than :data:`REPLACED_WITHIN` before the
    successor began and began before it. Statements that fit neither are
    dropped (``attrs["unmatched"]`` counts them).
    """
    w = watches.set_index("wid")
    rows, unmatched = [], 0
    for b, rep in zip(watches.wid, watches.replaces):
        if not rep:
            continue
        b0 = w.at[b, "first_start"]
        for stated in rep.split(";"):
            year, num = (int(x) for x in stated.split("_"))
            found = None
            for a in (watch_id(year, num), watch_id(year - 1, num)):
                if a in w.index and a != b:
                    a0, a1 = w.at[a, "first_start"], w.at[a, "last_end"]
                    if a0 < b0 and a1 >= b0 - REPLACED_WITHIN:
                        found = a
                        break
            if found:
                rows.append((found, b))
            else:
                unmatched += 1
    out = pd.DataFrame(rows, columns=["a", "b"]).assign(rule="replaces")
    out.attrs["unmatched"] = unmatched
    return out


_EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
KNOT_MS = 1852.0 / 3600.0


def _secs(ts: pd.Series) -> np.ndarray:
    return (ts - _EPOCH).dt.total_seconds().to_numpy()


class Footprints:
    """Watches' county footprints at a hand-over, and the geometry between two of them.

    Built once; :meth:`pair` measures one (A, B) pair:

    * ``gap_s`` — B's first county start minus A's last county end (negative
      when they overlap);
    * ``edge_m`` — distance between A's counties still active within
      :data:`HANDOVER_S` of the hand-over and B's counties active within
      :data:`HANDOVER_S` of its start, county edge to county edge (0 when
      they touch or share a county);
    * ``centre_m``, ``along_m`` — displacement between the two footprints'
      centres, and its component along A's storm motion (``MV_DRCT`` is the
      direction storms come *from*; negative = B lies upstream);
    * ``speed_reach_m`` — how far storms at A's speed (``MV_SKNT``) travel in
      the gap plus the hand-over hour: a diagnostic, not a rule.
    """

    def __init__(self, watches: pd.DataFrame, counties: pd.DataFrame, geo: pd.DataFrame):
        c = counties.merge(geo, on="ugc")
        c = c.assign(s0=_secs(c.start), s1=_secs(c.end))
        self.num = {k: g[["x", "y", "reach", "s0", "s1"]].to_numpy() for k, g in c.groupby("wid")}
        self.geom = {k: g.geometry.to_numpy() for k, g in c.groupby("wid")}
        w = watches.set_index("wid")
        self.t0 = dict(zip(w.index, _secs(w.first_start)))
        self.t1 = dict(zip(w.index, _secs(w.last_end)))
        self.drct = w.mv_drct.astype(float).to_dict()
        self.sknt = w.mv_sknt.astype(float).to_dict()

    def pair(self, a: str, b: str, max_edge_m: float = np.inf) -> tuple | None:
        import shapely

        if a not in self.num or b not in self.num:
            return None
        t0b, t1a = self.t0[b], self.t1[a]
        hand = min(t0b, t1a)
        na, nb = self.num[a], self.num[b]
        ma, mb = na[:, 4] >= hand - HANDOVER_S, nb[:, 3] <= t0b + HANDOVER_S
        fa, fb = na[ma], nb[mb]
        if not len(fa) or not len(fb):
            return None
        dist = np.hypot(fa[:, None, 0] - fb[None, :, 0], fa[:, None, 1] - fb[None, :, 1])
        lower = dist - fa[:, None, 2] - fb[None, :, 2]
        if lower.min() > max_edge_m:
            return None
        edge = _min_distance(self.geom[a][ma], self.geom[b][mb], lower)
        if edge > max_edge_m:
            return None
        d = self.drct.get(a)
        if d is None or np.isnan(d):
            d = self.drct.get(b, np.nan)
        dx, dy = fb[:, :2].mean(axis=0) - fa[:, :2].mean(axis=0)
        along = np.nan
        if not np.isnan(d):
            toward = np.deg2rad((d + 180.0) % 360.0)
            along = float(dx * np.sin(toward) + dy * np.cos(toward))
        speed = self.sknt.get(a, np.nan)
        reach = (speed * KNOT_MS * (max(t0b - t1a, 0.0) + HANDOVER_S)
                 if speed is not None and not np.isnan(speed) else np.nan)
        return (t0b - t1a, edge, float(np.hypot(dx, dy)), along, reach)


def _min_distance(ga: np.ndarray, gb: np.ndarray, lower: np.ndarray, chunk: int = 64) -> float:
    """Exact minimum distance between two sets of polygons.

    County pairs are measured in order of their lower bound, and the search
    stops once the next bound exceeds the best distance found — usually after
    the first chunk, since neighbouring counties have bounds near zero.
    """
    import shapely

    order = np.argsort(lower, axis=None)
    flat = lower.ravel()
    best = np.inf
    for k in range(0, len(order), chunk):
        idx = order[k:k + chunk]
        if flat[idx[0]] > best:
            break
        ia, ib = np.unravel_index(idx, lower.shape)
        best = min(best, float(shapely.distance(ga[ia], gb[ib]).min()))
        if best == 0.0:
            break
    return best


PAIR_COLUMNS = ["gap_s", "edge_m", "centre_m", "along_m", "speed_reach_m"]


def succession_candidates(watches: pd.DataFrame, fp: Footprints, *,
                          max_gap_s: float = 6 * 3600.0,
                          max_edge_m: float = 150_000.0) -> pd.DataFrame:
    """Rule 3 candidates: B begins after A and within ``max_gap_s`` of A's end.

    Computed once at the widest thresholds (see :class:`Footprints` for the
    columns), so the sensitivity grid only filters.
    """
    w = watches.dropna(subset=["first_start", "last_end"]).sort_values("first_start")
    wid = w.wid.to_numpy()
    t0, t1 = _secs(w.first_start), _secs(w.last_end)
    rows = []
    for ia in range(len(w)):
        stop = np.searchsorted(t0, t1[ia] + max_gap_s, side="right")
        for ib in range(ia + 1, stop):
            m = fp.pair(wid[ia], wid[ib], max_edge_m)
            if m is not None:
                rows.append((wid[ia], wid[ib], *m))
    return pd.DataFrame(rows, columns=["a", "b", *PAIR_COLUMNS])


def measure_links(links: pd.DataFrame, fp: Footprints) -> pd.DataFrame:
    """The same measures for given pairs — SPC's "replaces" links, for calibration."""
    rows = [(a, b, *(fp.pair(a, b) or (np.nan,) * len(PAIR_COLUMNS)))
            for a, b in zip(links.a, links.b)]
    return pd.DataFrame(rows, columns=["a", "b", *PAIR_COLUMNS])


CALIBRATION_PASS = 0.95        # share of SPC-stated successions the motion check must pass


def calibrate_motion_slack(explicit: pd.DataFrame) -> dict:
    """Upstream tolerance from SPC's own successions.

    "Replaces" links are successions forecasters stated themselves, so their
    displacement along the storm motion shows how far upstream a genuine
    successor's footprint centre can lie — mostly noise from footprint shape
    and sideways extension. The tolerance is the distance that lets
    :data:`CALIBRATION_PASS` of them through.
    """
    along = explicit.along_m.dropna()
    if len(along) < 20:
        return {"n": len(along), "slack_m": MOTION_SLACK_M, "calibrated": False}
    q = float(np.quantile(along, 1 - CALIBRATION_PASS))
    return {"n": len(along), "slack_m": max(-q, 0.0), "calibrated": True,
            "p5_m": q, "p25_m": float(np.quantile(along, .25)),
            "median_m": float(along.median()), "upstream_share": float((along < 0).mean())}


def inferred_links(candidates: pd.DataFrame, *, gap_s: float = DEFAULT_GAP_S,
                   edge_m: float = DEFAULT_EDGE_M, motion_check: bool = True,
                   motion_slack_m: float = MOTION_SLACK_M) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rule 3 at given thresholds: the links, and the candidates rejected only by motion."""
    c = candidates[(candidates.gap_s <= gap_s) & (candidates.edge_m <= edge_m)]
    ok = c.along_m.isna() | (c.along_m >= -motion_slack_m) | (not motion_check)
    return c[ok].assign(rule="succession"), c[~ok].assign(rule="rejected_upstream")


def sequence_links(links: pd.DataFrame) -> pd.DataFrame:
    """The links of a watch *sequence*: rule 3 only where B begins after A has ended.

    Two granularities come out of the same links. **Systems** (all links)
    join side-by-side watches in force at the same time — touching county
    sets along one front — and so describe connected watch coverage, often
    across a thousand kilometres or more. **Sequences** keep only hand-overs in
    time (same county at once, "replaces", or B starting after A's last county
    ended) and describe one chain of watches. Stage 51 uses systems as the
    upper bound of an event (do not merge what SPC never connected) and
    sequences as the lower bound (do not split what SPC carried as one chain).
    """
    return links[(links.rule != "succession") | (links.gap_s >= 0)]


def systems(watches: pd.DataFrame, links: pd.DataFrame, prefix: str = "ws_") -> pd.Series:
    """Connected components of the links: ``<prefix><earliest watch>`` per watch."""
    from .hazards import UnionFind

    pos = {wid: i for i, wid in enumerate(watches.wid)}
    uf = UnionFind(len(watches))
    for a, b in zip(links.a, links.b):
        if a in pos and b in pos:
            uf.union(pos[a], pos[b], "")
    first = watches.first_start.to_numpy()
    out = {}
    for members in uf.groups().values():
        root = min(members, key=lambda i: (first[i], watches.wid.iloc[i]))
        for i in members:
            out[watches.wid.iloc[i]] = prefix + watches.wid.iloc[root]
    return watches.wid.map(out)


# ── tornadoes in watches ────────────────────────────────────────────────────
def assign_tornadoes(tracks: pd.DataFrame, counties: pd.DataFrame, polygons: pd.DataFrame,
                     system_of: dict, sequence_of: dict | None = None) -> pd.DataFrame:
    """Each SPC tornado's watch(es) and watch system.

    By county when SPC records one (the official area, with that county's own
    times); by polygon only when it does not. ``margin_*_min`` are minutes from
    the county's start to the tornado, and from the tornado to the county's end.
    """
    t = pd.DataFrame({"spc_id": tracks.spc_id.to_numpy(), "ugc": tornado_ugc(tracks).to_numpy(),
                      "t0": pd.to_datetime(tracks.begin_utc, utc=True).to_numpy()})
    m = t.dropna(subset=["ugc"]).merge(counties[["wid", "ugc", "start", "end"]], on="ugc")
    m = m[(m.start <= m.t0) & (m.t0 < m.end)]
    m = m.assign(method="county",
                 margin_start_min=(m.t0 - m.start).dt.total_seconds() / 60,
                 margin_end_min=(m.end - m.t0).dt.total_seconds() / 60)
    no_county = tracks[t.ugc.isna().to_numpy()]
    poly = polygon_hits(no_county, polygons)
    if len(poly):
        poly = poly.assign(wid=[watch_id(y, n) for y, n in zip(poly.year, poly.num)],
                           method="polygon")
    hits = pd.concat([m[["spc_id", "wid", "method", "margin_start_min", "margin_end_min"]],
                      poly[["spc_id", "wid", "method"]] if len(poly) else None],
                     ignore_index=True)
    hits["system_id"] = hits.wid.map(system_of)
    g = hits.groupby("spc_id")
    out = pd.DataFrame({
        "watches": g.wid.agg(lambda s: ";".join(sorted(set(s)))),
        "method": g.method.first(),
        "system_id": g.system_id.agg(lambda s: sorted(set(s.dropna()))[0] if s.notna().any() else None),
        "n_systems": g.system_id.nunique(),
        "margin_start_min": g.margin_start_min.min(),
        "margin_end_min": g.margin_end_min.max(),
    }).reset_index()
    if sequence_of is not None:
        seq = hits.assign(q=hits.wid.map(sequence_of)).groupby("spc_id").q.agg(
            lambda s: sorted(set(s.dropna()))[0] if s.notna().any() else None)
        out = out.join(seq.rename("sequence_id"), on="spc_id")
    res = tracks[["spc_id", "yr", "mag", "begin_utc"]].merge(out, on="spc_id", how="left")
    res["method"] = res.method.fillna("none")
    res["n_systems"] = res.n_systems.fillna(0).astype(int)
    return res
