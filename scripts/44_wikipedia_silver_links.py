#!/usr/bin/env python
"""Stage 44 — silver links: Wikipedia text and the news it cites, to tornadoes and DAT polygons.

An evaluation set for the news → tornado linker (stage 31 and its successors),
made from links Wikipedia's editors already drew:

    passage ──cites──► NCEI EVENT_ID ──stage 14──► Storm Events tornado ──► DAT hazard (polygon)
       │                                                   └──► SPC track ──► DAT hazard, or
       │                                                        an SPC hazard of its own (line)
       └──cites──► news article  (inherits the passage's tornado)

Each link carries its tornado's best geometry (``geometry``): a DAT damage
polygon, else a DAT track line, else SPC's straight start–end track (a tornado
DAT has no survey for, stage 15's SPC hazards), else none; and its stage 15
episode.

A passage's evidence is the NCEI ids its own prose cites, the ids its own
infobox cites, and the ids of the table row it was matched to (stage 28). Each
id resolves to a whole tornado through Storm Events' county-segment chains;
the passage's tornado is checked against what the passage says (date, state,
places, rating) and gets a **strength** (``silver.strength``). A cited news
article inherits a link only when every tornado-level passage citing it points
at the same tornado, and is then checked itself (published from the day before
the event on, naming one of its places).

Episode-level passages (outbreak overviews, yearly events) link to the set of
tornadoes their prose, tables and infobox cite. News cited only by them gets
an episode link.

These are **silver** labels: written by editors, checked automatically, not by
a person. A blind sample is drawn for a hand check; until it is labelled, the
strengths are a ranking, not a precision. The texts that were not linked are
counted in the report, not dropped silently.

    python scripts/44_wikipedia_silver_links.py
    python scripts/44_wikipedia_silver_links.py --sample 100

Reads stage 28 (passages, facts, fact links), stage 29 (cited news, citations,
LexisNexis cross-reference), stage 23's LexisNexis articles, stage 14 (Storm
Events tornadoes, their DAT and SPC links), stage 15 (episodes and SPC hazards,
optional: without them links stop at DAT) and stage 12 (hazards). Writes
``data/processed/wikipedia_silver_links.csv``,
``outputs/wikipedia_silver_links_report.md``, and the hand-check sheet
``outputs/annotation/wikipedia_silver_handcheck.csv`` with its key in
``data/interim/``. Offline.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

import _bootstrap  # noqa: F401

from tornado_dataset import config
from tornado_dataset.dat import episode_table as et
from tornado_dataset.dat import references as refs
from tornado_dataset.ids import write_manifest
from tornado_dataset.text import silver
from tornado_dataset.text import wikifacts as wf

PASSAGES_JSONL = config.PROCESSED_DIR / "wikipedia_passages.jsonl"
FACTS_CSV = config.PROCESSED_DIR / "wikipedia_facts.csv"
FACT_LINKS_CSV = config.PROCESSED_DIR / "wikipedia_fact_links.csv"
NEWS_JSONL = config.PROCESSED_DIR / "wikipedia_cited_news.jsonl"
CITATIONS_CSV = config.PROCESSED_DIR / "wikipedia_cited_news_citations.csv"
LEXIS_XREF_CSV = config.PROCESSED_DIR / "wikipedia_cited_lexisnexis.csv"
LEXIS_JSONL = config.OUTPUT_DIR / "lexisnexis_articles.jsonl"
SILVER_CSV = config.PROCESSED_DIR / "wikipedia_silver_links.csv"
# The silver links as Media Cloud stories: the evaluation set on that corpus.
SILVER_MC_CSV = config.PROCESSED_DIR / "wikipedia_silver_mediacloud.csv"
MC_MATCHES_CSV = config.INTERIM_DIR / "wikipedia_ref_matches_mediacloud.csv"
MC_CSV = config.PROCESSED_DIR / "mediacloud_filtered.csv.gz"
REPORT = config.OUTPUT_DIR / "wikipedia_silver_links_report.md"
SHEET = config.OUTPUT_DIR / "annotation" / "wikipedia_silver_handcheck.csv"
SHEET_KEY = config.INTERIM_DIR / "wikipedia_silver_handcheck_key.csv"
LABELS = ("same_tornado", "other_tornado", "outbreak_only", "not_about_a_tornado", "unsure")


def _ids(value) -> set[str]:
    return set(str(value or "").split("|")) - {"", "nan"}


# ── inputs ───────────────────────────────────────────────────────────────────
def load(tag: str) -> dict:
    hazards_csv = config.PROCESSED_DIR / f"hazards_{tag}.csv"
    config.require_data(PASSAGES_JSONL, FACTS_CSV, FACT_LINKS_CSV, NEWS_JSONL, CITATIONS_CSV,
                        LEXIS_XREF_CSV, refs.SE_TORNADOES, refs.se_links_path(tag), hazards_csv)
    passages = pd.DataFrame([json.loads(l) for l in PASSAGES_JSONL.open(encoding="utf-8")])
    if "ncei_event_ids_facts" not in passages.columns:
        raise SystemExit("passages predate facts — rerun scripts/28_wikipedia_passages.py")
    se = pd.read_csv(refs.SE_TORNADOES, low_memory=False)
    links = pd.read_csv(refs.se_links_path(tag))
    hazards = pd.read_csv(hazards_csv, low_memory=False,
                          usecols=["hazard_uid", "has_polygon", "geometry_source", "efscale"])
    return {**load_spc(tag), "hazard_places": load_places(tag),
        "passages": passages,
        "facts": pd.read_csv(FACTS_CSV, keep_default_na=False, dtype=str).set_index("fact_uid"),
        "fact_links": pd.read_csv(FACT_LINKS_CSV, keep_default_na=False),
        "news": pd.DataFrame([json.loads(l) for l in NEWS_JSONL.open(encoding="utf-8")]),
        "citations": pd.read_csv(CITATIONS_CSV, keep_default_na=False),
        "lexis_xref": pd.read_csv(LEXIS_XREF_CSV, keep_default_na=False),
        "tornadoes": silver.tornadoes(se),
        "id_to_key": dict(zip(se.EVENT_ID.astype(int).astype(str), se.TORNADO_KEY)),
        "key_hazards": links[links.rank_for_event == 1].groupby("TORNADO_KEY").hazard_uid
        .agg(lambda s: sorted(set(s))).to_dict(),
        "has_polygon": dict(zip(hazards.hazard_uid, hazards.has_polygon.astype(str).eq("True"))),
    }


def load_spc(tag: str) -> dict:
    """Storm Events tornado → SPC tracks (stage 14), SPC track → DAT hazards and
    SPC hazards, hazard → episode (stage 15). Empty when stage 14's SPC part or
    stage 15 has not run."""
    empty = {"key_spc": {}, "spc_dat": {}, "spc_own": {}, "episode_of": {}}
    if not (refs.spc_se_links_path(tag).exists() and et.membership_path(tag).exists()):
        print("  no SPC links or episodes (stages 14 with an SPC file, 15) — links stop at DAT")
        return empty
    se_spc = pd.read_csv(refs.spc_se_links_path(tag))
    member = pd.read_csv(et.membership_path(tag), usecols=["hazard_uid", "hazard_source",
                                                           "spc_id", "episode_uid"])
    on_track = member.dropna(subset=["spc_id"])
    return {
        "key_spc": se_spc[se_spc.rank_for_event == 1].groupby("TORNADO_KEY").spc_id
        .agg(lambda s: sorted(set(s))).to_dict(),
        "spc_dat": on_track[on_track.hazard_source == "dat"].groupby("spc_id").hazard_uid
        .agg(list).to_dict(),
        "spc_own": on_track[on_track.hazard_source == "spc"].groupby("spc_id").hazard_uid
        .agg(list).to_dict(),
        "episode_of": dict(zip(member.hazard_uid, member.episode_uid.fillna(""))),
    }


def load_places(tag: str) -> dict[str, set[str]]:
    """Each hazard's towns on or near its path (stage 16: every GNIS place
    within 25 km, not the larger towns farther out); empty when stage 16 has
    not run."""
    path = config.PROCESSED_DIR / f"hazard_geography_{tag}.csv"
    if not path.exists():
        print("  no hazard geography (stage 16) — news is checked against Storm Data's towns only")
        return {}
    geo = pd.read_csv(path, usecols=["hazard_uid", "places", "places_near"], keep_default_na=False)
    # As GNIS spells them: matched as proper names, since many are also words.
    return {u: {re.sub(r"\s*\(historical\)$", "", p.strip()) for v in (a, b)
                for p in str(v).split(";") if p.strip()}
            for u, a, b in zip(geo.hazard_uid, geo.places, geo.places_near)}


GEOMETRIES = ("dat_polygon", "dat_line", "spc_track", "none")


def geometry(d: dict, keys) -> dict:
    """The hazards of Storm Events tornadoes ``keys``, and their best geometry.

    DAT hazards are those stage 14 linked to the tornado's county segments, and
    those on the SPC track its segments match (``dat_via`` says which). An SPC
    track with no DAT hazard is a hazard of its own (stage 15), a straight line.
    """
    spc_ids = sorted({s for k in keys for s in d["key_spc"].get(k, [])})
    by_se = {h for k in keys for h in d["key_hazards"].get(k, [])}
    by_spc = {h for s in spc_ids for h in d["spc_dat"].get(s, [])}
    dat = by_se | by_spc
    own = sorted({h for s in spc_ids for h in d["spc_own"].get(s, [])})
    n_poly = sum(d["has_polygon"].get(h, False) for h in dat)
    return {"dat_hazard_uids": "|".join(sorted(dat)), "n_dat_polygons": n_poly,
            "dat_via": ("both" if by_se and by_spc else "storm_events" if by_se
                        else "spc" if by_spc else ""),
            "spc_ids": "|".join(spc_ids), "spc_hazard_uids": "|".join(own),
            "episode_uids": "|".join(sorted({e for h in dat | set(own)
                                             if (e := d["episode_of"].get(h))})),
            "geometry": ("dat_polygon" if n_poly else "dat_line" if dat
                         else "spc_track" if spc_ids else "none")}


def lexis_texts(uids: set[str]) -> dict[str, dict]:
    """Bodies and dates of the LexisNexis articles Wikipedia cites."""
    from tornado_dataset.text.lexisnexis import textref_uid
    if not uids or not LEXIS_JSONL.exists():
        return {}
    out = {}
    for line in LEXIS_JSONL.open(encoding="utf-8"):
        r = json.loads(line)
        u = textref_uid(r)
        if u in uids:
            out[u] = {"text": r.get("body") or "", "title": r.get("headline") or "",
                      "published": str(r.get("pub_date") or "")[:10], "source": r.get("source") or ""}
    return out


# ── passages ─────────────────────────────────────────────────────────────────
def passage_evidence(p, facts: pd.DataFrame, fact_links: pd.DataFrame) -> tuple[dict, dict]:
    """``({ncei_id: kinds}, facts)`` for one passage: prose ids, its infobox's,
    its matched table row's; and the facts' rating, state, date."""
    evidence: dict[str, set] = {i: {"prose"} for i in _ids(p.ncei_event_ids)}
    mine = fact_links[(fact_links.passage_uid == p.textref_uid)
                      & fact_links.relation.isin(["infobox_of", "same_tornado"])]
    info = {"rating": "", "states": set(), "match": ""}
    for link in mine.itertuples():
        fact = facts.loc[link.fact_uid]
        kind = "infobox" if link.relation == "infobox_of" else "table_row"
        for i in _ids(fact.ncei_event_ids):
            evidence.setdefault(i, set()).add(kind)
        info["rating"] = info["rating"] or fact.rating
        info["states"] |= wf.states_in(fact.state)
        if kind == "table_row":
            info["match"] = link.match
    return evidence, info


def link_passages(d: dict) -> tuple[pd.DataFrame, Counter]:
    """One row per hazard-level passage with a tornado; episode-level passages
    with their tornado sets."""
    rows, why = [], Counter()
    tors, id_to_key = d["tornadoes"], d["id_to_key"]
    for p in d["passages"].itertuples():
        evidence, info = passage_evidence(p, d["facts"], d["fact_links"])
        base = {"text_uid": p.textref_uid, "text_kind": "wikipedia_passage",
                "unit_kind": p.unit_kind, "title": p.title, "url": p.url,
                "published_at": str(p.published_at)[:10], "event_date": p.event_date,
                "page_title": p.page_title, "heading": p.heading}
        if p.link_level == "episode":
            ids = set(evidence) | _ids(p.ncei_event_ids_tables)
            ids |= {i for link in d["fact_links"][(d["fact_links"].passage_uid == p.textref_uid)
                                                  & (d["fact_links"].relation == "listed_in_outbreak")]
                    .itertuples() for i in _ids(d["facts"].loc[link.fact_uid].ncei_event_ids)}
            keys = sorted({id_to_key[i] for i in ids if i in id_to_key})
            if not keys:
                why["episode: no NCEI id in Storm Events"] += 1
                continue
            rows.append({**base, "link_level": "episode", "tornado_key": "|".join(keys),
                         "n_tornadoes": len(keys), "cited_ncei_ids": "|".join(sorted(ids, key=int)),
                         "evidence": "", "how": "episode", "strength": "episode",
                         **geometry(d, keys)})
            continue
        if not evidence:
            why["tornado: no NCEI id in prose, infobox or matched row"] += 1
            continue
        found = {i: id_to_key[i] for i in evidence if i in id_to_key}
        if not found:
            why["tornado: its NCEI ids are not Storm Events tornadoes"] += 1
            continue
        heading = p.heading or p.page_title
        states = wf.states_in(heading) | wf.states_in(p.us_states) | info["states"]
        places = wf.place_names(heading)
        rating = info["rating"] or getattr(p, "infobox_rating", "")
        cands = {}
        for i, key in found.items():
            c = cands.setdefault(key, {"evidence": set(), "ids": set()})
            c["evidence"] |= evidence[i]
            c["ids"].add(i)
        for key, c in cands.items():
            c.update(silver.checks(date=p.event_date, states=states, places=places,
                                   rating=rating, tornado=tors[key],
                                   within_days=14 if p.event_date_basis == "outbreak_start" else 0))
        key, how = silver.choose(cands)
        if key is None:
            why["tornado: several tornadoes, none stands out"] += 1
            continue
        c, tor = cands[key], tors[key]
        rows.append({**base, "link_level": "hazard", "tornado_key": key, "n_tornadoes": 1,
                     "cited_ncei_ids": "|".join(sorted(c["ids"], key=int)),
                     "n_tornadoes_cited": len(cands),
                     "evidence": "|".join(k for k in ("prose", "infobox", "table_row")
                                          if k in c["evidence"]),
                     "table_match": info["match"], "how": how,
                     **{k: c[k] for k in ("date_ok", "state_ok", "place_ok", "rating_ok",
                                          "consistency")},
                     "strength": silver.strength(how, c),
                     "reject_reason": silver.reject_reason("wikipedia_passage", c)
                     if silver.strength(how, c) == "rejected" else "",
                     "tornado_date": tor["date"], "tornado_rating": tor["rating"],
                     "tornado_states": "|".join(sorted(tor["states"])),
                     "se_event_ids": "|".join(tor["event_ids"]),
                     **geometry(d, [key]),
                     "_places": places})
    return pd.DataFrame(rows), why


# ── news ─────────────────────────────────────────────────────────────────────
MC_COLUMNS = ("mc_ids", "mc_tier", "mc_label")       # stage 29, from stage 27's Media Cloud tiers
MC_ORDER = {"url": 0, "title_outlet": 1, "title_syndicated": 2}


def mediacloud_of(rows: pd.DataFrame) -> dict:
    """The Media Cloud stories of several citations of one LexisNexis article,
    pooled: every id, best tier first."""
    if "mc_ids" not in rows:
        return {c: "" for c in MC_COLUMNS}
    held = rows[rows.mc_ids != ""].assign(_o=lambda r: r.mc_tier.map(MC_ORDER)).sort_values("_o")
    ids = list(dict.fromkeys(i for v in held.mc_ids for i in v.split("|") if i))
    return {"mc_ids": "|".join(ids), "mc_tier": held.mc_tier.iloc[0] if len(held) else "",
            "mc_label": held.mc_label.iloc[0] if len(held) else ""}


def link_news(d: dict, plinks: pd.DataFrame) -> tuple[pd.DataFrame, Counter]:
    """Cited news inherits its citing passages' tornado, when they agree."""
    hazard = plinks[plinks.link_level == "hazard"].set_index("text_uid")
    episode = plinks[plinks.link_level == "episode"].set_index("text_uid")
    news = d["news"].set_index("textref_uid")
    # (news uid, kind, citing passage uids, record)
    items = [(uid, "cited_news", list(g.passage_uid), news.loc[uid])
             for uid, g in d["citations"].groupby("textref_uid")]
    xref = d["lexis_xref"]
    texts = lexis_texts(set(xref.lexis_textref_uid))
    # One row per LexisNexis article: two citations (a web URL and a print
    # citation, say) can match the same record. Their citing passages are
    # pooled, so the article is linked only when all of them agree.
    for lexis_uid, g in xref[xref.lexis_textref_uid != ""].groupby("lexis_textref_uid", sort=False):
        t = texts.get(lexis_uid, {})
        citing = sorted({p for v in g.citing_passages for p in str(v).split("|") if p})
        urls = [u for u in g.url if u]
        mc = mediacloud_of(g)
        items.append((lexis_uid, "lexisnexis", citing,
                      pd.Series({"title": t.get("title") or g.title.iloc[0],
                                 "url": urls[0] if urls else "",
                                 "published_at": t.get("published") or g.lexis_date.iloc[0],
                                 "text": t.get("text", ""), "text_quality": "lexisnexis",
                                 "story_id": "", "story_primary": True, **mc})))
    rows, why = [], Counter()
    for uid, kind, citing, rec in items:
        base = {"text_uid": uid, "text_kind": kind, "unit_kind": "news", "title": rec.title,
                "url": rec.url, "published_at": str(rec.published_at or "")[:10],
                "text_quality": rec.text_quality, "story_id": rec.story_id,
                "story_primary": rec.story_primary, "citing_passages": "|".join(sorted(citing)),
                **{f"mediacloud_{c[3:]}": rec.get(c, "") or "" for c in MC_COLUMNS}}
        mine = hazard[hazard.index.isin(citing)]
        usable = mine[mine.strength != "rejected"]
        if len(usable):
            keys = set(usable.tornado_key)
            if len(keys) > 1:
                why["news: citing passages name different tornadoes"] += 1
                continue
            key = keys.pop()
            tor = d["tornadoes"][key]
            places = sorted({pl for ps in usable["_places"] for pl in ps})
            # Only an intact text can show the article names none of the places.
            intact = rec.text_quality in ("good", "lexisnexis")
            geo = geometry(d, [key])
            path_towns = {p for u in _ids(geo["dat_hazard_uids"]) | _ids(geo["spc_hazard_uids"])
                          for p in d["hazard_places"].get(u, ())}
            check = silver.news_checks(published=base["published_at"], event_date=tor["date"],
                                       text=(rec.get("text") or "") if intact else "",
                                       title=rec.title or "", places=places,
                                       counties=tor["counties"], towns=tor.get("places", ()),
                                       path_towns=path_towns)
            strength = silver.news_strength(usable.strength, check)
            rows.append({**base, "link_level": "hazard", "tornado_key": key, "n_tornadoes": 1,
                         "evidence": "cited_by_passage", "how": "inherited",
                         "n_citing_hazard_passages": len(usable),
                         "passage_strengths": "|".join(sorted(usable.strength)),
                         "days_after_event": check["days_after_event"],
                         "date_ok": check["date_ok"], "place_ok": check["mentions_place"],
                         "strength": strength,
                         "reject_reason": silver.reject_reason(kind, check)
                         if strength == "rejected" else "",
                         "tornado_date": tor["date"], "tornado_rating": tor["rating"],
                         "tornado_states": "|".join(sorted(tor["states"])),
                         "se_event_ids": "|".join(tor["event_ids"]), **geo})
            continue
        if len(mine):
            why["news: only rejected passages cite it"] += 1
            continue
        eps = episode[episode.index.isin(citing)]
        if len(eps) and eps.page_title.nunique() == 1:
            e = eps.iloc[0]
            rows.append({**base, "link_level": "episode", "tornado_key": e.tornado_key,
                         "n_tornadoes": e.n_tornadoes, "evidence": "cited_by_passage",
                         "how": "inherited", "strength": "episode",
                         **{c: e[c] for c in ("dat_hazard_uids", "n_dat_polygons", "dat_via",
                                              "spc_ids", "spc_hazard_uids", "episode_uids",
                                              "geometry")}})
        else:
            why["news: no citing passage with a tornado or one outbreak"] += 1
    return pd.DataFrame(rows), why


