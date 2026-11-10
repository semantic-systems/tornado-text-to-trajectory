#!/usr/bin/env python
"""Browse the Wikipedia tables (stages 23–26) in the browser, with Datasette.

Loads the passages, the cited news, the citations between them, the
LexisNexis cross-reference, and the discovery tables into one SQLite file,
with full-text search on the texts, then serves it locally:

    python scripts/browse_wikipedia.py            # build (seconds) and serve
    python scripts/browse_wikipedia.py build      # only build the database
    python scripts/browse_wikipedia.py serve --port 8001

Open http://127.0.0.1:8001. Every table can be filtered by clicking a value,
the counts above a table are facets, and each row has a page with its full
text. The database lives in ``data/processed/`` next to its inputs and is not
in git: the cited news texts are copyrighted. Serve it on 127.0.0.1 only.

Needs ``datasette`` and ``sqlite-utils`` (see requirements.txt).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

import pandas as pd

import _bootstrap  # noqa: F401

from tornado_dataset import config

DB = config.PROCESSED_DIR / "wikipedia_browse.db"
METADATA = config.PROCESSED_DIR / "wikipedia_browse_metadata.json"

# table name → (source file, primary key, columns searched, facets, description)
TABLES = {
    "passages": (
        config.PROCESSED_DIR / "wikipedia_passages.jsonl", "textref_uid", ["title", "text"],
        ["unit_kind", "temporal_class", "derived_from_oracle"],
        "Stage 25: Wikipedia passages as text records (tornado articles, tornado "
        "sections of outbreak articles, outbreak overviews, US events on yearly pages)."),
    "cited_news": (
        config.PROCESSED_DIR / "wikipedia_cited_news.jsonl", "textref_uid", ["title", "text"],
        ["text_quality", "outlet_type", "retrieval_via"],
        "Stage 26: news articles cited by those pages and not in LexisNexis, with "
        "text_quality (is the fetched text the cited article?) and story groups."),
    "cited_news_citations": (
        config.PROCESSED_DIR / "wikipedia_cited_news_citations.csv", None, [],
        ["unit_kind", "link_level"],
        "Stage 26: which passage cites which news article (one row per pair), with "
        "the passage's event date and NCEI event ids."),
    "cited_in_lexisnexis": (
        config.PROCESSED_DIR / "wikipedia_cited_lexisnexis.csv", "article_key", ["title"],
        ["match_tiers", "outlet_type", "lexis_source"],
        "Stage 24/26: cited articles LexisNexis already holds, with the matching "
        "LexisNexis record."),
    "pages": (
        config.INTERIM_DIR / "wikipedia_pages.csv", "pageid", ["title"],
        ["kind", "scope", "year"],
        "Stage 23: every candidate page found, its kind and whether it is in scope."),
    "sections": (
        config.INTERIM_DIR / "wikipedia_sections.csv", None, ["heading"],
        ["section_type", "year", "us_basis"],
        "Stage 23: sections of outbreak and yearly pages and how they were classified."),
    "refs": (
        config.INTERIM_DIR / "wikipedia_refs.csv", None, ["title", "work"],
        ["ref_class", "page_kind", "domain"],
        "Stage 24: every reference on the in-scope pages."),
    "ref_matches": (
        config.INTERIM_DIR / "wikipedia_ref_matches.csv", None, ["lexis_headline"],
        ["tier", "outlet_match", "lexis_source"],
        "Stage 24: candidate LexisNexis matches per cited article, by tier."),
    "census": (
        config.INTERIM_DIR / "wikipedia_census.csv", None, ["location", "summary"],
        ["state", "rating", "year"],
        "Stage 23: rows of the 'List of … tornadoes' pages with NCEI ids. Lookup only, "
        "never text: the summaries paraphrase the NCEI narrative."),
}
# Shown as the link text for a row, and moved to the end of the table view.
LABELS = {"passages": "title", "cited_news": "title", "pages": "title"}
LONG = ("text", "summary")
FOREIGN_KEYS = [
    ("cited_news_citations", "textref_uid", "cited_news", "textref_uid"),
    ("cited_news_citations", "passage_uid", "passages", "textref_uid"),
]


def _frame(path) -> pd.DataFrame:
    if path.suffix == ".jsonl":
        frame = pd.read_json(path, lines=True, dtype=False)
    else:
        frame = pd.read_csv(path, keep_default_na=False, low_memory=False)
    for column in frame.columns:
        if frame[column].map(lambda v: isinstance(v, (list, dict))).any():
            frame[column] = frame[column].map(lambda v: json.dumps(v, ensure_ascii=False))
    # The long text last, so the table view stays readable.
    return frame[[c for c in frame.columns if c not in LONG]
                 + [c for c in frame.columns if c in LONG]]


def build() -> None:
    import sqlite_utils

    for path, *_ in TABLES.values():
        config.require_data(path)
    DB.unlink(missing_ok=True)
    db = sqlite_utils.Database(DB)
    for name, (path, pk, search, _, _) in TABLES.items():
        frame = _frame(path).drop(columns=["section_spans"], errors="ignore")
        records = frame.astype(object).where(frame.notna(), None).to_dict("records")
        db[name].insert_all(records, pk=pk, batch_size=500)
        if search:
            db[name].enable_fts(search, tokenize="porter")
        print(f"  {name:22s} {len(frame):7,} rows")
    for table, column, other, other_column in FOREIGN_KEYS:
        db[table].add_foreign_key(column, other, other_column)
    db.index_foreign_keys()

    metadata = {
        "title": "Tornado text-to-trajectory: Wikipedia tables",
        "description": "Stages 23–26. Local only: the cited news texts are copyrighted.",
        "license": "Wikipedia text: CC BY-SA 4.0; news text: copyright of the publishers",
        "databases": {DB.stem: {"tables": {
            name: {"description": description, "facets": facets,
                   **({"label_column": LABELS[name]} if name in LABELS else {})}
            for name, (_, _, _, facets, description) in TABLES.items()}}},
    }
    METADATA.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"wrote {DB} ({DB.stat().st_size / 1e6:.0f} MB)")


def serve(port: int) -> None:
    if not DB.exists():
        build()
    print(f"\n  Wikipedia tables → http://127.0.0.1:{port}/{DB.stem}\n")
    subprocess.run([sys.executable, "-m", "datasette", "serve", str(DB),
                    "--metadata", str(METADATA), "--host", "127.0.0.1", "--port", str(port),
                    "--setting", "truncate_cells_html", "300",
                    "--setting", "default_facet_size", "15"], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", default="all", choices=["all", "build", "serve"])
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    if args.command in ("all", "build"):
        build()
    if args.command in ("all", "serve"):
        serve(args.port)


if __name__ == "__main__":
    main()
