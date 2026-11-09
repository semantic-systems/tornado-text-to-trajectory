# Plan — an outbreak reference from SPC watches

Status: **step 0 done (2026-10-27), see below; steps 1–4 built and run on 2010–2025 (`scripts/26_watch_systems.py`, report `outputs/watch_systems_report.md`); step 5 built (stage 25); hand checks open.** Thread 6 in HANDOVER.

## Why

Stage 25 scores episode definitions against NCEI Storm Events episodes, which
are filed per forecast office: they test whether a method *splits* a weather
system, but they cannot see whether it *over-merges* across offices, because no
Storm Events episode spans two offices except where a tornado crossed between
them (linked episodes, stage 24). There is no authoritative cross-office
outbreak record; the literature defines outbreaks by rule (Galway 1977;
Fuhrmann et al. 2014) or by calendar day with manual review (Schneider,
Schaefer & Brooks 2004, who chose fixed days precisely because event
boundaries are "somewhat arbitrary").

SPC tornado and severe thunderstorm watches are a forecaster-made grouping that
does cross offices: SPC issues them per convective system, over whole regions,
and replaces or extends them as the system moves. Tornadoes that fall in one
connected sequence of watches were, in real time, treated by SPC as one
threat.

**Framing.** The reference is an *operational and communication* grouping, not
a physical one. For this dataset that is a strength rather than a compromise:
the dataset links tornadoes to news, and watches are the unit in which the
threat was announced to the public, emergency managers and the press. A watch
system is therefore a defensible definition of "one event" for text linking in
its own right, and it is independent of every method stage 25 compares. It is
used **alongside** the office episodes, not instead of them: conclusions should
hold against both.

## Scope

**In:** watch systems as a third reference in stage 25.

**Out, deliberately:** physical references — radar storm tracks for tornado
families (e.g. GridRad-Severe, Murphy, Homeyer & Allen 2023) and
extratropical-cyclone attribution from reanalysis (e.g. Kiefer et al. 2025,
preprint). They answer a meteorological question (do these tornadoes share a
parent storm or a synoptic system?) that the dataset's purpose — valid links
between texts and tornadoes, episodes and outbreaks — does not require, and
their validation needs domain expertise outside the project's audience. The
limitation is stated in the dataset documentation; a reader who needs physical
grouping can join those products to the published tornado identifiers.

## Data

### Primary: county-level watch records

Since the mid-2000s the official watch area is a **list of counties**, not a
shape. SPC lists the counties in the **WOU** (Watch Outline Update); each local
office then updates its own counties with **WCN** (Watch County Notification)
products as the watch runs — clearing counties early once the threat has
passed, or adding counties and extending the time in coordination with SPC.

IEM parses these into per-county records with their own start, end and cancel
times, in its VTEC watch/warning archive:
<https://mesonet.agron.iastate.edu/request/gis/watchwarn.phtml>, backend
`cgi-bin/request/gis/watchwarn.py`, watches coded `TO.A` (tornado) and `SV.A`
(severe thunderstorm), with the watch number as the event tracking number and
county shapes included.

Using these means a tornado counts as "in a watch" only when *its county* was
under a watch *at that minute*: counties cleared early, and extensions to new
counties, are handled as they were in reality.

To check first (feasibility step 0, `python scripts/26_watch_systems.py probe`,
report in `outputs/watch_probe_report.md`):

- the first year with complete `TO.A`/`SV.A` county records (expected mid-2000s,
  i.e. the whole 2010–2025 window; to confirm);
- that the county records carry the watch number and SPC's watch type, so they
  can be joined to the watch attributes below;
- how marine and zone-based entries appear, so they can be filtered.

### Secondary: watch attributes and polygons

The IEM SPC watch archive —
<https://mesonet.agron.iastate.edu/request/gis/spc_watch.phtml>, backend
`cgi-bin/request/gis/spc_watch.py` (`sts`, `ets` as ISO UTC,
`format=geojson|csv|shp|kml`) — gives per watch: `ISSUE`, `EXPIRE` (UTC), `NUM`
(resets yearly), `TYPE` (`TOR`/`SVR`), `IS_PDS`, storm motion
`MV_DRCT`/`MV_SKNT`, and probabilities (`P_TORTWO`, `P_TOREF2`, …) from about
May 2006.

