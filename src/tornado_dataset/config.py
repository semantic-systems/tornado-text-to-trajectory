"""Central configuration for the tornado text-geometry dataset pipeline.

Every tunable that affects *what the dataset contains* lives here, so a run is
described by this module plus the git SHA recorded in the manifest. Values that
encode a methodological choice carry the reasoning in a comment — they are part
of the dataset documentation, not incidental constants.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"            # verbatim API responses, never edited
INTERIM_DIR = DATA_DIR / "interim"    # intermediate tables (links, candidates)
PROCESSED_DIR = DATA_DIR / "processed"  # dataset-grade outputs
OUTPUT_DIR = REPO_ROOT / "outputs"    # reports and figures

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
MAX_PLACES_PER_HAZARD = 8

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
