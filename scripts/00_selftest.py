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
    "tornado_dataset.dat.hazards", "tornado_dataset.dat.storm_events",
    "tornado_dataset.dat.episodes", "tornado_dataset.dat.spc_tornadoes",
    "tornado_dataset.dat.episode_table", "tornado_dataset.dat.references",
    "tornado_dataset.dat.spc_watches", "tornado_dataset.dat.merge_check",
    "tornado_dataset.dat.unmatched_check", "tornado_dataset.handcheck",
    "tornado_dataset.text.link_check",
    "tornado_dataset.geo.gazetteer", "tornado_dataset.geo.pixels",
    "tornado_dataset.text.tiering", "tornado_dataset.text.iem",
    "tornado_dataset.text.gdelt", "tornado_dataset.text.lexisnexis",
    "tornado_dataset.text.labelling", "tornado_dataset.text.mediacloud",
    "tornado_dataset.text.lexisnexis_filter", "tornado_dataset.text.fulltext",
    "tornado_dataset.text.fulltext_corpus",
    "tornado_dataset.text.linking", "tornado_dataset.text.matching",
    "tornado_dataset.text.corpora",
    "tornado_dataset.text.overlap", "tornado_dataset.text.records",
    "tornado_dataset.text.same_source", "tornado_dataset.text.same_source_view",
    "tornado_dataset.text.official",
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
check("viewer.fulltext", lambda: importlib.import_module("tornado_dataset.viewer.fulltext"))

print("\nstage scripts compile")
scripts = sorted(p for p in (REPO / "scripts").glob("*.py")
                 if p.name[0].isdigit() or p.stem in ("_bootstrap", "viewer"))
for path in scripts:
    check(path.name, lambda p=path: py_compile.compile(str(p), doraise=True))
if len(scripts) < 31:
    failures.append(f"only {len(scripts)} stage scripts found — expected 31 "
                    "(00, 10-25, 30-35, 40-43, 50-51, viewer, _bootstrap). "
                    "Some are probably untracked.")
    print(f"  FAIL  expected 31 stage scripts, found {len(scripts)}")

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
from tornado_dataset.text import fulltext_corpus                         # noqa: E402


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


def soft_404_to_the_front_page_is_caught() -> None:
    """A dead article that 200s with the homepage must not pass as the article."""
    assert fulltext._redirected_home("https://cbsnews.com/news/tornado-kills-3",
                                     "https://www.cbsnews.com/", "direct")
    assert not fulltext._redirected_home("https://cbsnews.com/news/tornado-kills-3",
                                         "https://cbsnews.com/news/tornado-kills-3",
                                         "direct")
    # an archive fetch's final URL is the archive's, so it is never judged
    assert not fulltext._redirected_home("https://cbsnews.com/news/x",
                                         "https://web.archive.org/", "wayback")


def english_check_separates_prose_from_spanish() -> None:
    en = "The tornado tore through the town and it was the worst storm in a decade."
    es = "El tornado arrasó la ciudad y fue la peor tormenta en una década entera."
    assert fulltext._stopword_share(en) >= fulltext.MIN_ENGLISH_STOPWORD_SHARE
    assert fulltext._stopword_share(es) < fulltext.MIN_ENGLISH_STOPWORD_SHARE


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


def kappa_corrects_for_rare_flags() -> None:
    """Two labellers who never set a flag must not look like they agree on it."""
    assert abs(fulltext_corpus.cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) - 1.0) < 1e-9
    import math
    assert math.isnan(fulltext_corpus.cohen_kappa([0] * 5, [0] * 5)), \
        "kappa on a never-set flag must be undefined, not perfect"
    k = fulltext_corpus.cohen_kappa([1, 1, 0, 0], [1, 0, 1, 0])
    assert abs(k) < 1e-9, f"independent labels should give kappa 0, got {k}"


def fulltext_bodies_keep_both_labels_apart() -> None:
    """Headline labels ride along under hl_; one shared body is labelled once."""
    import pandas as pd
    body = "A tornado touched down in Moore on Monday. " * 30
    store = {"http://a.com/1": {"status": "ok", "text": body, "via": "direct"},
             "http://b.com/2": {"status": "ok", "text": body, "via": "wayback"},
             "http://c.com/3": {"status": "paywall"}}
    pop = pd.DataFrame({"url": list(store), "title": ["Moore tornado", "Tornado hits Moore",
                                                       "x"],
                        "publish_date": ["2013-05-20"] * 3, "media_name": ["a", "b", "c"],
                        "dup_group": [1, 2, 3], "year_band": ["2010-2015"] * 3,
                        "domain_size": ["small"] * 3, "primary": ["EVENT"] * 3,
                        "conf": [0.9] * 3, "is_outbreak": [False] * 3})
    df = fulltext_corpus.load_bodies(store, pop)
    assert len(df) == 2, "only retrieved bodies are rows"
    assert {"headline", "source", "pub_date", "body", "hl_primary", "hl_is_outbreak"} \
        <= set(df.columns)
    assert "primary" not in df.columns, "an unprefixed label would collide with stage 34's"
    assert df.body_key.nunique() == 1 and df.is_representative.sum() == 1


def cross_corpus_reads_either_edge_direction() -> None:
    import pandas as pd
    stories = pd.DataFrame({"headline": ["Tornado hits Moore"], "pub_date": ["2013-05-20"],
                            "hl_primary": ["EVENT"], "ft_primary": ["NOT_TORNADO_EVENT"]})
    sid = corpora._story_id(stories.headline, stories.pub_date).iloc[0]
    lexis = pd.DataFrame({"story_id": ["ln1", "ln2"], "primary": ["EVENT", "EVENT"]})
    edges = pd.DataFrame({"left_story": ["ln1", sid], "right_story": [sid, "ln2"],
                          "left_corpus": ["lexisnexis", "mediacloud"],
                          "right_corpus": ["mediacloud", "lexisnexis"]})
    pairs = fulltext_corpus.cross_corpus(stories, lexis, edges)
    assert len(pairs) == 2, f"expected both edge orientations, got {len(pairs)}"
    assert set(pairs.ln_story) == {"ln1", "ln2"}


def archive_refetch_skips_settled_and_retries_transient() -> None:
    """A rerun must retry a connection error but never a missing snapshot."""
    log = {"a": {"outcome": "ok"}, "b": {"outcome": "no_snapshot"},
           "c": {"outcome": "extract:too_short_26w"},
           "d": {"outcome": "archive_ConnectionError"}}
    items = [{"url": u} for u in ("a", "b", "c", "d", "e")]
    todo = [i["url"] for i in fulltext.refetch_pending(items, log)]
    assert todo == ["d", "e"], f"expected the transient and the untried, got {todo}"


def storm_events_times_are_standard_time() -> None:
    """Storm Data is local *standard* time all year; "CST-6" means UTC-6 in July too."""
    import pandas as pd
    from tornado_dataset.dat import storm_events
    utc = storm_events.to_utc(pd.Series(["15-JUL-25 15:52:00", "15-JAN-25 15:52:00"]),
                              pd.Series(["CST-6", "CST"]))
    assert list(utc.dt.hour) == [21, 21], f"got {list(utc.dt.hour)}"
    listing = ("StormEvents_details-ftp_v1.0_d2025_c20260316.csv.gz "
               "StormEvents_details-ftp_v1.0_d2025_c20260819.csv.gz")
    assert storm_events.latest_files(listing)[2025].endswith("c20260819.csv.gz")


def mistyped_end_dates_are_repaired() -> None:
    """A 7-minute tornado with an end date two years later must not span two years."""
    import pandas as pd
    from tornado_dataset.dat import episodes
    t0 = pd.to_datetime(pd.Series(["2013-03-18T17:11:00Z", "2013-03-18T17:11:00Z",
                                   "2013-03-18T17:11:00Z"]), utc=True)
    t1 = pd.to_datetime(pd.Series(["2015-01-23T17:18:00Z", "2013-03-18T17:30:00Z",
                                   "2013-03-20T05:00:00Z"]), utc=True)
    fixed, bad = episodes.repair_end_times(t0, t1)
    minutes = list(((fixed - t0).dt.total_seconds() / 60).round())
    assert minutes == [7, 19, 0], f"got {minutes}"
    assert list(bad) == [True, False, True]


def space_time_links_across_the_day_boundary() -> None:
    """Two tornadoes 30 min apart at 12 UTC: one episode by time gap, two by day."""
    import pandas as pd
    from shapely.geometry import LineString
    from tornado_dataset.dat import episodes
    h = pd.DataFrame({
        "geom": [LineString([(0, 0), (1000, 0)]), LineString([(5000, 0), (6000, 0)]),
                 LineString([(9e6, 0), (9.001e6, 0)])],
        "t0": pd.to_datetime(["2020-04-13T11:45Z", "2020-04-13T12:15Z",
                              "2020-04-13T12:15Z"], utc=True),
        "convective_day": ["2020-04-12", "2020-04-13", "2020-04-13"]})
    h["t1"] = h.t0
    by_day = episodes.convective_day(h, 200_000)
    by_gap = episodes.space_time(h, 200_000, 3 * 3600)
    assert by_day[0] != by_day[1], "the day rule should cut at 12 UTC"
    assert by_gap[0] == by_gap[1] != by_gap[2], "time gap should join near, keep far apart"
    assert abs(episodes.adjusted_rand(by_gap, by_gap) - 1.0) < 1e-9


