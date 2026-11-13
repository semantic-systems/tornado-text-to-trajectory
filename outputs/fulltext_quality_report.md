# Full-text quality — Stage 21

Generated 2026-10-08T17:41:27+00:00 from `retrievals.jsonl`.

> Retrieval `ok` means extraction produced at least 120 words that are not an obvious paywall or bot wall. This report asks the harder question: **is the body the article the headline names?** Every check is a flag with a stated threshold, reported with its rate, rather than a silent filter.

## Result

- **38,383** bodies retrieved; **32,272** pass every hard check = **84.1%** [83.7%, 84.4%].
- Against the 48,741 `EVENT` stories crawled, that is **66.2% usable full text**.

## Flags

| flag | kind | articles | share | what it catches |
|---|---|---:|---:|---|
| `no_tornado_mention` | hard | 5,613 | 14.6% | Media Cloud's own `tornado*` query matched this page, so a correct body should mention one; most often a wrong page or a truncated extraction, occasionally a mention trafilatura dropped with a caption |
| `redirected_home` | hard | 3,707 | 9.7% | direct fetch landed on the site's front page |
| `template_body` | hard | 5,122 | 13.3% | one body under ≥3 headlines that disagree with it *and* never mentions a tornado — an error or landing page served for many URLs |
| `not_english` | hard | 2,255 | 5.9% | English stopword share < 15% |
| `title_mismatch` | soft | 6,682 | 17.4% | retrieved page title shares < 30% of the headline's content words. **Soft**: these bodies mention tornadoes more than passing ones — mostly the right article, retitled after indexing |
| `high_boilerplate` | soft | 4,227 | 11.0% | ≥30% of the words are paragraphs that recur across most of the domain's pages |
| `very_long` | soft | 20 | 0.1% | ≥8,000 words — live blogs and page dumps |

Flags overlap; the shares do not sum to the failure rate.

## By route

| route | retrieved | quality ok | rate | 95% CI |
|---|---:|---:|---:|---|
| direct | 19,689 | 13,852 | 70% | [70%, 71%] |
| wayback | 18,694 | 18,420 | 99% | [98%, 99%] |

## By year band

| year band | retrieved | quality ok | rate | 95% CI |
|---|---:|---:|---:|---|
| 2010-2015 | 6,209 | 4,907 | 79% | [78%, 80%] |
| 2016-2020 | 13,576 | 10,593 | 78% | [77%, 79%] |
| 2021-2025 | 18,598 | 16,772 | 90% | [90%, 91%] |

## By domain size

| domain size | retrieved | quality ok | rate | 95% CI |
|---|---:|---:|---:|---|
| small (≤5) | 2,249 | 1,953 | 87% | [85%, 88%] |
| medium (6-50) | 10,859 | 8,756 | 81% | [80%, 81%] |
| large (>50) | 25,275 | 21,563 | 85% | [85%, 86%] |

## Shared bodies

32,230 distinct bodies sit under 38,383 distinct headlines. 1,007 bodies appear under more than one headline (largest: 1,070). Media Cloud deduplicates by *headline*, so syndicated copies retitled by each outlet survive as separate stories; **count articles by body, not by headline, wherever the text is what matters.** Shared bodies whose headlines disagree with them are flagged `template_body` above; the rest are ordinary wire copy.

## Length

Median 337 words (p10 156, p90 955) for all retrieved; median 382 for those passing.

## Examples to inspect

Five per hard flag, by URL and headline only. Open them before trusting a threshold.

**`no_tornado_mention`**

