# Why only 55% of articles get a candidate link — diagnosis and mitigation plan

Written 2026-08-04, before changing any linking code. Evidence is in
`outputs/unlinked_diagnosis.csv` (4,000 randomly sampled unlinked articles,
re-scored with the linker's own functions).

> **Status: M1–M6 implemented** (same day). What changed, concretely:
>
> | | before | after |
> |---|---|---|
> | names per hazard for matching | 8 (nearest) | **75 average** (all within 25 km + prominent cities to 50 km + county's largest town) |
> | prominence signal | none | Census sub-county population estimates, joined to GNIS |
> | name forms | GNIS spelling only | **both** spellings (`Saint`↔`St.`, `Fort`↔`Ft.`, `Mount`↔`Mt.`), sharing one IDF |
> | candidate floor | 0.25 | 0.15 (publish threshold still set by annotation) |
> | retrospective references | month or full date | plus **bare year** ("the 2011 tornado"), gated on a strong place match |
> | coverage reporting | one number | per-article `link_status` + an in-scope denominator |
>
> The GDELT query column (`places`) was verified **byte-identical for all 9,982
> hazards**, so the running sweep's cache stayed valid. All seven previously
> missing cities are now attached to their events.
>
> **Outcome: 55.1% → 80.0% of unique articles linked; 82.2% of in-scope articles.**
> What remains unlinked, on a fresh 3,000-article sample: 57.4% still match no
> toponym, 19.5% only a generic or state name (was 30.4%), 12.5% score below the
> floor, 10.6% have no surveyed event in the window (was 4.5% — this share grows
> because the easy cases left the pool). Two thirds of the remainder still look
> like real US events, so there is more to recover; the next lever is M7, not
> more permissive matching.
>
> ### Four defects the verification found (none visible in the coverage number)
>
> 1. **Fan-out** — one wire round-up collected 138 links. Capped at 12 per article.
> 2. **Wrong-year linking** — a Joplin 2011 article linked to the April 2011 Super
>    Outbreak, because **DAT holds no geometry for the Joplin EF5** (May 2011
>    contains only an EF2 and an EF1). Year-only candidates now also require
>    corroborating rating/casualty/date evidence, so the link is refused rather
>    than invented. This is the coverage ceiling of M7 showing up in practice.
> 3. **`textref_uid` was not unique** — filename + headline collided across 3,402
>    same-named files (every `GOOD MORNING AMERICA.RTF`), pooling 5,774 articles'
>    links under shared ids and breaking the per-article cap. Now keyed on
>    filename + headline + date + body hash.
> 4. **14% of the export is byte-identical duplicates** (1,568 groups) from
>    overlapping download batches. Each unique article is now scored once; the
>    true corpus size is **22,896 articles, not 24,917**.

## 1. The headline finding

**This is mostly a gazetteer problem, not a linking-logic problem.** The scoring,
the date window and the thresholds are behaving as designed. What is wrong is the
*list of place names each event is allowed to be recognised by*: it is capped at
eight, chosen by proximity, and so consists largely of hamlets that no newspaper
would ever name — while the town in the headline is missing.

Current state: 24,917 articles, **13,723 linked (55.1%)**, 3 without a date.

## 2. Where the 45% goes (n = 4,000 sampled unlinked articles)

| Failure mode | share | meaning |
|---|---|---|
| **B — no toponym match at all** | **50.9%** | not one of the event's names appears in the article |
| **C — only a generic or state-level match** | **30.4%** | e.g. only "Texas" matched, so the `has_specific_match` gate blocked it |
| **D — score below the 0.25 threshold** | 14.2% | matched something specific, but too weakly |
| **A — no surveyed event in the date window** | 4.5% | nothing to link to |

And what those articles *are* (heuristic, overlapping):

| | share of unlinked |
|---|---|
| foreign / non-US event (Canada, UK, India…) | 11.3% |
| explainer, policy, insurance, donation, anniversary | 20.0% |
| neither — **probably a real US event we missed** | **70.7%** |

So roughly **29%** of the unlinked set is legitimately unlinkable (out of scope for
a US-survey dataset), and **71%** — about 7,900 articles — is coverage we ought to
have.

## 3. Root causes, with the evidence

### 3.1 The place list is capped at eight, and the cap binds almost everywhere

`MAX_PLACES_PER_HAZARD = 8`, chosen by nearest-first within 25 km.

- **97.2% of hazards are at the cap.** A typical track has **40–100** populated
  places within 25 km; we keep eight.
- Because selection is by distance, the eight are the *closest*, not the
  *best-known*. Three real examples of what is kept versus dropped:

  | kept | dropped |
  |---|---|
  | Jernigans Crossroads, White Pond, Long Point | **Tabor City**, Goretown, Simpson |
  | Bluehouse Corners, Hudsons Mill, Pattillo (historical) | White Hall, Canadys, Blountville |
  | Buffalo Mop, Alto Springs, Petteway | **Bremond**, **Thornton**, Reagan |

- The consequence is visible in the aggregate: the most frequent names across the
  whole gazetteer column are **Midway (172 hazards), Fairview (98), Oak Grove (94),
  Union (93)** — generic hamlet names that carry almost no identifying power, while
  the names news uses are absent.

**Seven of thirty major tornado-belt cities are attached to no hazard at all:**
St. Louis, Kansas City, Fort Worth, Tuscaloosa, Des Moines, Shreveport, Lubbock.
For six of them the city exists in GNIS and was simply crowded out by the cap.

### 3.2 Name forms don't match how news writes them

GNIS stores the expanded form; newsrooms use the abbreviation.

| GNIS has | GNIS lacks | news writes |
|---|---|---|
| `Saint Louis` ✓ | `St. Louis` ✗ | "St. Louis" |
| `Fort Worth` ✓ | `Ft. Worth` ✗ | either |
| `Mount Juliet` ✓ | `Mt. Juliet` ✗ | "Mt. Juliet" |

St. Louis *is* attached to hazards — as "Saint Louis" — and therefore never matches
an article. This alone affects a corpus with 43 *St. Louis Post-Dispatch* articles
and a major May 2025 St. Louis tornado.

### 3.3 The `has_specific_match` gate is doing more work than intended

It exists for a good reason: a link should never rest on "Texas" alone. But with
the place lists impoverished by 3.1, it now blocks **30.4%** of unlinked articles
that had *only* a state match available — including articles that name a real town
which simply is not in our eight.

Fix 3.1 and most of category C should turn into category-B-solved, not into a
reason to weaken the gate.

### 3.4 Retrospective references by year alone

The retrospective pass understands "March 14, 2025", "May 2024" and "one year
after", but not a bare year — *"Joplin hospital honors 2011 tornado survivors"*
has no reachable candidate. Small (part of the 4.5% in category A) but cheap to fix.

## 4. Mitigation plan

Ordered by expected yield per unit of effort. **Nothing here is implemented yet.**

### M1 — Prominence-aware place selection *(largest expected effect)*

Replace "nearest 8" with:

- keep **all** populated places within 25 km for *matching* (typically 40–100);
- add any place with population above a threshold within a **wider** radius
  (~50 km), because news names the nearby city even when the track is well outside
  it ("tornado near Tuscaloosa");
- add the **county seat** for every county the track crosses.

Prominence needs a population signal, which GNIS does not carry. Options:
Census Gazetteer place files joined to population estimates (a single extra
download, offline, reproducible), or the Census "incorporated places" list as a
binary prominence flag. I'd use population, since it also gives a sensible ranking
for the GDELT query budget.

**Risk:** more names per event means more chances of a false match. The IDF
weighting already discounts common names, and the score is a sum, so this mostly
adds low-weight evidence — but precision must be re-measured, not assumed.

### M2 — Name aliases *(cheap, no downside)*

Generate alias forms at index time: `Saint ↔ St.`, `Fort ↔ Ft.`, `Mount ↔ Mt.`,
and strip trailing qualifiers like `(historical)`. Both forms map to the same
gazetteer entry, so IDF is unaffected.

### M3 — Keep the gate, but let it see the better list

No change to `has_specific_match` itself. Re-measure category C after M1+M2; if a
residue of genuinely state-only articles remains, the honest treatment is a
distinct low-confidence `link_level = "state_day"` rather than loosening the gate.

### M4 — Bare-year retrospectives

Add a `year_only` date kind ("the 2011 tornado"), admissible **only** when the
toponym score is strong — a year alone is far too coarse otherwise.

### M5 — Widen the candidate file, not the published one

14.2% of failures sit just below `LINK_MIN_SCORE = 0.25`; median near-miss score is
0.218, and **1,229 of 1,784** would clear 0.15. We already separate *candidates*
from *publishable links*, so lowering the candidate floor to ~0.15 costs nothing in
rigour and gives the annotation more to judge. **The publishable threshold still
comes from the annotated sample, never from this number.**

### M6 — Report coverage against the linkable population

Add a `link_status` to every article: `linked`, `out_of_scope_foreign`,
`no_event_article`, `no_event_in_window`, `below_threshold`. Then "55%" becomes an
honest pair of numbers: coverage of *all* articles, and coverage of the ~87% that
are in scope at all (currently ≈63%).

### M7 — Quantify the DAT ceiling *(optional, larger)*

Some articles describe tornadoes NWS never surveyed or digitised, which no linker
can reach. Cross-checking article dates against NCEI Storm Events would let us
state that ceiling instead of carrying it as unexplained loss.

## 5. What I deliberately do not propose

- **Lowering the publish threshold to raise the number.** Coverage bought by
  admitting weaker links is not coverage; it is unmeasured error.
- **Weakening `has_specific_match`** before fixing the place lists — that would
  convert a data problem into a precision problem.
- **Fuzzy/partial name matching.** With 29,447 names and prose full of proper
  nouns, approximate matching would add false positives faster than true ones.

## 6. Sequencing constraint — read before implementing

**The GDELT queries are built from the same `places` column.** Changing it changes
every query string, which changes every cache key, which would invalidate the
sweep currently running and force a full re-fetch (~24 h + rate limiting).

So the implementation must keep the two uses separate:

- `places` — unchanged, prominence-ranked, capped at ~12: **query construction only**
- `places_matching` — new, wide and alias-expanded: **article matching only**

That way the linking improves and the GDELT sweep keeps its cache. Alternatively,
wait for the sweep to finish and then regenerate both — but there is no reason to
couple them.

## 7. How we will know it worked

1. **Coverage**: linked share of in-scope articles, before and after, on the same
   corpus.
2. **Precision**: a fresh stratified annotation sample. Adding names can add false
   matches, so the existing precision estimate does not carry over.
3. **Regression on known cases**: Cushman/Cave City (March 2025) and the Rogers,
   Arkansas May 2024 retrospective must still link to the same episodes.
4. **The seven missing cities** must be attached to their events, and articles
   naming them must link.
5. **Category shares recomputed** on the same 4,000-article sample, so the movement
   between B/C/D is visible rather than inferred from the headline number.