def county_segments_chain_into_tornadoes_and_link_offices() -> None:
    """A tornado crossing from one office into another joins both offices' episodes."""
    import pandas as pd
    from tornado_dataset.dat import storm_events
    t = pd.DataFrame({
        "EVENT_ID": [10, 11, 12, 20], "EPISODE_ID": [1, 2, 2, 3],
        "WFO": ["MEG", "LZK", "LZK", "LZK"], "STATE": ["ARKANSAS"] * 4,
        "CZ_FIPS": [55, 31, 31, 99],
        "TOR_OTHER_WFO": ["LZK", None, None, None], "TOR_OTHER_CZ_STATE": ["AR", None, None, None],
        "TOR_OTHER_CZ_FIPS": [31, None, None, None],
        "BEGIN_LAT": [35.0, 35.1, 35.1, 36.0], "BEGIN_LON": [-90.0, -90.1, -90.5, -91.0],
        "END_LAT": [35.1, 35.2, 35.2, 36.1], "END_LON": [-90.1, -90.2, -90.6, -91.1],
        "begin_utc": pd.to_datetime(["2025-03-14T20:00Z", "2025-03-14T20:10Z",
                                     "2025-03-15T09:00Z", "2025-03-14T20:10Z"], utc=True)})
    t["end_utc"] = t.begin_utc + pd.Timedelta(minutes=10)
    t["TORNADO_KEY"] = storm_events.chain_segments(t)
    assert t.TORNADO_KEY.tolist()[:2] == ["setor_10", "setor_10"], t.TORNADO_KEY.tolist()
    assert t.TORNADO_KEY[2] != "setor_10", "a later tornado in the same county must not chain"
    linked = storm_events.link_episodes(t)
    assert linked[0] == linked[1] == linked[2] == "selep_1", linked.tolist()
    assert linked[3] == "selep_3"


def spc_records_are_cst_and_whole_tracks() -> None:
    """SPC times are CST (UTC-6) year round; only sg == 1 rows are whole tracks."""
    import tempfile
    from pathlib import Path
    from tornado_dataset.dat import spc_tornadoes
    csv = ("om,yr,mo,dy,date,time,tz,st,slat,slon,elat,elon,ns,sn,sg,edat,etime\n"
           "12,2025,7,15,2025-07-15,15:52:00,3,OK,35.0,-97.0,35.1,-96.9,1,1,1,"
           "2025-07-15,16:01:00\n"
           "12,2025,7,15,2025-07-15,15:52:00,3,OK,35.0,-97.0,35.1,-96.9,1,0,-9,,\n")
    path = Path(tempfile.mkdtemp()) / "2010-2025_actual_tornadoes.csv"
    path.write_text(csv)
    df, notes = spc_tornadoes.load(path, [2025])
    assert len(df) == 1 and notes["dropped_not_whole_track"] == 1
    assert df.begin_utc.iloc[0].hour == 21 and df.spc_id.iloc[0] == "spc_2025_12"
    assert (df.end_utc.iloc[0] - df.begin_utc.iloc[0]).total_seconds() == 540
    page = "1950-2024_actual_tornadoes.csv 1950-2025_actual_tornadoes.csv"
    assert spc_tornadoes.latest_file(page) == "1950-2025_actual_tornadoes.csv"


def dat_clock_errors_are_repaired_on_the_hour() -> None:
    """A DAT time off by whole hours links to its SPC track; one off by 5h17m does not."""
    import pandas as pd
    from shapely.geometry import LineString
    from tornado_dataset.dat import spc_tornadoes as spc
    t = pd.Timestamp("2012-04-14 21:00", tz="UTC")
    tracks = pd.DataFrame({"spc_id": ["spc_a", "spc_b", "spc_c"],
                           "begin_utc": [t, t + pd.Timedelta(hours=30), t],
                           "end_utc": [t + pd.Timedelta(minutes=10)] * 3,
                           "mag": [2, 1, 0]})
    geoms = [LineString([(0, 0), (5000, 0)]), LineString([(100_000, 0), (105_000, 0)]),
             LineString([(200_000, 0), (205_000, 0)])]
    line = lambda x: LineString([(x, 300), (x + 5000, 300)])  # noqa: E731
    hazards = pd.DataFrame({
        "hazard_uid": ["local", "date", "jitter", "first"],
        # local clock stored as UTC (CDT, 5 h early); wrong date (+1 day) plus
        # 6 h early; 5 h 17 min early (no clock error does that); already linked.
        "t0": [t - pd.Timedelta(hours=5), t + pd.Timedelta(hours=30 - 24 - 6),
               t - pd.Timedelta(hours=5, minutes=17), t],
        "track": [line(0), line(100_000), line(200_000), line(0)],
        "efscale": ["EF2", "EF1", "EF0", "EF2"],
        "dat_event_ids": [None, "greenwood_20120415", None, None]})
    first = spc.with_first_pass_columns(pd.DataFrame({
        "spc_id": ["spc_a"], "hazard_uid": ["first"], "distance_m": [300.0], "gap_s": [0.0],
        "rank_for_event": [1], "rank_for_hazard": [1],
        "link_method": ["spatial_temporal_join"]}), tracks, hazards)
    fixed, stats = spc.repair_time_links(tracks, geoms, hazards, first)
    got = fixed.set_index("hazard_uid")
    assert set(got.index) == {"local", "date"}, f"got {sorted(got.index)}"
    assert got.loc["local", "time_offset_h"] == 5
    assert got.loc["local", "offset_class"] == "local_as_utc"
    assert got.loc["date", "offset_class"] == "date+1+local_as_utc", got.loc["date", "offset_class"]
    assert bool(got.loc["local", "spc_already_linked"]) and not bool(got.loc["date", "spc_already_linked"])
    assert bool(got.loc["local", "ef_agrees"]) and stats["candidates"] == 3
    both = pd.concat([first, fixed], ignore_index=True)
    assert spc.event_id_date_check(both, tracks, hazards).tolist() == [None, "spc", None]
    assert spc.offset_class(-1) == "dst" and spc.offset_class(-24) == "date-1"
    assert spc.offset_class(3) == "unexplained"
    import datetime as dt
    assert spc.event_id_dates("7/12/16 Chip Falls") == {dt.date(2016, 7, 12)}
    assert spc.event_id_dates("UNR-2019-0629-Allen") == {dt.date(2019, 6, 29)}
    assert spc.event_id_dates("ilx061921;Erath 121322") == set()


def same_footprint_links_a_free_spc_track() -> None:
    """Both ends on DAT's track, a free SPC track, within 72 h: one tornado, not two."""
    import pandas as pd
    from shapely.geometry import LineString
    from tornado_dataset.dat import spc_tornadoes as spc
    t = pd.Timestamp("2016-05-31 23:53", tz="UTC")
    ids = ["taken", "free", "half", "late", "noon"]
    tracks = pd.DataFrame({"spc_id": ids,
                           "begin_utc": [t, t, t, t + pd.Timedelta(hours=80), t],
                           "mag": [1, 1, 1, 1, 2]})
    seg = lambda x, n=5000: LineString([(x, 0), (x + n, 0)])  # noqa: E731
    # "half": SPC's track runs 3 km beyond DAT's, so only its start is on it.
    geoms = [seg(0), seg(100_000), seg(200_000, 8000), seg(300_000), seg(400_000)]
    hazards = pd.DataFrame({
        "hazard_uid": ["dup", "jitter", "partial", "far_off", "midnight"],
        "t0": [t - pd.Timedelta(hours=9, minutes=11)] * 4
              + [pd.Timestamp("2016-05-31 00:00", tz="UTC")],
        "track": [LineString([(x, 20), (x + 5000, 20)])
                  for x in (0, 100_000, 200_000, 300_000, 400_000)],
        "efscale": ["EF1", "EF1", "EF1", "EF1", "EF2"]})
    first = spc.with_first_pass_columns(pd.DataFrame({
        "spc_id": ["taken"], "hazard_uid": ["other"], "distance_m": [0.0], "gap_s": [0.0],
        "rank_for_event": [1], "rank_for_hazard": [1],
        "link_method": ["spatial_temporal_join"]}), tracks, hazards)
    got, stats = spc.footprint_links(tracks, geoms, hazards, first)
    got = got.set_index("hazard_uid")
    assert set(got.index) == {"jitter", "midnight"}, f"got {sorted(got.index)}"
    assert got.loc["jitter", "spc_id"] == "free" and got.loc["jitter", "offset_class"] == "other"
    assert got.loc["midnight", "offset_class"] == "dat_midnight"
    assert got.loc["jitter", "link_method"] == "footprint_match"
    assert abs(got.loc["jitter", "endpoint_m"] - 20) < 1e-6 and bool(got.loc["jitter", "ef_agrees"])


