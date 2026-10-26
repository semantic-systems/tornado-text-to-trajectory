"""Central configuration for the tornado text-geometry dataset pipeline.

Every tunable that affects *what the dataset contains* lives here, so a run is
described by this module plus the git SHA recorded in the manifest. Values that
encode a methodological choice carry the reasoning in a comment — they are part
of the dataset documentation, not incidental constants.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
# `data/` is 4.7 GB and is not in git. It lives on the group server at
#   192.168.106.17:/data/share/geoai/tornado-text-to-trajectory/data
# so a colleague either copies it or mounts it, and then points the pipeline at
# it with TORNADO_DATA_DIR rather than moving it into the working tree:
#
#   export TORNADO_DATA_DIR=/mnt/geoai/tornado-text-to-trajectory/data
#
# The value must be a path this machine can open — a local directory or a mount
# point. It is not an SSH URL: nothing here speaks SSH, and a `host:/path` string
# would be silently created as a directory named "host:" in the current
# directory, which is exactly the kind of failure that looks like an empty
# dataset rather than a misconfiguration.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _dir_from_env(variable: str, default: Path) -> Path:
    raw = os.environ.get(variable)
    if not raw:
        return default
    if ":" in raw.split("/")[0] and not raw[1:3] == ":\\":   # host:/path, not C:\
        raise SystemExit(
            f"{variable}={raw!r} looks like a remote location. This project reads "
            "a local filesystem path; mount the share first (for example with "
            "sshfs) and point the variable at the mount point."
        )
    return Path(raw).expanduser().resolve()


DATA_DIR = _dir_from_env("TORNADO_DATA_DIR", REPO_ROOT / "data")
RAW_DIR = DATA_DIR / "raw"            # verbatim API responses, never edited
INTERIM_DIR = DATA_DIR / "interim"    # intermediate tables (links, candidates)
PROCESSED_DIR = DATA_DIR / "processed"  # dataset-grade outputs
# Reports are small and tracked in git, so they default to the working tree even
# when the data lives elsewhere; override only if you want them beside the data.
OUTPUT_DIR = _dir_from_env("TORNADO_OUTPUT_DIR", REPO_ROOT / "outputs")

# Where the canonical copy lives, for the error messages that need to say so.
DATA_SHARE = "192.168.106.17:/data/share/geoai/tornado-text-to-trajectory/data"


def require_data(*paths: Path) -> None:
    """Fail with the location of the canonical copy, not with a bare ENOENT.

    Every stage reads from `data/`, which is not in git. A colleague who has not
    obtained it should be told where it is and how to point at it, rather than
    left to interpret a missing-file traceback.
    """
    missing = [p for p in (paths or (DATA_DIR,)) if not p.exists()]
    if not missing:
        return
    where = "\n".join(f"  {p}" for p in missing)
    raise SystemExit(
        f"missing input:\n{where}\n\n"
        f"data/ is {('set by TORNADO_DATA_DIR to ' + str(DATA_DIR)) if 'TORNADO_DATA_DIR' in os.environ else 'expected at ' + str(DATA_DIR)}.\n"
        f"The canonical copy lives on the group server at\n  {DATA_SHARE}\n"
        "Copy or mount it, then point the pipeline at the local path:\n"
        "  export TORNADO_DATA_DIR=/path/to/tornado-text-to-trajectory/data"
    )

# ── temporal scope ───────────────────────────────────────────────────────────
# Geometry window. Closed on both ends and fully in the past, so a rerun of the
# pipeline sees the same population apart from retroactive DAT edits (which the
# manifest's retrieved_at makes visible).
WINDOW_START = date(2010, 1, 1)
WINDOW_END = date(2025, 12, 31)

# The GDELT DOC 2.0 API refuses startdatetime values before this date
# ("Invalid query start date"), verified against the live API on 2026-07-29.
# Hazards before it can carry oracle/official text but no GDELT news links.
GDELT_COVERAGE_START = date(2017, 1, 1)

# ── NOAA DAT feature service ─────────────────────────────────────────────────
DAT_BASE_URL = (
    "https://services.dat.noaa.gov/arcgis/rest/services/"
    "nws_damageassessmenttoolkit/DamageViewer/FeatureServer"
)
DAT_LAYERS = {"points": 0, "lines": 1, "polygons": 2}

# Some numeric/text columns on the polygon layer intermittently raise HTTP 400
# ("Unable to complete operation") when requested in a batch outFields list.
# These reduced field sets are the documented-safe fallback for such a chunk.
DAT_SAFE_FIELDS = {
    0: "objectid,globalid,event_id,stormdate,efscale,comments",
    1: ("objectid,globalid,event_id,stormdate,starttime,endtime,length,width,"
        "efscale,injuries,fatalities,comments,wfo"),
    2: ("objectid,globalid,event_id,stormdate,efscale,length,width,injuries,"
        "fatalities,comments,qc,path_guid"),
}

# Epoch-millisecond fields that are converted to ISO 8601 on ingest.
DAT_DATE_FIELDS = ("stormdate", "starttime", "endtime", "edit_time",
                   "created_date", "last_edited_date")

# Placeholder strings the DAT editor writes instead of a real NULL.
PLACEHOLDER_TEXT_VALUES = ("NONE", "N/A", "NULL", "NA", "UNKNOWN")

# ── HTTP behaviour ───────────────────────────────────────────────────────────
HTTP_TIMEOUT = 120
HTTP_RETRIES = 4
HTTP_BACKOFF = 1.5      # seconds, multiplied by the attempt number
# A rate limiter is not a transient error and must not be retried on the ordinary
# backoff: GDELT refused 38% of a sustained sweep's queries with HTTP 429 even at
# one request per 12-16 s, and four retries seconds apart all hit the same wall.
HTTP_RATE_LIMIT_BACKOFF = 45.0
DAT_CHUNK_SIZE = 200    # objectIds per attribute+geometry request
DAT_SLEEP = 0.2         # polite pause between DAT requests

# ── geometry / linkage ───────────────────────────────────────────────────────
CRS_WGS84 = "EPSG:4326"
# CONUS Albers Equal Area (metres): gap and containment metrics are true
# distances rather than degrees, which vary with latitude.
CRS_EQUAL_AREA = "EPSG:5070"

# Candidate generation is deliberately wider than the accepted-link threshold, so
# the evaluation can sweep operating points *upward* instead of only narrowing a
# pre-filtered set — and so near-misses stay visible as data.
LINK_SEARCH_RADIUS_M = 1000.0
LINK_SEARCH_MAX_DATE_DELTA_DAYS = 2

# Accepted link: gap threshold, which also sets the scale on which proximity
# decays in link_confidence. 200 m is the operating point chosen in
# outputs/dat_qa_report.md from the sweep against the path_guid gold set.
LINK_GAP_THRESHOLD_M = 200.0
# Buffer applied to the polygon when measuring how much of the line lies inside
# it, absorbing digitising jitter between two independently drawn features.
LINK_BUFFER_M = 50.0
# Survey dates for the same tornado can straddle midnight UTC between the line
# and polygon record, so allow one day; anything wider would let tornadoes from
# different years at the same place link up.
LINK_MAX_DATE_DELTA_DAYS = 1

# ── hazard / episode assembly ────────────────────────────────────────────────
# Two line segments are treated as one tornado track when an endpoint of one is
# within this distance of an endpoint of the other on the same convective day.
# 3 km is well above typical survey-segmentation gaps and well below the spacing
# of distinct tornadoes in an outbreak.
HAZARD_ENDPOINT_GAP_M = 3000.0
# Minimum geometric link confidence for a polygon to be merged into a hazard.
HAZARD_MIN_LINK_CONFIDENCE = 0.5
# Convective day boundary (UTC hour). NWS convention runs 12Z-12Z so that a
# night-time outbreak is not split across two calendar dates.
CONVECTIVE_DAY_START_HOUR = 12
# Hazards on the same convective day join one episode when their tracks are
# within this distance — an outbreak is a spatially coherent cluster, not every
# tornado in the country that day.
EPISODE_LINK_DISTANCE_M = 200_000.0

# ── geography ────────────────────────────────────────────────────────────────
# Populated places within this distance of a track are treated as its toponyms.
# 25 km is roughly what local reporting names as "the place that was hit"; wider
# radii pull in the next town over and dilute a news query.
PLACE_RADIUS_M = 25_000.0
# Query budget. This governs the `places` column ONLY, which builds the GDELT
# query strings — changing it changes every query, hence every cache key, hence a
# full refetch. It is deliberately decoupled from the matching set below.
MAX_PLACES_PER_HAZARD = 8

# The matching set is a different problem from the query set. Capping matching at
# the eight nearest names was the single largest cause of missed article links:
# 97% of hazards hit that cap while 40-100 places sat within range, and because
# selection was nearest-first the eight were hamlets ("Buffalo Mop") rather than
# the towns news actually names. See docs/linking_coverage_analysis.md.
PLACE_MATCH_RADIUS_M = 25_000.0
MAX_MATCH_PLACES_PER_HAZARD = 150
# A city is named in coverage well beyond the damage path ("a tornado near
# Tuscaloosa"), so prominent places get a wider radius of their own.
PLACE_PROMINENT_RADIUS_M = 50_000.0
PLACE_PROMINENT_MIN_POPULATION = 20_000
# The largest place in each county the track crosses, as a county-seat proxy:
# local reporting is organised by county and names its seat.
INCLUDE_COUNTY_LARGEST_PLACE = True

# ── NWS / IEM text ───────────────────────────────────────────────────────────
IEM_BASE = "https://mesonet.agron.iastate.edu"
# LSR types that describe a tornado (as opposed to wind/hail damage).
LSR_TORNADO_TYPES = ("TORNADO", "FUNNEL CLOUD", "LANDSPOUT", "WATERSPOUT")
# An LSR belongs to a hazard when it falls within this distance of the track and
# inside the time window. Tornado LSRs are point estimates reported by spotters
# under duress; 25 km absorbs that positional error without spanning two
# tornadoes in an outbreak.
LSR_MATCH_RADIUS_M = 25_000.0
LSR_MATCH_WINDOW_HOURS = 6
# Storm-survey PNS products are issued in the days after an event; this is how
# far ahead of the convective day to look for them.
PNS_SURVEY_WINDOW_DAYS = 10
# A survey section states its own start/end coordinates, so it can be matched to
# a DAT track geometrically: both endpoints must lie within this distance of the
# track. Chosen from the observed distribution, which is sharply bimodal — true
# counterparts sit at a median of 58 m (path lengths agreeing 1.00), while
# neighbouring tornadoes in the same outbreak appear only beyond 12 km. 5 km
# keeps the first mode with room for DAT/survey disagreement and excludes the
# second. See outputs/text_qa_report.md.
PNS_MATCH_RADIUS_M = 5_000.0
# Pre-template survey products carry no coordinates, so they are matched by
# office, date and place name. One name is not enough — "Madison" or "Central"
# appears in products about unrelated tornadoes the same office surveyed that
# week — so a link requires this many of the hazard's toponyms in the text.
PNS_LEGACY_MIN_NAME_HITS = 2
IEM_MIN_REQUEST_INTERVAL = 0.5  # be a good citizen on a free academic service

# ── GDELT ────────────────────────────────────────────────────────────────────
GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
# The DOC API returns HTTP 429 with an explicit "one every 5 seconds" message.
GDELT_MIN_REQUEST_INTERVAL = 5.5
GDELT_MAX_RECORDS = 250
# News window around an episode: from the convective day to a week after, which
# covers breaking coverage through the follow-up reporting that names the EF
# rating. Retrospectives beyond it are a separate, later query.
GDELT_WINDOW_DAYS_BEFORE = 0
GDELT_WINDOW_DAYS_AFTER = 7

WAYBACK_AVAILABILITY_URL = "https://archive.org/wayback/available"

# ── article → event linking (Stage C) ────────────────────────────────────────
# Candidate window: an article can look back over the aftermath reporting period
# and forward over forecast coverage. Measured on the current corpus, this leaves
# a median of 22 candidate episodes (125 hazards) per article — a shortlist, which
# the toponym step then has to decide.
LINK_DAYS_BEFORE_EVENT = 3      # article published up to 3 days *before* onset
LINK_DAYS_AFTER_EVENT = 14      # …up to 14 days after
# Place names are matched as 1–3 token n-grams ("Cave City", "Oak Grove").
LINK_MAX_NAME_TOKENS = 3
# Where a name appears changes what it means: a headline names the subject, a body
# also names context.
LINK_POSITION_WEIGHTS = {"headline": 1.5, "dateline": 1.5, "lede": 1.2, "body": 1.0}
LINK_LEDE_PARAGRAPHS = 2
# Specificity: a state-level hit is weak evidence and never sufficient alone.
LINK_LEVEL_WEIGHTS = {"place": 1.0, "county": 0.7, "state": 0.35}
# Saturation constant for the toponym sum, so an article naming twenty places
# cannot outscore one naming the right place unmistakably.
LINK_TOPONYM_SATURATION = 2.0
# How the two halves of the score combine. Deliberately simple and stored per
# component in the output, so both can be re-weighted after annotation without
# re-running the expensive parts.
LINK_WEIGHT_TOPONYM = 0.6
LINK_WEIGHT_CORROBORATION = 0.4
# Floor for writing a link into the *candidate* file. Lowered from 0.25 because
# the candidate/publish split means a low floor costs nothing in rigour: the
# median near-miss scored 0.218 and 1,229 of 1,784 near-misses clear 0.15, which
# is material the annotation should get to judge rather than material we discard
# on an unmeasured hunch. The *publishable* threshold comes from the annotated
# sample (docs/stage_c_plan.md §4) and from nothing else.
LINK_MIN_SCORE = 0.15
# A bare year ("the 2011 tornado") pins nothing on its own, so a year-only
# retrospective candidate is admitted only behind a strong place match that sits
# in the headline or lede. Without the position requirement the pass links to
# *an* outbreak in the right year rather than the right one — it sent a Joplin
# 2011 article to the April 2011 Super Outbreak.
LINK_YEAR_ONLY_MIN_TOPONYM = 0.45
LINK_YEAR_ONLY_REQUIRE_PROMINENT = True
# …and the non-geographic evidence has to agree too. A prominent name is not
# enough when the true event is absent from DAT: the Joplin EF5 of 22 May 2011
# (158 dead) has no surveyed geometry at all, so an article about it found only
# "Joplin" near the April 2011 Super Outbreak and linked there. Requiring the
# rating / casualty / date signals to agree refuses that link instead of
# inventing one.
LINK_YEAR_ONLY_MIN_CORROBORATION = 0.5

# An article is about a few events, not dozens. The cap keeps a wire round-up
# from contributing a hundred weak candidates that would swamp the annotation
# sample; ranked by score, so what survives is the strongest evidence.
LINK_MAX_PER_ARTICLE = 12
# A hazard-level link needs the best hazard to beat the runner-up by this factor,
# otherwise the article is about the outbreak and stays at episode level.
LINK_HAZARD_MARGIN = 1.4
LINK_HAZARD_MIN_SCORE = 0.3

# ── LexisNexis ↔ GDELT overlap (Stage C) ────────────────────────────────────
OVERLAP_DATE_TOLERANCE_DAYS = 3
OVERLAP_TITLE_SIMILARITY = 0.72     # same story, different desk edit
OVERLAP_TITLE_SIMILARITY_STRICT = 0.90   # accept without a source match

# ── Wikipedia (stage 23) ─────────────────────────────────────────────────────
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
# Wikimedia asks for serial requests and no hard rate; 0.2 s keeps a full
# discovery run to a few minutes. Wikidata is stricter: its query service was
# refusing everything above 1 req/min during probing (2026-10-21), so discovery
# uses the ordinary Wikidata search API instead, at 1 s.
WIKIPEDIA_MIN_REQUEST_INTERVAL = 0.2
WIKIDATA_MIN_REQUEST_INTERVAL = 1.0

# Only these two kinds of page are text sources. Per-tornado rows in the monthly
# and per-outbreak "List of …" pages paraphrase the NCEI narrative they cite, so
# they would enter the corpus as near-oracle text dressed as independent text;
# they are kept for lookup (the NCEI event ids they cite) and nothing else.
# The yearly "Tornadoes of <year>" pages are global; only their US event
# sections are text (see wikipedia.yearly_sections).
WIKIPEDIA_TEXT_KINDS = ("tornado", "outbreak", "yearly")

# Where the census lists live: every monthly/seasonal US list, and the lists
# split off from large outbreak articles. Their rows are the tornado census.
WIKIPEDIA_CENSUS_CATEGORIES = (
    "Category:Lists of tornadoes in the United States by time",
    "Category:Lists of tornadoes by outbreak",
)
# Hand-curated overview pages whose links are a discovery channel of their
# own — suggested as entry points and checked on 2026-10-26, when none of them
# linked an in-scope page the other channels had missed.
WIKIPEDIA_HUB_PAGES = (
    "List of North American tornadoes and tornado outbreaks",
    "List of F5, EF5, and IF5 tornadoes",
    "List of F4, EF4, and IF4 tornadoes",
    "List of F4, EF4, and IF4 tornadoes (2020–present)",
    "List of F3, EF3, and IF3 tornadoes (2020–present)",
)

# Wikidata classes whose items are discovery candidates: tornado (Q8081) and
# tornado outbreak (Q2696963), checked against known articles on 2026-10-21.
WIKIDATA_CLASSES = ("Q8081", "Q2696963")

# Full-text search catches articles that are missing from the year categories
# and navboxes. Each query is kept narrow; anything off-topic it returns is
# classified out later rather than trusted.
WIKIPEDIA_SEARCH_QUERIES = (
    'hastemplate:"Infobox weather event/Tornado"',
    'hastemplate:"Infobox weather event" intitle:outbreak',
    'intitle:"tornado outbreak"',
    'intitle:tornado incategory:"Tornado outbreaks in the United States"',
)

# The parent heading under which an outbreak article gives each significant
# tornado its own subsection. Matched case-insensitively against level-2
# headings; an outbreak article with none of these is listed in the report.
WIKIPEDIA_TORNADO_SECTION_PARENTS = (
    "confirmed tornadoes", "notable tornadoes", "tornadoes",
    "tornado summary", "significant tornadoes",
)

# ── Wikipedia reference coverage (stage 24) ─────────────────────────────────
# The title tiers reuse OVERLAP_DATE_TOLERANCE_DAYS and the OVERLAP_TITLE_*
# thresholds above, so "same story" means the same thing here as in the atlas.
# The weak tier widens the window to a week — print editions run a day or two
# behind the web copy Wikipedia cites, and corrections run later still — and
# accepts partial headline agreement, but only within the same outlet.
WIKI_REF_FUZZY_DATE_DAYS = 7
WIKI_REF_FUZZY_JACCARD = 0.5
WIKI_REF_FUZZY_CONTAINMENT = 0.75
# A near-identical headline from a *different* outlet is accepted as syndicated
# copy only when it is long enough to be distinctive: "Tornado hits town" is
# five words and matches a dozen unrelated stories.
WIKI_REF_SYNDICATED_MIN_TOKENS = 5
# Content tier: 8-word shingles, one in eight kept by hash, so the LexisNexis
# index fits in memory. Half the cited article's sampled shingles must appear in
# one LexisNexis body — wire copy trimmed by a local desk still clears that, a
# different article about the same tornado does not — and the dates must be
# within two weeks, so a later article quoting the first does not count.
WIKI_REF_SHINGLE_WORDS = 8
WIKI_REF_SHINGLE_SAMPLE = 8
WIKI_REF_MIN_SHINGLES = 8          # ≈ 70 words of text before a containment means anything
WIKI_REF_CONTENT_CONTAINMENT = 0.5
WIKI_REF_CONTENT_DATE_DAYS = 14
