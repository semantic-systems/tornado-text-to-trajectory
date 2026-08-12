"""Read LexisNexis full-text RTF exports into a structured table.

Python counterpart to the R package ``LexisNexisTools``
(https://jbgruber.r-universe.dev/LexisNexisTools): each RTF file delivered by
LexisNexis Uni is converted to plain text with :mod:`striprtf` and then split
into its documented parts::

    <headline>
    <source / publication>            [+ edition lines]
    <publication date> [weekday] [time zone]
    <copyright lines>
    Label:<nbsp><value>               Length, Byline, Section, Dateline, ...
    Body
    <article paragraphs>
    Graphic / Notes / Classification  (optional trailing sections)
    Load-Date:<nbsp><date>
    End of Document

The public API is deliberately small::

    article  = parse_file(path)                # -> Article
    articles = parse_directory(directory)      # -> list[Article]
    df       = to_dataframe(articles)          # -> pandas.DataFrame
    df       = add_duplicate_flags(df)         # -> + dup_group / is_duplicate

Run as a script, it parses ``data/lexis_nexis_tornado_news`` and writes
``outputs/lexisnexis_articles.{csv,jsonl}``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd
from striprtf.striprtf import rtf_to_text

# ── paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_DIR = REPO_ROOT / "data" / "lexis_nexis_tornado_news"
OUTPUT_DIR = REPO_ROOT / "outputs"
OUTPUT_STEM = "lexisnexis_articles"

# ── document structure ───────────────────────────────────────────────────────
# The language of the LexisNexis UI leaks into the export (the German interface
# ends documents with "Ende des Dokuments"), so markers are kept as sets.
BODY_MARKERS = {"Body", "Haupttext", "Corps"}
END_MARKERS = {"End of Document", "Ende des Dokuments", "Fin du document"}
# Optional sections between body and Load-Date, in the order LexisNexis emits them.
TRAILING_SECTIONS = ("Graphic", "Notes", "Classification")

# ``Label:<nbsp>value`` — LexisNexis separates label and value with a no-break
# space, which keeps metadata lines distinguishable from colons in the text.
LABEL_RE = re.compile(r"^([A-Za-z][\w \-/]{0,30}):\xa0\s*(.*)$")

MONTHS = ("January February March April May June July August September "
          "October November December").split()
DATE_RE = re.compile(
    r"^(?P<month>" + "|".join(MONTHS) + r")\s+"
    r"(?:(?P<day>\d{1,2}),\s*)?"            # no day on monthly editions
    r"(?P<year>\d{4})\b(?P<rest>.*)$"
)
WEEKDAY_RE = re.compile(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b")
TIME_RE = re.compile(r"\b(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?(?:\s+[A-Z]{2,5})?)")
LENGTH_RE = re.compile(r"(\d[\d,.]*)\s*(?:words|Wörter|mots)", re.IGNORECASE)
COPYRIGHT_RE = re.compile(r"copyright|all rights reserved|©", re.IGNORECASE)

# Placeholders left where the online article had a hyperlink or an image.
LINK_PLACEHOLDERS = {
    "Link to Image", "Link to Story", "Link to Video", "Link to Graphic",
    "Link to the original story.", "Link to the original article.",
}

# Labels that get their own column; every other label lands in ``meta``.
KNOWN_FIELDS = {
    "Section": "section",
    "Byline": "byline",
    "Dateline": "dateline",
    "Highlight": "highlight",
    "Load-Date": "load_date_raw",
    "Subject": "subject",
    "Company": "company",
    "Industry": "industry",
    "Geographic": "geographic",
}

# ── text cleaning ────────────────────────────────────────────────────────────
# Numeric character references that lost their "&" upstream ("#8217;").
ENTITY_RE = re.compile(r"&?#(\d{2,5});")
# UTF-8 bytes that were decoded as cp1252 somewhere upstream ("BeyoncÃ©").
MOJIBAKE_RE = re.compile(r"[\xc2-\xc3][\x80-\xbf]")


def _fix_mojibake(text: str) -> str:
    """Best-effort repair of double-encoded UTF-8, applied per occurrence."""
    def repair(match: re.Match[str]) -> str:
        try:
            return match.group(0).encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return match.group(0)
    return MOJIBAKE_RE.sub(repair, text)


def _norm(text: str) -> str:
    """Normalise a field value or paragraph: no-break spaces, runs of blanks."""
    return re.sub(r"[ \t\xa0]+", " ", text).strip()


def rtf_to_lines(path: Path) -> list[str]:
    """Convert one RTF file into a list of cleaned, non-empty text lines.

    No-break spaces are *kept* here because they carry the ``Label:`` structure;
    they are removed later by :func:`_norm` when a value is stored.
    """
    # The exports are pure ASCII: every non-ASCII character is an RTF escape.
    text = rtf_to_text(path.read_text(encoding="ascii", errors="ignore"), errors="ignore")
    text = ENTITY_RE.sub(lambda m: chr(int(m.group(1))), text)
    text = unicodedata.normalize("NFC", _fix_mojibake(text))
    text = text.replace("\u2028", "\n").replace("\u2029", "\n").replace("\r", "")
    return [line.strip() for line in text.split("\n") if line.strip()]


# ── data model ───────────────────────────────────────────────────────────────
@dataclass
class Article:
    """One LexisNexis document."""

    file: str
    headline: str = ""
    source: str = ""
    pub_date: date | None = None
    pub_date_raw: str = ""
    weekday: str = ""
    pub_time: str = ""
    edition: str = ""
    copyright: str = ""
    section: str = ""
    byline: str = ""
    dateline: str = ""
    highlight: str = ""
    length_words: int | None = None   # word count as reported by LexisNexis
    body: str = ""                    # paragraphs joined by a blank line
    n_paragraphs: int = 0
    n_words: int = 0                  # word count of the extracted body
    graphic: str = ""
    notes: str = ""
    subject: str = ""
    company: str = ""
    industry: str = ""
    geographic: str = ""
    load_date_raw: str = ""
    load_date: date | None = None
    meta: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def paragraphs(self) -> list[str]:
        return self.body.split("\n\n") if self.body else []


# ── parsing ──────────────────────────────────────────────────────────────────
def _parse_date(text: str) -> tuple[date | None, str, str, bool]:
    """Split a LexisNexis date line into date, weekday, time and day precision.

    Monthly editions carry no day of month ("May 2024 1:00 PM EST"); the date is
    then set to the first of the month and flagged via the returned ``day_known``.
    """
    match = DATE_RE.match(_norm(text))
    if not match:
        return None, "", "", False
    parsed = date(int(match.group("year")),
                  MONTHS.index(match.group("month")) + 1,
                  int(match.group("day") or 1))
    rest = match.group("rest")
    weekday = WEEKDAY_RE.search(rest)
    time = TIME_RE.search(rest)
    return (parsed,
            weekday.group(1) if weekday else "",
            time.group(1) if time else "",
            match.group("day") is not None)


def _split_document(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Split the lines of one document into (header, body, trailer)."""
    end_idx = next((i for i, l in enumerate(lines) if l in END_MARKERS), len(lines))
    body_idx = next((i for i, l in enumerate(lines[:end_idx]) if l in BODY_MARKERS), None)
    if body_idx is None:  # no body marker — treat everything after line 1 as body
        return lines[:1], lines[1:end_idx], []

    # Search the optional sections from the back, so that a stray "Notes" or
    # "Graphic" line inside the article text cannot cut the body short.
    candidates = [end_idx]
    for marker in TRAILING_SECTIONS:
        idx = next((i for i in range(end_idx - 1, body_idx, -1) if lines[i] == marker), None)
        if idx is not None:
            candidates.append(idx)
    idx = next((i for i in range(end_idx - 1, body_idx, -1)
                if (m := LABEL_RE.match(lines[i])) and m.group(1) == "Load-Date"), None)
    if idx is not None:
        candidates.append(idx)
    trailer_idx = min(candidates)
    return lines[:body_idx], lines[body_idx + 1:trailer_idx], lines[trailer_idx:end_idx]