def hazard_times_take_spc_or_repaired_ends() -> None:
    """SPC's start and end where DAT's time was wrong; DAT ends repaired or left empty."""
    import pandas as pd
    from tornado_dataset.dat import episode_table
    uids = ["ok", "typo", "none", "lost", "clock", "foot"]
    begin = "2020-04-12T20:00:00+00:00"
    hazards = pd.DataFrame({
        "hazard_uid": uids, "hazard_source": "dat", "time_begin_utc": begin,
        "convective_day": "2020-04-12",
        # 10 min; a mistyped date (+1 day, clock 10 min on); none; three days and
        # seven hours on (no plausible clock time); wrong clocks, SPC's to be used.
        "time_end_utc": ["2020-04-12T20:10:00+00:00", "2020-04-13T20:10:00+00:00", None,
                         "2020-04-15T03:00:00+00:00", "2020-04-12T20:10:00+00:00",
                         "2020-04-12T20:10:00+00:00"]})
    member = pd.DataFrame({"hazard_uid": uids, "spc_id": ["a", "b", "c", "d", "e", "f"],
                           "spc_link_method": ["spatial_temporal_join"] * 4
                           + ["time_repaired", "footprint_match"]})
    tracks = pd.DataFrame({"spc_id": list("abcdef"),
                           "begin_utc": ["2020-04-12 20:00:00+00:00"] * 4
                           + ["2020-04-13 01:00:00+00:00", "2020-04-13 05:00:00+00:00"],
                           "end_utc": ["2020-04-12 20:10:00+00:00"] * 4
                           + ["2020-04-13 01:20:00+00:00", "2020-04-13 05:30:00+00:00"]})
    t = episode_table.event_times(hazards, member, tracks).set_index("hazard_uid")
    assert t.at["ok", "end_utc"] == "2020-04-12T20:10:00+00:00" and not t.at["ok", "end_repaired"]
    assert t.at["typo", "end_utc"] == "2020-04-12T20:10:00+00:00" and t.at["typo", "end_repaired"]
    assert pd.isna(t.at["none", "end_utc"]) and not t.at["none", "end_repaired"]
    assert pd.isna(t.at["lost", "end_utc"]) and not t.at["lost", "end_repaired"]
    assert t.at["clock", "end_utc"] == "2020-04-13T01:20:00+00:00"
    assert t.at["foot", "time_source"] == "spc_track" and t.at["foot", "convective_day"] == "2020-04-12"
    assert t.at["foot", "begin_utc"] == "2020-04-13T05:00:00+00:00"


def dat_reference_extends_through_spc() -> None:
    """A DAT hazard with no Storm Events match of its own takes its SPC track's."""
    import pandas as pd
    from tornado_dataset.dat import episodes
    dat = pd.Series(["h1", "h2", "h3"])
    direct = pd.DataFrame({"hazard_uid": dat, "EPISODE_ID": [10, None, None],
                           "WFO": ["OUN", None, None]})
    spc_links = pd.DataFrame({"hazard_uid": ["h1", "h2"], "spc_id": ["s1", "s2"],
                              "rank_for_hazard": [1, 1]})
    spc_se = pd.DataFrame({"spc_id": ["s1", "s2"], "EPISODE_ID": [10, 20],
                           "WFO": ["OUN", "TSA"], "EVENT_ID": [1, 2],
                           "rank_for_hazard": [1, 1]})
    via = episodes.reference_via_spc(dat, spc_links, spc_se)
    ref, stats = episodes.combine_references(direct, via)
    assert ref.EPISODE_ID.tolist()[:2] == [10, 20] and pd.isna(ref.EPISODE_ID[2])
    assert ref.ref_source.tolist()[:2] == ["direct", "via_spc"] and pd.isna(ref.ref_source[2])
    assert stats["via_spc_only"] == 1 and stats["agree_episode"] == 1.0
    assert ref.WFO[1] == "TSA"


def spc_episodes_carry_to_dat_hazards() -> None:
    """DAT hazards take their closest SPC track's episode; unmatched ones stand alone."""
    import pandas as pd
    from tornado_dataset.dat import episodes
    labels = pd.Series([0, 0, 1])
    spc_uid = pd.Series(["spc_a", "spc_b", "spc_c"])
    dat_uid = pd.Series(["h1", "h2", "h3", "h4"])
    links = pd.DataFrame({"hazard_uid": ["h1", "h2", "h2", "h3"],
                          "spc_id": ["spc_a", "spc_c", "spc_b", "spc_c"],
                          "rank_for_hazard": [1, 2, 1, 1]})
    lab, matched = episodes.project_labels(labels, spc_uid, dat_uid, links)
    assert lab[0] == lab[1] != lab[2], f"got {lab.tolist()}"
    assert list(matched) == [True, True, True, False]
    assert lab[3] not in set(lab[:3]), "an unmatched hazard must be its own episode"


def episode_counts_cover_all_spc_tornadoes() -> None:
    """Counts come from SPC membership; EF-U is neither EF0 nor EF1+; DAT goes by its track."""
    import pandas as pd
    from tornado_dataset.dat import episodes
    h = pd.DataFrame({"hazard_uid": ["s1", "s2", "s3", "s4"], "mag": [0, 1, -9, 2]})
    labels = pd.Series([0, 0, 0, 1])
    dat_spc = pd.Series(["s1", "s4", "s4", None])     # one DAT hazard has no SPC track
    c = episodes.episode_counts(labels, h, dat_spc).set_index("episode")
    assert c.n_spc.tolist() == [3, 1] and c.n_spc_ef1plus.tolist() == [1, 1], c
    assert c.n_spc_unrated.tolist() == [1, 0] and c.n_dat.tolist() == [1, 2], c


def every_spc_episode_is_published_with_its_hazards() -> None:
    """All SPC groups published; DAT hazards carried over, unlinked SPC tornadoes as hazards."""
    import pandas as pd
    from tornado_dataset.dat import episode_table as et
    t = pd.to_datetime(["2020-04-12T11:00", "2020-04-12T13:00", "2020-05-01T20:00",
                        "2020-04-12T12:00"], utc=True)
    frame = pd.DataFrame({"hazard_uid": ["s1", "s2", "s3", "s4"], "t0": t, "t1": t,
                          "convective_day": ["2020-04-11", "2020-04-12", "2020-05-01",
                                             "2020-04-12"], "mag": [1, -9, 2, 0]})
    tracks = pd.DataFrame({"spc_id": ["s1", "s2", "s3", "s4"], "fat": [1, 0, 3, 0],
                           "inj": [2, 0, 5, 0], "len": [1.0] * 4, "wid": [50] * 4,
                           "st": ["OK"] * 4})
    labels = pd.Series([0, 0, 1, 0])          # s1, s2, s4 one episode across 12 UTC; s3 alone
    hazards = pd.DataFrame({"hazard_uid": ["h1", "h2", "h3", "h4"],
                            "convective_day": ["2020-04-11"] * 4,
                            "time_begin_utc": ["2020-04-12T11:00+00:00"] * 3 + [None],
                            "time_end_utc": [None] * 4, "efscale": ["EF1", "EF2", "EF0", "EF0"],
                            "fatalities": [1, 0, 0, 0], "injuries": [0, 0, 0, 0],
                            "wfo_all": ["OUN", "OUN;TSA", None, None]})
    links = pd.DataFrame({"hazard_uid": ["h1", "h2", "h1"], "spc_id": ["s1", "s1", "s4"],
                          "rank_for_hazard": [1, 1, 2],
                          "link_method": ["spatial_temporal_join", "time_repaired",
                                          "spatial_temporal_join"]})
    unmatched = pd.DataFrame({"hazard_uid": ["h3", "h4"],
                              "time_begin_utc": ["2020-04-12T11:00+00:00", None],
                              "nearest_spc_id": ["s1", None], "nearest_distance_km": [0.0, None],
                              "nearest_offset_h": [24.0, None]})
    episodes, member, grouping, spc_hazards = et.build(frame, labels, tracks, hazards, links,
                                                       unmatched=unmatched)
    assert len(episodes) == 2, "every SPC group is published, with or without DAT"
    big = episodes[episodes.has_dat].iloc[0]
    assert (big.n_dat, big.n_spc_hazards, big.n_spc, big.n_spc_ef1plus, big.n_spc_unrated) \
        == (2, 1, 3, 1, 1), big
    assert big.convective_days == "2020-04-11;2020-04-12" and big.max_efscale == "EF2"
    assert big.wfos == "OUN;TSA" and big.spc_fatalities == 1
    lone = episodes[~episodes.has_dat].iloc[0]
    assert lone.n_spc_hazards == 1 and pd.isna(lone.fatalities) and lone.spc_fatalities == 3
    roles = grouping.set_index("spc_id").role.to_dict()
    assert roles == {"s1": "dat_closest", "s2": "spc_hazard", "s3": "spc_hazard",
                     "s4": "dat_secondary"}, roles
    assert sorted(spc_hazards.spc_id) == ["s2", "s3"], "a linked SPC track is no hazard"
    assert spc_hazards.set_index("spc_id").efscale.to_dict() == {"s2": "EFU", "s3": "EF2"}
    m = member.set_index("hazard_uid")
    assert m.loc[["h3", "h4"]].episode_uid.isna().all(), "no SPC track, no episode"
    assert m.spc_match_status.loc[["h1", "h3", "h4"]].tolist() == [
        "linked", "probable_duplicate", "untimed_no_spc"]
    again, _, _, _ = et.build(frame, labels, tracks, hazards.iloc[:2], links)
    assert big.episode_uid in set(again.episode_uid), "episode ids rest on SPC tracks only"


