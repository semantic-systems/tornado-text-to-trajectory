#!/usr/bin/env python
"""Stage 00 — confirm the environment, without network, GPU, data or credentials.

The project has no test suite. This is the substitute: a colleague who has just
cloned the repository and installed the requirements can run one command and get
a straight answer to "is this working?" — which otherwise requires 4.7 GB of data
and an hour of reading.

It checks three things, in increasing specificity:

1. every library module imports and every stage script compiles — which is what
   catches a file that was written but never committed;
2. configuration resolves — the window, the paths, the thresholds;
3. the pure functions behave, on synthetic inputs. These are the checks that were
   run informally while the code was written; keeping them here means a later
   change that breaks one is noticed by whoever made it.

Run it after any change to `src/tornado_dataset/`::

    python scripts/00_selftest.py
"""

from __future__ import annotations

import importlib
import py_compile
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

MODULES = [
    "tornado_dataset.config", "tornado_dataset.http", "tornado_dataset.ids",
    "tornado_dataset.llm", "tornado_dataset.viz",
    "tornado_dataset.dat.fetch", "tornado_dataset.dat.geometry",
    "tornado_dataset.dat.link", "tornado_dataset.dat.evaluate",
    "tornado_dataset.dat.hazards",
    "tornado_dataset.geo.gazetteer", "tornado_dataset.geo.pixels",
    "tornado_dataset.text.tiering", "tornado_dataset.text.iem",
    "tornado_dataset.text.gdelt", "tornado_dataset.text.lexisnexis",
    "tornado_dataset.text.labelling", "tornado_dataset.text.mediacloud",
    "tornado_dataset.text.lexisnexis_filter", "tornado_dataset.text.fulltext",
    "tornado_dataset.text.linking", "tornado_dataset.text.matching",
    "tornado_dataset.text.overlap",
]

failures: list[str] = []
checks = 0


def check(name: str, fn) -> None:
    """Run one check, recording rather than raising, so one failure is not the end."""
    global checks
    checks += 1
    try:
        fn()
        print(f"  ok    {name}")
    except Exception as exc:                      # noqa: BLE001 — report everything
        failures.append(f"{name}: {exc}")
        print(f"  FAIL  {name}: {exc}")
        if "--verbose" in sys.argv:
            traceback.print_exc()


# ── 1. imports and compilation ──────────────────────────────────────────────
print("modules")
for module in MODULES:
    check(module.replace("tornado_dataset.", ""), lambda m=module: importlib.import_module(m))

print("\nviewer (needs flask)")
check("viewer.app", lambda: importlib.import_module("tornado_dataset.viewer.app"))

print("\nstage scripts compile")
scripts = sorted(p for p in (REPO / "scripts").glob("*.py")
                 if p.name[0].isdigit() or p.stem == "_bootstrap")
for path in scripts:
    check(path.name, lambda p=path: py_compile.compile(str(p), doraise=True))
if len(scripts) < 20:
    failures.append(f"only {len(scripts)} stage scripts found — expected 22 "
                    "(00 plus 01-21). Some are probably untracked.")
    print(f"  FAIL  expected 22 stage scripts, found {len(scripts)}")

# ── 2. configuration ────────────────────────────────────────────────────────
print("\nconfiguration")
from tornado_dataset import config                                    # noqa: E402


def config_sane() -> None:
    assert config.WINDOW_START < config.WINDOW_END, "window is inverted"
    assert config.REPO_ROOT.exists(), "REPO_ROOT does not exist"
    for name in ("DATA_DIR", "RAW_DIR", "INTERIM_DIR", "PROCESSED_DIR", "OUTPUT_DIR"):
        assert getattr(config, name).is_absolute(), f"{name} is not absolute"
    assert 0 < config.LINK_MIN_SCORE < 1, "LINK_MIN_SCORE out of range"


check("window and paths", config_sane)


# ── 3. pure functions ───────────────────────────────────────────────────────
print("\nbehaviour")
from tornado_dataset.text import fulltext, labelling, lexisnexis_filter  # noqa: E402
from tornado_dataset.text import matching, mediacloud                    # noqa: E402
from tornado_dataset.text import gdelt                                   # noqa: E402


def evidence_windows_reach_late_mentions() -> None:
    """A prefix would miss a tornado first named 300 words in; windows must not."""
    body = " ".join(f"w{i}" for i in range(500)).replace("w300", "tornado")
    text, n = lexisnexis_filter.evidence_windows(body)
    assert n == 1, f"expected 1 mention, got {n}"
    assert "tornado" in text, "late mention was dropped"
    assert "w0" in text, "lede anchor was dropped"
    lede, _ = lexisnexis_filter.render_evidence({"body": body}, "lede150")
    assert "tornado" not in lede, "the lede150 control should miss it"


