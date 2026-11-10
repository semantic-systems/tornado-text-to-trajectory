"""Text that comes with the official records: Storm Events narratives, DAT comments.

Three kinds of TextRef, all written by the NWS office from its survey and so
``oracle`` (:mod:`tiering`, ``POST_SURVEY_SOURCE_TYPES``):

* **Event narratives** (``storm_events_narrative``) — NCEI Storm Events'
  ``EVENT_NARRATIVE``, one per Storm Events row. Storm Events splits a tornado at
  county and office lines, so a long track has several, each linked to the
  hazard (``narrative_of``). The route to the hazard, in order: the DAT hazard
  the row is best matched to (stage 14); else, through the row's SPC track, the
  SPC hazard that track is, or the DAT hazard(s) it is the closest track of;
  else, for a track that is only a secondary link of a DAT hazard, the episode.
  A row is never linked to two hazards by two routes.
* **Episode narratives** (``storm_events_episode_narrative``) — one per Storm
  Events episode: the office's account of the weather situation, linked to every
  stage 15 episode its rows fall in (``episode_narrative_of``). Context, not a
  track description.
* **DAT comments** (``dat_comment``) — the comments surveyors entered on a
  hazard's track lines and damage polygons, one TextRef per distinct comment of
  the hazard, its ID resting on the features that carry it (``comment_of``).

No text is merged with another here: how they overlap is a separate step.
``mentions_track`` flags an event narrative or comment that names a start, an
end, a direction, a crossing or a movement — a coarse cue for "describes the
track", not a judgement of how well; empty for episode narratives.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

from ..dat.hazards import clean_text
from ..ids import uid
from . import tiering

# Cues that a text describes the track rather than only the damage or the event.
_DIRECTION = (r"(?:(?:north|south)-?(?:east|west)?|east|west"
              r"|nne|ene|ese|sse|ssw|wsw|wnw|nnw|ne|nw|se|sw)\b")
_TRACK_CUES = re.compile(
    r"touch(ed|ing|es)? ?down|began|start(ed|ing)?|first (damage|observed)|develop(ed|ing)"
    r"|lift(ed|ing|s)?|dissipat|ended|last damage|rope(d)? out"
    r"|(mov|track|travel|head|continu|proceed|curv|turn)\w* (\w+ ){0,3}" + _DIRECTION +
    r"|(north|south|east|west)(east|west)?ward|path (length|of)"
    r"|\bcross(ed|es|ing)\b|\b(moved|moving|tracked|traveled|travelled)\b",
    re.IGNORECASE)

NCEI_EVENT_URL = "https://www.ncdc.noaa.gov/stormevents/eventdetails.jsp?id={}"
NCEI_EPISODE_URL = "https://www.ncdc.noaa.gov/stormevents/listevents.jsp?eventType=ALL&episodeId={}"

REF_COLUMNS = ["textref_uid", "source_type", "source_name", "author_org", "language",
               "published_at", "title", "body", "body_is_public_domain", "url", "lat", "lon",
               "record_id", "wfo", "event_begin_utc", "n_words", "mentions_track",
               "same_org_as_geometry", "temporal_class", "text_role", "independence_tier",
               "time_offset_hours", "tier_rule_version"]
LINK_COLUMNS = ["textref_uid", "target_uid", "link_level", "link_relation", "linker",
                "link_route", "link_evidence", "link_confidence", "is_best_match"]


def mentions_track(text: str) -> bool:
    """Whether a text names where the tornado began or ended, or which way it went."""
    return bool(_TRACK_CUES.search(str(text or "")))


def _words(text: str) -> int:
    return len(str(text or "").split())


def _ref(**fields: Any) -> dict[str, Any]:
    tier = tiering.derive(fields["author_org"], fields["source_type"], None,
                          fields.get("event_begin_utc"))
    body = fields["body"]
    track = (None if fields["source_type"] == "storm_events_episode_narrative"
             else mentions_track(body))
    return {**fields, "language": "en", "published_at": None, "body_is_public_domain": True,
            "n_words": _words(body), "mentions_track": track, **tier}


def _link(textref_uid: str, target: str, level: str, relation: str, route: str,
          evidence: dict, best: bool = True) -> dict[str, Any]:
    return {"textref_uid": textref_uid, "target_uid": target, "link_level": level,
            "link_relation": relation, "linker": "record_join", "link_route": route,
            "link_evidence": json.dumps(evidence, sort_keys=True),
            "link_confidence": 1.0 if route == "dat_direct" else 0.9, "is_best_match": best}


def event_targets(se_links: pd.DataFrame, spc_se_links: pd.DataFrame,
                  membership: pd.DataFrame, grouping: pd.DataFrame
                  ) -> dict[int, tuple[str, list[str], str | None]]:
    """``EVENT_ID -> (route, hazard_uids, episode_uid)`` for each Storm Events row.

    ``se_links`` / ``spc_se_links`` are stage 14's Storm Events links to DAT
    hazards and to SPC tracks; ``membership`` and ``grouping`` stage 15's hazard
    table and SPC track roles.
    """
    episode_of = dict(zip(membership.hazard_uid, membership.episode_uid))
    spc_hazard = dict(zip(membership.spc_id[membership.hazard_source == "spc"],
                          membership.hazard_uid[membership.hazard_source == "spc"]))
    dat = membership[(membership.hazard_source == "dat") & membership.spc_id.notna()]
    dat_of_track = dat.groupby("spc_id").hazard_uid.agg(list).to_dict()
    track_episode = dict(zip(grouping.spc_id, grouping.episode_uid))
    out: dict[int, tuple[str, list[str], str | None]] = {}
    direct = se_links[se_links.rank_for_event == 1]
    for event, hazard in zip(direct.EVENT_ID, direct.hazard_uid):
        out[int(event)] = ("dat_direct", [hazard], episode_of.get(hazard))
    via = spc_se_links[spc_se_links.rank_for_event == 1]
    for event, spc_id in zip(via.EVENT_ID, via.spc_id):
        if int(event) in out:
            continue
        if spc_id in spc_hazard:
            h = spc_hazard[spc_id]
            out[int(event)] = ("spc_hazard", [h], episode_of.get(h))
        elif spc_id in dat_of_track:
            hs = dat_of_track[spc_id]
            out[int(event)] = ("dat_via_spc_track", hs, episode_of.get(hs[0]))
        elif spc_id in track_episode:
            out[int(event)] = ("episode_only", [], track_episode[spc_id])
    return out


def storm_events_refs(se: pd.DataFrame, targets: dict) -> tuple[list[dict], list[dict]]:
    """Event and episode narratives as TextRefs, with their links."""
    def clean(v):
        v = clean_text(v)
        return v if v and v.lower() != "nan" else None

    refs, links = [], []
    for row in se.itertuples():
        body = clean(row.EVENT_NARRATIVE)
        if not body:
            continue
        ref_uid = uid("textref", "storm_events_event", int(row.EVENT_ID))
        begin = pd.Timestamp(row.begin_utc).isoformat() if pd.notna(row.begin_utc) else None
        refs.append(_ref(
            textref_uid=ref_uid, source_type="storm_events_narrative",
            source_name=f"NCEI Storm Events ({row.WFO})", author_org=f"NWS {row.WFO}",
            title=f"Tornado — {str(row.CZ_NAME).title()}, {str(row.STATE).title()}",
            body=body, url=NCEI_EVENT_URL.format(int(row.EVENT_ID)),
            lat=row.BEGIN_LAT, lon=row.BEGIN_LON, record_id=str(int(row.EVENT_ID)),
            wfo=row.WFO, event_begin_utc=begin))
        route, hazards, episode = targets.get(int(row.EVENT_ID), ("none", [], None))
        evidence = {"event_id": int(row.EVENT_ID)}
        for h in hazards:
            links.append(_link(ref_uid, h, "hazard", "narrative_of", route, evidence,
                               best=len(hazards) == 1))
        if not hazards and episode:
            links.append(_link(ref_uid, episode, "episode", "narrative_of", route, evidence))

    episode_rows = se.dropna(subset=["EPISODE_ID"]).groupby("EPISODE_ID")
    for episode_id, g in episode_rows:
        body = clean(g.EPISODE_NARRATIVE.dropna().iloc[0] if g.EPISODE_NARRATIVE.notna().any()
                     else None)
        if not body:
            continue
        ref_uid = uid("textref", "storm_events_episode", int(episode_id))
        wfo = g.WFO.mode().iat[0]
        begin = pd.to_datetime(g.begin_utc, utc=True, errors="coerce").min()
        refs.append(_ref(
            textref_uid=ref_uid, source_type="storm_events_episode_narrative",
            source_name=f"NCEI Storm Events ({wfo})", author_org=f"NWS {wfo}",
            title=f"Storm Events episode {int(episode_id)} ({wfo})", body=body,
            url=NCEI_EPISODE_URL.format(int(episode_id)), lat=None, lon=None,
            record_id=str(int(episode_id)), wfo=wfo,
            event_begin_utc=None if pd.isna(begin) else begin.isoformat()))
        ours: dict[str, int] = {}
        for event in g.EVENT_ID:
            episode = targets.get(int(event), ("none", [], None))[2]
            if episode:
                ours[episode] = ours.get(episode, 0) + 1
        for episode, n in ours.items():
            links.append(_link(ref_uid, episode, "episode", "episode_narrative_of",
                               "storm_events_episode",
                               {"episode_id": int(episode_id), "events_in_episode": n,
                                "events": len(g)}, best=len(ours) == 1))
    return refs, links


def dat_comment_refs(hazards: pd.DataFrame, features: dict[str, dict[str, dict]]
                     ) -> tuple[list[dict], list[dict]]:
    """One TextRef per distinct comment of a hazard, linked to it.

    ``features`` maps ``"line"`` / ``"polygon"`` to ``{objectid: properties}`` of
    stage 10's DAT features; ``hazards`` is stage 12's table.
    """
    refs, links = [], []
    for h in hazards.itertuples():
        by_text: dict[str, list[tuple[str, dict]]] = {}
        for role, column in (("line", "line_objectids"), ("polygon", "polygon_objectids")):
            for oid in str(getattr(h, column, "") or "").split(";"):
                oid = oid.strip().split(".")[0]
                props = features[role].get(oid) if oid and oid != "nan" else None
                comment = clean_text(props.get("comments")) if props else None
                if comment:
                    by_text.setdefault(comment, []).append((f"{role}:{oid}", props))
        for comment, members in by_text.items():
            ids = sorted(m for m, _ in members)
            wfos = [str(p.get("wfo")) for _, p in members
                    if clean_text(p.get("wfo")) and str(p.get("wfo")).lower() != "none"]
            wfo = wfos[0] if wfos else (str(h.wfo) if isinstance(h.wfo, str) else None)
            ref_uid = uid("textref", "dat_comment", *ids)
            refs.append(_ref(
                textref_uid=ref_uid, source_type="dat_comment",
                source_name="NWS Damage Assessment Toolkit",
                author_org=f"NWS {wfo}" if wfo else "NWS",
                title=f"DAT survey comment ({', '.join(ids)})", body=comment, url=None,
                lat=None, lon=None, record_id=";".join(ids), wfo=wfo,
                event_begin_utc=h.time_begin_utc if isinstance(h.time_begin_utc, str) else None))
            links.append(_link(ref_uid, h.hazard_uid, "hazard", "comment_of", "dat_feature",
                               {"features": ids}))
    return refs, links


def frames(refs: list[dict], links: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The TextRef and TextLink tables, in a fixed column order."""
    r = pd.DataFrame(refs).reindex(columns=REF_COLUMNS)
    r = r.drop_duplicates("textref_uid")
    lk = pd.DataFrame(links).reindex(columns=LINK_COLUMNS)
    return r, lk
