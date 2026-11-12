# Disaster Text–Geometry Dataset — Data Model Specification (v0.2)

A dataset pairing natural-language descriptions of natural disasters with authoritative
damage geometries (polygon / polyline) and attributes, built to measure how accurately
humans and GeoAI systems can infer a disaster's spatial footprint from text.

## Design decisions locked for v0.2

| Decision | Choice | Consequence for the model |
|----------|--------|---------------------------|
| Temporal regime | **Both, staged** | Collect an all-text corpus with a per-item `time_offset`, then derive frozen-horizon subsets. Every text item carries publication time and (where available) a Wayback snapshot, so horizons like T+6h / T+24h / T+72h are *views*, not separate collections. |
| Record granularity | **Two-level** | An `Episode` (e.g. an outbreak) contains one or more `Hazard` tracks (one tornado each). Text links at **either** level via a join table with a `link_level` flag, so an outbreak article can attach to the episode while a survey PIS attaches to one track. |
| Scope | **Disaster-general** | Geometry is abstracted to *line-or-polygon + hazard_type*; hazard-specific attributes live in a typed key–value block, so floods / wildfires / hurricanes fit without a refactor. Tornado fields are the first populated profile. |

## Entities

```
Episode 1───* Hazard 1───* Geometry
   │              │
   └──────*───────┴───* TextRef   (via TextLink join, link_level = episode|hazard)
```

### 1. Episode
A named, time-bounded disaster event that groups one or more hazards. For the pilot,
an outbreak (e.g. "Tornado outbreak of March 13–16, 2025").

Key fields: `episode_uid`, `title`, `hazard_family` (tornado|flood|wildfire|tropical_cyclone|…),
`time_begin_utc`, `time_end_utc`, `country`, `admin_regions[]`, external IDs
(`ncei_episode_id`, `fema_disaster_no`, `wikipedia_title`), `source_refs[]`.

As built (stage 15, `dat/episode_table.py`): SPC's complete tornado list grouped by
single linkage within 400 km and 6 h (closest points of the tracks; end of one
tornado to start of the next; no day boundary). SPC is the population: every SPC
episode is published, `has_dat` flagging those with a DAT survey. Counts cover
every SPC tornado in the episode (`n_spc`, `n_spc_ef1plus`, `n_spc_unrated`, SPC
casualties), so a minimum size such as ≥6 EF1+ is a filter on them; `n_dat` and
`n_spc_hazards` count its hazards by source, and `max_efscale`, `fatalities`,
`injuries` are the DAT surveys' (empty without one). `convective_days` lists every
12 UTC day the episode touches. Membership lives in `hazard_episodes_<tag>.csv`,
not on the hazards.

### 2. Hazard
One authoritative sub-event with its own geometry — one tornado track, one flood extent,
one burn scar. 

Key fields: `hazard_uid`, `episode_uid` (FK), `hazard_type`, `time_begin_utc`,
`time_end_utc`, external IDs (`ncei_event_id`, `dat_event_ids[]`), `wfo`,
plus a typed **`attributes`** block whose schema is selected by `hazard_type`
(tornado profile below).

As built, a hazard has a `hazard_source`:

- `dat` — a DAT survey (stage 12, `hazards_<tag>.csv`). With an SPC track it is in
  that track's episode (`in_spc`); without one it is in **no episode** and carries
  `spc_match_status` (`time_mismatch`, `probable_duplicate`, `spc_far`,
  `no_spc_nearby`, `untimed_no_spc`) and its nearest SPC track.
- `spc` — an SPC tornado no DAT survey covers (stage 15, `spc_hazards_<tag>.csv`),
  with SPC's rating, casualties, length and width and its straight start→end line
  (`geometry_source` `spc_line`, or `spc_point` without an end).

Counties, offices (`wfo`, `wfo_source`, `wfo_all`) and place names for both are in
stage 16's `hazard_geography_<tag>.csv`.

A hazard's times are in stage 15's `hazard_episodes_<tag>.csv`: `begin_utc`,
`end_utc`, `convective_day`, with `time_source` (`dat`, `spc`, or `spc_track` where
DAT's time was wrong or missing and SPC's track gives it) and `end_repaired` (a DAT
end with a mistyped date, its clock time kept; an end that cannot be repaired is
empty). `time_begin_utc` and `time_end_utc` in `hazards_<tag>.csv` are DAT's as
entered, kept for provenance.