def paywall_stub_is_a_failure_not_an_article() -> None:
    """A 'subscribe to continue' teaser must never enter the corpus as text."""
    html = ("<html><body><article><p>Subscribe to continue reading this article. "
            + "Already a subscriber? Sign in. " * 12 + "</p></article></body></html>")
    _, _, reason = fulltext.extract_text(html, "http://example.com/a")
    assert reason, "a paywall teaser was accepted as an article"


def uncached_gdelt_query_is_a_third_state() -> None:
    """"Never fetched" must not read as "failed" or as "GDELT has nothing"."""
    import datetime as dt
    import tempfile
    from pathlib import Path
    empty = Path(tempfile.mkdtemp())
    got = gdelt.query_articles("Joplin tornado", dt.date(2011, 5, 22),
                               dt.date(2011, 5, 23), cache_dir=empty, cache_only=True)
    assert got is gdelt.NOT_CACHED, f"expected NOT_CACHED, got {got!r}"
    assert got is not None and got != [], "the third state collapsed into another"


def unparseable_answer_is_not_a_judgement() -> None:
    """A model answer that never arrived must not look like a decision."""
    out = labelling.parse_llm_answers([None, "not json at all",
                                       '{"primary": "EVENT", "conf": 0.9}'])
    assert list(out.primary) == ["UNCLEAR", "UNCLEAR", "EVENT"]
    assert list(out.parsed) == [False, False, True]
    assert not out.loc[0, "is_outbreak"], "flags must default False, not NaN"


def protect_rule_is_enforced() -> None:
    """The owner's rule: text naming weather is never a non-meteorological use."""
    import pandas as pd
    frame = pd.DataFrame({"protected": [True, False], "nonmet_sense": [True, True]})
    repaired = labelling.enforce_protect_invariant(frame)
    assert repaired == 1, f"expected 1 repair, got {repaired}"
    assert list(frame.nonmet_sense) == [False, True]


def dedup_groups_collapse_syndication() -> None:
    import pandas as pd
    frame = pd.DataFrame({
        "title": ["Tornado hits Marshall County", "TORNADO HITS MARSHALL COUNTY!",
                  "Something else entirely"],
        "url": ["http://a.com/x", "http://b.com/a-longer-slug-here", "http://c.com/z"],
    })
    out = mediacloud.add_dedup_groups(frame)
    assert out.dup_group.nunique() == 2, "case/punctuation variants should collapse"
    assert out.is_representative.sum() == 2, "exactly one representative per group"
    # The representative is the copy with the most evidence in its slug.
    assert out.loc[out.is_representative, "url"].str.contains("longer-slug").any(), \
        "representative should be the copy with the richest URL slug"


def title_similarity_separates_stories() -> None:
    same = matching.title_similarity("Tornado slams Dallas; 4 killed in Arkansas",
                                     "Tornado slams Dallas, 4 killed in Arkansas")
    diff = matching.title_similarity("Tornado slams Dallas; 4 killed in Arkansas",
                                     "Council approves new library budget")
    assert same["jaccard"] > 0.8, f"same story scored {same['jaccard']}"
    assert diff["jaccard"] < 0.2, f"unrelated scored {diff['jaccard']}"


def body_key_is_content_derived() -> None:
    """The join key must survive a process boundary, unlike factorize order."""
    import pandas as pd
    a = lexisnexis_filter.body_key(pd.Series(["A tornado struck the town."]))
    b = lexisnexis_filter.body_key(pd.Series(["a  TORNADO struck the town!"]))
    assert a.iloc[0] == b.iloc[0], "normalisation should make these identical"


for name, fn in [
    ("evidence windows reach late mentions", evidence_windows_reach_late_mentions),
    ("paywall stub is a failure, not an article", paywall_stub_is_a_failure_not_an_article),
    ("uncached GDELT query is a third state", uncached_gdelt_query_is_a_third_state),
    ("unparseable answer is not a judgement", unparseable_answer_is_not_a_judgement),
    ("protect rule is enforced", protect_rule_is_enforced),
    ("dedup groups collapse syndication", dedup_groups_collapse_syndication),
    ("title similarity separates stories", title_similarity_separates_stories),
    ("body key is content-derived", body_key_is_content_derived),
]:
    check(name, fn)

# ── verdict ─────────────────────────────────────────────────────────────────
print()
if failures:
    print(f"{len(failures)} of {checks} checks FAILED\n")
    for failure in failures:
        print(f"  - {failure}")
    print("\nRe-run with --verbose for tracebacks.")
    sys.exit(1)
print(f"all {checks} checks passed — the environment is usable.")
print("No data was read; see HANDOVER.md for how to obtain data/.")
