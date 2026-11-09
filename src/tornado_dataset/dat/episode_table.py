"""The published episodes: built on SPC tracks, carried to DAT hazards (stage 15).

An episode is a group of tornadoes linked by single linkage within
``config.EPISODE_MAX_DISTANCE_M`` and ``config.EPISODE_MAX_GAP_H`` (closest
points of the straight SPC tracks; end of one to start of the next), with no
day boundary. It is built on SPC's complete, reviewed tornado list rather than
on DAT, which holds only the surveyed subset — before ~2020 a small one — so a
tornado DAT lacks cannot cut an outbreak in two. Stage 51 compares this rule
with the alternatives.

Each DAT hazard takes the episode of its closest SPC track (stage 14's links,
including the time-repaired and date-only ones). A hazard with no SPC track is
an episode of its own, ``in_spc`` false. Only episodes holding at least one DAT
hazard are published; the grouping of every SPC track is kept beside them.

Readers: :func:`membership`, :func:`episode_of` and :func:`hazards_with_episodes`
— the hazards table (stage 12) carries no episode.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .. import config
from ..ids import uid
from . import episodes as ep
from .hazards import ef_rank

METHOD = (f"space_time_spc_{config.EPISODE_MAX_DISTANCE_M / 1000:g}km_"
          f"{config.EPISODE_MAX_GAP_H:g}h")


def episodes_path(tag: str) -> Path:
    return config.PROCESSED_DIR / f"episodes_{tag}.csv"


def membership_path(tag: str) -> Path:
    return config.PROCESSED_DIR / f"hazard_episodes_{tag}.csv"


def spc_episodes_path(tag: str) -> Path:
    return config.INTERIM_DIR / f"spc_episodes_{tag}.csv"


def group_spc(frame: pd.DataFrame) -> pd.Series:
    """Episode label of each SPC track (a :func:`episodes.load_spc_frame`)."""
    return ep.space_time(frame, config.EPISODE_MAX_DISTANCE_M,
                         config.EPISODE_MAX_GAP_H * ep.HOUR)


def build(frame: pd.DataFrame, labels: pd.Series, tracks: pd.DataFrame,
          hazards: pd.DataFrame, links: pd.DataFrame
          ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Episodes, hazard membership, and the SPC grouping.

    ``frame`` and ``labels`` are the SPC tracks and their groups; ``tracks`` the
    same tracks as stage 14 wrote them (for ``fat`` and ``inj``); ``hazards``
    stage 12's table; ``links`` stage 14's SPC ↔ DAT links.
    """
    spc = pd.DataFrame({"spc_id": frame.hazard_uid.to_numpy(), "label": labels.to_numpy(),
                        "t0": frame.t0.to_numpy(), "t1": frame.t1.to_numpy(),
                        "convective_day": frame.convective_day.to_numpy(),
                        "mag": frame.mag.to_numpy()})
    extra = tracks.set_index("spc_id")[["fat", "inj"]]
    spc = spc.join(extra, on="spc_id")
    ids = spc.groupby("label").spc_id.agg(lambda s: sorted(s))
    spc["episode_uid"] = spc.label.map(ids.map(lambda s: uid("episode", METHOD, *s)))

    best = links[links.rank_for_hazard == 1].drop_duplicates("hazard_uid").set_index("hazard_uid")
    member = pd.DataFrame({"hazard_uid": hazards.hazard_uid.to_numpy()})
    member["spc_id"] = member.hazard_uid.map(best.spc_id)
    member["spc_link_method"] = member.hazard_uid.map(best.link_method).fillna("none")
    member["in_spc"] = member.spc_id.notna()
    member["episode_uid"] = member.spc_id.map(spc.set_index("spc_id").episode_uid)
    alone = member.episode_uid.isna()
    member.loc[alone, "episode_uid"] = [uid("episode", METHOD, "dat", h)
                                       for h in member.hazard_uid[alone]]
    member["in_spc"] = member.in_spc & ~alone
    member = member[["hazard_uid", "episode_uid", "spc_id", "spc_link_method", "in_spc"]]

    hz = hazards.set_index("hazard_uid")
    rows = []
    with_dat = member.groupby("episode_uid")
    by_episode = spc.groupby("episode_uid")
    for episode_uid, m in with_dat:
        dat = hz.loc[m.hazard_uid]
        in_spc = bool(m.in_spc.iloc[0])
        if in_spc:
            s = by_episode.get_group(episode_uid)
            days = sorted(set(s.convective_day.dropna()))
            begin, end = s.t0.min(), s.t1.max()
            mag = s.mag[s.mag >= 0]
            spc_cols = {"n_spc": len(s), "n_spc_ef1plus": int((s.mag >= 1).sum()),
                        "n_spc_unrated": int((s.mag < 0).sum()),
                        "spc_max_mag": int(mag.max()) if len(mag) else None,
                        "spc_fatalities": int(s.fat.sum()), "spc_injuries": int(s.inj.sum()),
                        "spc_ids": ";".join(sorted(s.spc_id))}
        else:
            days = sorted(set(dat.convective_day.dropna()))
            begin = pd.to_datetime(dat.time_begin_utc, utc=True, errors="coerce").min()
            end = pd.to_datetime(dat.time_end_utc, utc=True, errors="coerce").max()
            spc_cols = {"n_spc": 0, "n_spc_ef1plus": 0, "n_spc_unrated": 0,
                        "spc_max_mag": None, "spc_fatalities": None, "spc_injuries": None,
                        "spc_ids": ""}
        efs = [e for e in dat.efscale if isinstance(e, str) and e]
        wfos = sorted({w for v in dat.wfo_all.dropna() for w in str(v).split(";") if w})
        rows.append({
            "episode_uid": episode_uid, "hazard_family": "tornado",
            "episode_method": METHOD, "in_spc": in_spc,
            "convective_day": days[0] if days else None,
            "convective_days": ";".join(days),
            "time_begin_utc": None if pd.isna(begin) else pd.Timestamp(begin).isoformat(),
            "time_end_utc": None if pd.isna(end) else pd.Timestamp(end).isoformat(),
            "duration_h": (None if pd.isna(begin) or pd.isna(end)
                           else round((end - begin).total_seconds() / 3600, 2)),
            "n_hazards": len(m), "n_dat": len(m), **{k: v for k, v in spc_cols.items()
                                                     if k != "spc_ids"},
            "max_efscale": max(efs, key=ef_rank) if efs else None,
            "fatalities": int(dat.fatalities.fillna(0).sum()),
            "injuries": int(dat.injuries.fillna(0).sum()),
            "wfos": ";".join(wfos),
            "hazard_uids": ";".join(m.hazard_uid),
            "spc_ids": spc_cols["spc_ids"],
        })
    episodes = pd.DataFrame(rows).sort_values(["time_begin_utc", "episode_uid"],
                                              na_position="last").reset_index(drop=True)
    grouping = spc[["spc_id", "episode_uid"]].assign(
        has_dat=lambda d: d.episode_uid.isin(set(member.episode_uid)))
    return episodes, member, grouping