# ── hand check ───────────────────────────────────────────────────────────────
SAMPLE_PLAN = {("wikipedia_passage", "strong"): 12, ("wikipedia_passage", "medium"): 10,
               ("wikipedia_passage", "weak"): 8, ("wikipedia_passage", "rejected"): 5,
               ("cited_news", "strong"): 20, ("cited_news", "medium"): 15,
               ("cited_news", "weak"): 15, ("cited_news", "rejected"): 8,
               ("lexisnexis", "strong"): 5,
               ("lexisnexis", "medium"): 5, ("lexisnexis", "weak"): 5}


def draw_sheet(links: pd.DataFrame, d: dict, n: int) -> int:
    """A blind, stratified sample of hazard-level links for a hand check."""
    if SHEET.exists() and "label" in (s := pd.read_csv(SHEET, keep_default_na=False)) \
            and (s.label != "").any():
        print(f"  {SHEET.name} already has labels — left untouched")
        return len(s)
    hazard = links[links.link_level == "hazard"]
    scale = n / sum(SAMPLE_PLAN.values())
    picks = []
    for (kind, strength), k in SAMPLE_PLAN.items():
        pool = hazard[(hazard.text_kind == kind) & (hazard.strength == strength)]
        picks.append(pool.sample(min(len(pool), max(1, round(k * scale))), random_state=44))
    sample = pd.concat(picks).sample(frac=1, random_state=44).reset_index(drop=True)
    passages = d["passages"].set_index("textref_uid")
    rows, key = [], []
    for i, r in enumerate(sample.itertuples(), 1):
        tor = d["tornadoes"][r.tornado_key]
        excerpt = (" ".join(passages.text[r.text_uid].split()[:80]) + " …"
                   if r.text_kind == "wikipedia_passage" else "(open the URL)")
        rows.append({
            "row_id": f"s{i:03d}", "text_kind": r.text_kind, "title": r.title, "url": r.url,
            "published": r.published_at, "excerpt": excerpt,
            "tornado": (f"{tor['date']} · {tor['rating']} · {', '.join(sorted(tor['states']))} · "
                        f"counties: {', '.join(sorted(tor['counties'])).title()} · "
                        f"{tor['length_mi']} mi · {tor['deaths']} deaths"),
            "ncei_event_ids": "|".join(tor["event_ids"]), "label": "", "notes": ""})
        key.append({"row_id": f"s{i:03d}", "text_uid": r.text_uid, "tornado_key": r.tornado_key,
                    "strength": r.strength, "how": r.how, "evidence": r.evidence})
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(SHEET, index=False, encoding="utf-8-sig")
    pd.DataFrame(key).to_csv(SHEET_KEY, index=False)
    return len(rows)


