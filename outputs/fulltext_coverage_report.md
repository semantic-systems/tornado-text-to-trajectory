# Full-text coverage — Stage 21

Generated 2026-08-11T09:30:07+00:00.

**37 of 40 attempted** = 92.5% [80.1%, 97.4%], out of 40 `EVENT` stories in the population.

Retrieval failure and article existence are different things. A story that cannot be fetched still happened and still appeared; excluding it changes what the corpus represents, so the tables below are a coverage-bias statement rather than a technical footnote.

## By year band

| year band | sampled | retrieved | rate | 95% CI |
|---|---:|---:|---:|---|
| 2010-2015 | 10 | 10 | 100% | [72%, 100%] |
| 2016-2020 | 13 | 12 | 92% | [67%, 99%] |
| 2021-2025 | 17 | 15 | 88% | [66%, 97%] |

## By domain size

| domain size | sampled | retrieved | rate | 95% CI |
|---|---:|---:|---:|---|
| small (≤5) | 20 | 18 | 90% | [70%, 97%] |
| medium (6-50) | 19 | 19 | 100% | [83%, 100%] |
| large (>50) | 1 | 0 | 0% | [0%, 79%] |

## Outcomes

| outcome | n | share |
|---|---:|---:|
| `ok` | 37 | 92.5% |
| `extraction_failed` | 2 | 5.0% |
| `http_error` | 1 | 2.5% |

## Route

| route | n | share |
|---|---:|---:|
| direct | 32 | 86.5% |
| wayback | 5 | 13.5% |

Extracted length: median **359 words** (p10 168, p90 832).

## Method

- `robots.txt` honoured per domain including `Crawl-delay`; a domain asking for more than 30s yields one article and the rest are recorded as skipped.
- Requests to one domain are serialised; domains run in parallel; archive.org is throttled globally because it is one host regardless of which publisher an article came from.
- Paywall teasers and bot-blocks are counted as failures, not short articles.
- Extraction by trafilatura, minimum 120 words.
- Text is stored locally for TDM under §60d UrhG; the published dataset carries links and derived annotations only.
