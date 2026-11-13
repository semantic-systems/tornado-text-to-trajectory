# Corpus overlap — LexisNexis × Media Cloud

Generated 2026-08-11T08:12:18+00:00.

**Every figure below counts distinct stories, never rows.** A wire story that ran on 200 outlets is one story. On the Media Cloud side that means distinct normalised headlines (266,258, from 491,432 rows); on the LexisNexis side, distinct article bodies (20,138, from 22,896 rows).

## How many distinct tornado-event news articles are there?

| | stories |
|---|---:|
| LexisNexis `EVENT` (distinct bodies) | 12,077 |
| Media Cloud `EVENT` (distinct headlines) | 48,741 |
| Shared — `EVENT` in both (2,183 LexisNexis bodies ↔ 1,849 Media Cloud headlines) | 1,681 |
| **Union** | **58,467** |

The shared row is the number of **connected components** of the match graph, not either side's count. Matching is many-to-many — one body can match several headlines and vice versa — so subtracting either side alone would still double-count.

The union is an **upper bound**. Matching uses the headline, the date and the outlet, because LexisNexis carries no URL and Media Cloud carries no body — so two desk edits of one wire story remain separate and inflate the count.

## Retrieval overlap

- **4,427 of 20,138** LexisNexis stories (22.0%) have a Media Cloud counterpart.
- **3,643 of 266,258** Media Cloud stories (1.4%) have a LexisNexis one.

For contrast, the same matches touch 36,938 Media Cloud *URLs* — that figure counts one wire story once per outlet that ran it and is not a story count.

The asymmetry between the two rates is expected: Media Cloud holds 13× more distinct stories, and the two corpora were built from different sampling frames.

### Where overlap is and is not possible

| source class | LexisNexis stories | matched | rate |
|---|---:|---:|---:|
| web_native_or_other | 12,722 | 1,785 | 14.0% |
| wire_or_syndicated | 6,080 | 2,473 | 40.7% |
| broadcast_transcript | 841 | 5 | 0.6% |
| print_or_campus | 495 | 164 | 33.1% |

Broadcast transcripts and press-release wires have no web article to match, so a low rate there is a property of the source class rather than a failure of the matcher.

## Do the two labellings agree?

On the 4,427 stories present in both corpora, the primary label agrees **76.3%** of the time [75.0%, 77.5%].

This is the most useful validation available so far: the same story was labelled twice from different evidence — stage 19 read the article body, stage 18 saw only a headline and a URL — by the same model, with neither run able to see the other. It is not ground truth, but unlike a self-consistency figure it is not a measure of the model agreeing with itself under identical conditions.

```
mediacloud         EVENT  NOT_TORNADO_EVENT  PROSPECTIVE  UNCLEAR
lexis                                                            
EVENT               2179                485           87      308
NOT_TORNADO_EVENT     83               1105           12       38
PROSPECTIVE            2                 28           94        6
```

## Limitations

1. **Matching is a lower bound.** No shared identifier exists; the only evidence is headline, date and outlet. Rewritten headlines and outlets absent from one collection cannot match.
2. **The corpora have different frames.** Media Cloud covers US national/state/local collections; the LexisNexis export includes wire services, broadcast transcripts and non-US outlets that Media Cloud never sampled.
3. **Both label sets are model output.** No human ground truth has been annotated for either corpus, so the agreement figure above bounds consistency, not correctness.
