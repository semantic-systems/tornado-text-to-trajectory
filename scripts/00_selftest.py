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
    "tornado_dataset.text.corpora",
    "tornado_dataset.text.overlap", "tornado_dataset.text.wikipedia",
    "tornado_dataset.text.refcoverage",
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
    failures.append(f"only {len(scripts)} stage scripts found — expected ~21 "
                    "(00, 01-12, 14-19, 21-22). Some are probably untracked.")
    print(f"  FAIL  expected ~21 stage scripts, found {len(scripts)}")

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
from tornado_dataset.text import corpora                                 # noqa: E402
from tornado_dataset.text import wikipedia                               # noqa: E402
from tornado_dataset.text import refcoverage                             # noqa: E402


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


def url_normalisation_keeps_the_article_id() -> None:
    """Dropping the query merged 2,253 distinct articles into one identifier."""
    import pandas as pd
    u = pd.Series(["https://ktbb.com/post/?p=1379487",
                   "https://ktbb.com/post/?p=1397923",
                   "https://www.cnn.com/a/b.html?utm_source=x&fbclid=y",
                   "https://cnn.com/a/b.html"])
    n = corpora.normalise_url(u)
    assert n.iloc[0] != n.iloc[1], "query-borne article ids must stay distinct"
    assert n.iloc[2] == n.iloc[3], "tracking parameters must be stripped"


def story_id_separates_recurring_headlines() -> None:
    """The same headline in two different years is two stories, not one."""
    import pandas as pd
    s = corpora._story_id(pd.Series(["Storms move through the area"] * 2),
                          pd.Series(["2012-04-14", "2019-05-20"]))
    assert s.nunique() == 2, "a recurring headline collapsed across years"


def components_are_transitive() -> None:
    """A story reached through an intermediate corpus must count once."""
    comp = corpora.components([("L::a", "M::b"), ("M::b", "G::c")])
    assert len(set(comp.values())) == 1, "transitive merge failed"
    two = corpora.components([("L::a", "M::b"), ("L::x", "M::y")])
    assert len(set(two.values())) == 2, "disjoint pairs were merged"


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


def wikipedia_sections_are_per_tornado() -> None:
    text = ("== Meteorological synopsis ==\nA trough.\n"
            "== Confirmed tornadoes ==\n{{Main|List of tornadoes in X}}\n"
            "=== Tuscaloosa–Birmingham, Alabama ===\n{{Main|2011 Tuscaloosa–Birmingham tornado}}\n"
            "The tornado touched down<ref>{{cite news|title=T}}</ref> southwest of town.\n"
            "==== Aftermath ====\nMore words here.\n"
            "=== April 27 event ===\n{| class=wikitable\n|-\n| EF4 \n|}\n"
            "=== Cullman–Arab, Alabama ===\nAn EF4 struck Cullman.\n"
            "== Aftermath ==\nRecovery.\n")
    secs = wikipedia.tornado_sections(text)
    assert [(s["heading"], s["section_type"]) for s in secs] == [
        ("Tuscaloosa–Birmingham, Alabama", "tornado"), ("April 27 event", "day"),
        ("Cullman–Arab, Alabama", "tornado")], secs
    assert secs[1]["prose_words"] == 0, "a day section that is only a table is empty"
    assert secs[0]["main_article"] == "2011 Tuscaloosa–Birmingham tornado"
    assert secs[0]["prose_words"] == 11, secs[0]     # level-4 child kept, ref stripped


def wikipedia_pages_are_classified_and_scoped() -> None:
    page = {"title": "Tornado outbreak of April 25–28, 2024", "templates": set(),
            "categories": {"Category:Tornadoes in Iowa", "Category:Tornadoes of 2024"}}
    page.update(kind=wikipedia.classify(page), year=wikipedia.event_year(page),
                us_states=wikipedia.us_states(page))
    assert (page["kind"], page["year"], page["us_states"]) == ("outbreak", 2024, ["Iowa"])
    assert wikipedia.scope(page, range(2010, 2026)) == "in_scope"
    canada = {"title": "2011 Goderich tornado", "templates": set(),
              "categories": {"Category:Tornadoes in Ontario"}}
    assert wikipedia.us_states(canada) == []
    georgia = {"categories": {"Category:Tornadoes in Georgia (country)"}}
    assert wikipedia.us_states(georgia) == [], "the country is not the state"
    assert wikipedia.classify({"title": "List of United States tornadoes in May 2024",
                               "templates": set()}) == "list"
    assert wikipedia.classify({"title": "December 2021 tornado outbreak", "templates": set(),
                               "categories": {"Category:Disambiguation pages"}}) == "disambiguation"