def populations_go_to_the_nearest_namesake() -> None:
    """A Census population goes to the same-named GNIS place nearest its point, not to all."""
    from tornado_dataset.geo import gazetteer as gz
    places = [{"name": "Oxford", "state": "Mississippi", "lat": 34.37, "lon": -89.52},
              {"name": "Oxford", "state": "Mississippi", "lat": 31.10, "lon": -90.80},
              {"name": "Oklahoma City", "state": "Oklahoma", "lat": 35.47, "lon": -97.52},
              {"name": "Lexington", "state": "Kentucky", "lat": 38.05, "lon": -84.50},
              {"name": "Lexington-Fayette", "state": "Kentucky", "lat": 38.04, "lon": -84.46}]
    census = [{"name": "Oxford city", "state": "mississippi", "population": 26801,
               "lat": 34.36, "lon": -89.53, "aland_m2": 6e7},
              {"name": "Oklahoma City city", "state": "oklahoma", "population": 712919,
               "lat": 35.47, "lon": -97.51, "aland_m2": 1.5e9},
              {"name": "Lexington-Fayette urban county", "state": "kentucky",
               "population": 329437, "lat": 38.04, "lon": -84.46, "aland_m2": 7e8}]
    stats = gz.assign_population(places, census)
    assert [p["population"] for p in places] == [26801, 0, 712919, 329437, 0], places
    assert stats["assigned"] == 3 and stats["ambiguous_names_resolved"] == 1, stats


def place_and_county_names_fold() -> None:
    """Legal suffixes come off Census names only; county spellings meet."""
    from tornado_dataset.geo import gazetteer as gz
    assert gz.canonical_place_key("Oklahoma City") == "oklahoma city"
    assert gz.canonical_place_key("Oklahoma City city", census=True) == "oklahoma city"
    assert gz.canonical_place_key("Saint Louis") == gz.canonical_place_key("St. Louis")
    assert gz._census_keys("Weymouth Town city")[:2] == ["weymouth town", "weymouth"]
    assert gz._census_keys("Lexington-Fayette urban county")[0] == "lexington"
    for a, b in (("De Kalb", "DeKalb"), ("Prince Georges", "Prince George's"),
                 ("Dona Ana", "Doña Ana"), ("City of Richmond", "Richmond (city)"),
                 ("Mainland Dare", "Dare")):
        assert gz.county_key(a) == gz.county_key(b), (a, b)
    assert gz.county_key("Richmond (city)") != gz.county_key("Richmond")


def counties_need_a_share_and_offices_an_order() -> None:
    """A track grazing a county does not add it; the office follows DAT, Storm Events, counties."""
    from shapely.geometry import LineString, box
    from tornado_dataset.geo import gazetteer as gz
    a = {"ugc": "A", "proj": box(0, 0, 10_000, 10_000)}
    b = {"ugc": "B", "proj": box(10_000, 0, 20_000, 10_000)}
    shares, unit = gz.county_shares(LineString([(1_000, 5_000), (10_300, 5_000)]), [a, b])
    assert unit == "length" and [c["ugc"] for c in gz.keep_counties(shares, unit)] == ["A"]
    shares, unit = gz.county_shares(LineString([(1_000, 5_000), (19_000, 5_000)]), [a, b])
    assert {c["ugc"] for c in gz.keep_counties(shares, unit)} == {"A", "B"}
    assert gz.choose_wfo(["TSA", "OUN"], ["OUN", "TSA"], []) == ("OUN", "dat", ["OUN", "TSA"])
    assert gz.choose_wfo([], ["LZK"], ["MEG", "LZK"]) == ("LZK", "storm_events", ["LZK", "MEG"])
    assert gz.choose_wfo([], [], ["MEG"])[:2] == ("MEG", "spatial_join")
    assert gz.choose_wfo([], [], []) == (None, "none", [])


def record_texts_link_once_and_count_as_oracle() -> None:
    """Narratives reach one hazard by the first route; comments are one ref per text."""
    import pandas as pd
    from tornado_dataset.text import records, tiering
    membership = pd.DataFrame({
        "hazard_uid": ["hd1", "hd2", "hs1"], "hazard_source": ["dat", "dat", "spc"],
        "spc_id": ["s1", "s2", "s3"], "episode_uid": ["e1", "e1", "e2"]})
    grouping = pd.DataFrame({"spc_id": ["s1", "s2", "s3", "s4"],
                             "episode_uid": ["e1", "e1", "e2", "e2"]})
    se_links = pd.DataFrame({"EVENT_ID": [1, 2], "hazard_uid": ["hd1", "hd2"],
                             "rank_for_event": [1, 2]})
    spc_se = pd.DataFrame({"EVENT_ID": [1, 2, 3, 4], "spc_id": ["s3", "s2", "s3", "s4"],
                           "rank_for_event": [1, 1, 1, 1]})
    targets = records.event_targets(se_links, spc_se, membership, grouping)
    assert targets[1] == ("dat_direct", ["hd1"], "e1"), "a direct DAT link wins"
    assert targets[2] == ("dat_via_spc_track", ["hd2"], "e1")
    assert targets[3] == ("spc_hazard", ["hs1"], "e2")
    assert targets[4] == ("episode_only", [], "e2")
    se = pd.DataFrame({"EVENT_ID": [1, 3], "EPISODE_ID": [9, 9], "WFO": ["OUN", "OUN"],
                       "STATE": ["OKLAHOMA"] * 2, "CZ_NAME": ["CLEVELAND"] * 2,
                       "begin_utc": ["2020-04-12 20:00:00+00:00"] * 2, "BEGIN_LAT": [35.0] * 2,
                       "BEGIN_LON": [-97.0] * 2,
                       "EVENT_NARRATIVE": ["The tornado touched down and moved northeast.", "nan"],
                       "EPISODE_NARRATIVE": ["A strong upper trough moved across the Plains."] * 2})
    refs, links = records.storm_events_refs(se, targets)
    kinds = sorted(r["source_type"] for r in refs)
    assert kinds == ["storm_events_episode_narrative", "storm_events_narrative"], kinds
    assert all(r["text_role"] == "oracle" for r in refs), "survey products are oracle text"
    assert {(lk["target_uid"], lk["link_relation"]) for lk in links} == {
        ("hd1", "narrative_of"), ("e1", "episode_narrative_of"), ("e2", "episode_narrative_of")}
    hazards = pd.DataFrame({"hazard_uid": ["hd1"], "line_objectids": ["10;11"],
                            "polygon_objectids": ["20"], "wfo": ["OUN"],
                            "time_begin_utc": ["2020-04-12T20:00:00+00:00"]})
    features = {"line": {"10": {"comments": "EF1 tornado began near Noble.", "wfo": "OUN"},
                         "11": {"comments": "None"}},
                "polygon": {"20": {"comments": "EF1 tornado began near Noble."}}}
    refs, links = records.dat_comment_refs(hazards, features)
    assert len(refs) == 1 and refs[0]["record_id"] == "line:10;polygon:20", refs
    assert refs[0]["mentions_track"] and links[0]["link_relation"] == "comment_of"
    assert tiering.derive("NWS OUN", "dat_comment", None, None)["temporal_class"] == "post_survey"
    assert not records.mentions_track("A rain wrapped tornado caused no reported damage.")