Its polygons are the aviation parallelogram from the SAW product ("*x* miles
either side of a line from A to B"), which IEM rightly notes are "not the
official spatial bounds anymore". Since county records cover the whole window
(step 0), polygons serve only for the watch attributes, for the ~2% of
tornadoes SPC records without a county, and for validation 5.

### Watch text: explicit replacements

The public watch text (SEL product, archived by IEM's NWS text archive) states
succession in prose, e.g. that a new watch *replaces* an earlier one, which
"will not be in effect after" a given time. Where this parses reliably it gives
watch-to-watch links made by SPC itself, instead of inferred ones. A
feasibility check on one season decided its role (step 0): it is reliable but
rare, so it is a secondary link and the test set for inferred succession.

### Step 0 results — `outputs/watch_probe_report.md`

| question | result | consequence |
|---|---|---|
| first year with county records | 2006 (99% of April watches; none in 2004–05) | county records are the primary source for all of 2010–2025; no polygon fallback by year |
| county records carry number and type | 100% join their polygon by year + number; type agrees 100% | watch attributes (motion, PDS) join directly |
| county timing | 55% of county records end >30 min before the watch expires (median 132 min early); none later | county-level timing is essential |
| tornadoes, counties vs polygons (spring 2011, 1,330 SPC tracks) | 1,078 in a watch both ways, 87 by county only, 36 by polygon only, 129 in none; 86% of the 1,078 in the same watch | ~20% of tornadoes are placed differently by polygons; the county choice is justified by numbers |
| concurrent coverage | 3 tornadoes' counties under two watches at once | rule 1 of step 3 is rare, as expected |
| "replaces" statements | 52 of 543 watches in 2011 (~10%), 1 of 103 in April 2024 | rare, and rarer in recent practice: inferred succession (rule 3) carries the method |
| parse quality | first parse missed the second watch in 11 multi-watch replacements; fixed; all 53 statements now agree with the separate "will not be in effect" sentence | rule 2 is used; its links double as a labelled test set for rule 3 |

Watch numbers are shared by tornado and severe thunderstorm watches within a
year (a tornado watch can replace severe thunderstorm watch 99), so a watch is
identified by year + number, with the type an attribute.

## Method

**Step 1 — fetch.** One request per year, 2010–2025, for the county records and
the watch attributes, into `data/raw/spc_watches/`, with provenance as in stage
24; the watch texts per year likewise, if step 0 passes.

**Step 2 — tornado → watch.** The anchor is the SPC whole track (decision 2),
placed in its county: the county shape that contains its start point, checked
against SPC's own first-county code; in practice the county is taken from
that code directly (`st` + `C` + `f1`, the UGC code the watch records use), and
the ~2% of tracks without one fall back to the polygon. It is *in* a watch when
that county's record for the watch is active at the tornado's start time —
after the county's own start, before its own end or cancellation. Recorded per
tornado: the watch (or watches), its type, and the margin in minutes to the
county's start and end. Tornadoes in no watch are kept and counted — a known,
non-random class (weak, quickly forming, QLCS and tropical-cyclone tornadoes)
whose share is itself a result.

**Step 3 — watch → watch (the sequence).** Watches are linked into systems by
three rules, in order of authority:

1. **Concurrent coverage.** Two watches active in the *same county at the same
   time* are always linked. This should be rare — when SPC re-issues an area,
   the county normally leaves the old watch as it joins the new — and its count
   is reported as a diagnostic.
2. **Explicit succession.** A "replaces watch N" statement parsed from the text
   links the two watches, whatever their geometry.
3. **Inferred succession.** Watch B follows watch A when B's first county
   becomes active after A's and no later than *Δt* after A's last county
   ends, **and** B's first counties (active within an hour of its start) lie
   within *d* of A's counties **at the hand-over** (still active within an
   hour of B's start, or of A's end if that is earlier) — county-level timing,
   so a watch whose counties were already cleared does not reach into its
   successor's area — **and** B does not lie upstream of A's storm motion:
   the displacement between the two footprints' centres, along the direction
   storms move (`MV_DRCT` + 180°, as `MV_DRCT` is the direction storms come
   *from*), must not be below a tolerance **calibrated on SPC's stated
   successions**: the value that 95% of "replaces" links pass (fallback 50 km
   with fewer than 20 links), with 0, 2× and no check in the sensitivity grid.
   A candidate that fails only the motion
   check is **not** linked; it is listed for review, because it is the typical
   signature of two separate systems whose watches happen to touch. Rule 3 is
   evaluated for all pairs; where rule 2 also links them, the result is the
   same, and the share of rule-2 links that rules 1 and 3 reproduce on their
   own is the test of rule 3 against SPC's stated succession.

   *Distance* *d* is the distance between county edges, from the Census 2020
   cartographic boundary file (1:500,000, simplified to 500 m; 0 for
   neighbouring counties). 2020 because later files replace Connecticut's
   counties with planning regions, which NWS county codes do not use.

   *Speed limit* — the plan's bound of storm speed × Δt — is not a rule: the
   edge-distance condition already bounds how far a successor can be. It is
   reported as a diagnostic: the share of links whose footprint centres move
   farther than storms at `MV_SKNT` travel in the gap plus the hand-over hour,
   for rule-3 and for "replaces" links alike.

Connected components of these links (union-find, as elsewhere in the pipeline)
are **watch systems**. `TOR` and `SVR` watches are linked alike (decision 1),
with the type kept. Candidate defaults to test: *Δt* = 3 h,
*d* = 50 km.

The motion check and the county timing exist to stop **over-chaining**: with
overlap alone, two genuinely separate systems (a Plains and a Gulf Coast
system, say) can be joined through one pair of touching watches.

**Step 4 — tornado → system.** A tornado's reference label is the system of the
watch it is in. No tie-break is needed: if a tornado's county is under two
watches at that minute, rule 1 of step 3 has linked those watches, so the
tornado is in one system **by construction**. One label per tornado is what
the stage 25 scores require (pair-based recall and precision, and the adjusted
Rand index, compare partitions). Unwatched tornadoes get no label and are
excluded from scoring, as Storm Events-unmatched hazards are now.

**Step 5 — use it in stage 25.** Add the watch-system label as a third
reference next to `EPISODE_ID` and `LINKED_EPISODE`, carried to DAT hazards
through `spc_tornado_links_<tag>.csv` (stage 24). Because systems span
offices, this is the first reference that can score **cross-office
precision**: of hazard pairs a method groups, the share SPC also treated as one
system. Recall against it is informative too, but weaker, since one weather
system can run through two watch sequences with a gap between them.

*As built (2026-10-27):* the first run showed that one reference granularity
cannot rank methods. Most rule-3 links (6,852 of 7,680) join watches in force at
the same time whose counties touch — side-by-side watches along one front — so
**systems** (all links) are connected watch coverage, ~790 km across for the
median tornado, coarser than every method. **Sequences** (rule 3 only where B
begins after A ended, plus rules 1 and 2) are one chain of hand-overs, ~260 km,
finer than every method. F1 against either ranks methods by how close their
granularity is to that one definition, and the ranking flips between the two.
Stage 25 therefore uses them as **bounds**: *within systems* (precision against
systems, and its cross-office part) flags merging beyond anything SPC
connected; *sequences kept* (recall against sequences) flags cutting a chain
SPC ran as one. F1 values stay in the metrics CSV, not in the report's ranking.

## Validation before it is used as a reference

1. **Coverage:** share of tornadoes inside any watch, per year and EF rating.
   If it is low, the reference only describes watched tornadoes, and the report
   must say so.
2. **Agreement with the office reference:** recall of Storm Events episodes
   against watch systems. Office episodes should rarely be split across two
   systems; where they are, read the cases.
3. **Named outbreaks:** 15–20 well-documented events, stratified by size and by
   whether they cross 12 UTC (e.g. 2011-04-25/28, 2013-11-17, 2020-04-12/13,
   2021-12-10/11, 2023-03-31/04-01, 2024-04-26/28), checked by hand against NWS
   office and SPC event summaries: one system, several, or merged with another?
4. **Sensitivity:** *Δt* ∈ {1, 3, 6} h × *d* ∈ {0, 50, 150} km, and with the
   motion check on and off. A reference whose conclusions flip within that
   range is not a reference.
5. **Counties against polygons:** for one recent year, build systems from both;
   report how many tornadoes change watch or system. This quantifies what the
   official-bounds choice changes and justifies the polygon fallback (or not).
6. **Review lists:** motion-check rejections and concurrent-coverage cases, a
   sample read by hand.

## Risks and limits

- **Forecast, not observation.** Watches encode where SPC *expected* severe
  weather, including false alarms and boundaries drawn along county lines for
  communication. Two separate systems under one large watch are merged; one
  system covered by consecutive watches with a gap is split. This is stated as
  the reference's definition, not hidden as noise.
- **Unwatched tornadoes** are systematically different, so any score against
  this reference is conditional on being watched.
- **County size** varies: large western counties make "in the watch" coarse.
- **Practice changes over time**: watch sizes and products changed during
  2010–2025; report results by period.
- **Circularity:** none with the methods compared — watch geometry does not
  depend on tornado locations — but forecasters drew later watches knowing
  where earlier tornadoes had occurred, and offices cleared counties once the
  threat had passed, so the reference is not independent of the observed track
  pattern either.

## Deliverables and effort

| piece | where | effort |
|---|---|---|
| feasibility: county-record coverage, watch-text parsing | notes in this file | ½ day |
| fetch + load county records, attributes, texts | `src/tornado_dataset/dat/spc_watches.py`, stage 26 `fetch` | ½–1 day |
| tornado ↔ watch, the three linking rules, systems | same module, stage 26 `link` | 1–2 days |
| replacement parsing (if feasible) | same | ½–1 day |
| validation report (coverage, office agreement, sensitivity, counties vs polygons) | `outputs/watch_systems_report.md` | 1 day |
| named-outbreak check, review lists | hand work, sheet under `outputs/annotation/` | ½–1 day |
| third reference in stage 25 | `scripts/25_compare_episodes.py` | ½ day |

## Decisions

1. *Decided:* `SVR` watches are linked as well as `TOR` — a system often
   starts under a severe thunderstorm watch and is upgraded as it organises.
   The type is kept on every watch and tornado, so results can also be shown
   for tornado watches only.
2. *Decided:* the anchor is SPC whole tracks (complete and reviewed). DAT
   hazards receive their system through the stage 24 SPC ↔ DAT links; a DAT
   hazard without an SPC match falls back to its own start point and is
   counted separately in the report.
3. *Decided:* the forecast-made reference is acceptable for publication when
   framed as the operational and communication unit, used alongside the office
   episodes, with conclusions required to hold against both.
4. *Decided:* physical references are out of scope (see Scope).

## References

- SPC tornado database: Schaefer, J. T., and R. Edwards (1999), The SPC
  tornado/severe thunderstorm database, *11th Conf. Applied Climatology*,
  215–220: <https://origin-east-www-spc.woc.noaa.gov/publications/schaefer/database.htm>
- Schneider, R. S., J. T. Schaefer, and H. E. Brooks (2004), Tornado outbreak
  days: an updated and expanded climatology (1875–2003), *22nd Conf. Severe
  Local Storms*: <https://origin-east-www-spc.woc.noaa.gov/publications/schneider/otbrkday.pdf>
- Galway, J. G. (1977), Some climatological aspects of tornado outbreaks,
  *Mon. Wea. Rev.* 105, 477–484 (as cited by Schneider et al. 2004).
- Fuhrmann, C. M., et al. (2014), *Weather and Forecasting* 29(3), 684–701,
  doi:10.1175/WAF-D-13-00128.1.
- IEM VTEC watch/warning archive: <https://mesonet.agron.iastate.edu/request/gis/watchwarn.phtml>
- IEM SPC watch archive: <https://mesonet.agron.iastate.edu/request/gis/spc_watch.phtml>
- Out of scope, for the record: Murphy, A. M., C. R. Homeyer, and K. Q. Allen
  (2023), *Mon. Wea. Rev.*, doi:10.1175/MWR-D-23-0017.1 (GridRad-Severe);
  Kiefer, Chavas, Gore & Dawson (2025), arXiv:2507.16975 (preprint).
