"""Independence tiering: the two axes every TextRef is classified on.

The dataset asks whether a damage footprint can be inferred from text. That
question only has meaning if we can say, for each text, **who wrote it** and
**when**, relative to the survey that produced the ground-truth geometry. A
single 0-3 "tier" conflates the two, so both are recorded (DATA_MODEL.md v0.2):

*Axis 1* ``same_org_as_geometry`` — is the author the NWS/NOAA organisation that
drew the polygon? Text written by the survey team cannot be an independent test
of whether text predicts the survey; it is downstream of it.

*Axis 2* ``temporal_class`` — ``forecast`` (before onset) · ``nowcast`` (during or
just after, before the field survey) · ``post_event_pre_survey`` · ``post_survey``.

Their 2x2 gives the derived ``text_role``:

|                   | independent                 | NWS/NOAA (same org) |
|-------------------|-----------------------------|---------------------|
| pre-survey        | ``independent_timely``      | ``official_timely`` |
| post-survey       | ``independent_retrospective`` | ``oracle``        |

Every assignment carries ``tier_rule_version``. When the rules change, existing
rows stay interpretable and the corpus can be re-tiered reproducibly — which is
why this is one function rather than logic scattered across the connectors.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

TIER_RULE_VERSION = "tier_rules_v2_2026-11"
# v2: source types written from the survey by construction are post-survey
# without a publication time (POST_SURVEY_SOURCE_TYPES); v1 rows are unchanged
# for every other type.

# Source types produced by the same organisation that surveys the damage.
NWS_SOURCE_TYPES = {"lsr", "pns", "nws_warning", "survey_report",
                    "storm_events_narrative", "storm_events_episode_narrative", "dat_comment"}
# Written from the survey by construction, and carrying no publication time:
# the Storm Data narratives (compiled by the office after the event month) and
# the comments surveyors enter on DAT features. Without this rule a missing time
# falls back to "pre-survey", and the survey's own words would count as timely.
POST_SURVEY_SOURCE_TYPES = {"storm_events_narrative", "storm_events_episode_narrative",
                            "dat_comment"}
# Author-organisation markers for NWS/NOAA, matched case-insensitively.
NWS_ORG_MARKERS = ("nws", "national weather service", "noaa", "weather.gov",
                   "storm prediction center", "spc")

TEXT_ROLES = {
    (True, True): "oracle",                       # same org, post-survey
    (True, False): "official_timely",             # same org, pre-survey
    (False, True): "independent_retrospective",   # independent, post-survey
    (False, False): "independent_timely",         # independent, pre-survey
}
INDEPENDENCE_TIER = {"ground_truth": 0, "oracle": 1, "official_timely": 2,
                     "independent_timely": 2, "independent_retrospective": 3}


def _as_datetime(value: Any) -> dt.datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


def is_same_org(author_org: str | None, source_type: str | None) -> bool:
    """Whether the author is the NWS/NOAA organisation behind the geometry."""
    if str(source_type or "").lower() in NWS_SOURCE_TYPES:
        return True
    org = str(author_org or "").lower()
    return any(marker in org for marker in NWS_ORG_MARKERS)


def temporal_class(published_at: Any, event_begin: Any, survey_at: Any = None) -> str:
    """Where a text sits on the event -> survey timeline.

    An unknown survey time is treated as *not yet surveyed* rather than guessed:
    calling something ``post_survey`` without knowing when the survey happened
    would manufacture the very circularity the axis exists to detect.
    """
    published = _as_datetime(published_at)
    begin = _as_datetime(event_begin)
    survey = _as_datetime(survey_at)
    if published is None or begin is None:
        return "post_event_pre_survey"       # conservative default
    if published < begin:
        return "forecast"
    if survey is not None and published >= survey:
        return "post_survey"
    # Within the first day the text describes an unfolding event; afterwards it
    # is retrospective reporting that still predates any survey product.
    return "nowcast" if (published - begin) <= dt.timedelta(hours=24) else "post_event_pre_survey"


def derive(author_org: str | None, source_type: str | None, published_at: Any,
           event_begin: Any, survey_at: Any = None) -> dict[str, Any]:
    """Full independence classification for one text reference."""
    same_org = is_same_org(author_org, source_type)
    if str(source_type or "").lower() in POST_SURVEY_SOURCE_TYPES:
        tclass = "post_survey"
    else:
        tclass = temporal_class(published_at, event_begin, survey_at)
    role = TEXT_ROLES[(same_org, tclass == "post_survey")]
    published = _as_datetime(published_at)
    begin = _as_datetime(event_begin)
    offset_hours = round((published - begin).total_seconds() / 3600, 2) \
        if published and begin else None
    return {
        "same_org_as_geometry": same_org,
        "temporal_class": tclass,
        "text_role": role,
        "independence_tier": INDEPENDENCE_TIER[role],
        "time_offset_hours": offset_hours,
        "tier_rule_version": TIER_RULE_VERSION,
    }