def same_source_links_need_specific_wording() -> None:
    """Shared formulas do not link; shared tornado-specific wording does, transitively."""
    import random
    from tornado_dataset.text import same_source as ss
    assert ss.tokens("An EF-1 tornado (EF 2)") == ["an", "ef1", "tornado", "ef2"]
    formula = "the national weather service conducted a storm survey and found"
    texts = {f"h{i}": f"{formula} damage near town{i} on road{i}" for i in range(4)}
    counts = ss.hazard_counts((set(ss.runs(ss.tokens(t), 5)), {h}) for h, t in texts.items())
    common = ss.common_runs(counts, 3)
    assert hash(tuple(ss.tokens(formula)[:5])) in common, "a run of 4 hazards is a formula"
    two = ss.common_runs(ss.hazard_counts((set(ss.runs(ss.tokens(t), 5)), {h}) for h, t in
                                          list(texts.items())[:2]), 3)
    assert not two, "a run shared by two hazards is still specific"
    assert ss.common_runs(counts, None) == set(), "None switches the filter off"
    source = ("the tornado touched down west of noble and snapped dozens of trees before it "
              "crossed highway 9 and lifted east of the lake near the old mill")
    excerpt = "it crossed highway 9 and lifted east of the lake near the old mill"
    other = f"{formula} damage near town9 on road9"
    p = {k: ss.profile(t, 5, common) for k, t in
         (("source", source), ("excerpt", excerpt), ("other", other), ("f", texts["h0"]))}
    s = ss.compare(p["excerpt"], p["source"])
    assert s.a_in_b == 1.0 and s.b_in_a < 0.6 and s.shared >= 10, s
    assert ss.compare(p["f"], p["other"]).shared == 0, "only a formula in common"
    assert ss.groups(["a", "b", "c", "d"], [("a", "b"), ("c", "b")]) == {
        "a": 0, "b": 0, "c": 0, "d": 1}, "two excerpts of one text are one account"
    m, how = ss.choose_min_shared([0] * 2000, [0] * 200, 10, 0.001, 0.01)
    assert (m, how) == (10, "calibrated")
    m, _ = ss.choose_min_shared([0] * 1990 + [12] * 10, [0] * 200, 10, 0.001, 0.01)
    assert m == 13, f"0.5% of comparison pairs reach 12 shared tokens: needs 13, got {m}"
    assert ss.choose_min_shared([0] * 10, [0] * 10, 10, 0.001, 0.01)[1].startswith("floor")
    cut = ss.derive(source * 2, "truncate_170", random.Random(1))
    assert cut.endswith("(XXX)") and len(cut) <= 176
    assert ss.order_key("pns", 5, "x") < ss.order_key("lsr", 500, "a"), "PNS first on ties"


def sample_page_marks_what_was_counted() -> None:
    """The sample page highlights exactly the counted tokens and keeps the text intact."""
    import html
    import re
    from tornado_dataset.text import same_source as ss
    from tornado_dataset.text import same_source_view as view
    text = "An EF-1 tornado <b> crossed Hwy 9 & lifted...\nnear the OLD mill, chef 1 said"
    spans = ss.token_spans(text)
    assert [t for t, _, _ in spans] == ss.tokens(text), "spans must give the same tokens"
    other = ss.profile("then it crossed hwy 9, lifted near the old barn", 5, set())
    prof = ss.profile(text, 5, set())
    spans, states = view.token_states(text, prof, set(other.run_set), set(), "p")
    marked = [t for (t, _, _), s in zip(spans, states) if s == "p"]
    assert marked == ["crossed", "hwy", "9", "lifted", "near", "the", "old"], marked
    out = view.render(text, spans, states)
    assert html.unescape(re.sub(r"<[^>]+>", "", out)) == text, "the text must survive intact"
    assert "<b>" not in out, "text is escaped"


def nws_text_matches_on_repaired_times() -> None:
    """SPC's time for DAT clock errors; signs restored; cache-only fetches nothing."""
    import datetime as dt
    import tempfile
    import pandas as pd
    from tornado_dataset.dat import episode_table
    from tornado_dataset.text import iem, tiering
    hazards = pd.DataFrame({
        "hazard_uid": ["ok", "clock", "dateonly", "spc"],
        "hazard_source": ["dat", "dat", "dat", "spc"],
        "time_begin_utc": ["2020-04-12T20:00:00+00:00", "2020-04-13T02:00:00+00:00", None,
                           "2020-04-12T21:00:00+00:00"],
        "convective_day": ["2020-04-12", "2020-04-12", "2020-04-12", "2020-04-12"]})
    member = pd.DataFrame({"hazard_uid": ["ok", "clock", "dateonly", "spc"],
                           "spc_id": ["s1", "s2", "s3", "s4"],
                           "spc_link_method": ["spatial_temporal_join", "time_repaired",
                                               "date_only", "spc_record"]})
    tracks = pd.DataFrame({"spc_id": ["s1", "s2", "s3", "s4"],
                           "begin_utc": ["2020-04-12 20:00:00+00:00", "2020-04-14 01:00:00+00:00",
                                         "2020-04-12 22:30:00+00:00",
                                         "2020-04-12 21:00:00+00:00"]})
    t = episode_table.event_times(hazards, member, tracks).set_index("hazard_uid")
    assert t.time_source.to_dict() == {"ok": "dat", "clock": "spc_track",
                                       "dateonly": "spc_track", "spc": "spc"}
    assert t.at["clock", "convective_day"] == "2020-04-13", "a wrong date moves the day"
    assert t.at["dateonly", "begin_utc"].startswith("2020-04-12T22:30")
    assert t.at["ok", "begin_utc"] == "2020-04-12T20:00:00+00:00"
    assert iem.stated_point(42.79, 92.78) == (42.79, -92.78), "a lost minus sign"
    assert iem.stated_point(39.2, -39.2) is None and iem.stated_point(None, -90) is None
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp)
        assert iem.fetch_product_text("X-PNS", cache_dir=cache, offline=True) is None
        (cache / "X-PNS.txt").write_text("cached", encoding="utf-8")
        assert iem.fetch_product_text("X-PNS", cache_dir=cache, offline=True) == "cached"
        assert iem.list_pns_products(dt.date(2020, 4, 13), cache_dir=cache, offline=True) is None
        assert iem.fetch_lsr_year(2020, cache_dir=cache, offline=True) is None
    links = pd.DataFrame({"textref_uid": ["p1", "p2", "l1"], "target_uid": ["ok", "spc", "ok"],
                          "link_relation": ["primary_survey_of", "primary_survey_of",
                                            "describes"]})
    refs = pd.DataFrame({"textref_uid": ["p1", "p2", "l1"],
                         "published_at": ["2020-04-14T18:00:00+00:00",
                                          "2020-04-13T18:00:00+00:00",
                                          "2020-04-12T20:05:00+00:00"]})
    episodes = pd.DataFrame({"hazard_uid": ["ok", "spc"], "episode_uid": ["e1", "e1"]})
    first = tiering.first_surveys(links, refs, episodes)
    assert first == {"e1": dt.datetime(2020, 4, 13, 18, tzinfo=dt.timezone.utc)}, \
        "an SPC hazard's survey counts for its episode"


def lsrs_go_to_one_hazard() -> None:
    """LSR time gap to begin-end; best match by distance, then time; its basis."""
    import datetime as dt
    from tornado_dataset.text import iem
    t = lambda h, m=0: dt.datetime(2020, 4, 12, h, m, tzinfo=dt.timezone.utc)
    assert iem.lsr_time_gap_min(t(20, 5), t(20), t(20, 30)) == 0
    assert iem.lsr_time_gap_min(t(19, 15), t(20), t(20, 30)) == 45
    assert iem.lsr_time_gap_min(t(21), t(20), t(20, 30)) == 30
    assert iem.lsr_time_gap_min(t(20, 10), t(20), None) == 10, "no end: the moment it began"
    far = lambda a, b: 20_000.0
    c = lambda uid, d, gap: {"uid": uid, "distance_m": d, "gap_min": gap}
    assert iem.assign_lsr([c("a", 900, 30)], far) == ("a", "sole")
    assert iem.assign_lsr([c("a", 300, 30), c("b", 8_000, 0)], far) == ("a", "clear"), \
        "a track 3x as far does not compete, however close in time"
    assert iem.assign_lsr([c("a", 2_000, 20), c("b", 4_000, 0)], far) == ("b", "time")
    assert iem.assign_lsr([c("a", 200, 0), c("b", 600, 0)],
                          lambda a, b: 300.0) == ("a", "touching")
    assert iem.assign_lsr([c("a", 2_000, 0), c("b", 3_000, 0)], far) == ("a", "unclear")
    assert iem.assign_lsr([c("a", 2_000, 15), c("b", 3_000, 5)], far) == ("b", "unclear"), \
        "unclear: the closest in time"