- [Rare tornado touched down in Montgomery County during Wednesday storms](http://rssfeeds.theleafchronicle.com/~/603327824/0/clarksville/home~Rare-tornado-touched-down-in-Montgomery-County-during-Wednesday-storms/)
- [Surprise overnight tornado kills a farmer and leaves behind tales of terror in rural centr](http://rssfeeds.desmoinesregister.com/~/602267782/0/desmoines/home~Surprise-overnight-tornado-kills-a-farmer-and-leaves-behind-tales-of-terror-in-rural-central-Iowa/)
- [Toxic Waste A Big Issue In Tornado Storm Cleanup](http://dfw.cbslocal.com/2012/04/19/toxic-waste-a-big-issue-in-tornado-storm-cleanup/)
- [Indiana appeals FEMA ruling, expands request for post-tornado help](http://www.jconline.com/viewart/20131223/NEWS01/312230018)
- [Tornadoes, damaging storms sweep through Illinois](http://archive.indystar.com/article/20131117/NEWS/311170027)

**`redirected_home`**

- [Little Rock tornado: Damage, injuries reported; severe weather news](http://rssfeeds.clarionledger.com/~/733313048/0/jacksonms/news~Large-and-destructive-tornado-hits-near-Little-Rock-Arkansas-another-tornado-emergency-in-eastern-Arkansas-Severe-weather-updates/)
- [Tornado confirmed in Warren County](https://www.goerie.com/news/20190415/tornado-confirmed-in-warren-county?rssfeed=true)
- ['Probable' tornadoes touch down across FWB](http://www.nwfdailynews.com/news/20170621/probable-tornadoes-touch-down-across-fwb?rssfeed=true)
- [Grief, uncertainty grip Joplin](http://rssfeeds.usatoday.com/~r/UsatodaycomNation-TopStories/~3/gYG8n7CaaI8/2011-05-24-joplin-tornado_n.htm)
- [Crushed Miss. town inspects tornado damage](http://rssfeeds.usatoday.com/~r/UsatodaycomNation-TopStories/~3/IU3kWnTbwI4/2011-04-28-Deadliest-day-tornadoes-South-Alabama_n.htm)

**`template_body`**

- [Gov. Mike DeWine requests FEMA assessment after wave of tornadoes](https://www.dispatch.com/news/20190530/gov-mike-dewine-requests-fema-assessment-after-wave-of-tornadoes?rssfeed=true)
- [NWS confirms two EF 1 tornados touched down Thursday -- one in the Cypress area and one in](https://www.cbs19.tv/article/news/local/houston-tornado-confirmed-cypress-texas/285-e492fdb5-3098-4bd4-8505-c09f9e9c6e4b)
- [MS tornado damage aftermath: See photos, videos of the storms' impacts](http://rssfeeds.clarionledger.com/~/647014986/0/jacksonms/news~See-the-Mississippi-tornado-damage-aftermath-left-in-the-wake-of-Wednesdays-outbreak/)
- [Tornado that hit Dayton-area upgraded to EF4; strongest in Ohio since 2010](https://www.10tv.com/article/tornado-hit-dayton-area-upgraded-ef4-strongest-ohio-2010-2019-may)
- [4.7 million gallons of sewage released into river during Ohio tornado outbreak, officials ](https://www.10tv.com/article/47-million-gallons-sewage-released-river-during-ohio-tornado-outbreak-officials-say-2019-jun)

**`not_english`**

- [WATCH: Tornado sweeps through Dallas, causing heavy damage](https://www.lubbockonline.com/news/20191021/watch-tornado-sweeps-through-dallas-causing-heavy-damage?rssfeed=true)
- [Lost pig reunited with owner in Mississippi after tornadoes: Good news](http://rssfeeds.usatoday.com/~/736252928/0/usatodaycomnation-topstories~Oink-is-home-How-cheese-puffs-helped-reunite-lost-pig-with-its-owner-after-devastating-tornado/)
- [Toledo crews helping with area tornado cleanup](http://www.toledoblade.com/article/20100609/NEWS16/100609688/-1/RSS)
- [BorgWarner in Seneca faces long road back from tornado, coronavirus](http://rssfeeds.greenvilleonline.com/~/621652952/0/greenville/home~BorgWarner-in-Seneca-faces-long-road-back-from-tornado-coronavirus/)
- [Lessons Learned: Volunteer response to Abilene's tornado provides guide for future](http://rssfeeds.reporternews.com/~/602788836/0/abilene/home~Lessons-Learned-Volunteer-response-to-Abileneaposs-tornado-provides-guide-for-future/)

## Limitations

1. **Thresholds are judgement, not measurement.** None has been calibrated against a human check. The per-article table (`data/interim/fulltext_quality.csv`) carries every raw measure, so a threshold can be moved without re-reading the bodies.
2. **`no_tornado_mention` has a known false-positive mode**: Media Cloud's extraction may have kept a caption or related-links box that trafilatura drops. The examples above are the way to estimate how often.
3. **`title_mismatch` is soft, on evidence.** As a hard flag it rejected articles whose bodies mentioned tornadoes more often than passing ones: pages are retitled as stories develop. A flag that removes the most on-topic text is not measuring what it claims to.
4. **`not_english` also catches video pages** with little prose, not only foreign-language articles. Both are unusable by the English-only stages downstream, but they are different reasons.
5. **Boilerplate detection needs volume**: domains with fewer than 10 retrieved pages are never scored.