# ── readers ─────────────────────────────────────────────────────────────────
def membership(tag: str) -> pd.DataFrame:
    """Stage 15's hazard → episode table; stops with a message if it has not run."""
    path = membership_path(tag)
    if not path.exists():
        raise SystemExit(f"no {path.name} — run scripts/15_build_episodes.py")
    return pd.read_csv(path)


def episode_of(tag: str) -> dict[str, str]:
    """Each hazard's ``episode_uid``."""
    m = membership(tag)
    return dict(zip(m.hazard_uid, m.episode_uid))


def hazards_with_episodes(tag: str, usecols: list[str] | None = None) -> pd.DataFrame:
    """Stage 12's hazards table with ``episode_uid`` (and ``in_spc``) joined on."""
    cols = None if usecols is None else [c for c in usecols
                                         if c not in ("episode_uid", "in_spc")] + ["hazard_uid"]
    hazards = pd.read_csv(config.PROCESSED_DIR / f"hazards_{tag}.csv", low_memory=False,
                          usecols=None if cols is None else list(dict.fromkeys(cols)))
    out = hazards.merge(membership(tag)[["hazard_uid", "episode_uid", "in_spc"]],
                        on="hazard_uid", how="left")
    return out if usecols is None else out[list(dict.fromkeys(usecols))]
