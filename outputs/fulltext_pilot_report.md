# Full-text retrieval pilot — Stage 21

Generated 2026-08-11T09:00:17+00:00.

## Question

The Media Cloud corpus has 48,741 distinct `EVENT` stories with no body text. Retrieving it would let those articles be labelled on the same evidence as the LexisNexis corpus and, more importantly, make them **linkable** — stage 11 matches toponyms in the body, so without text they cannot enter the dataset at all.

This pilot asks what fraction is retrievable and, since the answer will not be uniform, where the loss falls.

## Result

**319 of 594 = 54%** [50%, 58%] retrieved, from a sample stratified by year band × domain size across 445 domains.

### By year band

| year band | sampled | retrieved | rate | 95% CI |
|---|---:|---:|---:|---|
| 2010-2015 | 198 | 84 | 42% | [36%, 49%] |
| 2016-2020 | 198 | 113 | 57% | [50%, 64%] |
| 2021-2025 | 198 | 122 | 62% | [55%, 68%] |

### By domain size

| domain size | sampled | retrieved | rate | 95% CI |
|---|---:|---:|---:|---|
| small (≤5) | 198 | 97 | 49% | [42%, 56%] |
| medium (6-50) | 198 | 110 | 56% | [49%, 62%] |
| large (>50) | 198 | 112 | 57% | [50%, 63%] |

### Outcomes

| outcome | n | share |
|---|---:|---:|
| `ok` | 319 | 54% |
| `http_error` | 204 | 34% |
| `extraction_failed` | 53 | 9% |
| `geo_blocked` | 14 | 2% |
| `robots_disallowed` | 4 | 1% |

### Route taken

| route | n | share |
|---|---:|---:|
| direct | 259 | 81% |
| wayback | 60 | 19% |

Extracted length: median **330 words** (p10 150, p90 954).

## Media Cloud API (arm A)

Not tested — `MEDIACLOUD_API_KEY` was not set. Worth doing before committing to a crawl, since it would make one unnecessary.

## What this means for the full crawl

- At 54% overall, a full pass over 48,741 stories would yield roughly **26,175** articles with usable text.
- **The loss is not random.** Read the two rate tables above as a coverage bias statement, not a technical footnote: whatever they show about old and small-outlet articles carries into every downstream figure computed on the retrieved subset.
- Retrieval failure and article existence are different things. A story that cannot be fetched still happened and still appeared; excluding it changes what the corpus represents.

## Method notes

- `robots.txt` honoured per domain, including `Crawl-delay`; disallowed URLs are recorded and never fetched.
- Requests to one domain are serialised; domains run in parallel.
- Paywall teasers and bot-blocks are detected and counted as failures rather than accepted as short articles — a 180-word 'subscribe to continue' stub that entered the corpus would be labelled as though it were the article.
- Extraction by trafilatura, `favor_precision`, minimum 120 words.
