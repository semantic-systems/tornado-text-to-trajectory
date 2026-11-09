#!/usr/bin/env python
"""Stage 23 — import the LexisNexis Uni full-text exports.

LexisNexis Uni has no API for this corpus: the articles were exported by hand as
RTF files into ``data/lexis_nexis_tornado_news/`` (``config.LEXISNEXIS_EXPORT_DIR``).
This stage parses them (:mod:`tornado_dataset.text.lexisnexis`) into one row per
article — headline, source, dates, byline, section, body and metadata — and flags
verbatim duplicates, which the export repeats where download batches overlapped.

    python scripts/23_import_lexisnexis.py
    python scripts/23_import_lexisnexis.py --input /path/to/rtf --format jsonl

Writes ``outputs/lexisnexis_articles.{csv,jsonl}`` (gitignored: they hold article
text, kept locally for text and data mining under §60d UrhG) and a manifest in
``data/interim/``. Stages 31, 32, 40, 42 and 43 read the JSONL. Offline.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from tornado_dataset import config
from tornado_dataset.ids import write_manifest
from tornado_dataset.text import lexisnexis as ln


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", type=Path, default=config.LEXISNEXIS_EXPORT_DIR,
                   help="directory with LexisNexis RTF files")
    p.add_argument("--output-dir", type=Path, default=config.OUTPUT_DIR)
    p.add_argument("--format", choices=("csv", "jsonl", "both"), default="both")
    args = p.parse_args()

    if not args.input.exists():
        config.require_data((args.input,))
    print(f"parsing {args.input} …")
    articles = ln.parse_directory(args.input)
    if not articles:
        raise SystemExit(f"no RTF files found in {args.input}")
    df = ln.add_duplicate_flags(ln.to_dataframe(articles))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    if args.format in ("csv", "both"):
        written.append(args.output_dir / f"{ln.OUTPUT_STEM}.csv")
        df.to_csv(written[-1], index=False)
    if args.format in ("jsonl", "both"):
        written.append(args.output_dir / f"{ln.OUTPUT_STEM}.jsonl")
        df.to_json(written[-1], orient="records", lines=True, force_ascii=False,
                   date_format="iso")

    # The reported word count is a free consistency check on the parse.
    reported = df["length_words"]
    off = ((df["n_words"] - reported).abs() > 0.1 * reported).fillna(False)
    counts = {
        "articles": len(df), "sources": int(df["source"].nunique()),
        "first_pub_date": f"{df['pub_date'].min():%Y-%m-%d}",
        "last_pub_date": f"{df['pub_date'].max():%Y-%m-%d}",
        "missing_date": int(df["pub_date"].isna().sum()),
        "empty_body": int((df["n_words"] == 0).sum()),
        "word_count_off_10pct": int(off.sum()),
        "verbatim_duplicates": int(df["is_duplicate"].sum()),
        "rows_with_warnings": int((df["warnings"] != "").sum()),
    }
    write_manifest(config.INTERIM_DIR / "manifest_lexisnexis_import.json",
                   "23_import_lexisnexis", counts=counts, outputs=written)
    print(f"\n{counts['articles']:,} articles | {counts['sources']:,} sources | "
          f"{counts['first_pub_date']} to {counts['last_pub_date']}\n"
          f"missing date: {counts['missing_date']:,}, empty body: {counts['empty_body']:,}, "
          f"word count off by >10%: {counts['word_count_off_10pct']:,}, "
          f"verbatim duplicates: {counts['verbatim_duplicates']:,}, "
          f"rows with warnings: {counts['rows_with_warnings']:,}")
    for path in written:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
