# NOAA Tornado Damage Assessment — Analysis Report

> Generated 2026-06-15 17:25 UTC from `data/events_1976-03-01_2026-06-14_nonempty-comments.geojson`

## Overview

| | |
|---|---|
| Tornado events | 9,143 |
| Built from | 3,279 damage polygons + 8,943 path lines |
| Date range | 1979-08-05 – 2026-06-12 |
| Total injuries | 8,259 |
| Total fatalities | 660 |
| Total property damage | $18,322,764 |
| Total crop damage | $3,518,455 |

---

## EF-Scale Distribution

Non-standard ratings reported by NOAA (`EFU`, `UNKNOWN`, `N/A`) are grouped as **Unknown**; `TSTM/Wind` and `Tropical` are grouped as **Other**; `EF3+` is counted as **EF3**.

![EF-scale distribution](figures/ef_scale_distribution.png)

---

## Temporal Patterns

![Events per year](figures/events_per_year.png)

![Seasonal distribution](figures/seasonal_distribution.png)

---

## Geographic Distribution

_9,129 of 9,143 events have a usable centroid within the continental US / Alaska / Hawaii / Puerto Rico bounding box._

![Geographic distribution](figures/geographic_distribution.png)

---

## Track Geometry

_7,856 events with a known track length, 991 with a known max damage width._

![Track geometry](figures/track_geometry.png)

---

## Human Impact

![Human impact by EF-scale](figures/human_impact.png)

### 10 Deadliest Events

| Date | EF | Fatalities | Injuries | WFO |
|---|---|---|---|---|
| 2011-04-27 | EF5 | 65 | 1500 | JAN |
| 2011-04-27 | EF4 | 65 | 1500 | n/a |
| 2011-04-27 | EF5 | 25 | 0 | n/a |
| 2019-03-03 | EF4 | 23 | 90 | BMX |
| 2017-05-28 | EF4 | 19 | 87 | n/a |
| 2023-03-25 | EF4 | 17 | 165 | JAN |
| 2021-12-11 | EF3 | 17 | 63 | n/a |
| 2014-04-28 | EF4 | 16 | 193 | LZK |
| 2015-12-27 | EF4 | 10 | 468 | FWD |
| 2010-04-24 | EF4 | 10 | 146 | JAN |

### 10 Costliest Events

| Date | EF | Property Damage | Crop Damage | WFO |
|---|---|---|---|---|
| 2011-04-27 | EF3 | $7,300,000 | $0 | MEG |
| 2013-05-28 | EF3 | $1,800,000 | $3,500,000 | n/a |
| 2020-01-11 | EF1 | $2,000,000 | $0 | n/a |
| 2011-02-25 | EF2 | $1,525,000 | $0 | MEG,OHX |
| 2023-03-31 | EF1 | $1,000,000 | $0 | MKX |
| 2012-02-29 | EF2 | $1,000,000 | $0 | OHX |
| 2021-03-13 | EF2 | $600,000 | $0 | n/a |
| 2024-06-20 | EF1 | $500,000 | $0 | CYS |
| 2015-05-24 | EF1 | $400,000 | $0 | n/a |
| 2021-03-13 | EF1 | $300,000 | $0 | n/a |

---

## Comment & Georeferencing Analysis

Each event's `comments` field is run through spaCy NER (`en_core_web_sm`). Comments containing at least one entity tagged `GPE` (geo-political entity), `LOC` (location), or `FAC` (facility) are considered to describe a place that could be used to georeference the event's track/polygon from text alone.

| | |
|---|---|
| Events with a comment | 9,142 (100.0%) |
| **Events with a georeferenceable description** | **6,049 (66.2%)** |

![Comment length distribution](figures/comment_word_count.png)

_The 6,049 georeferenceable events were written to `outputs/georeferenceable_events.geojson`._
