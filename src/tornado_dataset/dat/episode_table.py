"""Episodes and the hazards in them: built on SPC tracks (stage 15).

An episode is a group of tornadoes linked by single linkage within
``config.EPISODE_MAX_DISTANCE_M`` and ``config.EPISODE_MAX_GAP_H`` (closest
points of the straight SPC tracks; end of one to start of the next), with no
day boundary. It is built on SPC's complete, reviewed tornado list, which is
the population: **every** SPC episode is published, ``has_dat`` saying whether
it holds a DAT survey. DAT holds only the surveyed subset — before ~2015 a small
one — so restricting to it would make the dataset's coverage follow DAT's
adoption rather than the tornadoes.

The hazards of an episode come from two sources (``hazard_source``):

* ``dat`` — a DAT hazard (stage 12) takes the episode of its closest SPC track
  (stage 14's links, the time-repaired and date-only ones included).
* ``spc`` — an SPC tornado with no DAT link at all becomes a hazard of its own,
  with SPC's straight start→end line as geometry (``geometry_source``
  ``spc_line``, or ``spc_point`` when SPC has no end point). An SPC track that is
  linked to a DAT hazard but is not its closest (``role`` ``dat_secondary``:
  mostly a piece of the same tornado) does not, or one tornado would count twice.

A DAT hazard with no SPC track is in no episode. It stays in the hazards table,
``in_spc`` false, with ``spc_match_status`` saying what the nearest SPC track
is: on it but at another time (``time_mismatch``), on a track that already has
a DAT hazard (``probable_duplicate``), 5–20 km away (``spc_far``), nothing within
20 km and 72 h (``no_spc_nearby``), or not searchable for lack of a time
(``untimed_no_spc``). See stage 51 for the episode rule's evidence.

Each hazard's rating, deaths and injuries (:func:`hazard_values`) are SPC's
where it has an SPC track, DAT's where it has none; DAT's and SPC's own values
stay beside them, with a flag where the two disagree.

Readers: :func:`membership`, :func:`episode_of`, :func:`hazards_with_episodes`,
:func:`spc_hazards` and :func:`geography`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .. import config
from ..ids import uid
from . import episodes as ep
from .hazards import convective_day, ef_rank

METHOD = (f"space_time_spc_{config.EPISODE_MAX_DISTANCE_M / 1000:g}km_"
          f"{config.EPISODE_MAX_GAP_H:g}h")
# A DAT hazard whose nearest SPC track lies within this distance is "on" it;
# the same distance as the matching rule (storm_events.MATCH_DISTANCE_M).
ON_TRACK_M = 5_000.0

MATCH_STATUSES = ("linked", "spc_only", "time_mismatch", "probable_duplicate",
                  "spc_far", "no_spc_nearby", "untimed_no_spc")


def episodes_path(tag: str) -> Path:
    return config.PROCESSED_DIR / f"episodes_{tag}.csv"


def membership_path(tag: str) -> Path:
    return config.PROCESSED_DIR / f"hazard_episodes_{tag}.csv"


def spc_hazards_path(tag: str, suffix: str = "csv") -> Path:
    return config.PROCESSED_DIR / f"spc_hazards_{tag}.{suffix}"


def spc_episodes_path(tag: str) -> Path:
    return config.INTERIM_DIR / f"spc_episodes_{tag}.csv"


def group_spc(frame: pd.DataFrame) -> pd.Series:
    """Episode label of each SPC track (a :func:`episodes.load_spc_frame`)."""
    return ep.space_time(frame, config.EPISODE_MAX_DISTANCE_M,
                         config.EPISODE_MAX_GAP_H * ep.HOUR)


def efscale_of(mag) -> str:
    """SPC's ``mag`` as DAT writes a rating: 0-5 -> "EF0".."EF5", -9 -> "EFU"."""
    return f"EF{int(mag)}" if pd.notna(mag) and int(mag) >= 0 else "EFU"


