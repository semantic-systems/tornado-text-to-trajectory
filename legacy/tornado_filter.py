"""
SUPERSEDED — kept for reference only.

The Media Cloud rewrite of this cascade lives in
``src/tornado_dataset/text/mediacloud.py``, driven by
``scripts/18_filter_media_cloud.py``. It differs in ways that matter: it works
from headline + URL rather than headline + lead, classifies once per distinct
headline and propagates to syndicated copies, encodes the reviewed protect/demote
keyword rules, and talks to a locally hosted vLLM server instead of a ``host.llm``
callable. The validation figures quoted below were measured on the LexisNexis
corpus with a lead paragraph available, and do **not** transfer to headlines.

tornado_filter.py — scalable filter to keep only news articles reporting ACTUAL
tornado events, from LexisNexis-style metadata (headline + lead paragraph).

Designed for a seed-train-apply cascade that scales to ~200k articles while
sending only a small fraction to an LLM:

  Stage A  cheap rules   -> drop obvious non-events (NONMET / FAKE / pure PROSPECTIVE)
  Stage B  TF-IDF+LogReg -> trained ONCE on an LLM-labeled seed, applied for free
  Stage C  LLM adjudication -> only for the low-confidence abstain band

The only column strictly required is the headline+lead text (LexisNexis "Hlead").
Publication date and length are used as weak features/tie-breakers.

Validated on a 526-article LLM-labeled reference (this project):
  Stage A rules-only  : P=0.91 R=0.74 F=0.81  (0 LLM calls)
  Stage B TF-IDF+LR   : P=0.87 R=0.95 F=0.91  (0 LLM calls/article after seed)
  Stage B + abstain   : ~97% auto-accuracy sending only ~21% to Stage C
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Stage A — cheap, transparent regex rules over headline+lead text
# ----------------------------------------------------------------------------
NONMET = re.compile(r'\b(honda|yamaha|suzuki|kawasaki|motorcycle|xr\s?\d|'
    r'\bband\b|album|song|film|movie|roller ?coaster|slot|casino|'
    r'tornado cash|crypto|\bpotato\b|nerf|video ?game|mixer|blender)\b', re.I)
PROSPECTIVE = re.compile(r'\b(watch(es)? issued|warning issued|could (hit|impact|bring)|'
    r'threat|risk of|braces? for|bracing for|forecast|expected to|may (bring|hit)|'
    r'potential for|outlook|be on alert|prepare for|map shows where)\b', re.I)
EVENT_POS = re.compile(r'\b(touched? down|ripped through|tore through|'
    r'damage(d)?|destroyed|killed|injured|fatalit|casualt|leveled|flattened|'
    r'aftermath|clean-?up|recovery|rebuild|survey|ef-?\d|ef ?\d|confirmed (a |an )?tornado|'
    r'struck|hit by|swept through|homes? (were )?(damaged|destroyed)|state of emergency)\b', re.I)
OUTBREAK = re.compile(r'\b(outbreak|multiple tornado|several tornado|\d+\s+tornado(es)?|'
    r'tornado(es)?\s+(touch|confirm|report)|swarm|spate)\b', re.I)
FAKE = re.compile(r'\b(fact[\s-]?check|debunk|digitally generated|ai[-\s]generated|'
    r'miscaption|misleading|deepfake|purported|falsely)\b', re.I)


def rule_label(text: str) -> str:
    """Return one of EVENT / PROSPECTIVE / NONMET / FAKE / UNSURE."""
    h = str(text)
    if FAKE.search(h):
        return "FAKE"
    if NONMET.search(h) and not EVENT_POS.search(h):
        return "NONMET"
    ev, pr = bool(EVENT_POS.search(h)), bool(PROSPECTIVE.search(h))
    if ev:                       # past-tense damage wins even if a forecast is co-mentioned
        return "EVENT"
    if pr:
        return "PROSPECTIVE"
    return "UNSURE"              # no strong signal -> defer to Stage B/C


def is_outbreak(text: str) -> bool:
    return bool(OUTBREAK.search(str(text)))


# ----------------------------------------------------------------------------
# Stage B — TF-IDF + logistic regression, trained on an LLM-labeled seed
# ----------------------------------------------------------------------------
def train_event_classifier(texts, labels_event_bool, C: float = 4.0):
    """Fit TF-IDF+LogReg EVENT detector on a seed set. labels are booleans."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2),
                                  min_df=2, max_features=20000, stop_words="english")),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", C=C)),
    ])
    pipe.fit(np.asarray(texts), np.asarray(labels_event_bool))
    return pipe