def each_spc_track_counts_once() -> None:
    """Rating, deaths, injuries: SPC's, each track on one hazard; DAT's beside them."""
    import pandas as pd
    from tornado_dataset.dat import episode_table as et
    # d1 holds t1 alone; d2 and d3 share t2 (d2 ranked first), d3 also links t3
    # (no one's closest); d4 has no SPC track; s1 is the SPC hazard of t4.
    member = pd.DataFrame({
        "hazard_uid": ["d1", "d2", "d3", "d4", "s1"],
        "hazard_source": ["dat", "dat", "dat", "dat", "spc"],
        "spc_id": ["t1", "t2", "t2", None, "t4"]})
    hazards = pd.DataFrame({"hazard_uid": ["d1", "d2", "d3", "d4"],
                            "efscale": ["EF2", "EF1", "EF3+", "UNKNOWN"],
                            "fatalities": [0, 2, 2, 1], "injuries": [5, 3, 3, None]})
    tracks = pd.DataFrame({"spc_id": ["t1", "t2", "t3", "t4"], "mag": [3, 1, 2, -9],
                           "fat": [1, 2, 0, 4], "inj": [5, 3, 1, 0]})
    links = pd.DataFrame({"spc_id": ["t1", "t2", "t2", "t3"], "hazard_uid": ["d1", "d2", "d3", "d3"],
                          "rank_for_event": [1, 1, 2, 1], "distance_m": [0.0, 10.0, 5.0, 50.0]})
    v = et.hazard_values(member, hazards, tracks, links).set_index("hazard_uid")
    assert v.spc_ids_counted.fillna("").to_dict() == {"d1": "t1", "d2": "t2", "d3": "t3",
                                                      "d4": "", "s1": "t4"}
    assert int(v.deaths.sum()) == int(tracks.fat.sum()) + 1, "every track once, plus DAT-only"
    assert v.values_source.to_dict() == {"d1": "spc", "d2": "spc", "d3": "spc", "d4": "dat",
                                         "s1": "spc"}
    assert v.values_compare.to_dict() == {"d1": "one_to_one", "d2": "shared_track",
                                          "d3": "shared_track", "d4": "dat_only",
                                          "s1": "spc_only"}
    assert v.values_held_by.get("d3") == "d2" and pd.isna(v.values_held_by.get("d2"))
    assert v.rating.to_dict() == {"d1": "EF3", "d2": "EF1", "d3": "EF2", "d4": "EFU",
                                  "s1": "EFU"}, "rating: the highest of held and closest"
    assert bool(v.rating_differs.get("d1")) and bool(v.deaths_differ.get("d1"))
    assert not bool(v.injuries_differ.get("d1"))
    assert pd.isna(v.deaths_differ.get("d2")), "a shared track is not compared"
    assert v.dat_rating.get("d3") == "EF3+" and pd.isna(v.dat_rating.get("s1"))
    # Without d3's own secondary track it holds nothing: a piece of d2's tornado.
    v = et.hazard_values(member, hazards, tracks[tracks.spc_id != "t3"],
                         links[links.spc_id != "t3"]).set_index("hazard_uid")
    assert v.values_source.get("d3") == "spc_piece" and pd.isna(v.deaths.get("d3"))
    assert v.rating.get("d3") == "EF1", "a piece takes its track's rating"
    # Several tracks on one DAT hazard: compared with their sum.
    v = et.hazard_values(member.iloc[[0, 1, 3, 4]], hazards,
                         tracks, links.assign(hazard_uid=["d1", "d2", "d2", "d2"])
                         ).set_index("hazard_uid")
    assert v.values_compare.get("d2") == "several_tracks" and v.spc_deaths.get("d2") == 2
    assert v.spc_injuries.get("d2") == 4 and bool(v.injuries_differ.get("d2"))


def merge_check_samples_by_rule() -> None:
    """Stage 12's rules as strata; the sample is drawn per stratum with weights."""
    import numpy as np
    import pandas as pd
    from tornado_dataset.dat import merge_check as mc
    assert mc.stratum("endpoint_gap") == "endpoint_gap"
    assert mc.stratum("event_id+date") == "event_id"
    assert mc.stratum("path_guid;spatial_link") == "polygon"
    assert mc.stratum("endpoint_gap;spatial_link") == "mixed"
    pop = pd.DataFrame({"hazard_uid": [f"h{i}" for i in range(12)],
                        "stratum": ["endpoint_gap"] * 8 + ["polygon"] * 4})
    a = mc.draw(pop, np.random.default_rng(0), {"endpoint_gap": 2, "polygon": 10, "mixed": 3})
    b = mc.draw(pop, np.random.default_rng(0), {"endpoint_gap": 2, "polygon": 10, "mixed": 3})
    assert a.equals(b), "same seed, same sample"
    assert a.stratum.value_counts().to_dict() == {"polygon": 4, "endpoint_gap": 2}
    assert a.groupby("stratum").weight.first().to_dict() == {"endpoint_gap": 4.0, "polygon": 1.0}
    assert list(a.case_id) == [f"M{k:03d}" for k in range(1, 7)]


def hand_checks_weigh_and_validate() -> None:
    """Hand checks: labels per stratum weighted back; sheets keep their labels."""
    import tempfile
    import pandas as pd
    from tornado_dataset import handcheck
    from tornado_dataset.text import link_check
    df = pd.DataFrame({"stratum": ["a", "a", "b", "b"], "weight": [10.0, 10.0, 1.0, 1.0],
                       "label": ["x", "y", "x", None]})
    lines = handcheck.label_table(df, ("x", "y"), ["a", "b"], {"a": 20, "b": 2})
    assert lines[2] == "| a (20) | 2/2 | 1 | 1 |" and lines[3] == "| b (2) | 1/2 | 1 | 0 |"
    assert lines[4] == "| **weighted to all** | 3/4 | 52% | 48% |", lines[4]
    assert handcheck.wilson_row("s", 0, 0) == "| s | 0 of 0 | n/a |"
    with tempfile.TemporaryDirectory() as tmp:
        sheet = Path(tmp) / "s.csv"
        pd.DataFrame({"case_id": ["A1", "A2"], "label": ["", " One_Tornado "]}).to_csv(sheet)
        assert handcheck.has_labels(sheet)
        assert handcheck.read_sheet(sheet).label.tolist()[1] == "one_tornado"
    # An LSR is the same report whether its time carries seconds or not.
    assert (link_check._key("2013-10-04T22:59:00+00:00", 42.3401, -96.77)
            == link_check._key("2013-10-04T22:59+00:00", 42.34, -96.7700))
    assert {"h1", "h9", "none", "cannot_tell"} <= set(link_check.LABELS)


def official_texts_are_counted_per_hazard() -> None:
    """Texts per hazard and kind; census divisions are the Census Bureau's."""
    import tempfile
    import pandas as pd
    from tornado_dataset import config
    from tornado_dataset.geo.gazetteer import census_division
    from tornado_dataset.text import official
    assert census_division("ok") == "West South Central" and census_division("PR") == "territory"
    saved = config.PROCESSED_DIR
    with tempfile.TemporaryDirectory() as tmp:
        config.PROCESSED_DIR = Path(tmp)
        try:
            assert official.counts("t") is None, "nothing on disk: no table"
            pd.DataFrame({"textref_uid": ["p", "l1", "l2", "l1"], "target_uid": ["h1", "h1", "h1", "h2"],
                          "link_relation": ["primary_survey_of", "describes", "describes",
                                            "describes"],
                          "is_best_match": [True, False, True, True]}).to_csv(
                Path(tmp) / "textlinks_nws_t.csv")
            pd.DataFrame({"textref_uid": ["p", "l1", "l2"],
                          "lsr_source": [None, "NWS Storm Survey", "TRAINED SPOTTER"]}).to_csv(
                Path(tmp) / "textrefs_nws_t.csv")
            pd.DataFrame({"textref_uid": ["n", "c", "e"], "target_uid": ["h2", "h1", "ep"],
                          "link_level": ["hazard", "hazard", "episode"],
                          "link_relation": ["narrative_of", "comment_of", "narrative_of"]}).to_csv(
                Path(tmp) / "textlinks_records_t.csv")
            table = official.counts("t")
        finally:
            config.PROCESSED_DIR = saved
    assert list(table.columns) == list(official.KINDS)
    assert table.loc["h1"].tolist() == [1, 0, 1, 0, 1], table.loc["h1"].tolist()
    assert table.loc["h2"].tolist() == [0, 1, 0, 1, 0], "an LSR counts for its best match"
    assert "ep" not in table.index, "episode-level narratives are not a hazard's"


def map_coordinates_match_leaflet() -> None:
    """Web Mercator world pixels as Leaflet's map.project computes them."""
    from tornado_dataset.geo import pixels
    assert pixels.mercator_world(-94, 38, 0) == (61, 99)
    assert pixels.mercator_world(0, 0, 1) == (256, 256), "the origin is the map centre"
    flat = pixels.ring_to_mercator([(-94, 38), (-94, 38), (-93, 38)])
    assert len(flat) == 4, "coincident vertices are dropped"


def accents_do_not_make_duplicates() -> None:
    """Bodies differing only in an accented letter are not verbatim duplicates."""
    import pandas as pd
    from tornado_dataset.text import lexisnexis as ln
    df = ln.add_duplicate_flags(pd.DataFrame({"body": [
        "Tornado hits Beyoncé's hometown.", "Tornado hits Beyonce's hometown.",
        "TORNADO hits   Beyoncé's hometown!", ""]}))
    assert df.is_duplicate.tolist() == [False, False, True, False], df.is_duplicate.tolist()
    assert df.dup_group.tolist()[:3] == [0, 1, 0]


def wind_features_are_not_tornadoes() -> None:
    """Only an explicit non-tornado rating keeps a DAT feature out; unrated ones stay."""
    from tornado_dataset.dat import hazards as hz
    assert not hz.is_tornado_rating("TSTM/Wind") and not hz.is_tornado_rating(" tstm/wind ")
    for rating in ("EF1", "EFU", "UNKNOWN", "N/A", None, "Tropical"):
        assert hz.is_tornado_rating(rating), rating
    kept, out = hz.split_by_rating([{"properties": {"efscale": "EF0"}},
                                    {"properties": {"efscale": "TSTM/Wind"}}])
    assert len(kept) == len(out) == 1