def match_status(unmatched: pd.DataFrame, closest: set[str]) -> pd.DataFrame:
    """``spc_match_status`` and the nearest SPC track for DAT hazards without one.

    ``unmatched`` is stage 14's ``spc_unmatched_dat`` table; ``closest`` the SPC
    tracks that are some DAT hazard's closest.
    """
    km = unmatched.nearest_distance_km
    on_track = km <= ON_TRACK_M / 1000
    status = pd.Series("spc_far", index=unmatched.index)
    status[km.isna()] = "no_spc_nearby"
    status[unmatched.time_begin_utc.isna()] = "untimed_no_spc"
    status[on_track] = "time_mismatch"
    status[on_track & unmatched.nearest_spc_id.isin(closest)] = "probable_duplicate"
    return pd.DataFrame({"hazard_uid": unmatched.hazard_uid, "spc_match_status": status,
                         "spc_nearest_id": unmatched.nearest_spc_id,
                         "spc_nearest_km": km.round(3),
                         "spc_nearest_offset_h": unmatched.nearest_offset_h.round(2)})


def build(frame: pd.DataFrame, labels: pd.Series, tracks: pd.DataFrame,
          hazards: pd.DataFrame, links: pd.DataFrame,
          unmatched: pd.DataFrame | None = None, spc_se_links: pd.DataFrame | None = None,
          ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Episodes, hazard membership, the SPC grouping, and the SPC hazards.

    ``frame`` and ``labels`` are the SPC tracks and their groups; ``tracks`` the
    same tracks as stage 14 wrote them (casualties, length, width, state);
    ``hazards`` stage 12's table; ``links`` stage 14's SPC ↔ DAT links;
    ``unmatched`` stage 14's DAT hazards without an SPC track and their nearest
    one; ``spc_se_links`` stage 14's SPC ↔ Storm Events links (for the offices).
    """
    spc = pd.DataFrame({"spc_id": frame.hazard_uid.to_numpy(), "label": labels.to_numpy(),
                        "t0": frame.t0.to_numpy(), "t1": frame.t1.to_numpy(),
                        "convective_day": frame.convective_day.to_numpy(),
                        "mag": frame.mag.to_numpy()})
    extra = tracks.set_index("spc_id")[["fat", "inj", "len", "wid", "st"]]
    spc = spc.join(extra, on="spc_id")
    ids = spc.groupby("label").spc_id.agg(lambda s: sorted(s))
    spc["episode_uid"] = spc.label.map(ids.map(lambda s: uid("episode", METHOD, *s)))

    # ── DAT hazards ──
    best = links[links.rank_for_hazard == 1].drop_duplicates("hazard_uid").set_index("hazard_uid")
    dat = pd.DataFrame({"hazard_uid": hazards.hazard_uid.to_numpy(), "hazard_source": "dat"})
    dat["spc_id"] = dat.hazard_uid.map(best.spc_id)
    dat["episode_uid"] = dat.spc_id.map(spc.set_index("spc_id").episode_uid)
    dat["in_spc"] = dat.episode_uid.notna()
    dat.loc[~dat.in_spc, "spc_id"] = None
    dat["spc_link_method"] = dat.hazard_uid.map(best.link_method).where(dat.in_spc, "none")
    dat["spc_match_status"] = dat.in_spc.map({True: "linked", False: None})
    closest = set(dat.spc_id.dropna())
    if unmatched is not None and len(unmatched):
        status = match_status(unmatched, closest).set_index("hazard_uid")
        for col in status.columns:
            dat[col] = dat.hazard_uid.map(status[col])
        dat.loc[dat.in_spc, "spc_match_status"] = "linked"
    dat["spc_match_status"] = dat.spc_match_status.fillna("unmatched")

    # ── SPC tracks: closest of a DAT hazard, linked otherwise, or a hazard of their own ──
    linked_any = set(links.spc_id)
    spc["role"] = "spc_hazard"
    spc.loc[spc.spc_id.isin(linked_any), "role"] = "dat_secondary"
    spc.loc[spc.spc_id.isin(closest), "role"] = "dat_closest"
    own = spc[spc.role == "spc_hazard"]
    spc_member = pd.DataFrame({
        "hazard_uid": [uid("hazard", "spc", s) for s in own.spc_id],
        "hazard_source": "spc", "spc_id": own.spc_id.to_numpy(),
        "episode_uid": own.episode_uid.to_numpy(), "in_spc": True,
        "spc_link_method": "spc_record", "spc_match_status": "spc_only"})
    member = pd.concat([dat, spc_member], ignore_index=True)
    member = member[["hazard_uid", "hazard_source", "episode_uid", "spc_id", "spc_link_method",
                     "in_spc", "spc_match_status"]
                    + [c for c in ("spc_nearest_id", "spc_nearest_km", "spc_nearest_offset_h")
                       if c in member.columns]]

    spc_hazards = pd.DataFrame({
        "hazard_uid": spc_member.hazard_uid.to_numpy(), "hazard_source": "spc",
        "spc_id": own.spc_id.to_numpy(), "hazard_type": "tornado",
        "convective_day": own.convective_day.to_numpy(),
        "time_begin_utc": [pd.Timestamp(t).isoformat() if pd.notna(t) else None for t in own.t0],
        "time_end_utc": [pd.Timestamp(t).isoformat() if pd.notna(t) else None for t in own.t1],
        "efscale": [efscale_of(m) for m in own.mag],
        "path_length_mi": own.len.to_numpy(), "path_width_yd": own.wid.to_numpy(),
        "injuries": own.inj.to_numpy(), "fatalities": own.fat.to_numpy(),
        "states": own.st.to_numpy(), "episode_uid": own.episode_uid.to_numpy()})

    # ── episodes ──
    se_wfos: dict[str, set[str]] = {}
    if spc_se_links is not None and len(spc_se_links):
        first = spc_se_links[spc_se_links.rank_for_event == 1]
        for s, w in zip(first.spc_id, first.WFO):
            if isinstance(w, str) and w:
                se_wfos.setdefault(s, set()).add(w)
    hz = hazards.set_index("hazard_uid")
    by_episode = member[member.episode_uid.notna()].groupby("episode_uid")
    rows = []
    for episode_uid, s in spc.groupby("episode_uid"):
        m = (by_episode.get_group(episode_uid) if episode_uid in by_episode.groups
             else member.iloc[0:0])
        dat_uids = m.hazard_uid[m.hazard_source == "dat"].tolist()
        spc_uids = m.hazard_uid[m.hazard_source == "spc"].tolist()
        d = hz.loc[dat_uids]
        days = sorted(set(s.convective_day.dropna()))
        begin, end = s.t0.min(), s.t1.max()
        mag = s.mag[s.mag >= 0]
        efs = [e for e in d.efscale if isinstance(e, str) and e]
        wfos = {w for v in d.wfo_all.dropna() for w in str(v).split(";") if w}
        wfos |= {w for sid in s.spc_id for w in se_wfos.get(sid, ())}
        rows.append({
            "episode_uid": episode_uid, "hazard_family": "tornado",
            "episode_method": METHOD, "has_dat": bool(dat_uids),
            "convective_day": days[0] if days else None,
            "convective_days": ";".join(days),
            "time_begin_utc": None if pd.isna(begin) else pd.Timestamp(begin).isoformat(),
            "time_end_utc": None if pd.isna(end) else pd.Timestamp(end).isoformat(),
            "duration_h": (None if pd.isna(begin) or pd.isna(end)
                           else round((end - begin).total_seconds() / 3600, 2)),
            "n_hazards": len(m), "n_dat": len(dat_uids), "n_spc_hazards": len(spc_uids),
            "n_spc": len(s), "n_spc_ef1plus": int((s.mag >= 1).sum()),
            "n_spc_unrated": int((s.mag < 0).sum()),
            "spc_max_mag": int(mag.max()) if len(mag) else None,
            "spc_fatalities": int(s.fat.sum()), "spc_injuries": int(s.inj.sum()),
            # From the DAT surveys; empty where the episode has none.
            "max_efscale": max(efs, key=ef_rank) if efs else None,
            "fatalities": int(d.fatalities.fillna(0).sum()) if dat_uids else None,
            "injuries": int(d.injuries.fillna(0).sum()) if dat_uids else None,
            "wfos": ";".join(sorted(wfos)),
            "hazard_uids": ";".join(dat_uids + spc_uids),
            "spc_ids": ";".join(sorted(s.spc_id)),
        })
    episodes = pd.DataFrame(rows).sort_values(["time_begin_utc", "episode_uid"],
                                              na_position="last").reset_index(drop=True)
    has_dat = set(episodes.episode_uid[episodes.has_dat])
    grouping = spc[["spc_id", "episode_uid", "role"]].assign(
        has_dat=lambda f: f.episode_uid.isin(has_dat))
    return episodes, member, grouping, spc_hazards


# ── rating, deaths and injuries ─────────────────────────────────────────────
VALUE_SOURCES = ("spc", "spc_piece", "dat")
VALUE_COMPARISONS = ("one_to_one", "several_tracks", "shared_track", "dat_only", "spc_only")
COMPARED = ("one_to_one", "several_tracks")


def ef_number(value) -> float:
    """A rating as a number: "EF3", "EF3+" -> 3; unrated or not a rating -> NaN."""
    rank = ef_rank(value)
    return float(rank) if rank >= 0 else float("nan")


def track_holders(member: pd.DataFrame, links: pd.DataFrame) -> pd.Series:
    """The one hazard each SPC track's deaths and injuries are counted on.

    An SPC hazard holds its own track. A track that is some DAT hazard's closest
    goes to that hazard, or, where several DAT hazards share it (pieces or
    duplicates of one tornado), to the one stage 14 ranks first for the track
    (``rank_for_event``, then distance, then uid). A track linked to DAT hazards
    but no one's closest (a piece of a tornado DAT drew as one line, or a
    tornado on a line stage 12 merged) goes to its first-ranked DAT hazard. So
    every SPC track is counted exactly once. Index ``spc_id``, values
    ``hazard_uid``.
    """
    ranked = links.sort_values(["rank_for_event", "distance_m", "hazard_uid"])
    own = member[member.hazard_source == "spc"]
    holder = dict(zip(own.spc_id, own.hazard_uid))
    dat = member[(member.hazard_source == "dat") & member.spc_id.notna()]
    closest = ranked.merge(dat[["hazard_uid", "spc_id"]], on=["hazard_uid", "spc_id"])
    for frame in (closest, ranked):
        for spc_id, hazard_uid in zip(frame.spc_id, frame.hazard_uid):
            holder.setdefault(spc_id, hazard_uid)
    return pd.Series(holder, name="hazard_uid").rename_axis("spc_id")


def hazard_values(member: pd.DataFrame, hazards: pd.DataFrame, tracks: pd.DataFrame,
                  links: pd.DataFrame) -> pd.DataFrame:
    """Each hazard's rating, deaths and injuries, with where they come from.

    ``member`` is the membership table of :func:`build`, ``hazards`` stage 12's
    DAT hazards (``efscale``, ``fatalities``, ``injuries``), ``tracks`` SPC's
    tornado list (``spc_id``, ``mag``, ``fat``, ``inj``), ``links`` stage 14's
    SPC ↔ DAT links. SPC's record is the primary source; DAT's survey fields are
    kept beside it, so the two can be compared.

    * ``spc_ids_counted`` — the SPC tracks this hazard holds
      (:func:`track_holders`); ``spc_deaths`` and ``spc_injuries`` are their sums,
      so a total over hazards counts every SPC tornado once. ``spc_rating`` is the
      highest rating of these tracks and the hazard's closest one (a maximum, so
      a piece may repeat its tornado's rating).
    * ``dat_rating``, ``dat_deaths``, ``dat_injuries`` — stage 12's values for a
      DAT hazard as DAT wrote them (``efscale``, ``fatalities``, ``injuries``).
    * ``rating``, ``deaths``, ``injuries`` with ``values_source``: ``spc`` (SPC's,
      for every SPC hazard and every DAT hazard that holds a track), ``spc_piece``
      (a DAT hazard whose track is held by another DAT hazard, ``values_held_by``:
      SPC's rating, deaths and injuries empty as they are counted there), or
      ``dat`` (a DAT hazard with no SPC track: DAT's own).
    * ``values_compare`` says on what DAT and SPC were compared: ``one_to_one``
      (the hazard holds its closest track and nothing else, and no other DAT
      hazard shares it), ``several_tracks`` (it holds more, mostly a line stage 12
      merged or SPC split: DAT against SPC's sum), ``shared_track`` (pieces of one
      track; not compared), ``dat_only``, ``spc_only``. Where compared,
      ``rating_differs``, ``deaths_differ`` and ``injuries_differ`` are true or
      false (empty where either side is unrated or unknown).
    """
    holder = track_holders(member, links)
    t = tracks.set_index("spc_id")[["mag", "fat", "inj"]]
    held = holder.reset_index().groupby("hazard_uid").spc_id.agg(sorted)
    h = hazards.set_index("hazard_uid")
    out = member[["hazard_uid", "hazard_source", "spc_id"]].copy()
    uids = out.hazard_uid
    held_of = uids.map(held)
    has_held = held_of.notna()

    def tracks_of(row_held, closest) -> list[str]:
        ids = list(row_held) if isinstance(row_held, list) else []
        return ids + ([closest] if isinstance(closest, str) and closest not in ids else [])

    def spc_sum(col: str) -> pd.Series:
        return held_of.map(lambda ids: float(t.loc[ids, col].sum())
                           if isinstance(ids, list) else float("nan"))

    mags = [t.loc[tracks_of(a, b), "mag"] for a, b in zip(held_of, out.spc_id)]
    spc_mag = pd.Series([m[m >= 0].max() if (m >= 0).any() else float("nan") for m in mags],
                        index=out.index)
    on_spc = out.spc_id.notna()
    out["spc_ids_counted"] = held_of.map(lambda ids: ";".join(ids) if isinstance(ids, list)
                                         else None)
    out["spc_rating"] = [efscale_of(m) if on else None for m, on in zip(spc_mag, on_spc)]
    out["spc_deaths"] = spc_sum("fat")
    out["spc_injuries"] = spc_sum("inj")

    dat = out.hazard_source == "dat"
    out["dat_rating"] = uids.map(h.efscale).where(dat)
    out["dat_deaths"] = uids.map(h.fatalities).where(dat)
    out["dat_injuries"] = uids.map(h.injuries).where(dat)

    source = pd.Series("spc", index=out.index)
    source[dat & on_spc & ~has_held] = "spc_piece"
    source[dat & ~on_spc] = "dat"
    out["values_source"] = source
    closest_holder = out.spc_id.map(holder)
    out["values_held_by"] = closest_holder.where(dat & on_spc & (closest_holder != uids))
    dat_mag = out.dat_rating.map(ef_number)
    from_dat = source == "dat"
    out["rating"] = out.spc_rating.where(~from_dat, [
        efscale_of(m) if pd.notna(r) else None for m, r in zip(dat_mag, out.dat_rating)])
    out["deaths"] = out.spc_deaths.where(~from_dat, out.dat_deaths)
    out["injuries"] = out.spc_injuries.where(~from_dat, out.dat_injuries)

    shared = out.spc_id.map(out.spc_id[dat].value_counts()).fillna(0) > 1
    alone = has_held & held_of.map(lambda ids: isinstance(ids, list) and len(ids) == 1)
    compare = pd.Series("spc_only", index=out.index)
    compare[dat & ~on_spc] = "dat_only"
    compare[dat & on_spc & shared] = "shared_track"
    compare[dat & on_spc & ~shared & has_held] = "several_tracks"
    compare[dat & on_spc & ~shared & alone] = "one_to_one"
    out["values_compare"] = compare
    compared = compare.isin(COMPARED)

    def differs(a: pd.Series, b: pd.Series) -> pd.Series:
        flag = pd.Series(pd.NA, index=out.index, dtype="boolean")
        ok = compared & a.notna() & b.notna()
        flag[ok] = (a[ok] != b[ok]).to_numpy()
        return flag

    out["rating_differs"] = differs(dat_mag, spc_mag)
    out["deaths_differ"] = differs(out.dat_deaths, out.spc_deaths)
    out["injuries_differ"] = differs(out.dat_injuries, out.spc_injuries)
    for col in ("deaths", "injuries", "spc_deaths", "spc_injuries", "dat_deaths",
                "dat_injuries"):
        out[col] = out[col].astype("Int64")
    return out[["hazard_uid", "rating", "deaths", "injuries", "values_source",
                "values_held_by", "spc_ids_counted", "spc_rating", "spc_deaths",
                "spc_injuries", "dat_rating", "dat_deaths", "dat_injuries", "values_compare",
                "rating_differs", "deaths_differ", "injuries_differ"]]


def spc_hazard_features(spc_hazards: pd.DataFrame, tracks: pd.DataFrame) -> list[dict]:
    """GeoJSON features for the SPC hazards: SPC's straight start→end line (WGS84)."""
    from shapely.geometry import mapping

    from . import spc_tornadoes

    rows = tracks.set_index("spc_id").loc[spc_hazards.spc_id].reset_index()
    geoms = spc_tornadoes.track_geometries(rows, lambda g: g)
    features = []
    for props, geom in zip(spc_hazards.to_dict("records"), geoms):
        source = (None if geom is None else
                  "spc_point" if geom.geom_type == "Point" else "spc_line")
        props = {k: (None if isinstance(v, float) and v != v else v) for k, v in props.items()}
        features.append({"type": "Feature",
                         "geometry": None if geom is None else mapping(geom),
                         "properties": {**props, "geometry_source": source}})
    return features


# ── readers ─────────────────────────────────────────────────────────────────
def _require(path: Path) -> Path:
    if not path.exists():
        raise SystemExit(f"no {path.name} — run scripts/15_build_episodes.py")
    return path


def membership(tag: str) -> pd.DataFrame:
    """Stage 15's hazard → episode table (DAT and SPC hazards)."""
    return pd.read_csv(_require(membership_path(tag)))


def episode_of(tag: str) -> dict[str, str]:
    """Each hazard's ``episode_uid``; hazards in no episode are left out."""
    m = membership(tag).dropna(subset=["episode_uid"])
    return dict(zip(m.hazard_uid, m.episode_uid))


_JOINED = ("episode_uid", "in_spc", "spc_match_status")


def hazards_with_episodes(tag: str, usecols: list[str] | None = None) -> pd.DataFrame:
    """Stage 12's DAT hazards with ``episode_uid``, ``in_spc`` and ``spc_match_status``.

    ``episode_uid`` is empty for a DAT hazard with no SPC track.
    """
    cols = None if usecols is None else [c for c in usecols if c not in _JOINED] + ["hazard_uid"]
    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv", low_memory=False,
                          usecols=None if cols is None else list(dict.fromkeys(cols)))
    # A hazards table written before stage 15 existed carries its own episode_uid.
    hazards = hazards.drop(columns=list(_JOINED), errors="ignore")
    out = hazards.merge(membership(tag)[["hazard_uid", *_JOINED]], on="hazard_uid", how="left")
    return out if usecols is None else out[list(dict.fromkeys(usecols))]


def spc_hazards(tag: str) -> pd.DataFrame:
    """Stage 15's SPC hazards (SPC tornadoes with no DAT link)."""
    return pd.read_csv(_require(spc_hazards_path(tag)), low_memory=False)


# Stage 14 links these DAT hazards to their SPC track only after finding DAT's own
# time wrong (a whole-hour clock error, or another error on the same footprint) or
# missing (a date only).
SPC_TIME_METHODS = ("time_repaired", "footprint_match", "date_only")
TIME_SOURCES = ("dat", "spc", "spc_track")


def event_times(hazards: pd.DataFrame, member: pd.DataFrame, tracks: pd.DataFrame
                ) -> pd.DataFrame:
    """When, and on which convective day, each hazard happened.

    ``hazards`` has ``hazard_uid``, ``hazard_source``, ``time_begin_utc`` and
    ``convective_day`` (DAT and SPC hazards), and ``time_end_utc`` if the end is
    wanted; ``member`` is stage 15's membership table, ``tracks`` SPC's tornado
    list (``spc_id``, ``begin_utc``, and ``end_utc`` for the end).

    A DAT hazard takes its SPC track's start, end and day where stage 14 found
    DAT's time wrong or missing (``SPC_TIME_METHODS``; ``time_source`` ``spc_track``).
    Every other hazard keeps its own (``dat`` or ``spc``). An end before the start
    or more than 5 h after it is mistyped: its clock time is kept where that gives
    at most 5 h (``end_repaired``, :func:`episodes.repair_end_times`), and the end
    is left empty where it does not, as where DAT has none. Returns
    ``hazard_uid``, ``begin_utc``, ``end_utc``, ``convective_day``,
    ``time_source`` and ``end_repaired``; times as ISO strings.
    """
    out = hazards[["hazard_uid", "hazard_source", "time_begin_utc", "convective_day"]].merge(
        member[["hazard_uid", "spc_id", "spc_link_method"]], on="hazard_uid", how="left")
    own_end = (hazards.set_index("hazard_uid").time_end_utc.reindex(out.hazard_uid).to_numpy()
               if "time_end_utc" in hazards.columns else None)
    track = tracks.set_index("spc_id")
    use = ((out.hazard_source == "dat") & out.spc_link_method.isin(SPC_TIME_METHODS)
           & out.spc_id.map(lambda s: s in track.index and isinstance(track.begin_utc.get(s), str)))

    t0 = pd.to_datetime(out.time_begin_utc, utc=True, errors="coerce")
    t1 = (pd.to_datetime(pd.Series(own_end, index=out.index), utc=True, errors="coerce")
          if own_end is not None else pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns, UTC]"))
    if own_end is not None:
        fixed, bad = ep.repair_end_times(t0, t1)
        clock = ((t1.dt.hour * 60 + t1.dt.minute) - (t0.dt.hour * 60 + t0.dt.minute)) % 1440
        kept = bad & t0.notna() & t1.notna() & (clock <= ep.MAX_TORNADO_DURATION_H * 60)
        t1 = fixed.where(~bad | kept)
        repaired = kept & ~use
    else:
        repaired = pd.Series(False, index=out.index)
    t0 = t0.copy()
    t0[use] = pd.to_datetime(out.spc_id[use].map(track.begin_utc), utc=True)
    if "end_utc" in track.columns:
        t1 = t1.copy()
        t1[use] = pd.to_datetime(out.spc_id[use].map(track.end_utc), utc=True)

    def iso(t: pd.Series) -> list:
        return [x.isoformat() if pd.notna(x) else None for x in t]

    out["begin_utc"] = iso(t0)
    out["end_utc"] = iso(t1) if (own_end is not None or "end_utc" in track.columns) else None
    out.loc[use, "convective_day"] = [convective_day(t.to_pydatetime()).isoformat()
                                      for t in t0[use]]
    out["time_source"] = out.hazard_source.where(~use, "spc_track")
    out["end_repaired"] = repaired.to_numpy()
    return out[["hazard_uid", "begin_utc", "end_utc", "convective_day", "time_source",
                "end_repaired"]]


def geography(tag: str, sources: tuple[str, ...] = ("dat",)) -> pd.DataFrame:
    """Stage 16's geography table for the hazards of ``sources``, with ``episode_uid``.

    The default is DAT hazards only: stages not yet revisited for SPC hazards
    read it so. ``("dat", "spc")`` gives both.
    """
    path = config.PROCESSED_DIR / f"hazard_geography_{tag}.csv"
    if not path.exists():
        raise SystemExit(f"no {path.name} — run scripts/16_enrich_geography.py")
    geo = pd.read_csv(path)
    if "hazard_source" in geo.columns:
        geo = geo[geo.hazard_source.isin(sources)]
    geo = geo.drop(columns=["episode_uid"], errors="ignore")
    return geo.merge(membership(tag)[["hazard_uid", "episode_uid"]], on="hazard_uid",
                     how="left").reset_index(drop=True)
