# SPC watch archive — feasibility probe (stage 26)

Generated 2026-10-27T21:26:10+00:00. Plan: `docs/plan_watch_linking.md`, step 0. Sources: IEM VTEC county records (`watchwarn.py`, TO.A/SV.A), IEM SPC watch polygons (`spc_watch.py`), SPC SEL watch texts (IEM text archive). Responses are cached under `data/raw/spc_watches/probe/`.

## 1–2. County records per year (April)

| year | watches (polygons) | with county records | type agrees | county rows |
|---|---:|---:|---:|---:|
| 2004 | 96 | 0 (0%) | — | 0 |
| 2005 | 102 | 0 (0%) | — | 0 |
| 2006 | 149 | 148 (99%) | 100% | 8,274 |
| 2007 | 102 | 102 (100%) | 100% | 4,907 |
| 2008 | 91 | 91 (100%) | 100% | 4,459 |
| 2009 | 118 | 118 (100%) | 100% | 5,998 |
| 2010 | 76 | 76 (100%) | 100% | 4,790 |
| 2011 | 175 | 175 (100%) | 100% | 11,857 |
| 2012 | 91 | 91 (100%) | 100% | 3,986 |

Read: the first year at ~100% is where county records can be the primary source; earlier years need the polygon fallback.

## 3. County timing — season 2011-03-01 to 2011-07-01

- 541 watches, 100% with county records.
- Of 32,908 county records joined to their watch: **55% ended more than 30 min before the watch's expiry** (median 132 min early), 0% more than 30 min after it.

Read: a large early share means polygons overstate where and when a watch was in force, and county timing matters.

## 4. Tornadoes: counties against polygons

1,330 SPC tracks in the season (26 without a county code in SPC's record, so not placeable by county).

| | in a watch by polygon | not by polygon |
|---|---:|---:|
| **in a watch by county** | 1,078 | 87 |
| **not by county** | 36 | 129 |

- Of tornadoes in a watch both ways, **86%** are in the same watch(es).
- 3 tornadoes' counties were under two watches at once (rule 1 of step 3 links those watches; expected rare).

## 5. Watch texts (SEL)

| month | products | watches | cancellations | unidentified | “replaces” | “will not be in effect” | “CONTINUE…WW” list |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2011-03 | 90 | 47 | 43 | 0 | 4 | 4 | 25 |
| 2011-04 | 327 | 178 | 145 | 0 | 28 | 28 | 156 |
| 2011-05 | 295 | 151 | 137 | 0 | 14 | 14 | 134 |
| 2011-06 | 332 | 167 | 163 | 0 | 6 | 6 | 133 |
| 2024-04 | 216 | 103 | 113 | 0 | 1 | 1 | 85 |

The “CONTINUE…WW” list names watches still in effect elsewhere — concurrency, not succession. Explicit succession is the “replaces” statement. *Unidentified* products have no recognisable watch number and should be read before trusting the counts.

Replacement statements found (NWS text, public domain), for a hand check of the parse:

- SVR 38 → replaces [36, 37]: “… DO PRODUCE TORNADOES. OTHER WATCH INFORMATION...THIS SEVERE THUNDERSTORM WATCH REPLACES SEVERE THUNDERSTORM WATCH NUMBER 36...TORNADO WATCH NUMBER 37. WATCH NUMBER 36 37 WILL NOT BE IN EFFECT AFTER 650 PM CST. DISCUSSION...SCTD TS…”
- TOR 40 → replaces [39]: “… STATEMENTS AND POSSIBLE WARNINGS. OTHER WATCH INFORMATION...THIS TORNADO WATCH REPLACES TORNADO WATCH NUMBER 39. WATCH NUMBER 39 WILL NOT BE IN EFFECT AFTER 315 PM CST. DISCUSSION...SEVERE THU…”
- TOR 54 → replaces [53]: “… STATEMENTS AND POSSIBLE WARNINGS. OTHER WATCH INFORMATION...THIS TORNADO WATCH REPLACES TORNADO WATCH NUMBER 53. WATCH NUMBER 53 WILL NOT BE IN EFFECT AFTER 835 PM CDT. DISCUSSION...LINE OF SE…”
- TOR 81 → replaces [80]: “… STATEMENTS AND POSSIBLE WARNINGS. OTHER WATCH INFORMATION...THIS TORNADO WATCH REPLACES TORNADO WATCH NUMBER 80. WATCH NUMBER 80 WILL NOT BE IN EFFECT AFTER 1245 PM EDT. DISCUSSION...AN ONGOIN…”
- TOR 101 → replaces [99]: “… STATEMENTS AND POSSIBLE WARNINGS. OTHER WATCH INFORMATION...THIS TORNADO WATCH REPLACES SEVERE THUNDERSTORM WATCH NUMBER 99. WATCH NUMBER 99 WILL NOT BE IN EFFECT AFTER 220 AM EDT. CONTINUE...WW 97...WW 9…”
- SVR 110 → replaces [107]: “… DO PRODUCE TORNADOES. OTHER WATCH INFORMATION...THIS SEVERE THUNDERSTORM WATCH REPLACES SEVERE THUNDERSTORM WATCH NUMBER 107. WATCH NUMBER 107 WILL NOT BE IN EFFECT AFTER 1110 PM EDT. CONTINUE...WW 108...W…”
- TOR 113 → replaces [112]: “… STATEMENTS AND POSSIBLE WARNINGS. OTHER WATCH INFORMATION...THIS TORNADO WATCH REPLACES SEVERE THUNDERSTORM WATCH NUMBER 112. WATCH NUMBER 112 WILL NOT BE IN EFFECT AFTER 200 PM EDT. DISCUSSION...SUPERCELL…”
- SVR 117 → replaces [114]: “… DO PRODUCE TORNADOES. OTHER WATCH INFORMATION...THIS SEVERE THUNDERSTORM WATCH REPLACES SEVERE THUNDERSTORM WATCH NUMBER 114. WATCH NUMBER 114 WILL NOT BE IN EFFECT AFTER 825 PM EDT. CONTINUE...WW 113...WW…”
- TOR 131 → replaces [128, 129]: “… STATEMENTS AND POSSIBLE WARNINGS. OTHER WATCH INFORMATION...THIS TORNADO WATCH REPLACES TORNADO WATCH NUMBER 128...TORNADO WATCH NUMBER 129. WATCH NUMBER 128 129 WILL NOT BE IN EFFECT AFTER 510 PM CDT. CONTINUE...WW 130.…”
- TOR 136 → replaces [135]: “… STATEMENTS AND POSSIBLE WARNINGS. OTHER WATCH INFORMATION...THIS TORNADO WATCH REPLACES TORNADO WATCH NUMBER 135. WATCH NUMBER 135 WILL NOT BE IN EFFECT AFTER 910 PM CDT. DISCUSSION...SUPERCELL…”

## What decides the design

- County records complete from the first year of the window → primary source as planned; otherwise polygons for the years before.
- Replacement statements present and parsing in ≥95% of a hand-checked sample → step 3 rule 2 is used; rare or unparseable → inferred succession only, and the plan says so.
- Counties and polygons disagreeing for a material share of tornadoes → the county choice is justified by numbers, and validation 5 reports it.