def unclaimed_polygons_become_hazards() -> None:
    """Touching polygons of one tornado form a hazard; a linked one, or one hours later, does not."""
    import datetime as dt
    from shapely.geometry import box
    from tornado_dataset.dat import hazards as hz

    def polygon(oid, x, when, ef="EF1"):          # shaped as link.prepare leaves it
        g = box(x, 0, x + 1000, 1000)
        return {"objectid": oid, "globalid": f"G{oid}", "geom": g, "proj": g,
                "date": dt.datetime.fromisoformat(when).date(),
                "properties": {"stormdate": when, "efscale": ef,
                                             "comments": f"survey {oid}"}}
    ps = [polygon(1, 0, "2020-04-12T20:00:00+00:00"),            # nested contours …
          polygon(2, 500, "2020-04-12T20:30:00+00:00", "EF2"),   # … of one tornado
          polygon(3, 1100, "2020-04-12T23:30:00+00:00"),         # 100 m on, 3 h later
          polygon(4, 50_000, "2020-04-13T00:00:00+00:00"),       # date only, far away
          polygon(5, 1050, "2020-04-12T20:10:00+00:00")]         # linked to a line
    built, stats = hz.build_polygon_hazards(ps, [{"polygon_oid": 5}])
    groups = sorted(h["polygon_objectids"] for h in built)
    assert groups == ["1;2", "3", "4"] or groups == ["2;1", "3", "4"], groups
    first = next(h for h in built if h["n_polygons"] == 2)
    assert first["efscale"] == "EF2" and first["geometry_source"] == "polygon"
    assert first["time_begin_utc"].startswith("2020-04-12T20:00")
    alone = next(h for h in built if h["polygon_objectids"] == "4")
    assert alone["time_begin_utc"] is None and alone["convective_day"] == "2020-04-13"
    assert stats["polygon_hazards_date_only"] == 1


def date_only_hazards_match_by_date() -> None:
    """A hazard with a date but no time matches a record nearby within a day, by date."""
    import datetime as dt
    import pandas as pd
    from shapely.geometry import LineString, box
    from tornado_dataset.dat import storm_events
    targets = pd.DataFrame({"geom": [box(0, 0, 1000, 1000), box(0, 0, 1000, 1000)],
                            "t0": [pd.NaT, pd.Timestamp("2020-04-12T20:00", tz="UTC")],
                            "t1": [pd.NaT, pd.Timestamp("2020-04-12T20:10", tz="UTC")],
                            "date": [dt.date(2020, 4, 12), dt.date(2020, 4, 12)]})
    near = LineString([(500, 500), (3000, 500)])
    begin = pd.Series(pd.to_datetime(["2020-04-13T02:00", "2020-04-15T02:00"], utc=True))
    pairs = storm_events.match_pairs(begin, begin, [near, near], targets)
    got = {(r.row, r.hz, bool(r.by_date)) for r in pairs.itertuples()}
    assert got == {(0, 0, True)}, got        # timed hazard: 6 h apart; second record: 3 days


def watch_records_and_texts_parse() -> None:
    """County records place a tornado by its own county's times; texts give relations."""
    import pandas as pd
    from tornado_dataset.dat import spc_watches as sw
    csv = ("wfo,utc_issue,utc_expire,utc_prodissue,utc_init_expire,phenomena,gtype,"
           "significance,eventid,status,ugc,vtec_year\n"
           "HUN,2011-04-27 13:10,2011-04-27 18:45,2011-04-27 13:08,201104271900,TO,C,A,"
           "230,CAN,ALC089,2011\n"
           "HUN,2011-04-27 13:10,2011-04-27 15:00,2011-04-27 13:08,201104271900,TO,C,A,"
           "230,CAN,ALC083,2011\n"
           "MOB,2011-04-27 13:10,2011-04-27 18:45,2011-04-27 13:08,201104271900,TO,Z,A,"
           "230,CAN,GMZ650,2011\n")
    rec = sw.parse_county_records(csv)
    assert len(rec) == 2 and set(rec.type) == {"TOR"} and rec.num.iloc[0] == 230
    tracks = pd.DataFrame({"spc_id": ["a", "b", "c"], "st": ["AL", "AL", "AL"],
                           "f1": [89, 83, 0],
                           "begin_utc": ["2011-04-27T16:00Z"] * 3})
    ugc = sw.tornado_ugc(tracks)
    assert ugc[:2].tolist() == ["ALC089", "ALC083"] and pd.isna(ugc[2]), ugc.tolist()
    hits = sw.county_hits(tracks, rec)
    assert hits.spc_id.tolist() == ["a"], "county ALC083 was cleared at 15:00"
    text = ("\x01\n265\nWWUS20 KWNS 271310\nSEL0\nURGENT\nTORNADO WATCH NUMBER 231\n"
            "THIS TORNADO WATCH REPLACES TORNADO WATCH NUMBER 225. WATCH NUMBER 225 WILL "
            "NOT BE IN EFFECT AFTER 900 AM CDT.\nOTHER WATCH INFORMATION...CONTINUE..."
            "WW 226...WW 227...\n\x03\x01\n300\nWWUS20 KWNS 271330\nSEL8\n"
            "SEVERE THUNDERSTORM WATCH NUMBER 38\nOTHER WATCH INFORMATION...THIS SEVERE "
            "THUNDERSTORM WATCH REPLACES SEVERE THUNDERSTORM WATCH NUMBER 36...TORNADO WATCH "
            "NUMBER 37. WATCH NUMBER 36 37 WILL NOT BE IN EFFECT AFTER 650 PM CDT.\n"
            "\x03\x01\n808\nWWUS20 KWNS 271400\nSEL5\n"
            "The NWS Storm Prediction Center has cancelled Severe Thunderstorm Watch 228\n\x03")
    t = sw.parse_watch_texts(text)
    assert len(t) == 3
    assert t.replaces[1] == [36, 37] and t.not_in_effect[1] == [36, 37], t.loc[1].to_dict()
    assert t.num[0] == 231 and t.type[0] == "TOR" and t.replaces[0] == [225]
    assert t.not_in_effect[0] == [225] and t.continues[0] == [226, 227]
    assert t.cancellation[2] and t.num[2] == 228 and t.type[2] == "SVR"
    no_soh = text.replace("\x01", "").replace("\x03", "")
    assert len(sw.split_products(no_soh)) == 3, "header split without control characters"


