# Full-text coverage — Stage 21

Generated 2026-10-08T14:48:05+00:00.

**38,383 of 48,741 attempted** = 78.7% [78.4%, 79.1%], out of 48,741 `EVENT` stories in the population.

Retrieval failure and article existence are different things. A story that cannot be fetched still happened and still appeared; excluding it changes what the corpus represents, so the tables below are a coverage-bias statement rather than a technical footnote.

## By year band

| year band | sampled | retrieved | rate | 95% CI |
|---|---:|---:|---:|---|
| 2010-2015 | 11128 | 6209 | 56% | [55%, 57%] |
| 2016-2020 | 16608 | 13576 | 82% | [81%, 82%] |
| 2021-2025 | 21005 | 18598 | 89% | [88%, 89%] |

## By domain size

| domain size | sampled | retrieved | rate | 95% CI |
|---|---:|---:|---:|---|
| small (≤5) | 2772 | 2249 | 81% | [80%, 83%] |
| medium (6-50) | 13446 | 10859 | 81% | [80%, 81%] |
| large (>50) | 32523 | 25275 | 78% | [77%, 78%] |

## Outcomes

| outcome | n | share |
|---|---:|---:|
| `ok` | 38,383 | 78.7% |
| `http_error` | 6,745 | 13.8% |
| `extraction_failed` | 2,531 | 5.2% |
| `geo_blocked` | 472 | 1.0% |
| `robots_disallowed` | 326 | 0.7% |
| `robots_crawl_delay_too_long` | 257 | 0.5% |
| `paywalled` | 14 | 0.0% |
| `archive_rate_limited` | 8 | 0.0% |
| `blocked` | 5 | 0.0% |

## Route

| route | n | share |
|---|---:|---:|
| direct | 19,689 | 51.3% |
| wayback | 18,694 | 48.7% |

Extracted length: median **337 words** (p10 156, p90 955).

## Method

- `robots.txt` honoured per domain including `Crawl-delay`; a domain asking for more than 30s yields one article and the rest are recorded as skipped.
- Requests to one domain are serialised; domains run in parallel; archive.org is throttled globally because it is one host regardless of which publisher an article came from.
- Paywall teasers and bot-blocks are counted as failures, not short articles.
- Extraction by trafilatura, minimum 120 words.
- Text is stored locally for TDM under §60d UrhG; the published dataset carries links and derived annotations only.