### 3. Geometry
One geospatial ground-truth object attached to a hazard. A hazard may have several
(a line *and* a polygon *and* points).

Key fields: `geometry_uid`, `hazard_uid` (FK), `geom_role` (track_line | damage_polygon |
point_damage | inferred_extent), `geojson` (or a `geometry_ref` to a GeoJSON/GeoPackage
file for large features), `crs` (default EPSG:4326), and **provenance**:
`source` (noaa_dat | ncei | spc | copernicus_ems | mtbs | …), `source_feature_id`,
`surveying_org`, `survey_date`, `access_url`, `retrieved_at`.

#### The line↔polygon linkage problem
Because DAT `event_id` is free text and unreliable, link is stored explicitly, not assumed:
- `link_method` — `shared_event_id` | `spatial_temporal_join` | `manual`
- `link_confidence` — 0–1
- `link_evidence` — e.g. `{ "hausdorff_m": 240, "date_match": true, "rating_match": true, "polygon_contains_line_frac": 0.87 }`

A line and polygon are candidate-linked when geometries are proximate/overlapping, dates
coincide, and rating/attributes agree — recorded so the join is auditable and reproducible.

#### What a hazard rests on (`geometry_source`)
DAT features rated as not a tornado (`TSTM/Wind`, `config.NON_TORNADO_RATINGS`) are
left out, lines and polygons alike; every other rating, unrated included, stays in.
A hazard is then `line` (track line(s) only), `line+polygon` (with the polygons linked
to its lines) or `polygon` (polygons no line claims: a tornado surveyed without a
drawn track; touching polygons of one day and within an hour form one hazard). A
`polygon` hazard has no path length, no WFO until stage 16 backfills it, no end time,
and — where DAT gives only a date — no start time either. An SPC hazard's geometry
is `spc_line` or `spc_point`; stage 16 measures that an SPC line finds 98.6% of the
counties and 98% of the places of the surveyed track of the same tornado.

### 4. TextRef
A single natural-language artifact **stored by reference, not by body** (copyright-safe).

Key fields: `textref_uid`, `url`, `source_name`, `source_type`
(news | wire | nws_warning | lsr | pns | storm_events_narrative |
storm_events_episode_narrative | dat_comment | tv_caption | radio | social | encyclopedic |
survey_report | official_statement), `author_org` (the publishing organization, e.g.
"NWS Little Rock", "Arkansas Democrat-Gazette"), `language`, `published_at`, `retrieved_at`,
`wayback_snapshot_url`, `title`, `snippet` (short, fair-use-length quote only), the two
independence axes **`same_org_as_geometry`** (bool) and **`temporal_class`**, the derived
**`text_role`** and coarse **`independence_tier`** (see below), and derived NLP outputs you
*may* store: `toponym_spans[]`
(`{text, char_start, char_end, resolved_lat, resolved_lon, gazetteer, confidence}`),
`geoparse_model`, `content_hash`.

> Store URLs, metadata, extracted toponyms, and short snippets — **not** full article bodies.
> Full text is retrieved on demand from the link or from a licensed library database.

### 5. TextLink (join)
Connects a `TextRef` to an `Episode` or a `Hazard`.

Key fields: `textref_uid` (FK), `target_uid` (FK), `link_level` (episode | hazard),
`link_relation` (describes | mentions | primary_survey_of | narrative_of | comment_of |
episode_narrative_of), `time_offset` (published_at −
hazard/episode begin, ISO 8601 duration, signed), `linker` (auto | manual), `link_confidence`.

An LSR (`describes`, stage 20) is linked to every hazard within reach and is
*about* one of them: `is_best_match` marks that one, and every count of a
hazard's texts uses it alone. `lsr_candidates` is how many hazards were within
reach; `lsr_time_gap_min` the minutes from the hazard's begin–end to the report
(0 inside it); `lsr_assignment` how the best match was found — `sole`, `clear`
(every other track at least 3× as far), `time` (of tracks about as near, the
report falls in one's begin–end), `touching` (tracks within 1 km: pieces of one
tornado, or crossing) or `unclear` (closest in time, a guess).

### 6. Same-source edit group (stage 25)
Which official texts of one hazard are edits of one account
(`same_source_edits_<tag>.csv`, one row per hazard and text). Two texts are linked
when enough of their tokens lie in shared 5-token runs that are rare in the
texts of other tornadoes (at least 10, calibrated; the value used is
`min_shared` in the manifest); linked texts form a group.