def _assign_field(article: Article, label: str, value: str) -> None:
    """Store a ``Label: value`` pair in its column, or in ``meta`` if unknown."""
    value = _norm(value)
    if label == "Length":
        match = LENGTH_RE.search(value)
        article.length_words = int(re.sub(r"[,.]", "", match.group(1))) if match else None
    elif label in KNOWN_FIELDS:
        attribute = KNOWN_FIELDS[label]
        setattr(article, attribute, f"{getattr(article, attribute)} {value}".strip())
    else:
        article.meta[label] = value


def _parse_header(header: list[str], article: Article) -> None:
    """Headline, source, date, copyright/edition lines and labelled fields."""
    if not header:
        article.warnings.append("empty header")
        return
    article.headline = _norm(header[0])

    date_idx = next((i for i, l in enumerate(header[1:], 1) if DATE_RE.match(_norm(l))), None)
    if date_idx is None:
        article.warnings.append("no publication date found")
        article.source = _norm(header[1]) if len(header) > 1 else ""
        rest = header[2:]
    else:
        article.source = " | ".join(_norm(l) for l in header[1:date_idx])
        article.pub_date_raw = _norm(header[date_idx])
        (article.pub_date, article.weekday,
         article.pub_time, day_known) = _parse_date(header[date_idx])
        if not day_known:
            article.warnings.append("no day of month; date set to the 1st")
        rest = header[date_idx + 1:]

    editions, copyrights = [], []
    for line in rest:
        match = LABEL_RE.match(line)
        if match:
            _assign_field(article, match.group(1), match.group(2))
        elif COPYRIGHT_RE.search(line):
            copyrights.append(_norm(line))
        else:
            editions.append(_norm(line))
    article.copyright = " ".join(copyrights)
    article.edition = " | ".join(editions)


