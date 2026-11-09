"""Inspection viewer for the retrieved Media Cloud full texts.

A second, smaller app beside the LexisNexis viewer, for the questions the
retrieval and labelling stages leave open and only a reader can settle:

* **Is this body the article?** Every quality flag is shown with the measure it
  was computed from, next to the text and links to the live page and the
  archived copy.
* **Which label is right?** The headline-only label (stage 30) and the
  full-text label (stage 34) sit side by side, and the body can be switched to
  exactly the evidence window the model saw.
* **Record the answer.** Single keystrokes store a verdict — whether the body
  is the article, and the label a reader would give — in
  ``data/interim/fulltext_inspection.csv``. Stage 34's ``compare`` reads it back.
  ``r`` draws a random article from the current filter and marks the verdict
  as randomly drawn, which is what makes an accuracy estimate from it valid.

The verdict file holds URL, headline and the verdict only, never body text.

    python scripts/viewer.py --corpus mediacloud      # http://127.0.0.1:8799
"""

from __future__ import annotations

import csv
import random
import threading
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from flask import Flask, jsonify, render_template, request

from .. import config
from ..text import fulltext, labelling
from ..text import fulltext_corpus as fc
from ..text import lexisnexis_filter as lf

HL, FT = fc.HL, fc.FT
_WRITE_LOCK = threading.Lock()


def _story_labels_path(tag: str | None):
    suffix = f"_{tag}" if tag else ""
    return config.PROCESSED_DIR / f"mediacloud_fulltext_story_labels{suffix}.csv"


