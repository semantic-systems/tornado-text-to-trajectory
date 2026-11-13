#!/usr/bin/env python
"""Stage 44 — silver links: Wikipedia text and the news it cites, to tornadoes and DAT polygons.

An evaluation set for the news → tornado linker (stage 31 and its successors),
made from links Wikipedia's editors already drew:

    passage ──cites──► NCEI EVENT_ID ──stage 14──► Storm Events tornado ──► DAT hazard (polygon)
       └──cites──► news article  (inherits the passage's tornado)

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
Events tornadoes and their DAT links) and stage 12 (hazards). Writes
``data/processed/wikipedia_silver_links.csv``,
``outputs/wikipedia_silver_links_report.md``, and the hand-check sheet
``outputs/annotation/wikipedia_silver_handcheck.csv`` with its key in
``data/interim/``. Offline.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

import _bootstrap  # noqa: F401

from tornado_dataset import config
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
    return {
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
            hz = sorted({h for k in keys for h in d["key_hazards"].get(k, [])})
            rows.append({**base, "link_level": "episode", "tornado_key": "|".join(keys),
                         "n_tornadoes": len(keys), "cited_ncei_ids": "|".join(sorted(ids, key=int)),
                         "evidence": "", "how": "episode", "strength": "episode",
                         "dat_hazard_uids": "|".join(hz),
                         "n_dat_polygons": sum(d["has_polygon"].get(h, False) for h in hz)})
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
        hz = d["key_hazards"].get(key, [])
        rows.append({**base, "link_level": "hazard", "tornado_key": key, "n_tornadoes": 1,
                     "cited_ncei_ids": "|".join(sorted(c["ids"], key=int)),
                     "n_tornadoes_cited": len(cands),
                     "evidence": "|".join(k for k in ("prose", "infobox", "table_row")
                                          if k in c["evidence"]),
                     "table_match": info["match"], "how": how,
                     **{k: c[k] for k in ("date_ok", "state_ok", "place_ok", "rating_ok",
                                          "consistency")},
                     "strength": silver.strength(how, c),
                     "tornado_date": tor["date"], "tornado_rating": tor["rating"],
                     "tornado_states": "|".join(sorted(tor["states"])),
                     "se_event_ids": "|".join(tor["event_ids"]),
                     "dat_hazard_uids": "|".join(hz),
                     "n_dat_polygons": sum(d["has_polygon"].get(h, False) for h in hz),
                     "_places": places})
    return pd.DataFrame(rows), why


# ── news ─────────────────────────────────────────────────────────────────────
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
    for r in xref.itertuples():
        t = texts.get(r.lexis_textref_uid, {})
        items.append((r.lexis_textref_uid, "lexisnexis", [p for p in str(r.citing_passages).split("|") if p],
                      pd.Series({"title": t.get("title") or r.title, "url": r.url,
                                 "published_at": t.get("published") or r.lexis_date,
                                 "text": t.get("text", ""), "text_quality": "lexisnexis",
                                 "story_id": "", "story_primary": True})))
    rows, why = [], Counter()
    for uid, kind, citing, rec in items:
        base = {"text_uid": uid, "text_kind": kind, "unit_kind": "news", "title": rec.title,
                "url": rec.url, "published_at": str(rec.published_at or "")[:10],
                "text_quality": rec.text_quality, "story_id": rec.story_id,
                "story_primary": rec.story_primary, "citing_passages": "|".join(sorted(citing))}
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
            check = silver.news_checks(published=base["published_at"], event_date=tor["date"],
                                       text=rec.get("text") or "", places=places, counties=tor["counties"])
            hz = d["key_hazards"].get(key, [])
            rows.append({**base, "link_level": "hazard", "tornado_key": key, "n_tornadoes": 1,
                         "evidence": "cited_by_passage", "how": "inherited",
                         "n_citing_hazard_passages": len(usable),
                         "passage_strengths": "|".join(sorted(usable.strength)),
                         "days_after_event": check["days_after_event"],
                         "date_ok": check["date_ok"], "place_ok": check["mentions_place"],
                         "strength": silver.news_strength(usable.strength, check),
                         "tornado_date": tor["date"], "tornado_rating": tor["rating"],
                         "tornado_states": "|".join(sorted(tor["states"])),
                         "se_event_ids": "|".join(tor["event_ids"]),
                         "dat_hazard_uids": "|".join(hz),
                         "n_dat_polygons": sum(d["has_polygon"].get(h, False) for h in hz)})
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
                         "dat_hazard_uids": e.dat_hazard_uids, "n_dat_polygons": e.n_dat_polygons})
        else:
            why["news: no citing passage with a tornado or one outbreak"] += 1
    return pd.DataFrame(rows), why


# ── hand check ───────────────────────────────────────────────────────────────
SAMPLE_PLAN = {("wikipedia_passage", "strong"): 12, ("wikipedia_passage", "medium"): 10,
               ("wikipedia_passage", "weak"): 8, ("wikipedia_passage", "rejected"): 5,
               ("cited_news", "strong"): 20, ("cited_news", "medium"): 15,
               ("cited_news", "weak"): 15, ("lexisnexis", "strong"): 5,
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
    table["with a DAT polygon"] = hazard.assign(p=hazard.n_dat_polygons > 0) \
        .groupby("text_kind").p.sum()
    table["with any DAT hazard"] = hazard.assign(h=hazard.dat_hazard_uids != "") \
        .groupby("text_kind").h.sum()
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
        f"{hazard[hazard.n_dat_polygons > 0].tornado_key.nunique()} of them have a DAT damage polygon.",
        "",
        "**Strength** (`text.silver.strength`): *strong* — the passage names one tornado and its "
        "date (±1 day), state and a place agree with the Storm Events record; *medium* — one "
        "tornado, nothing disagrees, a place or the rating agrees; *weak* — nothing disagrees but "
        "little could be checked, or the tornado was chosen among several the passage cites; "
        "*rejected* — the date or state disagrees (kept for inspection, not for evaluation). "
        "A news article takes its weakest citing passage's strength, one step lower if it was "
        f"published before the event or more than {silver.NEWS_MAX_DAYS} days after, or names "
        "none of the tornado's places.",
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
        "no polygon here; SPC's track (stage 14's SPC part) would give it a line.",
        "4. **Storm Events dates are local standard time**; the date check allows ±1 day.",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    write_report(links, why + why_news, n_sheet, d)
    hazard = links[links.link_level == "hazard"]
    write_manifest(config.PROCESSED_DIR / "manifest_wikipedia_silver_links.json",
                   "44_wikipedia_silver_links",
                   counts={"links": len(links), "hazard_links": len(hazard),
                           **{f"{k}_{s}": int(v) for (k, s), v in
                              hazard.groupby(["text_kind", "strength"]).size().items()},
                           "handcheck_rows": n_sheet},
                   outputs=[SILVER_CSV])
    print(pd.crosstab(hazard.text_kind, hazard.strength).to_string())
    print(f"wrote {SILVER_CSV.name}, {REPORT.name}, {SHEET.name}")


if __name__ == "__main__":
    main()