def wikipedia_references_keep_their_section() -> None:
    text = ("Lead.<ref name=nws>{{cite web|url=https://www.weather.gov/x|title=Survey"
            "|publisher=National Weather Service}}</ref>\n"
            "== Confirmed tornadoes ==\n=== Cullman, Alabama ===\n"
            "Hit.<ref>{{cite news|url=https://web.archive.org/web/2011/http://al.com/a"
            "|title=Cullman hit|work=AL.com|date=April 28, 2011}}</ref>"
            "<ref name=nws/><ref group=note>An aside.</ref>\n")
    refs = {r["ref_key"]: r for r in wikipedia.extract_references(text)}
    assert len(refs) == 2, "the footnote group is not a source"
    nws = refs["name:nws"]
    assert nws["n_citations"] == 2 and nws["sections"] == "(lead) | Confirmed tornadoes > Cullman, Alabama"
    assert wikipedia.classify_reference(nws) == "nws"
    news = next(r for k, r in refs.items() if k.startswith("anon:"))
    assert news["url"] == "http://al.com/a" and news["archive_url"].startswith("https://web.archive.org")
    assert (news["pub_date"], news["date_precision"]) == ("2011-04-28", "day")
    assert wikipedia.classify_reference(news) == "news"
    assert wikipedia.parse_cite_date("April 2011") == ("2011-04-01", "month")


def outlet_names_match_only_their_own_paper() -> None:
    import pandas as pd

    lexis = pd.DataFrame({"source": [
        "The Courier-Journal (Louisville, Kentucky)", "The Leader", "Daily News (New York)",
        "Associated Press State & Local", "The Associated Press", "The Gazette (Montreal)",
        "CBS News Transcripts CBS EVENING NEWS 6:30 PM EST"], "body": ""})
    idx = refcoverage.OutletIndex(lexis)
    assert idx.sources_for("courier-journal.com", ["Courier Journal"]) == {
        "The Courier-Journal (Louisville, Kentucky)"}
    assert idx.sources_for("apnews.com", ["Associated Press"]) == {
        "Associated Press State & Local", "The Associated Press"}
    assert not idx.sources_for("kentucky.com", ["Lexington Herald-Leader"]), "Leader is not it"
    assert not idx.sources_for("daytondailynews.com", ["Dayton Daily News"])
    assert not idx.sources_for("thegazette.com", ["The Gazette"]), "one generic word"
    assert not idx.sources_for("cbsnews.com", ["CBS News"]), "transcripts are not web articles"


def content_tier_sees_through_a_new_headline() -> None:
    import pandas as pd

    body = ("A powerful tornado tore through the town late Wednesday, destroying dozens of "
            "homes along Main Street and injuring at least twelve people, officials said. "
            "The National Weather Service rated the storm EF3 after a survey on Thursday, "
            "with peak winds estimated at 150 miles per hour along a path of nine miles. ") * 2
    lexis = pd.DataFrame({"textref_uid": ["a", "b"], "headline": ["x", "y"],
                          "source": ["S", "S"], "pub_date": ["2020-03-03", "2020-03-03"],
                          "body": [body + " Local reaction followed.", "An unrelated budget story. " * 30]})
    best = refcoverage.ShingleIndex(lexis).best(body)
    assert best["textref_uid"] == "a" and best["containment"] > 0.9, best


for name, fn in [
    ("evidence windows reach late mentions", evidence_windows_reach_late_mentions),
    ("paywall stub is a failure, not an article", paywall_stub_is_a_failure_not_an_article),
    ("uncached GDELT query is a third state", uncached_gdelt_query_is_a_third_state),
    ("url normalisation keeps the article id", url_normalisation_keeps_the_article_id),
    ("story id separates recurring headlines", story_id_separates_recurring_headlines),
    ("components are transitive", components_are_transitive),
    ("unparseable answer is not a judgement", unparseable_answer_is_not_a_judgement),
    ("protect rule is enforced", protect_rule_is_enforced),
    ("dedup groups collapse syndication", dedup_groups_collapse_syndication),
    ("title similarity separates stories", title_similarity_separates_stories),
    ("body key is content-derived", body_key_is_content_derived),
    ("wikipedia sections are per tornado", wikipedia_sections_are_per_tornado),
    ("wikipedia pages are classified and scoped", wikipedia_pages_are_classified_and_scoped),
    ("wikipedia references keep their section", wikipedia_references_keep_their_section),
    ("outlet names match only their own paper", outlet_names_match_only_their_own_paper),
    ("content tier sees through a new headline", content_tier_sees_through_a_new_headline),
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