def classify_with_abstain(pipe, texts, lo: float = 0.30, hi: float = 0.70):
    """Return (pred_bool, proba, needs_llm_bool). Rows with lo<=p<hi abstain."""
    proba = pipe.predict_proba(np.asarray(texts))[:, 1]
    pred = proba >= 0.5
    needs_llm = (proba >= lo) & (proba < hi)
    return pred, proba, needs_llm


# ----------------------------------------------------------------------------
# Stage C — LLM adjudication (only the abstain band). Requires host.llm.
# ----------------------------------------------------------------------------
LLM_PROMPT = (
 'Label this news headline+lead for a tornado dataset. One category:\n'
 'EVENT=a tornado ACTUALLY occurred (touchdown/damage/casualties/aftermath/survey/EF rating).\n'
 'PROSPECTIVE=only forecast/watch/warning/risk, none occurred yet.\n'
 'MENTION=peripheral (sports, metaphor, event delayed by storm, "tornado alley" explainer, preparedness, law).\n'
 'NONMET="tornado" is a product/band/film/company name.\n'
 'FAKE=fact-check/debunk of fake/AI/miscaptioned tornado imagery.\n'
 'is_outbreak=true only if MULTIPLE tornadoes/named outbreak.\n'
 'JSON only: {"cat":"...","is_outbreak":bool,"conf":0-1}\n\nTEXT: ')


def llm_label_batch(host, texts, max_per_batch: int = 400, max_concurrency: int = 12):
    """Adjudicate a list of texts via host.llm. Returns list of category strings."""
    import json
    reqs = [{"prompt": LLM_PROMPT + str(t)[:500], "max_tokens": 40} for t in texts]
    out = []
    for i in range(0, len(reqs), max_per_batch):
        out += host.llm(reqs[i:i + max_per_batch], max_concurrency=max_concurrency)
    cats = []
    for r in out:
        if "error" in r:
            cats.append(None); continue
        try:
            m = re.search(r"\{.*\}", r["text"], re.S)
            cats.append(json.loads(m.group(0)).get("cat"))
        except Exception:
            cats.append(None)
    return cats


# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------
def run_cascade(df, text_col="Hlead", pipe=None, host=None,
                use_llm_on_abstain=True, lo=0.30, hi=0.70):
    """
    Full filter over a dataframe. Returns df with columns:
      rule, stageB_pred, stageB_proba, needs_llm, final_cat, is_event, is_outbreak
    - Stage A rules run always.
    - If `pipe` given, Stage B runs on rule==UNSURE (and refines others).
    - If host given and use_llm_on_abstain, Stage C runs on the abstain band.
    """
    d = df.copy()
    txt = d[text_col].astype(str)
    d["rule"] = txt.map(rule_label)
    d["is_outbreak"] = txt.map(is_outbreak)

    d["final_cat"] = d["rule"]
    if pipe is not None:
        pred, proba, needs = classify_with_abstain(pipe, txt.values, lo, hi)
        d["stageB_pred"] = pred; d["stageB_proba"] = proba; d["needs_llm"] = needs
        # Stage B overrides only the UNSURE rows (rules are high-precision on the rest)
        u = d["rule"] == "UNSURE"
        d.loc[u, "final_cat"] = np.where(pred[u.values], "EVENT", "NOT_EVENT")
        if host is not None and use_llm_on_abstain:
            band = u & d["needs_llm"]
            if band.any():
                cats = llm_label_batch(host, txt[band].tolist())
                d.loc[band, "final_cat"] = [c or "UNSURE" for c in cats]
    d["is_event"] = d["final_cat"] == "EVENT"
    return d