def _parse_trailer(trailer: list[str], article: Article) -> None:
    """Optional Graphic / Notes / Classification sections and Load-Date."""
    section, buffers = None, {}
    for line in trailer:
        if line in TRAILING_SECTIONS:
            section = line.lower()
        elif match := LABEL_RE.match(line):
            section = None
            _assign_field(article, match.group(1), match.group(2))
        elif section:
            buffers.setdefault(section, []).append(_norm(line))
    article.graphic = "\n".join(buffers.get("graphic", []))
    article.notes = "\n".join(buffers.get("notes", []))
    if article.load_date_raw:
        article.load_date = _parse_date(article.load_date_raw)[0]


def parse_lines(lines: list[str], name: str = "") -> Article:
    """Parse one already-converted document (list of non-empty text lines)."""
    article = Article(file=name)
    header, body, trailer = _split_document(lines)
    _parse_header(header, article)
    _parse_trailer(trailer, article)

    paragraphs = [_norm(l) for l in body if l not in LINK_PLACEHOLDERS]
    article.body = "\n\n".join(paragraphs)
    article.n_paragraphs = len(paragraphs)
    article.n_words = len(article.body.split())
    if not paragraphs:
        article.warnings.append("empty body")
    return article


def parse_file(path: str | Path) -> Article:
    """Parse a single LexisNexis RTF file."""
    path = Path(path)
    return parse_lines(rtf_to_lines(path), name=path.name)


def parse_directory(directory: str | Path, recursive: bool = True,
                    progress: bool = True) -> list[Article]:
    """Parse every ``.rtf`` file in ``directory`` (case-insensitive suffix)."""
    directory = Path(directory)
    files = sorted(p for p in directory.glob("**/*" if recursive else "*")
                   if p.is_file() and p.suffix.lower() == ".rtf")
    articles = []
    for i, path in enumerate(files, 1):
        try:
            articles.append(parse_file(path))
        except Exception as exc:  # keep going; record the failure on the row
            articles.append(Article(file=path.name, warnings=[f"parse error: {exc!r}"]))
        if progress and (i % 100 == 0 or i == len(files)):
            print(f"  parsed {i}/{len(files)} files", file=sys.stderr)
    return articles