def watch_systems_follow_the_three_rules() -> None:
    """Concurrent county links; downstream successors link, upstream ones are held for review."""
    import pandas as pd
    from tornado_dataset.dat import spc_watches as sw
    T = lambda s: pd.Timestamp(s, tz="UTC")
    # Watch 1 over county A then B (moving east); watch 2 takes over east of B;
    # watch 3 starts west of A (upstream) right after; watch 4 shares county B with 1.
    rec = pd.DataFrame({
        "year": [2011] * 6, "num": [1, 1, 2, 3, 4, 5], "type": ["TOR"] * 6,
        "ugc": ["XXC001", "XXC002", "XXC003", "XXC000", "XXC002", "XXC009"],
        "wfo": ["AAA"] * 6, "status": ["EXP"] * 6,
        "start": [T("2011-04-27 12:00"), T("2011-04-27 12:00"), T("2011-04-27 17:30"),
                  T("2011-04-27 17:30"), T("2011-04-27 14:00"), T("2011-04-28 12:00")],
        "end": [T("2011-04-27 15:00"), T("2011-04-27 18:00"), T("2011-04-27 22:00"),
                T("2011-04-27 22:00"), T("2011-04-27 16:00"), T("2011-04-28 15:00")]})
    poly = pd.DataFrame({"year": [2011] * 5, "num": [1, 2, 3, 4, 5], "type": ["TOR"] * 5,
                         "issue": [T("2011-04-27 12:00")] * 4 + [T("2011-04-28 12:00")],
                         "expire": [T("2011-04-28 00:00")] * 4 + [T("2011-04-28 18:00")],
                         "is_pds": [0] * 5, "mv_drct": [270.0] * 5, "mv_sknt": [40.0] * 5,
                         "geometry": [None] * 5})
    texts = sw.parse_watch_texts("")
    texts["year"] = 2011
    from shapely.geometry import box
    xs = [-40e3, 0, 40e3, 80e3, 3000e3]      # 40 km squares: neighbours touch
    geo = pd.DataFrame({"ugc": ["XXC000", "XXC001", "XXC002", "XXC003", "XXC009"],
                        "geometry": [box(x - 20e3, -20e3, x + 20e3, 20e3) for x in xs],
                        "x": xs, "y": [0.0] * 5, "reach": [20e3 * 2 ** .5] * 5})
    hfo = rec.iloc[[0]].assign(ugc="HIC007", start=T("2011-12-19 10:00"), end=T("2011-12-19 18:00"))
    typo = rec.iloc[[0]].assign(ugc="XXC001", start=T("2011-08-01 10:00"), end=T("2011-08-01 12:00"))
    cleaned, notes = sw.clean_county_records(pd.concat([rec, hfo, typo], ignore_index=True), poly)
    assert len(cleaned) == len(rec) and notes["dropped_outside_spc_area"] == 1 \
        and notes["dropped_after_expiry"] == 1, notes
    w, c = sw.build_watches(cleaned, poly, texts)
    l1 = sw.concurrent_links(c)
    assert {tuple(sorted(x)) for x in zip(l1.a, l1.b)} == {("2011_0001", "2011_0004")}
    # "Replaces watch 765" on 1 January means last year's 765, not this year's.
    ny = pd.DataFrame({"wid": ["2010_0765", "2011_0001", "2011_0765"],
                       "first_start": [T("2010-12-31 20:00"), T("2011-01-01 02:00"), T("2011-08-01 12:00")],
                       "last_end": [T("2011-01-01 03:00"), T("2011-01-01 09:00"), T("2011-08-01 18:00")],
                       "replaces": ["", "2011_0765", ""]})
    l2 = sw.explicit_links(ny)
    assert list(zip(l2.a, l2.b)) == [("2010_0765", "2011_0001")], l2.to_dict("records")
    fp = sw.Footprints(w, c, geo)
    cand = sw.succession_candidates(w, fp)
    one_two = cand[(cand.a == "2011_0001") & (cand.b == "2011_0002")]
    assert one_two.edge_m.iloc[0] == 0.0, "touching counties are 0 km apart"
    l3, rej = sw.inferred_links(cand, motion_slack_m=50e3)
    pairs3 = set(zip(l3.a, l3.b))
    assert ("2011_0001", "2011_0002") in pairs3, cand.to_dict("records")
    assert set(zip(rej.a, rej.b)) >= {("2011_0001", "2011_0003")}, "upstream must be held"
    # The pruned search must return the exact minimum distance.
    import numpy as np
    import shapely
    rng = np.random.default_rng(0)
    ga = np.array([box(x, y, x + 5e3, y + 5e3) for x, y in rng.uniform(0, 3e5, (30, 2))])
    gb = np.array([box(x, y, x + 5e3, y + 5e3) for x, y in rng.uniform(4e5, 7e5, (30, 2))])
    ca = np.array([[g.centroid.x, g.centroid.y] for g in ga])
    cb = np.array([[g.centroid.x, g.centroid.y] for g in gb])
    lower = np.hypot(*(ca[:, None, :] - cb[None, :, :]).transpose(2, 0, 1)) - 2 * 2.5e3 * 2 ** .5
    exact = shapely.distance(ga[:, None], gb[None, :]).min()
    assert abs(sw._min_distance(ga, gb, lower, chunk=8) - exact) < 1e-6
    w["system_id"] = sw.systems(w, pd.concat([l1, l3]))
    sid = dict(zip(w.wid, w.system_id))
    assert sid["2011_0001"] == sid["2011_0002"] == sid["2011_0004"] != sid["2011_0005"]
    # Watch 2 begins while watch 1 still runs next door: a side-by-side link, not
    # a hand-over; watch 4 had ended before watch 2 began, so that one is a hand-over.
    seq = set(zip(*[sw.sequence_links(pd.concat([l1, l3]))[c] for c in ("a", "b")]))
    assert ("2011_0001", "2011_0002") not in seq and ("2011_0004", "2011_0002") in seq, seq
    tracks = pd.DataFrame({"spc_id": ["t1", "t2"], "yr": [2011, 2011], "mag": [1, 2],
                           "st": ["XX", "XX"], "f1": [2, 9], "slat": [0, 0], "slon": [0, 0],
                           "begin_utc": ["2011-04-27T14:30Z", "2011-04-28T09:00Z"]})
    a = sw.assign_tornadoes(tracks, c, poly, sid)
    assert a.system_id[0] == sid["2011_0001"] and a.n_systems[0] == 1, a.to_dict("records")
    assert a.method[1] == "none", "t2 starts before its county's watch"


def watch_scores_see_merging_across_offices() -> None:
    """Merging two watch systems costs precision; the cross-office part isolates it."""
    import pandas as pd
    from tornado_dataset.dat import episodes
    system = pd.Series(["s1", "s1", "s2", "s2", None])
    wfo = pd.Series(["OUN", "TSA", "OUN", "TSA", "OUN"])
    exact = episodes.score_watch(pd.Series([0, 0, 1, 1, 2]), system, wfo)
    assert exact["recall"] == exact["precision"] == exact["f1"] == 1.0, exact
    merged = episodes.score_watch(pd.Series([0, 0, 0, 0, 0]), system, wfo)
    assert merged["recall"] == 1.0 and abs(merged["precision"] - 2 / 6) < 1e-9, merged
    # Grouped cross-office pairs: (1,2) (1,4) (2,3) (3,4) — two within a system.
    assert abs(merged["cross_office_precision"] - 0.5) < 1e-9, merged
    assert merged["scored"] == 4, "the unwatched tornado is left out"
    split = episodes.score_watch(pd.Series([0, 1, 2, 3, 4]), system, wfo)
    assert split["recall"] == 0.0 and split["systems_split"] == 1.0


for name, fn in [
    ("evidence windows reach late mentions", evidence_windows_reach_late_mentions),
    ("paywall stub is a failure, not an article", paywall_stub_is_a_failure_not_an_article),
    ("uncached GDELT query is a third state", uncached_gdelt_query_is_a_third_state),
    ("url normalisation keeps the article id", url_normalisation_keeps_the_article_id),
    ("story id separates recurring headlines", story_id_separates_recurring_headlines),
    ("components are transitive", components_are_transitive),
    ("soft 404 to the front page is caught", soft_404_to_the_front_page_is_caught),
    ("english check separates prose from spanish", english_check_separates_prose_from_spanish),
    ("unparseable answer is not a judgement", unparseable_answer_is_not_a_judgement),
    ("protect rule is enforced", protect_rule_is_enforced),
    ("dedup groups collapse syndication", dedup_groups_collapse_syndication),
    ("title similarity separates stories", title_similarity_separates_stories),
    ("body key is content-derived", body_key_is_content_derived),
    ("kappa corrects for rare flags", kappa_corrects_for_rare_flags),
    ("full-text bodies keep both labels apart", fulltext_bodies_keep_both_labels_apart),
    ("cross-corpus reads either edge direction", cross_corpus_reads_either_edge_direction),
    ("archive re-fetch skips settled, retries transient",
     archive_refetch_skips_settled_and_retries_transient),
    ("storm events times are standard time", storm_events_times_are_standard_time),
    ("mistyped end dates are repaired", mistyped_end_dates_are_repaired),
    ("space-time links across the day boundary", space_time_links_across_the_day_boundary),
    ("county segments chain and link offices",
     county_segments_chain_into_tornadoes_and_link_offices),
    ("spc records are CST and whole tracks", spc_records_are_cst_and_whole_tracks),
    ("DAT clock errors are repaired on the hour", dat_clock_errors_are_repaired_on_the_hour),
    ("the same footprint links a free SPC track", same_footprint_links_a_free_spc_track),
    ("hazard times take SPC's or repaired ends", hazard_times_take_spc_or_repaired_ends),
    ("DAT reference extends through SPC", dat_reference_extends_through_spc),
    ("spc episodes carry to DAT hazards", spc_episodes_carry_to_dat_hazards),
    ("episode counts cover all SPC tornadoes", episode_counts_cover_all_spc_tornadoes),
    ("every SPC episode is published with its hazards",
     every_spc_episode_is_published_with_its_hazards),
    ("populations go to the nearest namesake", populations_go_to_the_nearest_namesake),
    ("place and county names fold", place_and_county_names_fold),
    ("counties need a share, offices an order", counties_need_a_share_and_offices_an_order),
    ("record texts link once and count as oracle", record_texts_link_once_and_count_as_oracle),
    ("same-source links need specific wording", same_source_links_need_specific_wording),
    ("sample page marks what was counted", sample_page_marks_what_was_counted),
    ("LSRs go to one hazard", lsrs_go_to_one_hazard),
    ("each SPC track counts once", each_spc_track_counts_once),
    ("merge check samples by rule", merge_check_samples_by_rule),
    ("hand checks weigh and validate", hand_checks_weigh_and_validate),
    ("official texts are counted per hazard", official_texts_are_counted_per_hazard),
    ("map coordinates match Leaflet", map_coordinates_match_leaflet),
    ("NWS text matches on repaired times", nws_text_matches_on_repaired_times),
    ("accents do not make duplicates", accents_do_not_make_duplicates),
    ("wind features are not tornadoes", wind_features_are_not_tornadoes),
    ("unclaimed polygons become hazards", unclaimed_polygons_become_hazards),
    ("date-only hazards match by date", date_only_hazards_match_by_date),
    ("watch records and texts parse", watch_records_and_texts_parse),
    ("watch systems follow the three rules", watch_systems_follow_the_three_rules),
    ("watch scores see merging across offices", watch_scores_see_merging_across_offices),
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