Key fields: `hazard_uid`, `textref_uid`, `source_type`, `link_relation`,
`edit_group` (per hazard), `group_size`, `group_source_types`, `is_representative`
and `representative_uid` (the member covering most of the others' wording; ties
PNS > narrative > DAT comment > LSR), `coverage_by_representative`,
`contained_in` (the member covering ≥80% of this text), `max_coverage`,
`bridged`, `comparable` (enough specific tokens to be linked at all),
`n_tokens`, `n_specific`, `hazard_texts`, `hazard_accounts`. No field says which
text was written first: the texts do not show it. Every compared pair, with both
coverages, is in `data/interim/same_source_pairs_<tag>.csv`.

## Independence — two orthogonal axes (the pivotal methodological design)

A single 0–3 "tier" conflates two independent questions. v0.2 records them separately on
every `TextRef`, because the experiments depend on being able to slice them apart:

**Axis 1 — `same_org_as_geometry` (boolean).** Is the text author the *same organization*
(NWS/NOAA) that produced the ground-truth geometry? This is the circularity axis. Text
written by the survey team cannot be an *independent* test of whether text predicts the
survey — it is downstream of it.

**Axis 2 — `temporal_class` (enum).** When was the text produced, relative to event and
survey? `forecast` (before) · `nowcast` (during / immediately after, **before** the field
survey) · `post_event_pre_survey` · `post_survey` (after the survey that made the geometry).
This is the timeliness / information-availability axis.

The two axes give a 2×2 that maps directly onto the source landscape:

| | **independent** (not NWS/NOAA) | **same_org** (NWS/NOAA) |
|---|---|---|
| **timely** (forecast/nowcast, pre-survey) | **independent-timely** — real-time news, breaking TV, social. *The honest nowcasting input.* | **official-timely** — LSRs, warnings, PNS issued during the event. Public-domain, timely, but same-org. |
| **retrospective** (post-survey) | **independent-retrospective** — later news, encyclopedic write-ups. | **oracle** — DAT comments, PNS survey summaries, NCEI narratives. *Near-circular with geometry.* |

`text_role` is the derived single-label convenience field with exactly these four values
(plus `ground_truth` for the geometry itself); `independence_tier` (0–3) is kept as a coarse
alias (0 = geometry, 1 = oracle, 2 = timely, 3 = retrospective) but the two axes are canonical.

### Why this serves the user's two experiments

The dataset is built to support **two separable NL-text experiments**, and the axes are what
make each one clean:

1. **Text→text ("can independent text reproduce the oracle text?")** — input =
   `independent` text (optionally + `official-timely`); target = `oracle` text. Tests whether
   the rich, survey-grade description can be *generated* from what was independently
   observable. Requires the `same_org_as_geometry` flag to define input vs target.
2. **Text→geometry ("even from the oracle text, can we recover the authoritative
   polygon/polyline?")** — input = `oracle` text; target = geometry. Establishes the **upper
   bound**: if the survey team's own prose can't reconstruct the footprint, no independent
   text can. Requires `temporal_class=post_survey & same_org` to isolate the oracle.

The honest end-to-end task chains them: `independent-timely` text → geometry, with the oracle
providing the ceiling and the text→text step providing an interpretable intermediate.

Slicing views: **independent-timely only** = true nowcasting · **all independent** = all
public text · **oracle** = ceiling · **official-timely** = public-domain same-org (include or
exclude per experiment, tagged either way).

Both axes are assigned by rule from (`author_org`, `source_type`, `published_at`,
`survey_date`); the rule id is stored in `tier_rule_version` so re-tiering stays reproducible.
Since `tier_rules_v2`, Storm Events narratives and DAT comments are `post_survey` by source
type: they are written from the survey and carry no publication time, and a missing time
would otherwise fall back to pre-survey.

## Caveats recorded as data, not assumed away
- **Ground truth is an estimate.** DAT/NCEI geometries are field-survey products; coverage
  varies by WFO and surveyors cannot reach every location. `survey_date`, `surveying_org`,
  and a free `geometry_caveats` field record this per geometry.
- **Independence is a judgement.** `independence_tier` is assigned by rule (source_type +
  authorship + timing) and the rule is stored in `tier_rule_version` so re-tiering is traceable.
- **Texts of one hazard are not independent of each other.** Narratives, DAT comments
  and survey LSRs often reuse the survey statement's wording. `edit_group` (stage 25)
  records which texts are one account; it detects verbatim reuse, not paraphrase.
