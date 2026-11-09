# Watch hand checks — Stage 26

Generated 2026-11-09T15:24:05+00:00 from `outputs/annotation/watch_*_sheet.csv`.

## Named outbreaks: does each grouping cut them as the summaries do?

| grouping | labelled | matches | too coarse | too fine | cannot tell |
|---|---:|---:|---:|---:|---:|
| watch systems | 10/10 | 5 | 2 | 3 | 0 |
| watch sequences | 10/10 | 0 | 0 | 10 | 0 |
| convective_day 200km (stage 3) | 10/10 | 3 | 0 | 7 | 0 |
| convective_day 400km | 10/10 | 4 | 1 | 5 | 0 |
| time-gap 6h, all ratings (Fuhrmann variant) | 10/10 | 8 | 2 | 0 | 0 |
| space_time 400km 6h | 10/10 | 8 | 1 | 1 | 0 |
| kde day bw=100km | 10/10 | 5 | 1 | 4 | 0 |
| kde overlap 24h/12h bw=50km | 10/10 | 3 | 4 | 3 | 0 |
| kde overlap 24h/12h bw=100km | 10/10 | 4 | 6 | 0 | 0 |

## Motion-check rejections: was the rejection right?

21 of 50 sampled pairs labelled: 2 separate systems, 11 should have been linked, 8 cannot tell.

Wrongly rejected: **85%** [58%, 96%] of decided pairs.

Read: above ~20%, the motion check rejects too many genuine successions — prefer the setting without it (sensitivity grid, `--no-motion-check`). Below, keep it.