def _clean(value: Any) -> Any:
    """JSON-safe scalars: NaN becomes None, numpy types become Python ones."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return value.item()
    return value


class FulltextStore:
    def __init__(self, tag: str | None = None):
        config.require_data(config.PROCESSED_DIR, fc.STORE)
        self.tag = tag
        print("loading the Media Cloud population and the full-text store…")
        population = fc.load_population()
        store = fulltext.load_store(fc.STORE)
        quality = fc.load_quality()
        if quality is None:
            print("  no quality table yet — scoring in memory (run "
                  "`scripts/33_fetch_fulltext.py quality` to make this instant)")
            quality = fulltext.quality_table(store, population)
        df = fc.load_bodies(store, population, quality)
        del store

        self.labels_path = _story_labels_path(tag)
        self.has_labels = self.labels_path.exists()
        if self.has_labels:
            labels = pd.read_csv(self.labels_path, keep_default_na=False, low_memory=False)
            ft_cols = [c for c in labels.columns if c.startswith(FT)]
            df = df.merge(labels[["url", *ft_cols]], on="url", how="left")
            for flag in [*lf.FLAGS, "parsed"]:
                col = FT + flag
                if col in df.columns:
                    df[col] = df[col].astype(str).str.lower().isin(("true", "1"))
            print(f"  full-text labels: {self.labels_path.name}")
        else:
            df[FT + "primary"] = ""
            print("  no full-text labels yet — run scripts/34_label_fulltext.py")
        df[FT + "primary"] = df[FT + "primary"].fillna("").astype(str)

        df = df.reset_index(drop=True)
        self.texts: list[str] = df.body.tolist()
        self.df = df.drop(columns=["body"])
        self.df["year"] = self.df.pub_date.astype(str).str[:4]
        self.df["shared"] = self.df.dup_count > 1
        self.haystack = (self.df.headline.astype(str) + " " + self.df.source.astype(str)
                         + " " + self.df.url.astype(str)).str.lower()
        self.siblings = self.df.groupby("body_key").groups

        self.verdicts: dict[str, dict] = {
            r["url"]: r for r in fc.load_inspections().to_dict("records")}
        print(f"  {len(self.df):,} retrieved articles, "
              f"{self.df.body_key.nunique():,} distinct bodies, "
              f"{len(self.verdicts):,} already inspected")

    # ── list ────────────────────────────────────────────────────────────────
    def facets(self) -> dict:
        d = self.df
        return {
            "total": len(d),
            "flags": [f for f in (*fulltext.HARD_FLAGS, *fulltext.SOFT_FLAGS)
                      if f in d.columns],
            "vias": sorted(v for v in d.via.unique() if v),
            "year_bands": sorted(d.year_band.astype(str).unique()),
            "labels": list(labelling.PRIMARY_LABELS),
            "has_labels": self.has_labels,
        }

    def _mask(self, a: dict) -> pd.Series:
        d = self.df
        m = pd.Series(True, index=d.index)
        if a.get("q"):
            m &= self.haystack.str.contains(a["q"].lower(), regex=False)
        quality = a.get("quality", "")
        if quality == "ok":
            m &= d.quality_ok
        elif quality == "fail":
            m &= ~d.quality_ok
        elif quality in d.columns:
            m &= d[quality].astype(bool)
        if a.get("via"):
            m &= d.via == a["via"]
        if a.get("year_band"):
            m &= d.year_band.astype(str) == a["year_band"]
        ft = a.get("ft", "")
        if ft == "unlabelled":
            m &= d[FT + "primary"] == ""
        elif ft:
            m &= d[FT + "primary"] == ft
        compare = a.get("compare", "")
        labelled = d[FT + "primary"] != ""
        if compare == "agree":
            m &= labelled & (d[HL + "primary"] == d[FT + "primary"])
        elif compare == "disagree":
            m &= labelled & (d[HL + "primary"] != d[FT + "primary"])
        if a.get("shared") == "yes":
            m &= d.shared
        inspected = d.url.isin(self.verdicts.keys())
        if a.get("inspected") == "yes":
            m &= inspected
        elif a.get("inspected") == "no":
            m &= ~inspected
        return m

    def _row(self, i: int) -> dict:
        r = self.df.loc[i]
        flags = [f for f in (*fulltext.HARD_FLAGS, *fulltext.SOFT_FLAGS)
                 if f in self.df.columns and bool(r[f])]
        v = self.verdicts.get(r.url, {})
        return {"id": int(i), "headline": r.headline, "source": r.source,
                "date": str(r.pub_date)[:10], "via": r.via, "n_words": int(r.n_words),
                "quality_ok": bool(r.quality_ok), "flags": flags,
                "hard": [f for f in flags if f in fulltext.HARD_FLAGS],
                "hl": r[HL + "primary"], "ft": r[FT + "primary"],
                "shared": int(r.dup_count) if r.dup_count > 1 else 0,
                "verdict": v.get("label") or v.get("body_verdict") or ""}

    def search(self, args: dict, offset: int = 0, limit: int = 60) -> dict:
        idx = self.df.index[self._mask(args)]
        if args.get("random"):
            if not len(idx):
                return {"total": 0, "rows": [], "random": None}
            pick = int(random.choice(list(idx)))
            return {"total": len(idx), "rows": [self._row(pick)], "random": pick}
        page = idx[offset:offset + limit]
        return {"total": len(idx), "rows": [self._row(int(i)) for i in page]}

    # ── one article ─────────────────────────────────────────────────────────
    def article(self, i: int) -> dict | None:
        if i not in self.df.index:
            return None
        r = self.df.loc[i]
        text = self.texts[i]
        # Unlabelled rows (e.g. failing a quality check) have no mode of their
        # own; show them the window stage 34 would use by default.
        mode = _clean(r.get(FT + "evidence_mode")) or "windows"
        evidence, _ = lf.render_evidence({"body": text}, str(mode))
        measures = {k: _clean(r.get(k)) for k in (
            "n_words", "n_mentions", "title_containment", "stopword_share",
            "boilerplate_share", "body_headlines", "n_states", "protected")}
        flags = {f: bool(r[f]) for f in (*fulltext.HARD_FLAGS, *fulltext.SOFT_FLAGS)
                 if f in self.df.columns}

        def labels(prefix: str, names) -> dict:
            out = {"primary": _clean(r.get(prefix + "primary")),
                   "conf": _clean(r.get(prefix + "conf"))}
            out["flags"] = [f for f in names if bool(r.get(prefix + f, False))]
            return out

        # A template page can sit under a thousand URLs; list a sample.
        others = [int(j) for j in self.siblings.get(r.body_key, []) if int(j) != i]
        siblings = [self._row(j) for j in others[:25]]
        return {
            **self._row(i),
            "url": r.url, "final_url": r.final_url, "page_title": r.page_title,
            # The archive's normal page (with its toolbar), not the raw `id_`
            # bytes the crawler fetches: this one is for a person to read.
            "archive_url": "https://web.archive.org/web/"
                           f"{str(r.pub_date)[:10].replace('-', '') or '2015'}/{r.url}",
            "year_band": str(r.year_band), "domain_size": str(r.domain_size),
            "retrieved_at": r.retrieved_at, "measures": measures, "quality_flags": flags,
            "headline_label": labels(HL, labelling.BASE_FLAGS),
            "fulltext_label": labels(FT, lf.FLAGS) if r[FT + "primary"] else None,
            "text": text, "evidence": evidence, "siblings": siblings, "n_siblings": len(others),
            "inspection": self.verdicts.get(r.url),
        }

    # ── verdicts ────────────────────────────────────────────────────────────
    def record(self, payload: dict) -> dict:
        i = int(payload["id"])
        r = self.df.loc[i]
        prior = self.verdicts.get(r.url, {})
        row = {
            "inspected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "url": r.url, "headline": r.headline,
            "body_verdict": payload.get("body_verdict", prior.get("body_verdict", "")),
            "label": payload.get("label", prior.get("label", "")),
            "note": str(payload.get("note", prior.get("note", "")))[:500],
            "via_random": bool(payload.get("via_random", prior.get("via_random", False))),
            "filter": str(payload.get("filter", prior.get("filter", "")))[:300],
        }
        if row["body_verdict"] and row["body_verdict"] not in fc.BODY_VERDICTS:
            raise ValueError(f"unknown body verdict {row['body_verdict']!r}")
        if row["label"] and row["label"] not in labelling.PRIMARY_LABELS:
            raise ValueError(f"unknown label {row['label']!r}")
        path = fc.INSPECTION_CSV
        with _WRITE_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            new = not path.exists()
            with path.open("a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=fc.INSPECTION_COLUMNS)
                if new:
                    w.writeheader()
                w.writerow(row)
            self.verdicts[r.url] = row
        return row


def create_fulltext_app(tag: str | None = None) -> Flask:
    app = Flask(__name__)
    store = FulltextStore(tag)

    @app.get("/")
    def index():
        return render_template("fulltext.html", facets=store.facets(), tag=tag,
                               inspection_file=fc.INSPECTION_CSV.name)

    @app.get("/api/articles")
    def api_articles():
        a = {k: request.args.get(k, "").strip() for k in (
            "q", "quality", "via", "year_band", "ft", "compare", "shared", "inspected",
            "random")}
        return jsonify(store.search(a, request.args.get("offset", 0, type=int),
                                    min(request.args.get("limit", 60, type=int), 200)))

    @app.get("/api/article/<int:i>")
    def api_article(i: int):
        article = store.article(i)
        if article is None:
            return jsonify({"error": "unknown article"}), 404
        return jsonify(article)

    @app.post("/api/verdict")
    def api_verdict():
        try:
            return jsonify(store.record(request.get_json(force=True)))
        except (KeyError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

    return app