# ── report ───────────────────────────────────────────────────────────────────
def write_report(links: pd.DataFrame, why: Counter, n_sheet: int, d: dict) -> None:
    hazard = links[links.link_level == "hazard"]
    order = ["strong", "medium", "weak", "rejected"]
    table = pd.crosstab(hazard.text_kind, hazard.strength).reindex(columns=order, fill_value=0)
    geo = pd.crosstab(hazard.text_kind, hazard.geometry).reindex(columns=list(GEOMETRIES),
                                                                  fill_value=0)
    table = table.join(geo.rename(columns=lambda c: f"geometry: {c}"))
    passages = hazard[hazard.text_kind == "wikipedia_passage"]
    news = hazard[hazard.text_kind != "wikipedia_passage"]
    good = news[(news.text_kind == "lexisnexis") | (news.text_quality == "good")]
    episode = links[links.link_level == "episode"]
    lines = [
        "# Silver links: Wikipedia text and cited news to tornadoes",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by "
        "`scripts/44_wikipedia_silver_links.py`.",
        "",
        "Wikipedia passages about one tornado cite its NCEI Storm Events record; Storm Events "
        "chains county segments into tornadoes and stage 14 links them to DAT hazards. The news "
        "a passage cites inherits its tornado. These are **silver** labels — drawn by editors, "
        "checked automatically against Storm Events, not by a person — for evaluating the "
        f"news → tornado linker. Written to `{SILVER_CSV.relative_to(config.REPO_ROOT)}`.",
        "",
        "## Tornado-level links",
        "",
        table.reset_index().to_markdown(index=False),
        "",
        f"- **{len(passages)} Wikipedia passages** and **{len(news)} news articles** "
        f"({len(news[news.text_kind == 'cited_news'])} cited articles outside LexisNexis, "
        f"{len(news[news.text_kind == 'lexisnexis'])} in it) link to one tornado; "
        f"{len(good)} of the news articles have text that checks out as the article "
        "(`text_quality = good`, or LexisNexis).",
        f"- {hazard.tornado_key.nunique()} distinct tornadoes; "
        f"{hazard[hazard.n_dat_polygons > 0].tornado_key.nunique()} of them have a DAT damage polygon, "
        f"{hazard[hazard.geometry == 'dat_line'].tornado_key.nunique()} a DAT track line only, "
        f"{hazard[hazard.geometry == 'spc_track'].tornado_key.nunique()} only SPC's straight track "
        f"(no DAT survey), {hazard[hazard.geometry == 'none'].tornado_key.nunique()} none.",
        f"- DAT hazards found through the SPC track and not through Storm Events directly: "
        f"{(hazard.dat_via == 'spc').sum()} links.",
        "",
        "**Geometry** is the tornado's best: a DAT damage polygon, else DAT's track line, else "
        "SPC's start–end line (stage 15's SPC hazards), else none.",
        "",
        "**Strength** (`text.silver.strength`): *strong* — the passage names one tornado and its "
        "date (±1 day), state and a place agree with the Storm Events record; *medium* — one "
        "tornado, nothing disagrees, a place or the rating agrees; *weak* — nothing disagrees but "
        "little could be checked, or the tornado was chosen among several the passage cites; "
        "*rejected* — the date or state disagrees (kept for inspection, not for evaluation). "
        "A news article takes its weakest citing passage's strength, one step lower if it was "
        f"published before the event or more than {silver.NEWS_MAX_DAYS} days after; it is "
        "*rejected* when its intact text (`text_quality = good`, or LexisNexis) names none of "
        "the tornado's places — heading towns, counties, Storm Data's begin and end towns — "
        "since Wikipedia then cites it for something else (a comparison, the whole outbreak).",
        "",
        "### Rejected",
        "",
        (hazard[hazard.strength == "rejected"].groupby(["text_kind", "reject_reason"]).size()
         .rename("links").reset_index().to_markdown(index=False)
         if (hazard.strength == "rejected").any() else "None."),
        "",
        "### How a passage's tornado was found",
        "",
        pd.crosstab(passages.evidence, passages.strength).reindex(columns=order, fill_value=0)
        .reset_index().to_markdown(index=False),
        "",
        "`prose`: an NCEI id the passage's own text cites; `infobox`: one its infobox cites; "
        "`table_row`: one its matched table row cites (stage 28).",
        "",
        "## Episode-level links",
        "",
        f"{(episode.text_kind == 'wikipedia_passage').sum()} outbreak overviews and yearly events "
        f"link to the set of tornadoes their prose, tables and infobox cite (median "
        f"{int(episode[episode.text_kind == 'wikipedia_passage'].n_tornadoes.median() or 0)}); "
        f"{(episode.text_kind != 'wikipedia_passage').sum()} news articles cited only by one such "
        "passage inherit that set.",
        "",
        "## Not linked",
        "",
        pd.DataFrame({"reason": list(why), "texts": list(why.values())})
        .sort_values("texts", ascending=False).to_markdown(index=False),
        "",
        "## Hand check",
        "",
        f"`{SHEET.relative_to(config.REPO_ROOT)}` holds {n_sheet} tornado-level links, "
        "stratified by kind and strength, **blind** (no strength or checks shown; the key is "
        f"in `{SHEET_KEY.relative_to(config.REPO_ROOT)}`). For each row, read the text (or "
        "open the URL) and the tornado's Storm Events summary, and put one label: "
        + ", ".join(f"`{l}`" for l in LABELS) + ". Save the labelled copy as "
        "`outputs/annotation/wikipedia_silver_handcheck_labels.csv` (tracked in git); the "
        "precision per strength comes from it.",
        "",
        "## Caveats",
        "",
        "1. **A citation is not a label.** A news article cited in one tornado's section can be "
        "about the whole outbreak; the place check catches some, the hand check measures the rest.",
        "2. **Wikipedia text is easier than news.** It is written after the survey and often "
        "from it; evaluate the linker on the news rows, and use the passages as a check.",
        "3. **DAT is incomplete in early years** (stage 17): a tornado without a DAT hazard has "
        "SPC's straight start–end line at best — fine for which-tornado, not for where-exactly.",
        "4. **Storm Events dates are local standard time**; the date check allows ±1 day.",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Media Cloud ──────────────────────────────────────────────────────────────
def mediacloud_items(links: pd.DataFrame) -> tuple[pd.DataFrame | None, int]:
    """The tornado-level links as Media Cloud stories (``silver.corpus_items``),
    with how each was found and stage 30's label; ``None`` without stage 27's
    Media Cloud matches."""
    if "mediacloud_ids" not in links or not MC_MATCHES_CSV.exists():
        return None, 0
    items, conflicts = silver.corpus_items(links, "mediacloud_ids")
    m = pd.read_csv(MC_MATCHES_CSV, keep_default_na=False, dtype={"mc_id": str})
    m = m[m.tier.isin(MC_ORDER)].assign(_o=lambda t: t.tier.map(MC_ORDER)).sort_values("_o")
    best = m.drop_duplicates("mc_id").set_index("mc_id")
    first = links.drop_duplicates("tornado_key").set_index("tornado_key")
    items = items.rename(columns={"item_id": "mc_id"})
    items["mc_tier"] = items.mc_id.map(best.tier).fillna("")
    items["mc_label"] = items.mc_id.map(best.mc_primary).fillna("")
    items["mc_headline"] = items.mc_id.map(best.mc_headline).fillna("")
    items["mc_source"] = items.mc_id.map(best.mc_source).fillna("")
    items["mc_date"] = items.mc_id.map(best.mc_date).fillna("")
    # Media Cloud's own headline groups (stage 30): wire copy run by many outlets
    # is one group, labelled and linked once through its representative row.
    if MC_CSV.exists():
        mc = pd.read_csv(MC_CSV, keep_default_na=False, dtype={"id": str},
                         usecols=["id", "dup_group", "is_representative"]).set_index("id")
        items["mc_dup_group"] = items.mc_id.map(mc.dup_group).fillna("").astype(str)
        items["mc_representative"] = items.mc_id.map(mc.is_representative).astype(str).eq("True")
    else:
        items["mc_dup_group"], items["mc_representative"] = items.mc_id, True
    for col in ("tornado_date", "tornado_rating", "tornado_states", "geometry",
                "dat_hazard_uids", "spc_hazard_uids", "episode_uids"):
        items[col] = items.tornado_key.map(first[col]) if col in first else ""
    return items, conflicts


def mediacloud_lines(items: pd.DataFrame, conflicts: int, links: pd.DataFrame) -> list[str]:
    order = ["strong", "medium", "weak"]
    groups = items.drop_duplicates("mc_dup_group")
    table = pd.crosstab(groups.mc_tier, groups.strength).reindex(columns=order, fill_value=0)
    event = groups[groups.mc_label == "EVENT"]
    return [
        "## On Media Cloud",
        "",
        f"`{SILVER_MC_CSV.relative_to(config.REPO_ROOT)}`: the tornado-level news links as "
        f"stories of our Media Cloud export — **{len(groups):,} distinct headlines** "
        f"(Media Cloud's `dup_group`; {len(items):,} rows, since one wire story runs in many "
        f"outlets — one cited article reaches up to {items.groupby('text_uids').size().max()}) "
        f"**linked to one of {items.tornado_key.nunique()} tornadoes**, {len(event):,} of them "
        "labelled `EVENT` by stage 30 (the ones the linker is run on; `mc_representative` "
        "marks the row stage 30 labelled). A story is found through a cited article "
        "(stage 27: its URL, the same headline in its outlet, or wire copy in another); one "
        "story found through several cited articles takes its tornado only when they agree "
        f"({conflicts} dropped because they do not) and the weakest strength.",
        "",
        "Distinct headlines, by how the first was found and the link's strength:",
        "",
        table.reset_index().to_markdown(index=False),
        "",
        f"With a DAT polygon: {(groups.geometry == 'dat_polygon').sum():,}; only SPC's track: "
        f"{(groups.geometry == 'spc_track').sum():,}. Labels: "
        + ", ".join(f"{k} {v}" for k, v in groups.mc_label.replace("", "unlabelled")
                    .value_counts().items()) + ".",
        "",
        "A story labelled anything but `EVENT` that a citation ties to a tornado is a "
        "filter miss worth reading — or a citation for context (a relief fund, a "
        "power outage); the strength and the hand check tell them apart.",
        "",
    ]


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    parser.add_argument("--sample", type=int, default=100, help="hand-check sheet size")
    args = parser.parse_args()
    d = load(args.tag)
    plinks, why = link_passages(d)
    nlinks, why_news = link_news(d, plinks)
    links = pd.concat([plinks, nlinks], ignore_index=True)
    n_sheet = draw_sheet(links, d, args.sample)
    links = links.drop(columns=["_places"], errors="ignore")
    links.to_csv(SILVER_CSV, index=False)
    mc_items, mc_conflicts = mediacloud_items(links)
    if mc_items is not None:
        mc_items.to_csv(SILVER_MC_CSV, index=False)
    write_report(links, why + why_news, n_sheet, d)
    if mc_items is not None:
        with REPORT.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(mediacloud_lines(mc_items, mc_conflicts, links)) + "\n")
    hazard = links[links.link_level == "hazard"]
    write_manifest(config.PROCESSED_DIR / "manifest_wikipedia_silver_links.json",
                   "44_wikipedia_silver_links",
                   counts={"links": len(links), "hazard_links": len(hazard),
                           **{f"{k}_{s}": int(v) for (k, s), v in
                              hazard.groupby(["text_kind", "strength"]).size().items()},
                           "handcheck_rows": n_sheet},
                   outputs=[SILVER_CSV] + ([SILVER_MC_CSV] if mc_items is not None else []))
    print(pd.crosstab(hazard.text_kind, hazard.strength).to_string())
    print(f"wrote {SILVER_CSV.name}, {REPORT.name}, {SHEET.name}")
    if mc_items is not None:
        g = mc_items.drop_duplicates("mc_dup_group")
        print(f"{len(g)} Media Cloud headlines ({len(mc_items)} rows) linked to one tornado "
              f"({(g.mc_label == 'EVENT').sum()} labelled EVENT); wrote {SILVER_MC_CSV.name}")


if __name__ == "__main__":
    main()
