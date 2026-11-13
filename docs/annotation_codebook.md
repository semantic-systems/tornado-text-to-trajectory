# Annotation codebook — article ↔ event links

Written before looking at the pipeline's output, so the rules describe the task
rather than the tool. Version `codebook_v1_2026-07-30`.

Your judgements set the threshold above which links are published, and they are the
only reason a precision figure means anything. Where the article genuinely does not
say enough, `cannot_tell` is the right answer and is more useful than a guess.

## The sheets

| File | What you do |
|---|---|
`outputs/annotation/precision_sheet.csv` | For each row: read the article excerpt, look at the event described on the same row, and put one label in the `label` column.
`outputs/annotation/recall_sheet.csv` | Read the article and write down which event it is about — **from the text alone**, without consulting the dataset.
`outputs/annotation/agreement_sheet.csv` | Same task as the precision sheet, on a repeated subset. Do it on a different day, or have a second person do it. Do not compare with your earlier answers while working.

Neither sheet shows the pipeline's score, its chosen relation, or the event's
identifier. That is deliberate: seeing "0.94" makes it very hard not to agree.

## The five labels

### `describes`
The article's main subject is this event. Damage, casualties, response or recovery
*of this event* is what the article is reporting.

> *"Nine killed as deadly tornado causes devastation as search for survivors
> begins"* (17 May 2025), shown against the 16 May 2025 Kentucky outbreak →
> **describes**.

Use `describes` even when the article covers several tornadoes of the same outbreak
— the event on the row is the outbreak day.

### `mentions`
This event appears in the article, but the article is mainly about something else:
a later policy fight, a different tornado, an anniversary of a third event, a
person's biography.

> *"A Tornado Came for Cave City. Would Trump's FEMA?"* shown against a *different*
> May 2025 outbreak that the article names in passing → **mentions**.

Also use `mentions` for forecast coverage published *before* the event: an article
warning that storms are expected cannot be describing damage that has not happened.

### `unrelated`
The event on this row is not one the article is about or refers to. This is the
label for a wrong link — expect it most often where two outbreaks hit the same
region within a fortnight, or where a place name is shared between states.

> An article about a tornado in **Rogers, Arkansas** shown against an outbreak in
> **Rogers County, Oklahoma** → **unrelated**.

### `no_event`
The article is not about any specific tornado at all. Whatever event is on the row,
the correct outcome is no link. Typical cases in this corpus:

- preparedness and explainer pieces — *"How to Prepare for Tornado Season"*
- season outlooks and climatology — *"Forecasters say US is facing worst tornado season…"*
- legislation, insurance products, corporate donations — *"Boozman, Wicker introduce TORNADO Act"*
- sport, film and metaphor — a team nicknamed the Tornadoes

`no_event` is about the **article**, not the pair. If you label a row `no_event`,
every other row for that article is `no_event` too.

### `cannot_tell`
The excerpt does not contain enough to decide: no place, no date, or a place so
generic that it could be several events. Do not open the full article to resolve
these — if the excerpt cannot settle it, that is a finding about the evidence
available, and the excerpt is 700 characters of the lede, which is where news
puts the who and where.

## Rules for the awkward cases

1. **Several tornadoes in one article.** Label each row on its own merits. One
   article can legitimately have one `describes` and several `mentions`.
2. **Wire copy printed by many outlets.** Judge the text in front of you; the
   duplicate handling happens elsewhere.
3. **The article is about a tornado *near* the event's places.** If it is the same
   tornado or the same outbreak day, `describes`/`mentions`. If it is a different
   tornado on the same day in another state, `unrelated`.
4. **Anniversary pieces.** *"One year after the tornado…"* shown against the
   original event → `describes` (that event is the subject). Shown against a recent
   outbreak the article merely notes → `mentions`.
5. **Canada, Europe, elsewhere.** The dataset covers US surveys only. A tornado in
   British Columbia has no event in the dataset, so any row for it is `unrelated`,
   and the article as a whole is a coverage gap rather than an error.
6. **Damage was not from a tornado.** *"A downburst, not a tornado, devastated…"* →
   `no_event` unless a real tornado is also the subject.

## Recall sheet

For each article write:

- `true_event_date` — the date of the event, as best the text supports
  (`2025-05-16`, or `2025-05` if only the month is given, or blank if none).
- `true_event_place` — the most specific place named (town preferred over county
  over state).
- `is_about_one_event` — `yes`, `no` (several events or none), `cannot_tell`.

Do not look anything up. The point is to capture what a reader can extract from the
article, which is exactly what the pipeline has to work from.

## After annotating

```bash
python scripts/41_qa_links.py
```

It joins your labels to the withheld keys and reports precision per score band with
Wilson intervals, the calibration of `link_confidence`, recall against the recall
sheet, and Cohen's κ from the repeated subset. Nothing is published as a link until
those numbers exist.
