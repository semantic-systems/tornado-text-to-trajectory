#!/usr/bin/env python
"""Stage 26 — the names the official records give each tornado.

Collects, per hazard, the labels of two official sources
(:mod:`tornado_dataset.text.names`): the heading of the storm-survey section
that is the hazard's primary survey (stage 20; structured statements only) and
DAT's free-text ``event_id`` (stage 12). Each is kept as written, cleaned
(rating, counter, date and "tornado" dropped), classed as a name or a code, and
checked against the places near the track: a GNIS populated place within
50 km or a county the track crosses (stage 16). One label per hazard is
preferred: a name that matches a place or that the other source agrees with;
the one most labels agree with, a survey heading before DAT's.

Storm Events narratives are not used (few and noisy "the X tornado" phrases),
nor names from outside the official record (media, Wikipedia).

    python scripts/26_collect_names.py

Offline. Needs stages 12, 15, 16 and 20. Writes
``data/processed/hazard_names_<tag>.csv`` (one row per label, ``is_preferred`` on
one per hazard) and a manifest.
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

import pandas as pd

from tornado_dataset import config, handcheck
from tornado_dataset.dat import episode_table
from tornado_dataset.geo.gazetteer import PlaceIndex, alias_forms
from tornado_dataset.ids import write_manifest
from tornado_dataset.text import names


def names_path(tag: str):
    return config.PROCESSED_DIR / f"hazard_names_{tag}.csv"


def main() -> None:
    default_tag = f"{config.WINDOW_START.isoformat()}_{config.WINDOW_END.isoformat()}"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=default_tag)
    args = parser.parse_args()
    tag, P = args.tag, config.PROCESSED_DIR

    needed = {P / f"hazards_{tag}.csv": "12_build_hazards",
              episode_table.membership_path(tag): "15_build_episodes",
              P / f"hazard_geography_{tag}.csv": "16_enrich_geography",
              P / f"textrefs_nws_{tag}.csv": "20_fetch_nws_text",
              P / f"textlinks_nws_{tag}.csv": "20_fetch_nws_text"}
    for path, stage in needed.items():
        if not path.exists():
            raise SystemExit(f"no {path.name} — run scripts/{stage}.py")

    dat = pd.read_csv(P / f"hazards_{tag}.csv", usecols=["hazard_uid", "dat_event_ids"])
    links = pd.read_csv(P / f"textlinks_nws_{tag}.csv", low_memory=False)
    texts = pd.read_csv(P / f"textrefs_nws_{tag}.csv", low_memory=False,
                        usecols=["textref_uid", "source_type", "title", "survey_format"])
    primary = links[links.link_relation == "primary_survey_of"][["textref_uid", "target_uid"]]
    sections = (primary.merge(texts[(texts.source_type == "pns")
                                    & (texts.survey_format == "structured")],
                              on="textref_uid")
                .rename(columns={"target_uid": "hazard_uid"}))
    cands = names.candidates(dat, sections[["hazard_uid", "textref_uid", "title"]])

    # The places a label may name: GNIS populated places near the track, and the
    # counties it crosses (stage 16), in every spelling an office might use.
    hz = handcheck.load_hazards(tag).set_index("hazard_uid")
    geo = pd.read_csv(P / f"hazard_geography_{tag}.csv", usecols=["hazard_uid", "counties"]
                      ).set_index("hazard_uid").counties
    index = PlaceIndex()
    place_keys = {}
    for uid in cands.hazard_uid.unique():
        keys = set()
        if uid in hz.index:
            for place in index.nearby(hz.proj[uid], names.PLACE_RADIUS_M, limit=10_000):
                keys |= alias_forms(place["name"])
        for county in str(geo.get(uid) or "").split(";"):
            county = county.split(",")[0].strip()
            if county and county.lower() != "nan":
                keys |= alias_forms(county)
        place_keys[uid] = keys
    table = names.annotate(cands, place_keys)
    table.drop(columns="name_key").to_csv(names_path(tag), index=False)

    member = episode_table.membership(tag)
    preferred = table[table.is_preferred]
    by_source = {s: {"labels": int((table.source == s).sum()),
                     "hazards": int(table.hazard_uid[table.source == s].nunique()),
                     "names": int(((table.source == s) & (table.name_kind == "name")).sum()),
                     "place_match": int(((table.source == s) & table.place_match).sum()),
                     "preferred": int((preferred.source == s).sum())}
                 for s in names.SOURCES}
    both = table[table.name_kind == "name"].groupby("hazard_uid").source.nunique()
    both = both[both == 2].index
    agree = 0
    for uid in both:
        rows = table[(table.hazard_uid == uid) & (table.name_kind == "name")]
        a = rows.name_key[rows.source == "pns_section"]
        b = rows.name_key[rows.source == "dat_event_id"]
        agree += any(names._agrees(x, y) for x in a for y in b)
    counts = {
        "labels": len(table), "hazards_with_label": int(table.hazard_uid.nunique()),
        "hazards_with_preferred_name": len(preferred),
        "hazards": len(member),
        "preferred_by_hazard_source": preferred.merge(
            member[["hazard_uid", "hazard_source"]], on="hazard_uid"
        ).hazard_source.value_counts().to_dict(),
        "by_source": by_source,
        "hazards_named_by_both_sources": len(both), "both_sources_agree": int(agree),
        "place_radius_m": names.PLACE_RADIUS_M,
    }
    write_manifest(P / f"manifest_names_{tag}.json", "26_collect_names", counts=counts,
                   outputs=[names_path(tag)])
    print(f"{len(table):,} labels on {counts['hazards_with_label']:,} hazards; a preferred "
          f"name for {len(preferred):,} of {len(member):,} hazards")
    for s, c in by_source.items():
        print(f"  {s}: {c['labels']:,} labels on {c['hazards']:,} hazards, {c['names']:,} "
              f"names, {c['place_match']:,} match a place, {c['preferred']:,} preferred")
    print(f"  named by both sources: {len(both):,}, agreeing {agree:,}")
    print(f"wrote {names_path(tag)}")


if __name__ == "__main__":
    main()