def textref_uid(row: dict) -> str:
    """Stable identifier for one LexisNexis article.

    File name and headline are **not** enough: LexisNexis exports every episode of
    a programme under one title, so 3,402 of the downloaded files share a name and
    keying on those alone merged 5,774 distinct articles. The publication date and
    a body hash pin it down. Two byte-identical copies of the same article — 14% of
    the export, from overlapping download batches — deliberately share an id.

    Every consumer must import this rather than recompute it; the linker, the
    overlap study and the viewer all have to agree on which article is which.
    """
    from ..ids import uid

    body = str(row.get("body") or "")
    return uid("textref", "lexisnexis", row.get("file", ""), row.get("headline", ""),
               str(row.get("pub_date") or ""),
               hashlib.sha1(body.encode("utf-8")).hexdigest()[:12])


def add_duplicate_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Group articles whose text is identical after normalisation.

    Wire copy (AP, AFP, Reuters …) is re-published verbatim by several outlets,
    so a LexisNexis download always contains near-identical documents. This is
    the cheap, exact variant of ``LexisNexisTools::lnt_similarity``: it catches
    verbatim re-runs but not lightly edited ones.
    """
    key = df["body"].str.lower().str.replace(r"\W+", " ", regex=True).str.strip()
    df = df.copy()
    df["dup_group"] = key.factorize()[0]
    df["is_duplicate"] = key.duplicated(keep="first") & (key != "")
    return df


def to_dataframe(articles: list[Article]) -> pd.DataFrame:
    """Turn parsed articles into a DataFrame (``meta``/``warnings`` flattened)."""
    df = pd.DataFrame([asdict(a) for a in articles])
    df["meta"] = df["meta"].map(lambda d: json.dumps(d, ensure_ascii=False) if d else "")
    df["warnings"] = df["warnings"].map("; ".join)
    for column in ("pub_date", "load_date"):
        df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


# ── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", nargs="?", type=Path, default=INPUT_DIR,
                        help=f"directory with LexisNexis RTF files (default: {INPUT_DIR})")
    parser.add_argument("-o", "--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("-f", "--format", choices=("csv", "jsonl", "both"), default="both")
    args = parser.parse_args()

    print(f"Parsing {args.input} ...", file=sys.stderr)
    articles = parse_directory(args.input)
    if not articles:
        sys.exit(f"No RTF files found in {args.input}")
    df = add_duplicate_flags(to_dataframe(articles))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.format in ("csv", "both"):
        df.to_csv(args.output_dir / f"{OUTPUT_STEM}.csv", index=False)
    if args.format in ("jsonl", "both"):
        df.to_json(args.output_dir / f"{OUTPUT_STEM}.jsonl", orient="records",
                   lines=True, force_ascii=False, date_format="iso")

    # ── summary: the reported word count is a free consistency check ──
    reported = df["length_words"]
    off = ((df["n_words"] - reported).abs() > 0.1 * reported).fillna(False)
    print(
        f"\n{len(df)} articles | {df['source'].nunique()} sources | "
        f"{df['pub_date'].min():%Y-%m-%d} to {df['pub_date'].max():%Y-%m-%d}\n"
        f"missing date: {df['pub_date'].isna().sum()}, "
        f"empty body: {(df['n_words'] == 0).sum()}, "
        f"word count off by >10%: {int(off.sum())}, "
        f"verbatim duplicates: {int(df['is_duplicate'].sum())}, "
        f"rows with warnings: {(df['warnings'] != '').sum()}\n"
        f"written to {args.output_dir / OUTPUT_STEM}.*",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
