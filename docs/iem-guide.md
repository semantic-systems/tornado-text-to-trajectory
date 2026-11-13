Mastering the Mesonet
A Comprehensive Guide to Environmental Data Acquisition and Analysis
Jonathan Sailor
March 2026

Table of contents
Preface 1
How to Use This Book . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
A Note on Data Quality . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
A Note on URLs . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
License . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
Introduction 4
I. Part I — Understanding the IEM 6
1. Chapter 1 — What Is the IEM? 7
1.1. The Short Version . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
1.2. Where It Came From. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
1.3. What “Mesonet” Means . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8
1.4. The Homepage . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8
1.5. The Navigation Structure . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
1.6. The Daily Feature Archive . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
1.7. What the IEM Is Not . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
1.8. A Note on the “Unofficial” Label . . . . . . . . . . . . . . . . . . . . . . . . 12
1.9. Key URLs — Chapter 1 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12
2. Chapter 2 — Station Networks: The Foundation of Everything 14
2.1. Finding Any Station . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
2.2. ASOS and AWOS: The Airport Backbone . . . . . . . . . . . . . . . . . . . 15
2.3. NWS COOP: A Century of Daily Observations . . . . . . . . . . . . . . . . 16
2.4. CoCoRaHS: The Precipitation Dense Network . . . . . . . . . . . . . . . . . 18
2.5. DCP/HADS: Rivers, Reservoirs, and Remote Gauges . . . . . . . . . . . . . 18
2.6. RWIS: Roadway Weather and Pavement Sensors . . . . . . . . . . . . . . . 19
2.7. Specialty Networks . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20
2.8. Station Metadata and the Network Table . . . . . . . . . . . . . . . . . . . 20
2.9. Key URLs — Chapter 2 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 21
3. Chapter 3 — Current Conditions: What’s Happening Right Now 23
3.1. The Current Mainpage . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 23
ii

Mastering the Mesonet iii
3.2. Sortable Currents: The Cross-Network Observation Table . . . . . . . . . . 23
3.3. IEM One: Radar and Warnings in a Single Interface . . . . . . . . . . . . . 24
3.4. The Severe Weather Mainpage . . . . . . . . . . . . . . . . . . . . . . . . . 25
3.5. The Precipitation Current Page . . . . . . . . . . . . . . . . . . . . . . . . . 26
3.6. What “Current” Actually Means on the IEM . . . . . . . . . . . . . . . . . 26
3.7. Key URLs — Chapter 3 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27
II. Part II — Tools and Applications 29
4. Chapter 4 — Apps: IEM’s Interactive Tools 30
4.1. The Application Index . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 30
4.2. Automated Data Plotting (Autoplot) . . . . . . . . . . . . . . . . . . . . . . 30
4.3. Other Apps Menu Tools . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 37
4.4. Workflow 2 — Building and Bookmarking a Custom Autoplot Chart . . . . 39
4.5. Workflow 5 — Building a Wind Rose for Your Airport . . . . . . . . . . . . 40
4.6. Key URLs — Chapter 4 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 41
5. Chapter 5 — Areas: Topic Portals 44
5.1. The Archive Mainpage . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 44
5.2. The GIS Mainpage . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 46
5.3. Drought Monitoring . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 49
5.4. Ag Weather/Climate Info . . . . . . . . . . . . . . . . . . . . . . . . . . . . 49
5.5. What the Areas Menu Does Not Contain . . . . . . . . . . . . . . . . . . . 51
5.6. What to Watch Out For . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 51
5.7. Key URLs — Chapter 5 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 52
6. Chapter 6 — Datasets: The Full Archive Explained 54
6.1. Daily Climatology: COOP Records and the Extremes Tool . . . . . . . . . 54
6.2. Daily Observations: The IEM Summary Dataset . . . . . . . . . . . . . . . 55
6.3. Dataset Documentation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 56
6.4. IEM Reanalysis (IEMRE) . . . . . . . . . . . . . . . . . . . . . . . . . . . . 56
6.5. Model Output Statistics (MOS) . . . . . . . . . . . . . . . . . . . . . . . . . 59
6.6. Sounding Archive (RAOB) . . . . . . . . . . . . . . . . . . . . . . . . . . . 62
6.7. Rainfall Data and MRMS . . . . . . . . . . . . . . . . . . . . . . . . . . . . 63
6.8. Soil Moisture Satellite . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 63
6.9. What to Watch Out For . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 64
6.10.Workflow 1 — Looking Up Period-of-Record Daily Extremes for a COOP
Station . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 64
6.11.Key URLs — Chapter 6 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 65
7. Chapter 7 — NWS Data: Warnings, Forecasts, and Official Products 67
7.1. VTEC: The Backbone of the Warning Archive . . . . . . . . . . . . . . . . 67

Mastering the Mesonet iv
7.2. The VTEC Browser . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 69
7.3. Warning Search . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 70
7.4. Storm-Based Warnings and IEM Cow . . . . . . . . . . . . . . . . . . . . . 70
7.5. Local Storm Reports . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 71
7.6. The Text Archive . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 72
7.7. SPC Products . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 74
7.8. Special Weather Statements and Warning Tags . . . . . . . . . . . . . . . . 75
7.9. Verification Autoplot Charts. . . . . . . . . . . . . . . . . . . . . . . . . . . 75
7.10.River and Hydrology Products . . . . . . . . . . . . . . . . . . . . . . . . . 76
7.11.What to Watch Out For . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 76
7.12.Workflow 3 — Researching a Past Warning Event End to End . . . . . . . 77
7.13.Key URLs — Chapter 7 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 78
III. Part III — Data Access and Quality 81
8. Chapter 8 — Downloading Data: Every Portal Explained 82
8.1. The Four Tiers . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 82
8.2. Tier 1: The UI Download Portals . . . . . . . . . . . . . . . . . . . . . . . . 83
8.3. Tier 2: CGI/Bulk Services . . . . . . . . . . . . . . . . . . . . . . . . . . . . 86
8.4. Tier 3: JSON/GeoJSON Ad-Hoc Services . . . . . . . . . . . . . . . . . . . 88
8.5. Tier 4: API v1 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 89
8.6. Two Special Services Worth Knowing . . . . . . . . . . . . . . . . . . . . . . 89
8.7. A Decision Framework . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 90
8.8. What to Watch Out For . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 91
8.9. Workflow 4 — Downloading a Year of Hourly ASOS Data . . . . . . . . . . 92
8.10.Key URLs — Chapter 8 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 93
9. Chapter 9 — Webcams 95
9.1. What the Network Actually Is. . . . . . . . . . . . . . . . . . . . . . . . . . 95
9.2. The Webcam Viewer . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 96
9.3. RWIS Cameras and the Data Combination . . . . . . . . . . . . . . . . . . 96
9.4. Building Time-Lapse Loops . . . . . . . . . . . . . . . . . . . . . . . . . . . 97
9.5. The Cool Lapses Archive . . . . . . . . . . . . . . . . . . . . . . . . . . . . 98
9.6. Coverage Limitations . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 98
9.7. What to Watch Out For . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 99
9.8. Key URLs — Chapter 9 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 99
10.Chapter 10 — Understanding Data Quality 100
10.1.The “Unofficial” Label . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 100
10.2.How IEM Handles Quality Control . . . . . . . . . . . . . . . . . . . . . . . 101
10.3.ASOS Temperature Storage: The Whole-Degree Problem . . . . . . . . . . 102
10.4.COOP Data and Time of Observation . . . . . . . . . . . . . . . . . . . . . 103

Mastering the Mesonet v
10.5.Trace Precipitation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 104
10.6.Missing Data Codes . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 104
10.7.What a Real Data Quality Investigation Looks Like: MDT and CXY . . . . 105
10.8.Station Metadata: Moves, Equipment Changes, and Archive Gaps . . . . . 106
10.9.What to Watch Out For . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 106
10.10.Key URLs — Chapter 10 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 107
11.Chapter 11 — Getting the Most Out of IEM: Putting It All Together 108
11.1.Using the IEM as a Research System . . . . . . . . . . . . . . . . . . . . . . 108
11.2.A Note on Using These Tools Together . . . . . . . . . . . . . . . . . . . . . 109
11.3.Key URLs — Chapter 11 . . . . . . . . . . . . . . . . . . . . . . . . . . . . 109
IV. Back Matter 111
Glossary 112
Appendix A — Network Quick Reference 123
Notes on Network Coverage Flags. . . . . . . . . . . . . . . . . . . . . . . . . . . 126
Network Comparison at a Glance . . . . . . . . . . . . . . . . . . . . . . . . . . . 126
Finding Network Station Lists . . . . . . . . . . . . . . . . . . . . . . . . . . . . 127
Appendix B — Complete URL Directory 128
1. Current Conditions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 128
2. Station Networks . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 129
3. Historical and Climate Data . . . . . . . . . . . . . . . . . . . . . . . . . . . . 130
4. NWS / Warnings / VTEC . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 132
5. Downloads . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 133
6. Services and APIs . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 135
7. Webcams . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 136
8. Admin, Info, and Site Resources . . . . . . . . . . . . . . . . . . . . . . . . . . 137
Appendix C — Autoplot Chart Reference 138
Daily . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 138
Monthly . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 147
Yearly . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 151
Hydrology / Drought Monitor Plots . . . . . . . . . . . . . . . . . . . . . . . . . 157
METAR ASOS Special Plots . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 157
NASS Quickstats (USDA Crop Statistics) . . . . . . . . . . . . . . . . . . . . . . 161
NWS Warning Plots . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 162
Tall Towers Plots . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 167
Upper Air / RAOB Sounding Plots . . . . . . . . . . . . . . . . . . . . . . . . . . 168
Miscellaneous . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 168

| Mastering | the Mesonet |                    |           | vi  |
| --------- | ----------- | ------------------ | --------- | --- |
| Appendix  | D — GIS     | Shapefile Download | Reference | 170 |
/request/gis/ Endpoints . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 170
Related Spatial Downloads . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 175
Coordinate System . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 176
Attribute Fields. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 177

Preface
Mastering the Mesonet
A Comprehensive Guide to Environmental Data Acquisition and Analysis
Author: Jonathan Sailor
Date: March 2026
License: CC BY-NC 4.0
Source: mesonet.agron.iastate.edu
1

| Mastering | the Mesonet |     |     |     |     |     | 2   |
| --------- | ----------- | --- | --- | --- | --- | --- | --- |
This guide is a comprehensive reference to the Iowa Environmental Mesonet (IEM), a free
public weather and climate data platform operated by Iowa State University that most
| weather | enthusiasts |     | have | only begun | to explore. |     |     |
| ------- | ----------- | --- | ---- | ---------- | ----------- | --- | --- |
TheIEMingestsdatafromdozensofobservingnetworks,preservesrecordsthatinsomecases
extend back to the 1800s, and makes them available through hundreds of tools, download
portals, and data services. Most regular users still rely on only a small fraction of what it
| offers. This | guide  | maps | the  | whole | thing. |     |     |
| ------------ | ------ | ---- | ---- | ----- | ------ | --- | --- |
| How          | to Use | This | Book |       |        |     |     |
The chapters follow a logical progression from orientation to detailed reference, but each one
is also designed to stand alone. Practical workflows are embedded directly in the chapters
where the relevant tools are introduced, so that when you finish reading about a tool, you
| immediately | see    | it applied |          | to a real  | problem.  |           |     |
| ----------- | ------ | ---------- | -------- | ---------- | --------- | --------- | --- |
| The back    | matter | is         | designed | as working | reference | material: |     |
• The Glossary defines 39 IEM-specific terms used throughout the book
• Appendix A is a network quick reference table you will return to repeatedly
• Appendix B is a complete URL directory — 166 verified links organized by category
• Appendix C is the full Autoplot chart reference — all 260 charts across 10 categories
| • Appendix |     | D    | covers  | the GIS | shapefile | download endpoints |     |
| ---------- | --- | ---- | ------- | ------- | --------- | ------------------ | --- |
| A Note     | on  | Data | Quality |         |           |                    |     |
Throughoutthebookyouwillencountercalloutboxesflaggingdataqualityissuesattheexact
point where they are relevant. These are not buried in a later chapter; they appear when
you first encounter the data they affect. Chapter 10 provides the full technical treatment;
| the callout | boxes | are  | the | early warning | signs. |     |     |
| ----------- | ----- | ---- | --- | ------------- | ------ | --- | --- |
| A Note      | on    | URLs |     |               |        |     |     |
Every URL in this guide was verified against the live IEM site in March 2026. In the HTML
| and EPUB | versions, |     | all URLs | are | live hyperlinks. |     |     |
| -------- | --------- | --- | -------- | --- | ---------------- | --- | --- |

| Mastering | the Mesonet |     | 3   |
| --------- | ----------- | --- | --- |
License
This work is licensed under the Creative Commons Attribution-NonCommercial 4.0 Interna-
tional license. You may share and adapt it for non-commercial purposes with attribution to
| Jonathan | Sailor. Commercial | use is prohibited. |     |
| -------- | ------------------ | ------------------ | --- |

Introduction
For more than two decades, a website run by the Agronomy Department at Iowa State
University has been quietly doing something remarkable: making a genuinely professional-
grade weather and climate data system freely available to anyone who wants to use it.
Ifyouhavespenttimeonweatherforums, youhavealmostcertainlyseenitscharts. Someone
posts a plot showing sixty years of daily high temperatures at their local airport, with the
period-of-record average overlaid and the current year highlighted in red. Someone else
shares a map of every tornado warning polygon issued over a five-state region across the
past twenty years. Another person pulls up a chart showing that last Tuesday’s dew point
reading at their station was the highest ever recorded for that date in March. All of those
charts came from the same place: the Iowa Environmental Mesonet, known as the IEM.
The problem with the IEM is not that it is hard to use — most of it is point-and-click. The
problem is that it is enormous, and the sheer scale of it means most people only ever use a
small corner of what is available. The navigation menu has eight top-level categories. Behind
those eight categories are hundreds of individual tools, download portals, data viewers, and
applications. Some of the most useful features on the entire site are not in any menu at all
— they exist at direct URLs that you only find if someone points you to them.
This guide is an attempt to fix that. It covers the IEM from the outside in: what the site
is, how it is organized, what each section actually contains, and how to get the most out
of the tools that matter most for serious weather hobbyists. It does not assume you are a
beginner. It does assume you have not spent years mapping every corner of the IEM the
way a researcher or developer might. Somewhere in between is exactly the reader this guide
is written for.
A few things this guide is not: it is not a programming tutorial, it is not a manual for
scraping data in bulk with Python scripts, and it is not a guide for forecasters or agricultural
scientists, even though the IEM serves those audiences too. For those topics, the IEM’s
own documentation is actually quite good. This guide is for the enthusiast who wants to
understand the weather record at their station, research past events, analyze patterns, and
know where to look for whatever question they happen to be asking on any given day.
Throughout the guide, URLs are provided as direct links. In the HTML and EPUB versions,
every URL is live — click it and you go directly to that page on the IEM website. The IEM
4

Mastering the Mesonet 5
is an actively maintained site and things occasionally move, but the core structure has been
stable for years. The URLs verified for this guide reflect the site as of March 2026.
One last note before getting started. The IEM is operated by a small team at Iowa State,
led by developer Daryl Herzmann, who has been building and maintaining the system for
over twenty years. It runs on public university resources. When you use the IEM, use it
thoughtfully — the server handles over 2,000 requests per second from users worldwide,
and it keeps running because the people behind it care about keeping it available. If you
download data in bulk, be polite about it. If you find a bug or a data quality issue, report
it. The IEM’s own QC ticket system is public, and the team actually reads and responds to
it.
With that, let’s start at the beginning.

Part I.
| Part | I — | Understanding | the IEM |
| ---- | --- | ------------- | ------- |
6

1. Chapter 1 — What Is the IEM?
1.1. The Short Version
The Iowa Environmental Mesonet is a free, public weather and climate data platform
operated by Iowa State University. It ingests data from dozens of observing networks,
archives it, and makes it available through a collection of web applications, download portals,
and data services. The archive goes back in some cases to the 1800s. The tools range
from simple current-conditions displays to sophisticated charting systems with hundreds
of configurable parameters. It is free to use for any lawful purpose, including commercial
use.
That is the functional description. The more interesting question is how something like this
came to exist at a land-grant university in Iowa — and why understanding that history
helps you use the site better.
1.2. Where It Came From
The IEM grew out of the Iowa Environmental Mesonet project, which began in the 1990s
as an effort to collect data from a variety of observing networks in Iowa and make them
available in a unified form. At the time, weather data from different networks — airport
ASOSstations, NWS cooperativeobservers, agriculturalweatherstations— livedin separate
systems that did not talk to each other. The IEM was built to aggregate them.
Over time, the project expanded well beyond Iowa. The network coverage now includes
stations across the entire contiguous United States and internationally. The tools evolved
from simple data displays into a full research and analysis platform. The Daily Feature —
a chart or analysis published almost every day since February 2002 — became a kind of
running meteorological journal that demonstrates what the data can show when you ask it
the right questions.
The key figure throughout this history has been Daryl Herzmann, a developer at Iowa State
who has been the primary architect and maintainer of the IEM for over two decades. His
name appears on the contact page, his GitHub repository contains the source code for the
entire site (it is open source), and his Twitter handle is linked from the footer. This is not
7

| Mastering | the Mesonet |     |     |     | 8   |
| --------- | ----------- | --- | --- | --- | --- |
a faceless institutional project — it is one person’s life work, supported by Iowa State’s
infrastructure and a small team of collaborators. Understanding that helps explain both the
remarkable depth of the system and the occasional rough edges that come with a project of
| this scale | maintained | by a small | team. |     |     |
| ---------- | ---------- | ---------- | ----- | --- | --- |
| 1.3. What  | “Mesonet”  |            | Means |     |     |
A mesonet — short for mesoscale network — is a network of weather stations designed to
observe atmospheric conditions at a scale smaller than the traditional synoptic weather
observation network but larger than a single point. The classic example is the Oklahoma
Mesonet, a statewide network of automated stations spaced roughly 30 kilometers apart,
designed to capture the mesoscale variability in temperature, humidity, and wind that drives
| severe | weather in | that region. |     |     |     |
| ------ | ---------- | ------------ | --- | --- | --- |
The IEM is not itself a physical observing network in that sense — it does not own and
operate a set of weather stations across Iowa. What it does is aggregate data from observing
networks that do exist: the ASOS airports, the NWS cooperative observers, the Iowa State
agriculturalweathernetwork,rivergauges,roadwaysensors,andmanyothers. The“mesonet”
in the name reflects the original ambition to build an integrated view of environmental
conditions across the state at mesoscale resolution. It has since grown into something
| considerably | larger.  |     |     |     |     |
| ------------ | -------- | --- | --- | --- | --- |
| 1.4. The     | Homepage |     |     |     |     |
When you navigate to mesonet.agron.iastate.edu, the homepage has a specific structure that
is worth understanding because it reveals how the IEM thinks about its own audience.
At the top is a red navigation bar with a search box and a hamburger menu. The search box
accepts natural-language queries in a specific format — the placeholder text shows 'DSM'
'autoplot 100' as an example, which means you can search for a station ID, an application
name, or a combination. It is a useful shortcut once you know what you are looking for.
Below the header, three audience buttons appear: Ag Weather, NWS Users, and
Researchers. These are portal buttons that take you to curated entry points for each
audience. Ag Weather leads to the agricultural weather and climate information pages.
NWS Users leads to the NWS data mainpage. Researchers leads to the archive mainpage.
If you are a weather enthusiast coming to the IEM for the first time, none of these three
buttons is exactly right for you — the closest is probably Researchers, because you want the
archive and the analytical tools. But do not get too attached to these portal labels. They
reflect the IEM’s primary funding audiences and do not define the limits of what the site
| can do | for someone | with a general | weather | interest. |     |
| ------ | ----------- | -------------- | ------- | --------- | --- |

Mastering the Mesonet 9
The center of the homepage is dominated by the IEM Daily Feature — a chart and short
explanation published most days, tied to whatever is happening meteorologically. On the
day this guide was verified, the feature covered an all-time March temperature record set at
Cedar Rapids, with a chart showing the monthly maximum temperature records by month
for that station. Below the current feature is a list of previous years’ features for the same
calendar date, going back to 2002. This is one of the most underrated features of the entire
site: you can see what the IEM was tracking on this exact date in every year going back
over two decades, which gives you an immediate sense of what the tools can produce and
what kinds of questions they answer.
The right column of the homepage has two sections worth noting. The Most Popular
sidebar lists the seven most-accessed applications on the site at any given time — currently
Automated Data Plotting, Climodat Reports, Iowa Mesonet Plot, IEM One (RADAR +
Warnings), IEM GIS Rainfall, Sortable Currents, and Winter Storms of 2025–2026. This is
a real-time list and changes with the season and with whatever weather is happening. It is a
reasonable proxy for “what do most users actually come here for.”
The Current Website Performance panel is a small but revealing feature. It shows live
bandwidth usage and request rates. When this guide was verified, the IEM was handling
2,259 requests per second across the entire site and 224 requests per second specifically
to the API and data services, with 100% API success rate. On a busy weather day — a
significant severe weather outbreak, a record-breaking heat event — these numbers spike
considerably. The fact that this performance data is displayed publicly on the homepage is
characteristic of the IEM’s general transparency about its own operations.
At the bottom of the homepage, three map widgets show current soil temperatures (from
the Iowa State soil moisture network), a current precipitation analysis, and a current surface
observation plot. These are live products that update automatically and give you a quick
read on current conditions across the Midwest.
1.5. The Navigation Structure
The main navigation menu — accessible via the hamburger icon in the top right corner
on mobile, or expanded on desktop — contains eight top-level categories: Apps, Areas,
Datasets, Info, Networks, NWS Data, Services, and Webcams. Each has a dropdown
with subcategories.
Understanding the distinction between these eight categories is the first step to using the
site efficiently, because the names are not always intuitive:
Apps contains interactive web applications — things you use in a browser to produce charts,
displays, and analyses. Automated Data Plotting (Autoplot) lives here, as do Climodat,
IEM Explorer, the Time Machine, and Wind Roses.

Mastering the Mesonet 10
Areas contains topic-based portals that aggregate content by subject rather than by tool
type. The Climate Mainpage, Severe Weather Mainpage, GIS Mainpage, and Drought
Monitor all live here. Think of Areas as the “I want to browse by topic” menu.
Datasets contains entry points to the major data archives — Daily Climatology, Daily
Observations, IEM Reanalysis, Model Output Statistics, the NEXRAD Mosaic, and others.
If you know what kind of data you want and want to go directly to it, start here.
Infocontainsdocumentation,news,qualitycontrolinformation,thestationmetadatalookup,
the variables reference, and the past Daily Features archive. This is the section that explains
how the site works.
Networks contains the observing network pages — ASOS airports, COOP stations, CoCo-
RaHS, DCP/HADS river gauges, RWIS roadway stations, and others. If you want to browse
stations within a network or understand what a specific network measures, start here.
NWS Data contains everything related to National Weather Service operational products
— warnings, watches, advisories, local storm reports, text products, SPC outlooks, and
the VTEC browser. This is one of the deepest sections on the site and gets its own full
chapter.
Services contains the technical access points — the API, bulk data download portals,
Gibson Ridge placefiles, OGC webservices, and the LDM data feed. This is where you go
when you want data programmatically rather than through a web interface.
Webcams contains the camera viewer, time-lapse tools, and the cool lapses archive.
One important caveat: the navigation menu is not a complete map of the site. A number
of useful pages exist at direct URLs that do not appear in any menu. These include IEM
One (a combined RADAR and warnings view), Sortable Currents (a real-time cross-network
observation table), and the full archive of raw text files. Where these hidden pages exist
and what they do is covered throughout the relevant chapters.
1.6. The Daily Feature Archive
The IEM Daily Feature deserves more attention than the one paragraph most visitors give
it. Since February 2002, someone at the IEM — almost always Daryl Herzmann — has
published a chart or map tied to whatever is currently interesting in the weather record,
with a short explanation of what the chart shows and why it matters. These are not press
releases. They are the kind of quick analysis a meteorologist does when something catches
their attention: an all-time record, an unusual pattern, a new tool worth demonstrating, a
climatological pattern that puts the current weather in context.

Mastering the Mesonet 11
The archive is at mesonet.agron.iastate.edu/onsite/features/past.php and is organized by
month. Every entry links to the chart, includes the short write-up, and — critically —
includes a “Generate This Chart on Website” link when the chart was produced by Autoplot.
That link takes you directly to the Autoplot configuration that produced the chart, with all
the parameters already set, so you can run it yourself, change the station, change the year,
and immediately start exploring.
The archive is also searchable by tag at mesonet.agron.iastate.edu/onsite/features/tags/.
Tags include things like winter2526 (the current winter storm season), blizzard, thunder,
aridity, warmfront, and dozens of others going back years. If you are trying to find
examples of a particular type of analysis — say, how the IEM has visualized cold air
damming events, or how it handles precipitation type verification — the tag archive is a fast
way to find representative examples.
There is a practical tip buried here for new users: if you do not know where to start with
the IEM, start with the Daily Feature archive. Read a month’s worth of entries. Every one
links to a live chart that you can immediately run for your own station. By the time you
have worked through a few dozen entries, you will have a much more concrete sense of what
the tools can do than you would get from reading any amount of documentation.
1.7. What the IEM Is Not
A few clarifications that save confusion later.
The IEM is not the official government archive. NCEI (the National Centers for
Environmental Information) is the official custodian of US climate records. The IEM draws
on some of the same underlying data — GHCND stations, ASOS observations, NWS COOP
reports — but the IEM’s processed products are explicitly labeled as unofficial. This means
the IEM’s period-of-record records for your station may not exactly match what NOAA
would cite in an official publication. This is not a flaw; it is an honest acknowledgment
that different processing choices produce slightly different results, and the IEM’s choices are
optimized for usability and currency rather than archival certification.
The IEM is not primarily a forecast site. You will not find model output, forecast
soundings, or ensemble guidance here. What you will find is historical data, climatology,
and analysis tools built on the observational record. The one exception is Model Output
Statistics (MOS), which is a statistical bias-correction of model forecasts archived at the
station level — but even MOS on the IEM is an archive product, not a live forecast display.
The IEM is not a real-time alerting service. It archives NWS warnings and processes
them in real time, and it operates iembot — a service that posts warning text to social
media — but it is not designed to be the source you rely on for life-safety alerts during

| Mastering | the Mesonet |     |     |     | 12  |
| --------- | ----------- | --- | --- | --- | --- |
an active severe weather event. Use the NWS directly for that. Use the IEM afterward to
| research | what happened. |     |     |     |     |
| -------- | -------------- | --- | --- | --- | --- |
The IEM is not always Iowa. Despite the name, the data coverage extends nationwide
and internationally. The observing networks, the Autoplot charts, the warning archive, the
MOS data — all of it works for stations across the contiguous US and in many cases beyond.
The Iowa-specific products (the Iowa flood center precipitation maps, the ISU Soil Moisture
Network data) are a subset. Do not let the Iowa branding lead you to conclude the site is
| only useful | if you care | about Iowa       | weather. |       |     |
| ----------- | ----------- | ---------------- | -------- | ----- | --- |
| 1.8. A      | Note on     | the “Unofficial” |          | Label |     |
Throughout the IEM, you will encounter the word “unofficial” applied to climate records
and statistics. This is worth understanding precisely, because it means something specific
| and does | not mean | what it might | first appear | to mean. |     |
| -------- | -------- | ------------- | ------------ | -------- | --- |
The IEM computes daily records and climatological statistics directly from the data it
ingests. Because its processing pipeline may handle missing data, duplicate reports, and
timing offsets differently than NCEI’s official climatological procedures, the numbers do not
always agree exactly. The IEM calls its results “unofficial” to clearly signal that they should
not be cited in official government reports or legal proceedings as the authoritative value.
What “unofficial” does not mean is inaccurate or unreliable for practical purposes. For the
kind of analysis a weather enthusiast does — comparing this year’s precipitation to the
historical average, finding out what the coldest temperature on record was for your station
on a given date, tracking how many days above 90°F a station has had over the past decade
— the IEM’s unofficial numbers are entirely appropriate. The differences from official values,
when they exist, are typically small and stem from defensible methodological choices rather
than errors.
The label is also a form of legal protection for the university. It keeps the IEM from
becoming the de facto cite in every insurance claim or agricultural contract dispute that
touches weather data. That is a reasonable position for a free public service to take.
| 1.9. Key     | URLs | — Chapter | 1   |                           |     |
| ------------ | ---- | --------- | --- | ------------------------- | --- |
| Page         |      |           |     | URL                       |     |
| IEM Homepage |      |           |     | mesonet.agron.iastate.edu |     |

| Mastering     | the Mesonet |     |                                       |     | 13  |
| ------------- | ----------- | --- | ------------------------------------- | --- | --- |
| Page          |             |     | URL                                   |     |     |
| Daily Feature | Archive     |     | mesonet.agron.iastate.edu/onsite/fea- |     |     |
tures/past.php
| Feature Tags |     |     | mesonet.agron.iastate.edu/onsite/fea- |     |     |
| ------------ | --- | --- | ------------------------------------- | --- | --- |
tures/tags/
Feature Titles (full list) mesonet.agron.iastate.edu/onsite/features/ti-
tles.php
| Daily Bulletin | Signup |     | groups.google.com/g/iem-dailyb |     |     |
| -------------- | ------ | --- | ------------------------------ | --- | --- |
| IEM News       |        |     | mesonet.agron.iastate.edu/on-  |     |     |
site/news.phtml
| RSS Feed      |             |           | mesonet.agron.iastate.edu/rss.php           |               |     |
| ------------- | ----------- | --------- | ------------------------------------------- | ------------- | --- |
| GitHub Source | Code        |           | github.com/akrherz/iem                      |               |     |
| Contact       |             |           | mesonet.agron.iastate.edu/info/contacts.php |               |     |
| Next: Chapter | 2 — Station | Networks: | The Foundation                              | of Everything |     |

2. Chapter 2 — Station Networks: The
Foundation of Everything
Everything the IEM does starts with a station. A chart of daily temperature departures
needs a station. A warning search needs a county or a Weather Forecast Office (WFO). A
precipitation download needs to know which network you want and which observer. Before
you can use any of the IEM’s tools effectively, you need to understand how it organizes the
raw material — the observing stations — and what each network actually represents.
The IEM ingests data from more than a dozen distinct observing networks, each with its
own history, its own measurement standards, its own strengths, and its own quirks. This
chapter covers the networks you will actually encounter when doing weather research: what
they measure, how far back they go, where their limitations are, and how to navigate them
on the IEM.
2.1. Finding Any Station
Before diving into specific networks, the most important page to know is the station locator
at mesonet.agron.iastate.edu/sites/locate.php. Type a city, a station ID, or a ZIP code,
select a network from the dropdown, and the IEM returns a list of matching stations with
their coordinates, elevation, archive start date, and a link to that station’s full data page.
This is your entry point whenever you need to identify the right station ID before pulling
data.
If you want to browse all stations in a given network, the Network Tables page at
mesonet.agron.iastate.edu/sites/networks.php lists every network the IEM tracks — from
Alabama ASOS to Zimbabwe ASOS, and everything in between. For a given network you
can generate the station list as an HTML table, CSV, shapefile, GEMPAK table, or MADIS
table. Each station entry links to its individual station page, which shows its attributes —
including things like whether it has 1-minute data, whether it has TAF forecasts, what
its GHCNH identifier is for cross-referencing with NCEI, and when the archive officially
begins.
Station IDs on the IEM follow a few different conventions depending on the network. ASOS
stations use 3-character domestic identifiers (DSM for Des Moines, MDT for Harrisburg) or
14

| Mastering |     | the Mesonet |     |     |     |     |     | 15  |
| --------- | --- | ----------- | --- | --- | --- | --- | --- | --- |
the full 4-character ICAO identifiers with the K prefix (KDSM, KMDT). COOP stations
use IEM-internal identifiers like IATDSM or station codes from the GHCND database
(USC00######, USW000######). DCP stations use the 5-character NWS Location
Identifiers (NWSLI) that appear in SHEF product headers. The station page for any station
shows all the relevant identifiers in one place, which avoids a great deal of confusion when
| cross-referencing |      |     | data      | between | systems. |         |          |     |
| ----------------- | ---- | --- | --------- | ------- | -------- | ------- | -------- | --- |
| 2.2.              | ASOS |     | and AWOS: |         | The      | Airport | Backbone |     |
The Automated Surface Observing System — ASOS — is the workhorse of the IEM for
weather hobbyists. These are the automated weather stations at airports across the United
States, operated jointly by the NWS, the FAA, and the Department of Defense. They
report continuously, have long records, and measure the variables most users care about:
temperature, dew point, wind speed and direction, visibility, ceiling, precipitation, and
pressure.
Exclamation-Triangle
|     | Data | Quality | Note | — ASOS | Temperature |     | Rounding |     |
| --- | ---- | ------- | ---- | ------ | ----------- | --- | -------- | --- |
ASOS stations record temperature in whole degrees Fahrenheit internally, but transmit
via the METAR format, which requires Celsius. The conversion introduces a rounding
artifact: 78°F becomes 25.56°C, transmits as 26°C, then converts back to 78.8°F —
which rounds to 79°F. A full degree of phantom warming can enter the record purely
|     | from the | transmission |     | pipeline. |     |     |     |     |
| --- | -------- | ------------ | --- | --------- | --- | --- | --- | --- |
If you are doing precise temperature analysis, especially around record extremes, look
for the supplemental T-group in the raw METAR feed; it carries the unrounded value.
|     | This is | covered | in depth | in  | Chapter | 10. |     |     |
| --- | ------- | ------- | -------- | --- | ------- | --- | --- | --- |
The IEM’s ASOS mainpage is at mesonet.agron.iastate.edu/ASOS/. From there you can
get to current conditions, recent METAR reports, monthly precipitation tables, download
| portals, | and | the | 1-minute | archive. |     |     |     |     |
| -------- | --- | --- | -------- | -------- | --- | --- | --- | --- |
A few points are worth keeping in mind before you rely heavily on ASOS data:
Archive depth varies considerably by station. The major airport stations — places
like Des Moines (DSM, January 1928), Burlington (BRL, September 1931), Mason City
(MCW, October 1940) — have records stretching back decades before ASOS hardware was
even invented. That is because those stations were manually observed airports before being
converted to automation. Smaller stations came online in the mid-1990s when ASOS was
deployed nationally; most of those have archives starting between 1994 and 1996. When you
pull ASOS data for a station, always check the archive begin date in the station metadata
| before | assuming |     | the record | goes | back | as far as | you need. |     |
| ------ | -------- | --- | ---------- | ---- | ---- | --------- | --------- | --- |

Mastering the Mesonet 16
ASOS is not AWOS, and the distinction matters. The Automated Weather Observing
System (AWOS) is a slightly older, less capable automated system found at smaller airports.
AWOSstationsgenerallyreportlessfrequentlythanASOS,donotalwaysreportprecipitation,
and have less rigorous quality control. The IEM lumps ASOS and AWOS together under the
same network category, but when you look at a station’s attributes you will see IS_AWOS=1
on AWOS stations. For serious precipitation analysis, you want ASOS stations — specifically
the ones with HAS_PHOUR=1 (hourly precip bucket) or HAS1MIN=1 (1-minute archive). Those
attributes appear in the station table and on each station’s page.
Temperature is stored internally in whole-degree Fahrenheit. This is a design
limitation of the original ASOS sensors. For most purposes it makes no difference, but if
you are doing analysis that requires sub-degree temperature precision — onset of freezing at
a specific threshold, for example — use the T-group from the raw METAR string when it is
available. The IEM’s hourly download includes the raw METAR field, so you can parse the
T-group yourself.
The precipitation record has a well-known gap around the ASOS transition.
When ASOS replaced manual observers at airports in the early-to-mid 1990s, precipitation
measurement changed. The original ASOS tipping-bucket gauges had documented problems
with snowfall and light precipitation. A program to install All-Weather Precipitation
Accumulation Gauges (AWPAG) at ASOS sites addressed some of these issues, but the
install dates varied by station and the improvement was gradual. For precipitation analysis
at ASOS stations that spans the pre- and post-automation period, treat the data on either
side of that transition with awareness that the measurement method changed.
The 1-minute ASOS archive is one of the IEM’s more useful hidden features. The
National Center for Environmental Information (NCEI) maintains a 1-minute resolution
dataset for many US ASOS sites going back to approximately 2000. The IEM processes this
archive daily — it is not real-time, with a delay of 18–36 hours — and makes it available
for download at mesonet.agron.iastate.edu/request/asos/1min.phtml and for plotting via
Autoplot chart q=211. This is the right data source when you want to look at the precise
timing of a temperature drop, a pressure jump, or a precipitation onset during an event.
Not every station has it, and the coverage gets thinner the further back you go, but for the
past ten to fifteen years at most major ASOS sites it is quite complete.
2.3. NWS COOP: A Century of Daily Observations
The NWS Cooperative Observer Program — universally called COOP — is where the IEM’s
real historical depth lives. These are the cooperative observer stations: human volunteers,
mostly private citizens, who take daily readings of temperature and precipitation. They read
a max-min thermometer once a day, measure whatever fell in the rain gauge, and call or
submit it to the NWS. Some stations have been doing this continuously since the 1880s.

Mastering the Mesonet 17
Thatlongevityisexactlywhythedatahasquirksthatanyserioususerneedstounderstand.
The IEM’s COOP mainpage is at mesonet.agron.iastate.edu/COOP/, and it is one of the
more feature-rich network pages on the site. It gives you access to current observations, the
full historical download, the normals download, freezing date statistics, snow depth duration
tools, the growing season plotter, and the daily extremes table. But before using any of
those, understand what the raw data actually is.
COOP reports are once-daily observations, not instantaneous readings. An
observer reads the maximum and minimum thermometer at a fixed time each day —
traditionally 7 AM, though some observe at other times — resets the thermometer, and
records whatever accumulated in the gauge since the previous reading. This means a “daily”
high temperature reading is the maximum over a roughly 24-hour period ending at the
observation time, and a “daily” precipitation reading is the accumulation over that same
period. This is fundamentally different from the way airport ASOS stations measure daily
summaries, where the day runs midnight to midnight.
This observation time offset matters enormously when comparing COOP data to ASOS
data, when looking at events that span observation times, and when computing things like
monthly totals that might not add up the way you expect. The IEM processes COOP
data into its Climodat dataset, which applies quality control and attempts to handle
some of these timing issues, but you should be aware that the raw COOP and the pro-
cessed Climodat are two different things. The Climodat download is at mesonet.agron.ias-
tate.edu/request/coop/fe.phtml (quality-controlled) and the raw COOP observations are at
mesonet.agron.iastate.edu/request/coop/obs-fe.phtml.
The COOP network is also where you get access to the IEM’s daily normals and records
— the period-of-record daily statistics that underpin most of the climatology tools. The
extremes table at mesonet.agron.iastate.edu/COOP/extremes.php shows daily records going
back as far as the station record allows, all labeled as unofficial in the IEM’s standard
convention. The normals download at mesonet.agron.iastate.edu/COOP/dl/normals.phtml
gives you the full 366-day normal climatology for any station, including average high, average
low, average precipitation, record values, growing degree days, and solar radiation.
Two COOP sub-tools deserve special mention. The freeze date tool at mesonet.agron.ias-
tate.edu/COOP/freezing.php gives you the statistics of first and last freeze dates across
stations — a question that comes up constantly in discussions of growing seasons, late-season
snow events, and climate trends. The snow depth duration tool at mesonet.agron.ias-
tate.edu/COOP/snowd_duration.phtml shows, for a given date, how long snow cover
typically persists — useful context when you are watching an early season snowfall and
wondering whether it is likely to stick around.
One thing to watch for in COOP data: gaps are common and are not always flagged.
Observers miss days. Stations go inactive for months or years and then restart. Equipment

| Mastering | the Mesonet |     |     |     |     | 18  |
| --------- | ----------- | --- | --- | --- | --- | --- |
changes. The longer the record, the more of this you will encounter. When you pull COOP
data for a long period and compute statistics, always check the count of valid observations —
the IEM reports this in the normals table as the “years” field — before drawing conclusions
| from stations  | with thin | records in certain | time periods. |               |     |     |
| -------------- | --------- | ------------------ | ------------- | ------------- | --- | --- |
| 2.4. CoCoRaHS: |           | The Precipitation  |               | Dense Network |     |     |
The Community Collaborative Rain, Hail and Snow Network is the largest precipitation
observing network in the United States by station count, and it is built almost entirely on
volunteerswithastandardgauge, atrainingmodule, andaninternetconnection. CoCoRaHS
observers report daily precipitation, snow, and hail at a much finer spatial density than
either ASOS or COOP — a typical metro area might have dozens of CoCoRaHS stations
| compared | to one or | two ASOS airports | and a handful | of COOP sites. |     |     |
| -------- | --------- | ----------------- | ------------- | -------------- | --- | --- |
The IEM’s CoCoRaHS page is at mesonet.agron.iastate.edu/cocorahs/, with current obser-
vations at mesonet.agron.iastate.edu/cocorahs/current.phtml and an observation listing at
mesonet.agron.iastate.edu/cocorahs/obs.phtml.
For precipitation research, CoCoRaHS data is most useful when you want to map the spatial
distribution of a specific event — how much fell where during a particular storm, whether
the radar QPE estimate was close to what gauges measured, how much a lake effect band
produced along its axis versus a few miles off it. The IEM integrates CoCoRaHS into its
precipitation maps and has it available in the daily summary download portal alongside
| ASOS and | COOP data. |     |     |     |     |     |
| -------- | ---------- | --- | --- | --- | --- | --- |
The limitation is consistency. CoCoRaHS observer density varies dramatically by region,
and individual observers join and leave the network constantly. A station with a 2012 start
date might have had one observer from 2012 to 2018 and a completely different person
since then. This is fine for event-specific analysis but makes CoCoRaHS difficult to use for
| long-term      | trend work. |         |             |            |        |     |
| -------------- | ----------- | ------- | ----------- | ---------- | ------ | --- |
| 2.5. DCP/HADS: |             | Rivers, | Reservoirs, | and Remote | Gauges |     |
TheGOESDataCollectionPlatforms—DCP—areadiversecollectionofautomatedsensors
that transmit data via GOES satellite. On the IEM, the DCP section at mesonet.agron.ias-
tate.edu/DCP/ covers the Hydrometeorological Automated Data System (HADS) network,
which is essentially the NWS’s aggregation of river gauges, reservoir sensors, snow depth
sensors, and other remote automated observations from hundreds of different operating
agencies.

Mastering the Mesonet 19
The data from DCP stations is encoded in the Standard Hydrometeorological Exchange
Format — SHEF — a coding system that assigns two-letter physical element codes to each
variable. River stage is HP. Streamflow is QR. Precipitation cumulative is PC. Air temperature
is TA. When the IEM displays DCP data, it shows these SHEF codes alongside the values. If
you are looking at a river gauge and wondering what HP means, that is your answer: height
primary, the stage in feet or meters above a local datum.
The most useful DCP tool for weather hobbyists is the interactive current map at
mesonet.agron.iastate.edu/DCP/map.php, which lets you select a SHEF code and see the
current value at every DCP station that reports that variable. Selecting HP gives you a map
of current river stage across the network — a quick way to assess which rivers are elevated
in your region during or after a heavy rain event.
The DCP section also has a “tomb” page at mesonet.agron.iastate.edu/DCP/tomb.phtml —
a list of NWSLI identifiers that the IEM has received data for but cannot identify because
they do not appear in the NWS Location Identifier database. This is a data quality artifact,
notacrisis,butitisthekindofhonesttransparencyaboutdatalimitationsthatcharacterizes
the IEM throughout.
2.6. RWIS: Roadway Weather and Pavement Sensors
Roadway Weather Information Systems (RWIS) are operated by state departments of
transportation to support winter road maintenance decisions. They measure not just
standardatmosphericvariablesbutpavement-specificsensors: pavementsurfacetemperature,
subsurface temperature, pavement condition (dry, wet, ice, snow), and sometimes chemical
sensors for detecting ice-melting agents.
The IEM’s RWIS mainpage is at mesonet.agron.iastate.edu/RWIS/, with current ob-
servations at mesonet.agron.iastate.edu/RWIS/current.phtml and road camera feeds at
mesonet.agron.iastate.edu/RWIS/camera.phtml.
For weather enthusiasts, RWIS is most useful in two situations. First, during winter weather
events, RWIS pavement temperature data tells you something that no atmospheric sensor
can: whether the road surface is actually at or below freezing, which is what determines
whether precipitation falls as rain or accumulates as ice. A 34°F air temperature with a
29°F pavement is a very different scenario from 34°F air over a 36°F pavement. Second,
RWIS stations often fill geographic gaps in the ASOS network — they are typically sited
on highways in areas between airports, so they can give you surface temperature and wind
readings in locations that would otherwise have no automated coverage.
The limitation is that RWIS stations were designed for road maintenance, not climatological
research. QualitycontrolislessrigorousthanASOS,sensorsdrift,andstationsaresometimes

| Mastering | the Mesonet |     |     |     | 20  |
| --------- | ----------- | --- | --- | --- | --- |
moved when highway construction changes the relevant road segment. Use RWIS for current
conditions and event analysis; do not build a long-term climatology from it.
| 2.7. Specialty |     | Networks |     |     |     |
| -------------- | --- | -------- | --- | --- | --- |
Several other networks appear in the IEM’s menu and are worth knowing about even if you
| use them | less frequently. |     |     |     |     |
| -------- | ---------------- | --- | --- | --- | --- |
ISU Soil Moisture Network at mesonet.agron.iastate.edu/agclimate/ is an Iowa-specific
agricultural weather network operated by Iowa State University. Beyond the obvious
agricultural applications, the soil moisture and temperature data from this network is
genuinely interesting during transition-season events — it shows you whether soils are frozen
or saturated, which affects how precipitation moves into rivers and whether spring warmth
is penetrating the ground. The soil temperature maps that appear on the IEM homepage
| are generated | from | this network. |     |     |     |
| ------------- | ---- | ------------- | --- | --- | --- |
SCAN (Soil Climate Analysis Network) at mesonet.agron.iastate.edu/scan/ is the USDA
NRCS equivalent — a national network of automated stations at agricultural research
sites measuring soil temperature and moisture at multiple depths, along with standard
atmospheric variables. Coverage is thinner than ASOS but the data quality is high.
USCRN (US Climate Reference Network) at mesonet.agron.iastate.edu/uscrn/ is NOAA’s
gold-standard reference network, designed specifically to detect long-term climate trends
without the site-change and urbanization issues that affect longer ASOS and COOP records.
USCRN stations are in pristine, undisturbed locations, triple-redundant, and meticulously
maintained. The network has been operational since the early 2000s and the data quality
is exceptional. The downside is coverage — there are only about 130 stations across the
| contiguous | US, so your | nearest USCRN | site may | be 100 miles away. |     |
| ---------- | ----------- | ------------- | -------- | ------------------ | --- |
CoCoRaHS was covered above. NLAE Flux at mesonet.agron.iastate.edu/nstl_flux/
covers flux tower data from the National Laboratory for Agriculture and the Environment
— specialized eddy covariance measurements of energy and carbon exchange that are not
likely to be part of most weather hobbyists’ workflows. The Other network page at
mesonet.agron.iastate.edu/other/ aggregates miscellaneous networks including TV station
weather networks (KCCI SchoolNet, KELO WeatherNet, KIMT StormNet) and specialized
| institutional | networks. |     |             |       |     |
| ------------- | --------- | --- | ----------- | ----- | --- |
| 2.8. Station  | Metadata  | and | the Network | Table |     |
Every station on the IEM has a page that shows its full metadata. You reach it either by
clicking the station ID in a network table or by going to mesonet.agron.iastate.edu/sites/lo-

| Mastering | the | Mesonet |     |     |     |     |     | 21  |
| --------- | --- | ------- | --- | --- | --- | --- | --- | --- |
cate.phpandsearching. Thestationpageshowscoordinates,elevation,archivedates,network
membership, and a set of attribute flags that tell you what data is available:
| • HAS1MIN=1 |     | —   | 1-minute | ASOS | data | available |     |     |
| ----------- | --- | --- | -------- | ---- | ---- | --------- | --- | --- |
• HASTAF=1 — Terminal Aerodrome Forecasts (TAF) issued for this station
| • HAS_PHOUR=1 |     | —   | hourly  | precipitation |          | bucket data | available |     |
| ------------- | --- | --- | ------- | ------------- | -------- | ----------- | --------- | --- |
| • IS_AWOS=1   |     | —   | this is | an AWOS       | station, | not ASOS    |           |     |
• GHCNH_ID — the GHCN-Hourly identifier for cross-referencing with NCEI
• FLOOR — the earliest reliable date for data from this station (overrides archive begin
| in  | some | cases) |     |     |     |     |     |     |
| --- | ---- | ------ | --- | --- | --- | --- | --- | --- |
• SHEF_6HR_SRC — which DCP gauge is used to supplement 6-hour precip data
These attributes are not just metadata — they tell you what you can actually do with a
station. Before building a long analysis pipeline around a specific ASOS station, pull its
station page and confirm it has the coverage you need. The FLOOR attribute in particular
is worth checking: some stations have archive dates that go back further than the data is
actually reliable, and the FLOOR reflects the IEM’s judgment about where the trustworthy
record begins.
The Network Tables page also offers direct export of any network’s station list as a CSV or
shapefile, which is useful when you want to do spatial analysis on a full network rather than
| looking  | up stations |      | one at | a time. |     |                                            |     |     |
| -------- | ----------- | ---- | ------ | ------- | --- | ------------------------------------------ | --- | --- |
| 2.9. Key |             | URLs | —      | Chapter | 2   |                                            |     |     |
| Page     |             |      |        |         |     | URL                                        |     |     |
| Station  | Locator     |      |        |         |     | mesonet.agron.iastate.edu/sites/locate.php |     |     |
| Network  | Tables      |      |        |         |     | mesonet.agron.iastate.edu/sites/net-       |     |     |
works.php
| ASOS/AWOS    |     | Mainpage   |     |     |     | mesonet.agron.iastate.edu/ASOS/     |     |     |
| ------------ | --- | ---------- | --- | --- | --- | ----------------------------------- | --- | --- |
| ASOS Current |     | Conditions |     |     |     | mesonet.agron.iastate.edu/ASOS/cur- |     |     |
rent.phtml
| ASOS 1-Minute |     | Download |     |     |     | mesonet.agron.iastate.edu/re- |     |     |
| ------------- | --- | -------- | --- | --- | --- | ----------------------------- | --- | --- |
quest/asos/1min.phtml
ASOS Monthly Precip Tables mesonet.agron.iastate.edu/ASOS/re-
ports/mon_prec.php
| COOP | Mainpage |     |     |     |     | mesonet.agron.iastate.edu/COOP/ |     |     |
| ---- | -------- | --- | --- | --- | --- | ------------------------------- | --- | --- |

| Mastering | the Mesonet |     | 22  |
| --------- | ----------- | --- | --- |
| Page      |             | URL |     |
COOP Daily Records/Extremes mesonet.agron.iastate.edu/COOP/ex-
tremes.php
| COOP Normals | Download | mesonet.agron.iastate.edu/COOP/dl/nor- |     |
| ------------ | -------- | -------------------------------------- | --- |
mals.phtml
COOP Freeze Date Statistics mesonet.agron.iastate.edu/COOP/freez-
ing.php
| COOP Snow | Depth Duration | mesonet.agron.ias- |     |
| --------- | -------------- | ------------------ | --- |
tate.edu/COOP/snowd_duration.phtml
COOP Hourly Precip (HPD) mesonet.agron.iastate.edu/COOP/hpd.php
| Climodat | Download (QC’d) | mesonet.agron.iastate.edu/re- |     |
| -------- | --------------- | ----------------------------- | --- |
quest/coop/fe.phtml
COOP Raw Obs Download mesonet.agron.iastate.edu/request/coop/obs-
fe.phtml
| CoCoRaHS | Mainpage    | mesonet.agron.iastate.edu/cocorahs/     |     |
| -------- | ----------- | --------------------------------------- | --- |
| CoCoRaHS | Current Obs | mesonet.agron.iastate.edu/cocorahs/cur- |     |
rent.phtml
| DCP/HADS | Mainpage | mesonet.agron.iastate.edu/DCP/ |     |
| -------- | -------- | ------------------------------ | --- |
DCP Current Map (by SHEF code) mesonet.agron.iastate.edu/DCP/map.php
DCP Tomb (unknown station IDs) mesonet.agron.iastate.edu/DCP/tomb.phtml
| RWIS Mainpage |            | mesonet.agron.iastate.edu/RWIS/     |     |
| ------------- | ---------- | ----------------------------------- | --- |
| RWIS Current  | Conditions | mesonet.agron.iastate.edu/RWIS/cur- |     |
rent.phtml
| RWIS Road | Cameras | mesonet.agron.iastate.edu/RWIS/cam- |     |
| --------- | ------- | ----------------------------------- | --- |
era.phtml
ISU Soil Moisture Network mesonet.agron.iastate.edu/agclimate/
| SCAN Network   |         | mesonet.agron.iastate.edu/scan/  |     |
| -------------- | ------- | -------------------------------- | --- |
| USCRN          | Network | mesonet.agron.iastate.edu/uscrn/ |     |
| Other Networks |         | mesonet.agron.iastate.edu/other/ |     |

| 3. Chapter |     | 3   | — Current |     | Conditions: |     | What’s |
| ---------- | --- | --- | --------- | --- | ----------- | --- | ------ |
| Happening  |     |     | Right     | Now |             |     |        |
The IEM is primarily known for its historical archive and analytical tools, but it has a
capable real-time layer that most users never fully explore. The current conditions section is
not one page — it is a collection of distinct tools scattered across several URLs, each serving
a different purpose. Some are in the navigation menu. A few are not. This chapter covers
| all of them | and     | explains | when to reach | for each | one. |     |     |
| ----------- | ------- | -------- | ------------- | -------- | ---- | --- | --- |
| 3.1. The    | Current |          | Mainpage      |          |      |     |     |
The entry point is mesonet.agron.iastate.edu/current/, which functions as a menu of real-
time map products rather than a display in itself. From here you select a variable — Air
Temperature, Humidity, Precipitation, Pressure, Snow, Soil Temperature, Station Plot,
Sounding, Wind, or Visibility — and the IEM generates a map product for that variable
| across its | observation | network. |     |     |     |     |     |
| ---------- | ----------- | -------- | --- | --- | --- | --- | --- |
These maps are static images that refresh on a schedule, not interactive layers. They are
generated from the combined IEM network, blending ASOS, COOP, RWIS, and other
stations into a single visualization. The station plot option produces the classic surface
analysis plot format — the circular station model with temperature, dew point, wind
barb, sky coverage, and pressure all encoded around a central point — which is the most
information-dense view available and the one most familiar to anyone who has spent time
| looking | at surface | analyses. |     |     |     |     |     |
| ------- | ---------- | --------- | --- | --- | --- | --- | --- |
The precipitation map at /current/index.phtml/precipitation is worth bookmarking
specifically during active weather events. It aggregates current precipitation reports from
across the network and gives you a quick ground-truth check against whatever the radar is
showing.
| 3.2. Sortable |     | Currents: | The | Cross-Network |     | Observation | Table |
| ------------- | --- | --------- | --- | ------------- | --- | ----------- | ----- |
The most useful real-time tool on the IEM for a weather enthusiast is Sortable Currents,
reached from the navigation menu at mesonet.agron.iastate.edu/my/current.phtml. Despite
23

Mastering the Mesonet 24
the “My Favorites” label in the URL, this page is far more than a favorites list — it is a full
cross-network observation hub that lets you view current conditions from every network the
IEM tracks in a single sortable table.
The page opens with a set of network tabs at the top: ASOS, CoCoRaHS, COOP, Cellular
COOP, DCP, ISU Soil Moisture, Other, SCAN, My Favorites, By State, RWIS, RWIS
Surface, RWIS Traffic, RWIS Soil, By NWS WFO, and USCRN. Each tab loads the current
observations for that network in a table where every column header is clickable for sorting.
Click the temperature header and every station in the network sorts from hottest to coldest.
Click precipitation and you instantly see which stations are reporting the most rain right
now. Click dew point and you can immediately identify where the moist boundary sits.
The “By State” tab is particularly useful for regional situational awareness. It lets you select
a state and see all ASOS observations across that state simultaneously — a faster and more
flexible view than the map products when you want to compare readings across a region
rather than look at one variable spatially.
The “My Favorites” functionality requires no login. Visit any network’s current conditions
page, find a station you want to track, and add it to your favorites with a single click. The
favorites list is stored in your browser’s local storage, so it persists across sessions without
requiring an account. A custom favorites list combining your regional ASOS stations, a
nearby CoCoRaHS observer, and a RWIS pavement sensor gives you a tailored real-time
dashboardthatnocommercialweathersitecanreplicatewiththiscombinationofnetworks.
The “By NWS WFO” tab at mesonet.agron.iastate.edu/nws/obs.php deserves separate
mention. It lets you select a Weather Forecast Office and see all current ASOS observations
within that WFO’s area of responsibility in a single table. For mid-Atlantic users, selecting
CTP (State College) pulls up every airport station from central Pennsylvania — MDT,
CXY, LNS, THV, SCE, IPT, RDG and more — in one sortable view. This is exactly what
you want when a front is moving through and you are watching temperatures fall or dew
points rise from west to east across a region.
3.3. IEM One: Radar and Warnings in a Single Interface
mesonet.agron.iastate.edu/one/ is a modern interactive mapping application that combines
radar imagery with live NWS warnings in a single interface. It is one of the most polished
tools on the IEM and, for real-time severe weather monitoring, the best starting point the
site offers.
IEM One has two modes: Real-time and Archive. In Real-time mode it displays the current
NEXRAD composite radar loop alongside any active watches, warnings, and advisories
overlaid as color-coded polygons. The warning panel on the right side lists every active

Mastering the Mesonet 25
warning by WFO with the phenomena, significance, and expiration time. Click any polygon
on the map and you get the full warning details.
Archive mode is where IEM One becomes genuinely powerful for post-event analysis. You
can navigate to any date and time and replay the radar and warning sequence exactly as it
unfolded. The time navigation controls at the bottom let you step through the archive at
whatever pace you want. This is the tool to use when you want to understand the timing
of a warning relative to the radar evolution during a past event — something that takes
considerable effort to reconstruct from text archives alone.
The layer controls, accessible via the hamburger menu in the top left, give you options that
go beyond basic radar and warnings. You can toggle on webcam imagery from the IEM
camera network, Iowa DOT truck dashcams (available back to 2014), Iowa DOT RWIS road
cameras (back to 2010), and RWIS surface observations with a choice of which variable
to label on the map — air temperature, or any of the four pavement temperature sensors.
Overlaying RWIS pavement temperatures on a radar loop during a winter precipitation
event is a combination that no commercial weather site offers and that is genuinely useful
for understanding where ice is forming on road surfaces in real time.
IEM One also supports URL parameters for deep linking into specific views. If you want to
share a specific location and zoom level, you can construct a URL with zoom=, lat=, and
lon= parameters. You can also pre-configure which layers are visible: radar=1, warnings=1,
rwis=1, webcam=1, dashcam=1, sps=1. This makes it easy to set up a bookmark that opens
directly to your region with your preferred layer configuration.
3.4. The Severe Weather Mainpage
The Severe Weather Mainpage at mesonet.agron.iastate.edu/current/severe.phtml is less a
real-time monitoring tool and more a hub connecting the IEM’s severe weather resources
— both current and archived. It is worth understanding what is on it because some of the
most useful links on the entire site are buried here rather than in the main navigation.
For current conditions, the page provides a link to the iembot monitor for watching text
products arrive in real time, the current NEXRAD storm attributes shapefile (a point
shapefile updated every minute with hail estimates, rotation, and storm top heights for every
tracked cell in the country), a convective watches overview showing the last ten SPC watch
locations, and GIS-ready downloads of the current 24-hour LSR reports and active warning
polygons.
For operational situational awareness, the current SPC and WPC outlooks are displayed
side-by-side with IEM’s own rendering of the same data pulled from its archive — a simple
visual check that the IEM’s ingest is working and matching the official products. On a

| Mastering | the Mesonet |     |     |     |     | 26  |
| --------- | ----------- | --- | --- | --- | --- | --- |
day with active outlooks this is a useful confirmation that the IEM’s warning and outlook
| archive | is current. |     |     |     |     |     |
| ------- | ----------- | --- | --- | --- | --- | --- |
The archived tools linked from this page — IEM Cow, IEM Raccoon, the VTEC browser,
the warning search — are covered in depth in Chapter 7. What is worth noting here is
that this is where you find them when approaching from the “current severe weather” angle
| rather | than from the     | NWS Data | menu.   |      |     |     |
| ------ | ----------------- | -------- | ------- | ---- | --- | --- |
| 3.5.   | The Precipitation |          | Current | Page |     |     |
For active precipitation events, mesonet.agron.iastate.edu/current/index.phtml/precipitation
gives you the combined network precipitation map — all reporting stations from ASOS,
COOP, and CoCoRaHS plotted simultaneously. This is the IEM’s equivalent of a real-time
gauge analysis map. It updates as new reports come in and gives you an immediate sense
of where precipitation is heaviest and how gauge reports compare to what the radar is
showing.
For more detailed precipitation tracking, the Hourly Precip application at mesonet.agron.ias-
tate.edu/rainfall/obhour.phtml shows the precipitation reported by each ASOS station in
the last hour alongside a running 24-hour total. It is narrower in scope than the combined
map but more precise in timing, and it includes the hourly bucket readings directly rather
than the summarized daily totals. Chapter 4 covers this in more detail under the Apps
section.
| 3.6. | What “Current” |     | Actually | Means | on the IEM |     |
| ---- | -------------- | --- | -------- | ----- | ---------- | --- |
One subtle but important point about the IEM’s current conditions tools: observation age
varies by network, and not everything labeled “current” is equally fresh.
ASOS stations report every hour at minimum, with special observations triggered by
significantchangesinconditions. ThedatareachestheIEMwithinminutesoftheobservation
time for most stations. When you load the ASOS sortable currents table, the observations
| you see | are typically less | than | an hour | old, and often | much less. |     |
| ------- | ------------------ | ---- | ------- | -------------- | ---------- | --- |
COOP observations are once-daily by design. The “current” COOP display shows the most
recent morning report, which was probably submitted between 6 and 8 AM local time.
Mid-afternoon, that observation is six to eight hours old. During an active precipitation
event, the COOP numbers you see are not telling you what is happening right now — they
| are telling | you what accumulated |     | since | the previous | morning. |     |
| ----------- | -------------------- | --- | ----- | ------------ | -------- | --- |
DCP river gauge data varies by station and reporting interval. Most gauges report every
hour or every few hours. During flood events, reporting may intensify. But some gauges

| Mastering | the Mesonet |     |     | 27  |
| --------- | ----------- | --- | --- | --- |
have longer reporting intervals or telemetry delays, so a “current” stage reading on the DCP
| map might | be two to | four hours old. |     |     |
| --------- | --------- | --------------- | --- | --- |
RWIS stations generally report every 20 minutes or every hour, with variation by state DOT
configuration.
The IEM does display observation timestamps alongside each reading, so you can always
check how old a value is. But knowing the typical reporting cadence for each network
helps you interpret the current display correctly, especially during rapidly evolving weather
situations.
| 3.7. Key | URLs — | Chapter | 3   |     |
| -------- | ------ | ------- | --- | --- |
Page URL
| Current | Mainpage |     | mesonet.agron.iastate.edu/current/ |     |
| ------- | -------- | --- | ---------------------------------- | --- |
Current Temperature Map mesonet.agron.iastate.edu/current/in-
dex.phtml/air_temperature
Current Precipitation Map mesonet.agron.iastate.edu/current/in-
dex.phtml/precipitation
Current Station Plot Map mesonet.agron.iastate.edu/current/in-
dex.phtml/station_plot
Sortable Currents (all networks) mesonet.agron.iastate.edu/my/current.phtml
Sortable Currents by WFO mesonet.agron.iastate.edu/nws/obs.php
Sortable Currents by State mesonet.agron.iastate.edu/current/all.phtml
| ASOS Current | Conditions |     | mesonet.agron.iastate.edu/ASOS/cur- |     |
| ------------ | ---------- | --- | ----------------------------------- | --- |
rent.phtml
| RWIS Current | Surface |     | mesonet.agron.iastate.edu/RWIS/cur- |     |
| ------------ | ------- | --- | ----------------------------------- | --- |
rentSF.phtml
| RWIS Current | Traffic |     | mesonet.agron.iastate.edu/RWIS/traf- |     |
| ------------ | ------- | --- | ------------------------------------ | --- |
fic.phtml
| IEM One | (Radar + Warnings) |     | mesonet.agron.iastate.edu/one/ |     |
| ------- | ------------------ | --- | ------------------------------ | --- |
Severe Weather Mainpage mesonet.agron.iastate.edu/current/se-
vere.phtml
Hourly Precip (current) mesonet.agron.iastate.edu/rainfall/ob-
hour.phtml
Convective Watches Overview mesonet.agron.iastate.edu/current/sel.phtml

| Mastering      | the Mesonet      |                    | 28  |
| -------------- | ---------------- | ------------------ | --- |
| Page           |                  | URL                |     |
| Current NEXRAD | Storm Attributes | mesonet.agron.ias- |     |
tate.edu/data/gis/shape/4326/us/cur-
rent_nexattr.zip
| Current Warning | Shapefile | mesonet.agron.ias- |     |
| --------------- | --------- | ------------------ | --- |
tate.edu/data/gis/shape/4326/us/cur-
rent_ww.zip
| Current 24-hr | LSR Shapefile | mesonet.agron.ias- |     |
| ------------- | ------------- | ------------------ | --- |
tate.edu/data/gis/shape/4326/us/lsr_24hour.zip

|      |      | Part  | II.              |
| ---- | ---- | ----- | ---------------- |
| Part | II — | Tools | and Applications |
29

| 4. Chapter |     | 4 — Apps: | IEM’s | Interactive |
| ---------- | --- | --------- | ----- | ----------- |
Tools
The Apps menu is where the IEM shifts from archive and network infrastructure to tools
you can actually use to answer questions. It contains the tools that produce the charts you
see shared on weather forums, the applications that let you explore a station’s full historical
record interactively, and several tools that most users never fully discover because the menu
| entry gives | little hint | of what lies inside. |     |     |
| ----------- | ----------- | -------------------- | --- | --- |
This chapter covers all of them, with most of the space devoted to Automated Data Plotting
— Autoplot — the single most powerful and underutilized tool on the IEM.
| 4.1. The | Application | Index |     |     |
| -------- | ----------- | ----- | --- | --- |
The Application Index at mesonet.agron.iastate.edu/apps.php is the complete catalog of
everything IEM has built. It is organized by category and lists well over a hundred individual
applications with short descriptions. If you ever find yourself lost on the site wondering
whether a tool exists for a specific task, start here. Browse it once in a dedicated session —
not to memorize it, but to build a mental map of the categories and where things live. It
| will save      | you significant | time later.   |            |     |
| -------------- | --------------- | ------------- | ---------- | --- |
| 4.2. Automated |                 | Data Plotting | (Autoplot) |     |
mesonet.agron.iastate.edu/plotting/auto/
Autoplot is the IEM’s chart generation engine. It is a single application with 260 chart types,
each capable of producing publication-quality graphics from the IEM’s full data archive.
It is the source of the overwhelming majority of charts you will ever see posted from the
IEM — temperature records, departure analyses, warning climatologies, MOS verification,
snowfall timelines, and dozens of other chart types that simply do not exist anywhere else
for free.
Understanding Autoplot requires three things: knowing how to find the right chart, how the
| URL structure | works, | and how to export | the data. |     |
| ------------- | ------ | ----------------- | --------- | --- |
30

| Mastering | the Mesonet |             |     | 31  |
| --------- | ----------- | ----------- | --- | --- |
| 4.2.1.    | Finding the | Right Chart |     |     |
The Autoplot interface has a large dropdown selector at the top — Step 1: Select a Chart
Type. The full list of 260 charts is in that dropdown, grouped into sections: Daily, Monthly,
Yearly, Hydrology/Drought, METAR/ASOS Special Plots, Agricultural, NWS/Warnings,
and a miscellaneous section for things that do not fit neatly. Each chart has a name and a
| number | in parentheses. |     |     |     |
| ------ | --------------- | --- | --- | --- |
Below the dropdown, the page shows a visual gallery of thumbnails — one sample image for
each chart, organized by the same category groups. This is the fastest way to browse if you
know roughly what kind of chart you want but do not know which number. The trending
section at the top of the gallery shows which charts are being requested most heavily in the
past six hours, which is a useful indicator of what the active weather is prompting people to
look at.
When you select a chart from the dropdown or click a thumbnail, the interface loads Step
2: Configure Chart Options. What you see here changes completely depending on which
chart you selected. Some charts ask only for a station and a year. Others have a dozen
parameters covering network, station, date range, variable, threshold, output format, and
display options. All of this configuration happens in the same interface — the form updates
| dynamically | when        | you change the chart | type. |     |
| ----------- | ----------- | -------------------- | ----- | --- |
| 4.2.2.      | How the URL | Works                |       |     |
This is where Autoplot becomes genuinely powerful. Every chart you configure generates a
direct URL that can be bookmarked, shared, or used to pull data programmatically. Once
you understand the URL structure, you often do not need the dropdown at all — you can
| construct | charts directly | in the address | bar. |     |
| --------- | --------------- | -------------- | ---- | --- |
The base URL is https://mesonet.agron.iastate.edu/plotting/auto/ and every indi-
vidual chart follows the pattern ?q={number} for the interactive interface. The chart image
itself — the actual PNG — is served at a different path that encodes all the parameters
| directly  | in the URL. |                  |     |     |
| --------- | ----------- | ---------------- | --- | --- |
| The image | URL pattern | looks like this: |     |     |
https://mesonet.agron.iastate.edu/plotting/auto/plot/{q}/{param1}:{value1}::{param2}:{value2}::{param3}:{value3}.png
For example, chart q=99 (Daily High + Low Temperatures with Departures) for Harrisburg
| Airport | in 2025 would | be: |     |     |
| ------- | ------------- | --- | --- | --- |
https://mesonet.agron.iastate.edu/plotting/auto/plot/99/network:PACLIMATE::station:PA5703::year:2025::delta:abs::dpi:100.png

| Mastering | the Mesonet |     |     | 32  |
| --------- | ----------- | --- | --- | --- |
The parameters are separated by :: (double colons) and each parameter is formatted as
name:value. The chart number follows /plot/ directly. This URL is stable — if you
bookmark it, it will always produce the same chart updated with whatever data the IEM
| currently | has for that station | and year. |     |     |
| --------- | -------------------- | --------- | --- | --- |
To change a parameter, change the value in the URL. Want 2024 instead of 2025? Change
year:2025 to year:2024. Want sigma departures instead of absolute? Change delta:abs
to delta:sigma. This makes Autoplot URLs composable — you can modify any parameter
by editing the URL directly, which is far faster than navigating the form when you know
| what you | want. |     |     |     |
| -------- | ----- | --- | --- | --- |
The _r:t parameter that appears in many Autoplot URLs tells the server to render the
page with a data-download link included. You can also retrieve data by replacing .png in
the image URL with .csv or .xlsx to get the underlying data directly.
| 4.2.3. Getting | the Data | Out |     |     |
| -------------- | -------- | --- | --- | --- |
Every Autoplot chart that is based on tabular data — which is most of them — can export
that data. On any chart’s page, after the chart is generated, you will see links for CSV Data
and Excel Download directly below the image. These export the exact data points used to
| draw the | chart. |     |     |     |
| -------- | ------ | --- | --- | --- |
This is one of Autoplot’s most underappreciated features. You are not just getting a picture
— you are getting a reproducible data pipeline. The IEM calculates the statistics, applies its
QC, draws the chart, and then hands you the same numbers in a spreadsheet-ready format.
For any analysis that starts with one of these charts, you can pull the data directly rather
| than downloading | raw observations | and computing | statistics yourself. |     |
| ---------------- | ---------------- | ------------- | -------------------- | --- |
4.2.4. The Curated Charts: What a Weather Enthusiast Actually Needs
The 260 charts divide into roughly three groups for weather hobbyist purposes: indispensable
tools you will use regularly, useful tools you will pull out for specific questions, and niche
tools (mostly agricultural and crop-specific) that you can safely ignore unless you have a
| specific reason | to care. |     |     |     |
| --------------- | -------- | --- | --- | --- |
What follows is a tour of the most valuable charts organized by the kind of question they
answer.

Mastering the Mesonet 33
4.2.4.1. Understanding Your Station’s Climate Record
Chart 99 — Daily High + Low Temperatures with DeparturesThesinglemost-used
climatology chart on the IEM. For any given year at any station, it plots every day’s high
and low temperature as a colored bar above or below the 1991-2020 NCEI climatological
average. Days above average are warm-colored, days below are cool-colored. At a glance
you can see which months ran warm or cold, how persistent any anomalies were, and how
the year compares to the baseline. The departure can be shown as absolute degrees or as
sigma units, which is useful when comparing the same departure across different seasons
where variability differs. Link: q=99
Chart 32 — Daily Departures / Percentiles / Ranges for One Year A related chart
to q=99 but using period-of-record climatology rather than the fixed 1991-2020 baseline.
This one overlays the current year’s observed temperatures against the full envelope of what
has been recorded, showing the record high, record low, and shaded percentile bands. Useful
when you want to know not just “was it above average” but “how unusual was it by historical
standards.” Link: q=32
Chart 113 — Daily Climatology The simple, clean version: the period-of-record normal
high, normal low, and average precipitation for every day of the year for a single station.
No current year overlay, no departures — just the baseline climatology plotted as smooth
curves. This is what you want when you need to explain to someone what “normal” is for a
location or when you want a reference chart to annotate with observed values. It accepts a
user-defined date range, so you can compute climatology for a specific sub-period rather
than the full record. Link: q=113
Chart 100 — Temperature / Precip Statistics by Year One of the most useful
charts for long-period analysis. For any station and any variable, it produces a bar chart
showing the yearly value across the full period of record, with the annual average overlaid.
Want to see every year’s total precipitation since 1888? This is the chart. Want to see how
2012’s drought compares to every prior dry year? This chart ranks them immediately. The
breadth of available variables is extensive: annual total precip, annual average temperature,
number of days above any temperature threshold, growing degree day totals, and more.
Link: q=100
Chart 5 — Daily Records for Each Month of Year Shows, for each month of the
year, when the all-time daily records were set. A horizontal bar for each month, with dots
indicating which days hold the current records and whether they were set by a more recent
year. This is the chart that shows you how old your station’s records are and which months
still have records from the early 20th century that have never been broken. Link: q=5
Chart 63 — Records Set by Year The inverse question from q=5: for each year in
the record, how many new daily high temperature records, daily low temperature records,
and daily precipitation records were set? This chart is revealing when interpreted carefully.

| Mastering | the Mesonet |     |     |     | 34  |
| --------- | ----------- | --- | --- | --- | --- |
Years with many records set are often either extreme weather years or years immediately
following a gap in the record (where the newly resumed record can set “records” against
a thin baseline). When you see a year like 1936 dominating the high temperature record
| count, that | is real. Link: | q=63     |     |     |     |
| ----------- | -------------- | -------- | --- | --- | --- |
| 4.2.4.2.    | Precipitation  | Analysis |     |     |     |
Chart 75 — Precip Totals by Season/Year Simple and essential: total precipitation
for each year or season across the full record, with a trend line option. This is your first
chart when someone asks “is it getting wetter or drier?” — it puts the full record in context
| immediately. | Link: q=75 |     |     |     |     |
| ------------ | ---------- | --- | --- | --- | --- |
Chart 172 — Accumulated Year-to-Date Precipitation For any station, shows the
accumulated precipitation from January 1st through whatever date you select, with the
current year highlighted against the envelope of all prior years. The wettest and driest years
are labeled. This is the chart you want during an ongoing drought or a wet spring — it tells
you exactly where the current year sits in the historical distribution at any point in the
| season. | Link: q=172 |     |     |     |     |
| ------- | ----------- | --- | --- | --- | --- |
Chart 108 — Accumulated Departures from Average (Long Term Climate)
Plots accumulated growing degree day, precipitation, and stress degree day departures from
climatology for a season. The running sum format shows you whether the year is trending
wetter or drier as it progresses, and how abrupt the transitions are. This is one of the charts
| highlighted | on the IEM | homepage | as trending. | Link: q=108 |     |
| ----------- | ---------- | -------- | ------------ | ----------- | --- |
Chart 207 — LSR + COOP Snowfall/Rainfall Analysis Maps Produces a gridded
analysis map of snowfall or rainfall for any event using Local Storm Reports, NWS COOP
data, and CoCoRaHS combined. This is the chart for reconstructing what fell where during
a specific storm — the IEM blends three data sources into a single analyzed map. Link:
q=207
| 4.2.4.3. | Departures, | Trends, and | Comparisons |     |     |
| -------- | ----------- | ----------- | ----------- | --- | --- |
Chart 55 — Daily Climatology Comparison Compares multiple 30-year climatological
normals at the same station on a single plot: the 1971-2000 normals, the 1981-2010 normals,
and the 1991-2020 normals, all plotted together. This is the intellectually honest chart for
showing climate change signals in the observational record — you can see directly whether
| the baseline | has shifted | and by | how much. Link: | q=55 |     |
| ------------ | ----------- | ------ | --------------- | ---- | --- |
Chart 215 — Compare Daily Temp Distributions over Two Periods Select two
user-defined year ranges and see the full distribution of daily high or low temperatures
compared between them as a kernel density estimate. Set period 1 as 1950-1979 and period
2 as 1990-2019 and you can directly visualize whether the tails have shifted. This is the

Mastering the Mesonet 35
chart for rigorous period-to-period comparison rather than visual inspection of time series.
Link: q=215
Chart 128 — Comparison of Yearly Summaries Between Two Stations For any
two long-term climate stations, plots their annual summary statistics side by side across all
shared years. This is the right tool when analyzing station homogeneity, comparing nearby
stations with different exposures, or validating bias correction work. Only years where both
stations have adequate data are included. Link: q=128
Chart 104 — Trailing X-Day Temp/Precip Departures (Weather Cycling) Shows
the time series of trailing-N-day departures from climatology expressed in sigma units. The
result is a plot that looks like a slowly varying signal showing whether the recent past has
been persistently warm/cold/wet/dry. Useful for contextualizing current conditions without
anchoring to calendar months. Link: q=104
4.2.4.4. MOS Forecast Verification
Chart 37 — MOS Forecast Ranges + ASOS Observations This chart overlays the
archived MOS forecast ranges against what actually occurred at a station. For any ASOS
station and any date range, it shows the MOS forecast spread for temperature (or other
variables) alongside the observed value, making it easy to see whether observations fell
within the forecast range and where systematic biases occurred. This is the gateway chart
for the IEM’s MOS verification capabilities and the most relevant Autoplot chart for anyone
interested in forecast verification. Link: q=37
4.2.4.5. Warnings and Severe Weather Climatology
Chart 109 — WFO/State VTEC Event Counts by Period (Map) Generates a map
showing the count or coverage of any type of watch, warning, or advisory issued by each
WFO or across each state for a user-defined time period. Want to see which WFOs issued
the most tornado warnings over the past decade? This chart. Want to see how the warning
load shifted during a particular season? This chart. It was the most requested chart on the
IEM on the day this guide was verified. Link: q=109
Chart 52 — Gantt Chart of Watch/Warning/Advisories by WFO or UGC
Produces a timeline showing when each type of VTEC product was active for a specific
WFO or county/zone. The Gantt format makes it easy to see overlapping events, gaps
between events, and the seasonal pattern of different warning types across multiple years.
Link: q=52
Chart 92 — Days Since Last Watch/Warning/Advisory by WFO A map showing,
for each WFO coverage area, how many days have elapsed since the most recent warning
of a specific type was issued. This is the “quiet period” chart — useful for contextualizing

Mastering the Mesonet 36
whether a region is overdue for a particular hazard based on historical frequency. Link:
q=92
Chart 44 — NWS Office Accumulated Warning Totals For a specific WFO, plots the
accumulated count of severe thunderstorm plus tornado warnings across the season, updated
daily, with historical season comparisons overlaid. This is the chart for tracking how active
a severe weather season is relative to the historical average at any point during the year.
Link: q=44
4.2.4.6. Hourly and Event-Based Analysis
Chart 43 — Recent Timeseries (Meteogram) A standard meteogram for any ASOS
station covering the past 2-3 days: temperature, dew point, wind speed, and precipitation
plotted as hourly time series. This is the IEM’s equivalent of the meteogram you see in
commercial weather apps, but for any station in the archive. Link: q=43
Chart 87 — Frequency of METAR Code by Week or Hour Shows the annual
frequency of any present weather code — thunder, fog, freezing rain, snow, blowing snow —
organized as a heatmap by week of year and hour of day. This chart answers questions like
“when does fog typically form at my local airport” and “what time of day do thunderstorms
most commonly occur at this station across the full record.” Link: q=87
Chart 18 — Long Term Observation Time Series Plots any ASOS variable as a raw
time series across the full station record. Want to see every temperature observation ever
recorded at your airport plotted in sequence? This chart. It is the most direct view of the
raw archive and useful for spotting data quality issues, regime changes, and long-term trends
that are visible in the hourly data but get averaged away in daily summaries. Link: q=18
4.2.5. Tips for Using Autoplot Efficiently
A few patterns that make Autoplot faster to use once you know them:
The _r:t URL parameter forces the page to render in a stripped-down format optimized
for sharing and embedding. When you copy a chart URL from the address bar, it typically
includes this parameter already.
The dpi parameter controls output resolution. The default of 100 DPI produces a sharp
web-scale image. For presentations or publications, set dpi:200 or dpi:300 in the URL.
The _fmt:png parameter can be changed to _fmt:pdf or _fmt:svg for different output
formats. SVG is particularly useful if you want to edit the chart further in vector graphics
software.

| Mastering | the Mesonet |     |     |     |     | 37  |
| --------- | ----------- | --- | --- | --- | --- | --- |
Below the generated image, each chart page shows a list of IEM Daily Features that have
used that chart type in the past. These are real examples from real weather events, with the
“Generate This Chart” link pre-configured. If you are trying to understand what a chart
| shows, these | historical | examples | are often | the fastest way | to grasp it. |     |
| ------------ | ---------- | -------- | --------- | --------------- | ------------ | --- |
| 4.3. Other   | Apps       | Menu     | Tools     |                 |              |     |
4.3.1. Climodat
mesonet.agron.iastate.edu/climodat/
ClimodatistheIEM’sprocessedversionoftheCOOPclimatedataset, cleanedandorganized
for easy retrieval. The main interface lets you select a station and pull monthly and yearly
climate summaries going back to the station’s full record. Unlike the raw COOP download,
Climodat presents data in a formatted report view with totals, departures, and period-of-
recordcontextalreadycomputed. TheClimodatMonitoratmesonet.agron.iastate.edu/climo-
dat/monitor.php adds a live dashboard showing current-month and current-year departures
| across all | monitored | stations. |     |     |     |     |
| ---------- | --------- | --------- | --- | --- | --- | --- |
| 4.3.2. IEM | Explorer  |           |     |     |     |     |
mesonet.agron.iastate.edu/explorer/
IEM Explorer is a simplified station-centric interface that aggregates data, charts, and
metadata for a single station into one page. It is described as a simplified version of Autoplot
— you select a station, and the Explorer presents a curated set of standard charts and recent
observations without requiring you to know which Autoplot number you want. If Autoplot’s
260-chart dropdown feels overwhelming, start with IEM Explorer for your local station to
| see what    | the data looks | like before | going deeper. |     |     |     |
| ----------- | -------------- | ----------- | ------------- | --- | --- | --- |
| 4.3.3. Time | Machine        |             |               |     |     |     |
mesonet.agron.iastate.edu/timemachine/
Time Machine lets you replay any IEM map product at any past date and time. The
interface has a dropdown of available products — the Iowa Mesonet surface plot, various
RADAR composites, precipitation analyses, soil temperature maps, and others — and a
date/time selector. Navigate to any past date and see what the IEM was displaying at that
moment. This is useful for quickly reconstructing surface conditions during a past event
| without pulling | raw | data. |     |     |     |     |
| --------------- | --- | ----- | --- | --- | --- | --- |

| Mastering | the Mesonet |     |     |     |     | 38  |
| --------- | ----------- | --- | --- | --- | --- | --- |
Product1istheIowaMesonetsurfaceplot. Product82istheIowaFloodCenterprecipitation
analysis. Both of these are linked from the IEM homepage as the “Iowa Mesonet Plot” and
| “More Precipitation |       | Maps” entries | in the Most | Popular | sidebar. |     |
| ------------------- | ----- | ------------- | ----------- | ------- | -------- | --- |
| 4.3.4. Wind         | Roses |               |             |         |          |     |
mesonet.agron.iastate.edu/sites/windrose.phtml
The Wind Rose application generates a standard meteorological wind rose for any ASOS
station: the percentage of observations from each direction, with speed categories shown as
color-coded rings. You can filter by month, season, or a custom date range, and filter by a
specific weather condition (e.g., show the wind rose only for hours when visibility was below
1 mile). The standard wind rose is the starting point for understanding the dominant flow
patterns at a station, which is prerequisite knowledge for interpreting temperature biases,
| precipitation | anomalies, | and fog | climatology | at any specific | location. |     |
| ------------- | ---------- | ------- | ----------- | --------------- | --------- | --- |
| 4.3.5. Hourly | Precip     |         |             |                 |           |     |
mesonet.agron.iastate.edu/rainfall/obhour.phtml
The Hourly Precipitation application shows precipitation reported by ASOS stations in the
last hour alongside the 24-hour running total. It is the most detailed real-time precipitation
view the IEM offers at the hourly resolution. For event analysis, the more powerful tool is
the archived hourly precip download at mesonet.agron.iastate.edu/request/asos/hourlypre-
cip.phtml, which lets you pull the hourly bucket readings for any station and date range in
CSV format.
| 4.3.6. Interactive |     | Radar |     |     |     |     |
| ------------------ | --- | ----- | --- | --- | --- | --- |
mesonet.agron.iastate.edu/GIS/apps/rview/warnings.phtml
What the IEM calls Interactive Radar in the nav menu is actually a GIS-based warnings
overlay application — it shows the current radar composite alongside active NWS watch
and warning polygons in an interactive map interface. For more capable radar visualization,
IEM One (Chapter 3) is the preferred tool. This application is the older, simpler alternative,
but it remains the most popular entry point in the menu because the label says “radar” and
| that is what | people | are looking | for. |     |     |     |
| ------------ | ------ | ----------- | ---- | --- | --- | --- |

| Mastering | the Mesonet |                 |     |     | 39  |
| --------- | ----------- | --------------- | --- | --- | --- |
| 4.3.7.    | Pest Maps   | and Forecasting |     |     |     |
mesonet.agron.iastate.edu/topics/pests/
Built for agricultural applications but genuinely useful for weather enthusiasts interested in
phenology: maps of accumulated growing degree days and forecasts of when specific GDD
thresholds will be reached. The GDD framework is the same math that drives seasonal
phenology questions — when do insects emerge, when do plants leaf out, when do first
freezes typically occur — so the pest mapping application is a practical interface to those
questions even if you have no interest in the specific pest models it was designed for.
| 4.4. | Workflow | 2 — Building | and Bookmarking | a Custom | Autoplot |
| ---- | -------- | ------------ | --------------- | -------- | -------- |
Chart
Question: How does this year’s accumulated precipitation at KMDT compare with the
historical average, and how do I save that chart so I can return to it in six months?
| Start | here: https://mesonet.agron.iastate.edu/plotting/auto/ |     |     |     |     |
| ----- | ------------------------------------------------------ | --- | --- | --- | --- |
The Autoplot interface opens with a dropdown selector for chart type and a rendering area
below it. The dropdown is organized by category — temperature, precipitation, climatology,
NWS/VTEC, and so on. For this example, you want Autoplot q=7, which plots accumulated
precipitation departure from average. You can either scroll through the categories to find it
| or type | “7” directly | into the chart number | field if you | know it. |     |
| ------- | ------------ | --------------------- | ------------ | -------- | --- |
Once you select q=7, the form below the chart selector shows the parameters for that specific
chart: network, station, start year, and options for the baseline period. Set the network to
PA_ASOS, set the station to MDT, and leave the other parameters at their defaults for a
| first look. | Click the | button to generate | the chart. |     |     |
| ----------- | --------- | ------------------ | ---------- | --- | --- |
The chart renders as an image. Now look at your browser’s address bar. The URL has
| changed | to something | like: |     |     |     |
| ------- | ------------ | ----- | --- | --- | --- |
https://mesonet.agron.iastate.edu/plotting/auto/plot/7/network:PA_ASOS::station:MDT::...

Mastering the Mesonet 40
This URL is the chart. Every parameter you set — network, station, year range, chart type
— is encoded in the path. Copy this URL and bookmark it, share it in a forum post, or save
it to a spreadsheet. When you load the URL six months from now, IEM will regenerate the
chart with the same parameters against the current data. The chart updates automatically;
the URL does not need to change.
To download the underlying data rather than the image, replace the /plot/ segment in
the URL with /json/, or add _fmt=json to the end of the parameter string. The API will
return the chart’s source data as a JSON object — the same values plotted in the chart,
available for your own analysis. This works for the majority of Autoplot charts, though a
small number of charts produce images that do not have a corresponding data endpoint.
A practical tip for finding the right chart: the Autoplot landing page shows a thumbnail
and one-line description for all 260 charts. If you are not sure which chart answers your
question, scroll through the thumbnails in the relevant category rather than trying to guess
the chart number. The precipitation category and the climatology category together cover
most of the questions weather enthusiasts bring to IEM Autoplot.
4.5. Workflow 5 — Building a Wind Rose for Your Airport
The question: What does the wind climatology at KMDT look like during winter months?
From which direction does the prevailing flow come, and at what speeds?
Start here: https://mesonet.agron.iastate.edu/sites/windrose.phtml
The wind rose tool opens with a network and station selector. Set the network to PA_ASOS
and the station to MDT. The date range fields default to a multi-year span; leave them
as-is for a first look at the full period of record, which for KMDT extends back to the early
1970s.
The tool offers three ways to filter the data used to build the rose. First, you can restrict to a
specific month or season — for a winter wind climatology, set the month filter to December,
January, and February. Second, you can restrict to a specific hour of the day, which is useful
for understanding diurnal wind patterns or for aviation purposes (morning versus afternoon
wind regimes differ significantly at valley airports like MDT due to drainage flow). Third,
you can set a start-hour to end-hour window. For a climatological picture of winter winds
generally, leave the hour filter open.

| Mastering | the Mesonet |     |     |     |     | 41  |
| --------- | ----------- | --- | --- | --- | --- | --- |
You can also specify up to six custom wind speed bins in units of your choice. The default
bins work fine for a first look, but if you are interested in a specific threshold — severe wind
criteria, aviation minimums, wildfire spread conditions — adjusting the bins to bracket that
| threshold | gives you | a more actionable | result. |     |     |     |
| --------- | --------- | ----------------- | ------- | --- | --- | --- |
After you click Submit, the tool takes a moment to process: it is querying the full ASOS
archive for your station across your time filter, which depending on the date range and
stationcanmeanseveralhundredthousandobservations. Thesiteitselfnotesthatgeneration
can take up to a few minutes for large requests; this is normal, not a timeout. The resulting
image shows the wind rose with spoke lengths proportional to frequency from each direction
| and coloring | indicating | speed category | within | each directional | bin. |     |
| ------------ | ---------- | -------------- | ------ | ---------------- | ---- | --- |
The image and the underlying data are both in the public domain. Below the rendered rose
you will find a link to the backend data as a JSON file — the raw frequency counts and
speed distributions by direction, available for custom plotting or analysis in your own tools.
The wind rose image itself can be embedded or shared directly; a stable URL for the plot is
generated after the image renders, bookmarkable in the same way as an Autoplot URL.
For KMDT specifically, the winter wind rose will show the dominant west-to-northwest fetch
that characterizes cold air advection events in the Susquehanna Valley, with a secondary
signature from the south-southwest during pre-frontal warm advection. The MDT wind
record is long enough that these patterns are statistically robust; this is not a pattern
| inferred    | from only a | few seasons | of data. |                                    |     |     |
| ----------- | ----------- | ----------- | -------- | ---------------------------------- | --- | --- |
| 4.6. Key    | URLs        | — Chapter   | 4        |                                    |     |     |
| Page        |             |             |          | URL                                |     |     |
| Application | Index       |             |          | mesonet.agron.iastate.edu/apps.php |     |     |
Autoplot Main Interface mesonet.agron.iastate.edu/plotting/auto/
Autoplot — Daily Departures (q=99) mesonet.agron.iastate.edu/plot-
ting/auto/?q=99
Autoplot — Daily Climatology (q=113) mesonet.agron.iastate.edu/plot-
ting/auto/?q=113
Autoplot — Yearly Totals (q=100) mesonet.agron.iastate.edu/plot-
ting/auto/?q=100
Autoplot — YTD Precipitation (q=172) mesonet.agron.iastate.edu/plot-
ting/auto/?q=172
Autoplot — Daily Records by Month (q=5) mesonet.agron.iastate.edu/plot-
ting/auto/?q=5

| Mastering | the Mesonet |     |     | 42  |
| --------- | ----------- | --- | --- | --- |
| Page      |             |     | URL |     |
Autoplot — Records Set by Year (q=63) mesonet.agron.iastate.edu/plot-
ting/auto/?q=63
Autoplot — Precip Totals by Year (q=75) mesonet.agron.iastate.edu/plot-
ting/auto/?q=75
Autoplot — Climatology Comparison mesonet.agron.iastate.edu/plot-
| (q=55) |     |     | ting/auto/?q=55 |     |
| ------ | --- | --- | --------------- | --- |
Autoplot — Two-Period Distribution mesonet.agron.iastate.edu/plot-
| (q=215) |     |     | ting/auto/?q=215 |     |
| ------- | --- | --- | ---------------- | --- |
Autoplot — MOS vs Observations (q=37) mesonet.agron.iastate.edu/plot-
ting/auto/?q=37
Autoplot — VTEC Counts Map (q=109) mesonet.agron.iastate.edu/plot-
ting/auto/?q=109
Autoplot — Warning Gantt (q=52) mesonet.agron.iastate.edu/plot-
ting/auto/?q=52
Autoplot — Days Since WWA (q=92) mesonet.agron.iastate.edu/plot-
ting/auto/?q=92
Autoplot — Accumulated Warnings (q=44) mesonet.agron.iastate.edu/plot-
ting/auto/?q=44
| Autoplot | — Meteogram | (q=43) | mesonet.agron.iastate.edu/plot- |     |
| -------- | ----------- | ------ | ------------------------------- | --- |
ting/auto/?q=43
Autoplot — METAR Code Frequency mesonet.agron.iastate.edu/plot-
| (q=87) |     |     | ting/auto/?q=87 |     |
| ------ | --- | --- | --------------- | --- |
Autoplot — Snowfall Map (q=207) mesonet.agron.iastate.edu/plot-
ting/auto/?q=207
Autoplot — Accumulated GDD/Precip mesonet.agron.iastate.edu/plot-
| (q=108)  |         |     | ting/auto/?q=108                         |     |
| -------- | ------- | --- | ---------------------------------------- | --- |
| Climodat |         |     | mesonet.agron.iastate.edu/climodat/      |     |
| Climodat | Monitor |     | mesonet.agron.iastate.edu/climodat/moni- |     |
tor.php
| IEM Explorer |     |     | mesonet.agron.iastate.edu/explorer/    |     |
| ------------ | --- | --- | -------------------------------------- | --- |
| Time Machine |     |     | mesonet.agron.iastate.edu/timemachine/ |     |
| Wind Roses   |     |     | mesonet.agron.iastate.edu/sites/win-   |     |
drose.phtml
Hourly Precip (current) mesonet.agron.iastate.edu/rainfall/ob-
hour.phtml
Hourly Precip (archived download) mesonet.agron.iastate.edu/re-
quest/asos/hourlyprecip.phtml
| Interactive | Radar / Warnings |     | mesonet.agron.ias- |     |
| ----------- | ---------------- | --- | ------------------ | --- |
tate.edu/GIS/apps/rview/warnings.phtml
Pest Maps + GDD Forecasting mesonet.agron.iastate.edu/topics/pests/

| Mastering | the Mesonet | 43  |
| --------- | ----------- | --- |
Page URL
Plant Hardiness Zones mesonet.agron.iastate.edu/topics/hardiness/

5. Chapter 5 — Areas: Topic Portals
The Areas menu is the IEM’s subject-matter navigation layer — not a collection of tools,
but a set of entry points organized around what you are trying to do rather than what kind
of data you are looking at. Where the Networks menu asks “which observing network?”,
Areas asks “which topic?”: climate, archive, GIS, drought, or agriculture. Each entry in the
menu opens into a substantially different part of the site, and some of them open into entire
sub-systems that could support a chapter on their own. This chapter maps the territory.
The Areas menu currently has eight entries: Ag Weather/Climate Info, Archive Mainpage,
Climate Mainpage, Current Mainpage, Drought, GIS Mainpage, NWS Mainpage, and Severe
Weather Mainpage. Current Mainpage and Severe Weather Mainpage were covered in
Chapter 3, and NWS Mainpage anchors Chapter 7. What remains — the Archive, GIS,
Drought, and Ag/Climate portals — is the subject of this chapter.
5.1. The Archive Mainpage
mesonet.agron.iastate.edu/archive/
The Archive Mainpage is worth understanding as a concept before you start clicking into it.
It is not primarily an interface — it is an annotated directory. The IEM uses it as a curated
index of archival resources, both internal (hosted at Iowa State) and external (third-party
archives the team considers worth pointing to). If you are trying to find raw historical data
and you do not know whether the IEM has it, this is the place to start your search.
5.1.1. The Raw File Archive
The deepest layer of the IEM’s own archive is the flat-file tree at mesonet.agron.ias-
tate.edu/archive/data/. It is organized by UTC date: /archive/data/YYYY/MM/DD/.
Within each date directory are subdirectories for different data types — GIS/uscomp/
for NEXRAD composite files, GIS/sat/ for GOES satellite products, bufkit/ for model
point soundings, text/ for NWS text products, and others. The directory schema is docu-
mented at mesonet.agron.iastate.edu/archive/schema.php, which is a useful reference before
you start navigating the tree directly.
44

| Mastering | the Mesonet |     |     |     |     | 45  |
| --------- | ----------- | --- | --- | --- | --- | --- |
The raw file archive is how you get data that is not available through any download portal or
API endpoint. If you want the actual NEXRAD base reflectivity composite GeoTIFF for a
specific hour during a specific event, it is in here. If you want the raw METAR observations
for all ASOS stations in their original text format, that is in /archive/raw/ organized by
network. The trade-off is that navigating raw files requires knowing what you are looking
| for — there | is no form | to fill | out, just | directory | trees. |     |
| ----------- | ---------- | ------- | --------- | --------- | ------ | --- |
For the IEM’s NEXRAD archive specifically: composite reflectivity in GIS-friendly raster
format goes back to 1997, making it one of the longer continuous radar archives available at
no cost. The individual station NIDS products for the seven Iowa-coverage radars (DMX,
DVN, OAX, FSD, ARX, MPX, EAX) are archived back to approximately mid-2002, with
base reflectivity going back further. If you need Level II (full-resolution, dual-polarization)
files, those are not hosted at the IEM — you want the Amazon S3 NEXRAD Level II archive,
| which the  | Archive Mainpage |          | links to | directly. |     |     |
| ---------- | ---------------- | -------- | -------- | --------- | --- | --- |
| 5.1.2. NWS | Text             | Products | Archive  |           |     |     |
The IEM archives an enormous volume of NWS text products — essentially everything
transmitted on NOAAPORT going back to the mid-2000s. The dedicated text archive is
covered in depth in Chapter 7, but the Archive Mainpage links to it and serves as the entry
point for users who arrive from the “what historical data exists” direction. Key things the
text archive contains: AFDs, LSRs, CLIs, CFRs, METs, TAFs, hydrologic text products,
and the full record of watches, warnings, and advisories. All of it is searchable by AWIPS
| identifier    | (PIL), WFO, | and      | date.    |     |     |     |
| ------------- | ----------- | -------- | -------- | --- | --- | --- |
| 5.1.3. BUFKIT | and         | Sounding | Archives |     |     |     |
The Archive Mainpage lists two sounding-related resources worth knowing about. BUFKIT
pointsoundingarchivesforIowalocations(andlaterformanymoresitesviaMTarchive)start
from January 2006 and run through the present via mtarchive.geol.iastate.edu. MTarchive,
maintained at Iowa State’s geology department, is a companion archive that holds model
data (GFS, NAM, RAP, RUC, ETA going back to 2001 for some products) in GEMPAK
format. If you work with BUFKIT for model sounding analysis, MTarchive is the source
| you want | for anything | before | the current | operational | archive. |     |
| -------- | ------------ | ------ | ----------- | ----------- | -------- | --- |
The IEM’s own sounding archive for upper-air RAOB data lives at mesonet.agron.ias-
tate.edu/archive/raob/, with a listing interface at /archive/raob/list.phtml. The RAOB
archive will be covered more thoroughly in Chapter 6 under Datasets, but it belongs in the
archive discussion as one of the IEM’s genuinely deep historical resources.

Mastering the Mesonet 46
5.1.4. What the Archive Mainpage Links Out To
One of the more useful things about this page is its curated list of external archives. The
IEM has no interest in reinventing resources that already exist elsewhere — the Archive
Mainpage is honest about what is better found at NOAA, NCEI, Unidata, or elsewhere.
Current external links include the USGS Instantaneous Data Archive (historical river gauge
records), the NOAA NOMADS model data archive, the WPC daily weather map archive
going back to 1872, and NCEI’s severe weather data inventory. These links are maintained
by the IEM team and, unlike a general web search, represent resources they have personally
used and found reliable.
5.2. The GIS Mainpage
mesonet.agron.iastate.edu/GIS/
The GIS Mainpage is the hub for spatial data services at the IEM. If you work with any GIS
platform — QGIS, ArcGIS, Google Earth, Gibson Ridge, or anything that can consume
WMS, WFS, or TMS layers — this is where you find out what the IEM can feed into it. The
page is organized around a simple premise: the IEM handles a lot of spatially referenced
data, and most of that data can be served in standard GIS formats rather than proprietary
ones.
5.2.1. NEXRAD Mosaics: The IEM’s Biggest GIS Product
The single highest-traffic GIS product the IEM produces is its NEXRAD composite mosaic.
The IEM has been generating GIS-friendly radar mosaics since 2003 — first the 4-bit N0R
product, then the 8-bit N0Q composite added in 2010 when the NWS moved to higher-
resolution imagery. The current operational mosaic uses N0Q (base reflectivity) and is
available in multiple formats: as static GeoTIFFs in the archive tree, as WMS (Web Map
Service) layers at mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0q.cgi, and as TMS tiles
suitable for slippy-map web applications.
The temporal WMS endpoints are particularly powerful: the Historical CONUS NEXRAD
Base Reflectivity WMS-T service lets a WMS client request any archived radar composite
back to 1997 by specifying a timestamp in the request. For a GIS user doing post-event
analysis, this means you can overlay archived radar data on any spatial context — county
polygons, road networks, station locations, warning polygons — without downloading and

| Mastering | the Mesonet |     |     | 47  |
| --------- | ----------- | --- | --- | --- |
processing raw files. The IEM’s NEXRAD mosaic documentation at mesonet.agron.ias-
tate.edu/docs/nexrad_mosaic/ explains the production chain, the color tables, and the
| limitations | of each | product version. |     |     |
| ----------- | ------- | ---------------- | --- | --- |
The RadView application at /GIS/radview.phtml is the older interface for accessing
NEXRAD data in GIS format — it predates IEM One and Time Machine and serves
primarily as a reference page for the WMS endpoint URLs and TMS tile server addresses.
If you want to configure a GIS client to consume live or archived IEM radar, this is where
| you find | the connection | strings.     |     |     |
| -------- | -------------- | ------------ | --- | --- |
| 5.2.2.   | GOES Satellite | GIS Products |     |     |
The IEM processes GOES-East imagery from the GOES-R/S series into GIS-ready formats.
The GOES products page at /GIS/goes.phtml documents the current product suite: the
imagery is sourced from Unidata NIMAGE products, stored in a geostationary satellite
projection, and served as WMS layers. All 16 GOES-East channels are available, both for
CONUS and sector views, via the WMS at https://mesonet.agron.iastate.edu/cgi-
| bin/wms/goes_east.cgi. |     | The same structure | exists for GOES-West. |     |
| ---------------------- | --- | ------------------ | --------------------- | --- |
The GOES archive is organized by UTC date in the same flat-file tree as the radar archive:
/archive/data/YYYY/MM/DD/GIS/sat/. Today’ssatellitefilesareaccessiblefromtheGOES
products page with the path pattern documented there. For anyone doing multi-source
overlayanalysis—radar,satellite,surfaceobservations,andwarningpolygonssimultaneously
inaGIS—theIEM’scombinationofarchivedproductsaccessibleviastandardOGCservices
| is genuinely | hard to    | match elsewhere. |     |     |
| ------------ | ---------- | ---------------- | --- | --- |
| 5.2.3.       | The RadMap | API              |     |     |
mesonet.agron.iastate.edu/GIS/radmap_api.phtml
The RadMap API is one of the IEM’s more remarkable hidden tools. It is a map-generation
service that takes a URL with parameters describing what you want — a geographic
bounding box, a timestamp, and a set of layers — and returns a rendered map image. The
layers available include NEXRAD reflectivity, NWS warning polygons (current and archived
storm-based warnings), SPC watches, county outlines, state outlines, and CWAS.
| A RadMap | URL looks | like this: |     |     |
| -------- | --------- | ---------- | --- | --- |
https://mesonet.agron.iastate.edu/GIS/radmap.php?
ts=20241115_1930&
width=640&height=480&
tz=EST&

Mastering the Mesonet 48
bbox=-80.5,39.5,-75.5,42.5&
layers[]=uscounties&
layers[]=nexrad&
layers[]=sbw
That URL would produce a 640×480 map of the central Pennsylvania region at 7:30 PM
Eastern on November 15, 2024, showing county boundaries, NEXRAD composite reflectivity,
and storm-based warning polygons — as a static PNG, directly embeddable in a forum
post or web page. For the mid-Atlantic region, the bounding box above covers essentially
everything from the Harrisburg CTP WFO’s area.
This is the tool that enables the animated radar loops embedded in many weather forum
posts. The IEM Radar Warnings page in the GIS section generates these loops at user-
specified bounding boxes and time ranges, producing animated GIFs directly. The interface
for this is at /GIS/apps/rview/warnings.phtml.
5.2.4. GIS Data Downloads
Beyond the live services, the GIS section offers several download products worth knowing
about:
GeoTIFF rasters—archivedradarandanalysisproductsinGeoTIFFformatareaccessible
from /GIS/tiff and via the rasters page at /GIS/rasters.php. The metadata on how to
interpret the raster values (the lookup tables for converting pixel values to dBZ for radar,
or to temperature units for analysis products) is documented at the Raster Lookup Tables
page linked from the GIS mainpage.
COOP GIS applications — the /GIS/apps/coop/ sub-section contains duration plot
applications that generate maps of COOP-derived statistics for user-specified date ranges.
You select a state, a variable (temperature, precipitation), a start and end date, and the
application computes the period totals for all stations in the network and produces both a
rendered map and a GIS-importable CSV of station values. This is a direct path to getting
spatially organized COOP summary statistics without touching the download portals.
Freeze and Warning viewers—theFreezeMapat/GIS/apps/iem/freeze.phtmlmapsthe
current freeze status and first/last freeze date observations across the ASOS network, useful
in the shoulder seasons. The Warnings Viewer at /GIS/apps/rview/warnings.phtml and
Watches Viewer at /GIS/apps/rview/watch.phtml are the interactive map-based alternatives
to the VTEC browser covered in Chapter 7, useful when you want a visual map interface
rather than a search form.
NEXRAD by Year — /GIS/rad-by-year-fe.phtml lets you compare radar mosaics for the
same geographic area and same clock time across multiple years simultaneously. Want to see

Mastering the Mesonet 49
what the composite reflectivity looked like at 6 PM on November 15 across the last twenty
years? This is the tool. It is more specialized than Time Machine but produces a more
direct visual comparison of the same meteorological setup across years.
5.3. Drought Monitoring
mesonet.agron.iastate.edu/dm/
The IEM’s Drought Monitoring portal is a focused section rather than a large tool suite. Its
primaryfunctionistoprovideaccesstoUSDroughtMonitordata—theweeklyclassification
maps that categorize drought severity from D0 (Abnormally Dry) through D4 (Exceptional
Drought) — in formats and contexts the IEM can connect to its own observational data.
The USDM is produced jointly by the National Drought Mitigation Center, NOAA, and the
USDA, and is released every Thursday. The IEM archives these releases and provides GIS
download access to current and historical shapefiles. The current Drought Monitor layer is
also available as a WMS endpoint for GIS integration — useful when you want to overlay
drought classification on the same map as station observations or radar.
TheIEM’svalue-addhereisprimarilycontextual: placingdroughtclassificationalongsidethe
same station’s precipitation record, CDD/HDD tallies, and departure-from-normal data that
live in the same system. An Autoplot chart showing a station’s year-to-date precipitation
departure against the weekly drought classification trend is the kind of combined view that
requires no special API work — you can produce it by combining Autoplot chart q=172
(YTD precipitation) with drought awareness from this portal.
5.4. Ag Weather/Climate Info
mesonet.agron.iastate.edu/agweather/
The Ag Weather section is where the IEM’s Iowa State roots show most clearly. A significant
fraction of the site’s funding and operational rationale comes from agricultural applications,
and this section reflects that. But even if you have no interest in corn or soybeans, the Ag
Weather and AgClimate sections contain tools that are genuinely useful for any weather
analyst who cares about soil conditions, phenology, or growing-season climate analysis.

| Mastering  | the Mesonet   |         |     | 50  |
| ---------- | ------------- | ------- | --- | --- |
| 5.4.1. The | ISU AgClimate | Network |     |     |
The core of this section is the Iowa State University Agricultural Climate Network, a set of
automatedweatherstationsatIowaStateresearchfarmsthathavebeenoperatingsince1986.
The AgClimate stations are full-featured: they measure standard atmospheric variables plus
soil temperature at multiple depths (2-inch, 4-inch, 8-inch, and deeper at some sites) and
volumetric soil moisture. The data is available in daily and hourly formats going back to
| the network’s | inception. |     |     |     |
| ------------- | ---------- | --- | --- | --- |
For a weather enthusiast, the soil temperature data is the most useful variable here. First
and last freeze probability is one application — but more interesting for mesoscale analysis
is how soil temperature modulates sensible heat flux and influences the surface energy
budget during spring and fall transitions. The 4-inch soil temperature in particular tracks
the transition between frozen and thawed soil with a lag that is valuable for interpreting
| precipitation | type and | snowmelt timing. |     |     |
| ------------- | -------- | ---------------- | --- | --- |
The AgClimate data download is at mesonet.agron.iastate.edu/agclimate/hist/dailyRe-
quest.php for daily summaries and /agclimate/hist/hourlyRequest.php for hourly. Coverage
is Iowa-focused; these stations are not spread across Pennsylvania. But the methodology
and data structure are the same as what you would want if your state had a comparable
network.
| 5.4.2. Soil | Temperature | Maps | and Probabilities |     |
| ----------- | ----------- | ---- | ----------------- | --- |
The soil temperature display maps at /agclimate/soilt.php show current observations across
the AgClimate network for any selected depth. The soil temperature probability tool at
/agclimate/soilt-prob.php lets you ask when a station’s soil temperature at a given depth has
historically reached a given threshold — useful for phenology questions like when to expect
the first significant thaw at root depth or when late-season soil cooling drops below 40°F.
The soil moisture time series application at /agclimate/smts.php provides the volumetric
| moisture   | data across | the network | for any date range. |     |
| ---------- | ----------- | ----------- | ------------------- | --- |
| 5.4.3. The | Broader     | Ag Weather  | Portal              |     |
TheAgWeatherentryintheAreasmenuleadsto/agweather/, whichisaportalpagelinking
to several additional resources: the pest forecasting and GDD maps covered in Chapter 4,
the evapotranspiration analysis, and the ISUSM (ISU Soil Moisture) network metadata. For
users primarily interested in Pennsylvania weather, most of these resources are Iowa-specific
in their observational depth but the conceptual framework — and the Autoplot charts that
draw on AgClimate variables — works wherever the underlying data exists.

| Mastering | the  | Mesonet   |     |      |      |     |         | 51  |
| --------- | ---- | --------- | --- | ---- | ---- | --- | ------- | --- |
| 5.5.      | What | the Areas |     | Menu | Does | Not | Contain |     |
A practical note before leaving this chapter: the Climate Mainpage at /climate/ is listed in
the Areas menu but functions primarily as a navigation hub linking to the COOP, Climodat,
and IEM Reanalysis tools covered in Chapters 2, 4, and 6 respectively. It is not a tool in
itself — if you arrive there expecting a distinct application, you will find a menu of things
covered elsewhere. Think of it as a bookmark for users who approach the site from the
| climate-analysis |     | angle | and want | a curated |     | set of | entry points. |     |
| ---------------- | --- | ----- | -------- | --------- | --- | ------ | ------------- | --- |
Similarly, the NWS Mainpage at /nws/ is listed in both Areas and the NWS Data menu. It
consolidates the warning archive, text product search, river summary tools, and the IEM
Cow verification application. Since that section has enough depth to anchor Chapter 7, the
| discussion | here | stops at | noting | that    | it exists | and | pointing forward. |     |
| ---------- | ---- | -------- | ------ | ------- | --------- | --- | ----------------- | --- |
| 5.6.       | What | to Watch |        | Out For |           |     |                   |     |
The Archive raw file tree is not a backup for disappeared portal data. If a specific
observation does not appear in a download portal result, it is not necessarily in the raw
file archive either. The raw files represent the IEM’s original ingest stream, which has had
gaps and processing failures over the years just like any operational system. The absence of
data in a portal is not always resolvable by going to the raw archive — sometimes the data
| simply | was not | ingested. |     |     |     |     |     |     |
| ------ | ------- | --------- | --- | --- | --- | --- | --- | --- |
GIS services have no SLA. The IEM’s WMS and TMS services are provided without
warrantyandhavechangedovertheyears. TheN0RmosaicWMS,forexample, wasupdated
when the IEM transitioned from N0R to N0Q in 2021. If you build a workflow against one of
these endpoints and it breaks, the RadMap API documentation and the NEXRAD mosaic
| documentation |     | page are | the | first places | to  | check | for what changed. |     |
| ------------- | --- | -------- | --- | ------------ | --- | ----- | ----------------- | --- |
The AgClimate archive starts in 1986 — but not all stations do. The Iowa State
soil moisture network has grown over time. If you are building a long climatological analysis
on soil temperature, check when each station’s record actually starts rather than assuming
the full 1986-present span. The metadata page at /agclimate/info.phtml lists the active
| stations | and | their archive | start | dates. |     |     |     |     |
| -------- | --- | ------------- | ----- | ------ | --- | --- | --- | --- |
The Drought Monitor section does not contain real-time station data. Thedrought
classificationisupdatedweeklyandrepresentsanexpertsynthesis,notanautomatedproduct.
Do not expect it to reflect last night’s rainfall; the USDM process has a deliberate lag built
in.

| Mastering | the Mesonet |         |     | 52  |
| --------- | ----------- | ------- | --- | --- |
| 5.7. Key  | URLs —      | Chapter | 5   |     |
Page URL
| Archive | Mainpage         |     | mesonet.agron.iastate.edu/archive/      |     |
| ------- | ---------------- | --- | --------------------------------------- | --- |
| Archive | Data Tree        |     | mesonet.agron.iastate.edu/archive/data/ |     |
| Archive | Directory Schema |     | mesonet.agron.ias-                      |     |
tate.edu/archive/schema.php
Raw Network Data Archive mesonet.agron.iastate.edu/archive/raw/
RAOB Sounding Archive mesonet.agron.iastate.edu/archive/raob/
RAOB Listing mesonet.agron.ias-
tate.edu/archive/raob/list.phtml
GIS Mainpage mesonet.agron.iastate.edu/GIS/
NEXRAD Mosaic Documentation mesonet.agron.iastate.edu/docs/nexrad_mo-
saic/
| GOES   | GIS Products |     | mesonet.agron.iastate.edu/GIS/goes.phtml |     |
| ------ | ------------ | --- | ---------------------------------------- | --- |
| NEXRAD | RadView      |     | mesonet.agron.iastate.edu/GIS/rad-       |     |
view.phtml
| RadMap | API |     | mesonet.agron.ias- |     |
| ------ | --- | --- | ------------------ | --- |
tate.edu/GIS/radmap_api.phtml
| Radar | + Warnings Viewer |     | mesonet.agron.ias- |     |
| ----- | ----------------- | --- | ------------------ | --- |
tate.edu/GIS/apps/rview/warnings.phtml
| Watches | Viewer |     | mesonet.agron.ias- |     |
| ------- | ------ | --- | ------------------ | --- |
tate.edu/GIS/apps/rview/watch.phtml
COOP GIS Duration Apps mesonet.agron.iastate.edu/GIS/apps/coop/
Freeze Map mesonet.agron.ias-
tate.edu/GIS/apps/iem/freeze.phtml
| NEXRAD | by Year |     | mesonet.agron.iastate.edu/GIS/rad-by-year- |     |
| ------ | ------- | --- | ------------------------------------------ | --- |
fe.phtml
| GeoTIFF    | Rasters        |     | mesonet.agron.iastate.edu/GIS/rasters.php |     |
| ---------- | -------------- | --- | ----------------------------------------- | --- |
| Drought    | Monitoring     |     | mesonet.agron.iastate.edu/dm/             |     |
| Ag Weather | Portal         |     | mesonet.agron.iastate.edu/agweather/      |     |
| AgClimate  | Network        |     | mesonet.agron.iastate.edu/agclimate/      |     |
| AgClimate  | Daily Download |     | mesonet.agron.iastate.edu/agcli-          |     |
mate/hist/dailyRequest.php
| AgClimate | Hourly Download |     | mesonet.agron.iastate.edu/agcli- |     |
| --------- | --------------- | --- | -------------------------------- | --- |
mate/hist/hourlyRequest.php
| Soil Temperature | Map |     | mesonet.agron.iastate.edu/agcli- |     |
| ---------------- | --- | --- | -------------------------------- | --- |
mate/soilt.php

| Mastering | the Mesonet |     | 53  |
| --------- | ----------- | --- | --- |
| Page      |             | URL |     |
Soil Temp Probabilities mesonet.agron.iastate.edu/agclimate/soilt-
prob.php
| Soil Moisture | Time Series | mesonet.agron.iastate.edu/agcli- |     |
| ------------- | ----------- | -------------------------------- | --- |
mate/smts.php
| Climate Mainpage |     | mesonet.agron.iastate.edu/climate/ |     |
| ---------------- | --- | ---------------------------------- | --- |

| 6. Chapter |     | 6   | — Datasets: |     | The | Full Archive |     |
| ---------- | --- | --- | ----------- | --- | --- | ------------ | --- |
Explained
The Datasets menu is where the IEM stops being a collection of tools and starts being a data
warehouse. Everything in the previous five chapters — the networks, the current conditions
displays, the Autoplot charts, the GIS services — ultimately draws from datasets that live
here. This chapter maps those datasets: what each one actually contains, how far back it
goes, how the data is structured, and when you should reach for one over another. Two of
them — MOS and IEMRE — get extended treatment because they are genuinely complex
| and genuinely | underexplained |     | elsewhere. |     |     |     |     |
| ------------- | -------------- | --- | ---------- | --- | --- | --- | --- |
The Datasets menu currently has twelve entries: Daily Climatology, Daily Observations,
Dataset Documentation, IEM Reanalysis, Model Output Statistics, NEXRAD Mosaic,
PIREP - Pilot Reports, Roads Mainpage, RADAR & Satellite, Rainfall Data, Sounding
Archive, and Soil Moisture Satellite. NEXRAD Mosaic and RADAR & Satellite were covered
in Chapters 5 and 6 respectively. Roads and PIREPs are specialized enough to note briefly
and move on. That leaves the core analytical datasets, which are the heart of this chapter.
| 6.1. Daily | Climatology: |     | COOP | Records | and the | Extremes | Tool |
| ---------- | ------------ | --- | ---- | ------- | ------- | -------- | ---- |
mesonet.agron.iastate.edu/COOP/extremes.php
Exclamation-Triangle
| Data | Quality | Note — | COOP Time | of Observation | Bias (TOBS) |     |     |
| ---- | ------- | ------ | --------- | -------------- | ----------- | --- | --- |
COOP observers take readings at self-selected times — some at 7 AM, some at 5 PM.
This creates a systematic bias: a 5 PM observer who records a 95°F peak on Tuesday
will still see that peak on Wednesday’s max-min thermometer if a cold front moved in
overnight. Wednesday gets logged as 95°F even though the actual high was 75°F. The
| 24-hour | observation | window | double-counts | the extreme. |     |     |     |
| ------- | ----------- | ------ | ------------- | ------------ | --- | --- | --- |
If you are building consecutive-day heat wave analyses or comparing stations with
different observation times, account for TOBS offsets before drawing conclusions. The
| full correction | methodology |     | is in Chapter | 10. |     |     |     |
| --------------- | ----------- | --- | ------------- | --- | --- | --- | --- |
54

Mastering the Mesonet 55
The Daily Climatology entry in the Datasets menu points to the COOP extremes tool,
which is the surface-level entry point to the IEM’s deepest historical climate dataset. The
underlying data is the NWS Cooperative Observer network — the same observations covered
in Chapter 2 — but through the Datasets lens, the question shifts from “how do I find a
station” to “how do I work with a century of daily records.”
The COOP extremes tool at /COOP/extremes.php lets you select a state, a station, and a
date, then browse the period-of-record statistics for that date: the all-time high and low
temperatures, the highest and lowest precipitation totals, the record snowfall, and the years
in which each record was set. For any station with a long record — Pennsylvania COOP
stationsroutinelyextendtothe1890s—thistoolsurfaceshistoricalcontextthatisotherwise
buried in raw data files.
The companion download tool for normals is at mesonet.agron.iastate.edu/COOP/dl/nor-
mals.phtml, which outputs the 366-day climatological normals for any station in CSV format.
These normals are computed by the IEM from the full period of record rather than the
official 1991–2020 NCEI normals, which matters when you want a station-specific baseline
that uses all available data rather than the most recent 30-year window. For stations with
80 or 100 years of record, the IEM’s period-of-record normals tend to be slightly more
conservative (less influenced by recent warming) than the NCEI 1991–2020 normals — a
meaningful difference when you are analyzing trend departures.
The Climodat application at mesonet.agron.iastate.edu/climodat/ builds on the same un-
derlying COOP data and generates a series of pre-formatted climate reports — monthly
summaries, annual rankings, first and last freeze dates, precipitation frequency statistics,
and more — for any station in the network. Climodat is covered in Chapter 4 as an App, but
it is worth noting here as the primary user interface to the COOP climatological dataset.
6.2. Daily Observations: The IEM Summary Dataset
mesonet.agron.iastate.edu/request/daily.phtml
The Daily Observations download portal is the IEM’s unified single-day-per-row summary
product. Where the COOP download gives you raw cooperative observer reports and the
ASOS download gives you hourly observations, this portal gives you a one-line-per-station-
per-day summary computed by the IEM across multiple networks.
The variables available vary by network. For ASOS/AWOS stations, the daily summary
includes high temperature, low temperature, average temperature, dew point high and
low, peak wind gust and direction, average wind speed, precipitation total, snowfall (where
reported), and sky condition. For COOP stations, the set is different: max/min temperature,

Mastering the Mesonet 56
precipitation, snowfall, snow depth, and observation time. The portal lets you select a
network, a date range, and a set of stations, then download in CSV, Excel, or HTML.
ThekeydistinctionbetweenthisportalandtherawASOSdownloadat/request/download.phtml
is aggregation level. The daily summary portal gives you IEM-computed daily statistics —
a single row capturing the whole day. The ASOS download gives you individual hourly
observations that you aggregate yourself. For most climatological analysis, the daily
summary is faster and easier. For any analysis that requires sub-daily timing — hourly
temperature evolution, precipitation start and end times, wind shift timing — go to the raw
hourly download.
6.3. Dataset Documentation
mesonet.agron.iastate.edu/info/datasets/
This page is the IEM’s own reference documentation for its data products. It is written
for developers and researchers rather than casual users, but it contains information that is
genuinelyhardtofindelsewhere: the variabledefinitions, theunits andencodingconventions,
the processing pipeline for each dataset, and the known limitations. The Variables reference
page at /info/variables.phtml is an essential companion — if you pull data from any IEM
portal and see a column header you do not recognize, this is where you look it up.
Before building any serious analysis pipeline against IEM data, spend twenty minutes
with the dataset documentation for the network you are using. The encoding choices are
occasionally counterintuitive — wind direction in MOS, for example, is stored as the raw
encodedvaluemultipliedby10forthetruedegreevalue—andsomevariableshavehistorical
processingchangesthataffecthowyouinterpretearlyversusrecentdata. Thedocumentation
catches these.
6.4. IEM Reanalysis (IEMRE)
mesonet.agron.iastate.edu/iemre/
IEMRE is one of those datasets where the IEM’s own description is so direct it is worth
engaging with directly. The page says: “IEMRE is nothing special. It was cool maybe 15
years ago, but now days there are superior products available. Use those instead!” That is a

| Mastering | the Mesonet |     |     |     | 57  |
| --------- | ----------- | --- | --- | --- | --- |
remarkable thing for a data product to say about itself, and it tells you something important
| about both | the product | and the | people behind | it. |     |
| ---------- | ----------- | ------- | ------------- | --- | --- |
Here is what IEMRE actually is, why it exists despite that disclaimer, and when it is still
| the right | choice.    |     |     |     |     |
| --------- | ---------- | --- | --- | --- | --- |
| 6.4.1.    | What IEMRE | Is  |     |     |     |
IEMRE is a gridded analysis product — meaning it takes point observations from across
the IEM’s station networks and interpolates them onto a regular grid, producing spatially
continuous fields of temperature, precipitation, dew point, wind speed, snowfall, soil temper-
ature, and solar radiation. The current CONUS grid resolution is 0.125 × 0.125 degrees
(roughly 8–14 km depending on latitude). The archive runs from 1950 to real-time, with
hourly and daily temporal resolution. As of July 2025, non-CONUS domains have been
| added for | South America, | Europe, | and Southeast | Asia/China. |     |
| --------- | -------------- | ------- | ------------- | ----------- | --- |
The honest version of why this exists: the IEM needed a gridded analysis product to drive
agricultural modeling work — specifically the Daily Erosion Project, which requires spatially
continuous precipitation and temperature fields to compute soil loss estimates across Iowa.
Building IEMRE was solving that operational need. Once it existed, the IEM made it
public.
| 6.4.2. | The Data Flow |     |     |     |     |
| ------ | ------------- | --- | --- | --- | --- |
The intelligence in IEMRE is in how it sources each variable and handles the transition
betweenreal-timeoperationalproductsandlonger-termreanalysisproducts. FortheCONUS
domain, the precipitation chain works like this: hourly values are initially sourced from
NCEP Stage IV (radar-estimated precipitation bias-corrected by gauges), then replaced
with Stage IV adjusted by PRISM for dates more than eight days old, then replaced by
ERA5-Land for dates before 1997. For temperature, the near-real-time source is RTMA (the
NWS’s Real-Time Mesoscale Analysis) for post-2010 data, falling back to a cruder ASOS
grid analysis for older data and ERA5-Land before 2010. Solar radiation as of January 2023
uses HRRR for the most recent eight days and ERA5-Land for anything older.
The practical implication of this layered sourcing is that IEMRE values for a given location
will change retroactively as better analysis products become available. A precipitation
estimate from last week may look different in six months once the Stage IV/PRISM
adjustment cycle catches up. This is appropriate behavior — the system is improving its
estimates with time — but it means you should not treat IEMRE values as fixed the way
| you would | treat a station | observation. |     |     |     |
| --------- | --------------- | ------------ | --- | --- | --- |

| Mastering | the Mesonet |       |     |     | 58  |
| --------- | ----------- | ----- | --- | --- | --- |
| 6.4.3.    | When to Use | IEMRE |     |     |     |
The disclaimer on the IEMRE page points to four alternatives: ERA5-Land, DayMet,
GridMet, and PRISM. Those are all genuinely good products, and for research requiring
defensible, peer-reviewed, stable gridded climate data, they are better choices. IEMRE’s
| advantages | are narrow | but real: |     |     |     |
| ---------- | ---------- | --------- | --- | --- | --- |
Real-time currency. IEMRE updates within about ten minutes of each hour. ERA5-Land
has a five-day lag for near-real-time data, and DayMet and PRISM do not provide near-real-
time at all. If you need gridded analysis for an event that happened yesterday or last week,
| IEMRE | is the only | free option. |     |     |     |
| ----- | ----------- | ------------ | --- | --- | --- |
IEM-native variables. IEMRE includes snowfall, snow depth, and soil temperature
variables that are sourced from the IEM’s own network data. ERA5-Land does not include
| observed | snowfall the | way COOP | observers report | it. |     |
| -------- | ------------ | -------- | ---------------- | --- | --- |
SeamlessAPIaccess. TheIEMREJSONAPIat/iemre/daily/{date}/{lat}/{lon}/json
and /iemre/multiday/{date1}/{date2}/{lat}/{lon}/json is simple to call and returns
clean JSON with no authentication required. If you want gridded climate data at a specific
location and you are building something that needs to run programmatically, IEMRE’s API
is considerably easier to work with than the NetCDF interfaces of ERA5-Land or PRISM.
Point sampling as spatial interpolation. The IEM uses IEMRE to backfill climate
station values for the Climodat product — when a COOP station has missing data, the
system samples from the IEMRE grid at that location as a fill value. This is documented
and flagged in the output, but it means IEMRE and Climodat are tightly coupled in ways
| that matter | for quality | analysis. |     |     |     |
| ----------- | ----------- | --------- | --- | --- | --- |
| 6.4.4.      | Accessing   | IEMRE     |     |     |     |
The cleanest way to use IEMRE for a specific location is the JSON API. For a Pennsylvania
example — say, the location of the Harrisburg airport at 40.19°N, 76.76°W — a daily query
| for 2024 | looks like: |     |     |     |     |
| -------- | ----------- | --- | --- | --- | --- |
https://mesonet.agron.iastate.edu/iemre/multiday/2024-01-01/2024-12-31/40.19/-
76.76/json
That returns a JSON object with daily values for all available IEMRE variables at the grid
cell nearest to those coordinates. The output includes high_tmpf, low_tmpf, precip_in,
snow_in, snowd_in, rstage4_precip_in (Stage IV precipitation), soil4t_f (4-inch soil
| temperature), | and several | others. |     |     |     |
| ------------- | ----------- | ------- | --- | --- | --- |

Mastering the Mesonet 59
For raw gridded access, annual NetCDF files for the CONUS domain are available at
mesonet.agron.iastate.edu/onsite/iemre/. These are the source files the IEM uses internally
— xarray or any NetCDF-aware library can open them directly.
6.5. Model Output Statistics (MOS)
mesonet.agron.iastate.edu/mos/
MOS is one of the most useful datasets in the IEM archive for serious weather analysis, and
also one of the most misunderstood. Most people who have heard of MOS think of it as “a
forecast.” That is true but incomplete in ways that matter for how you use the archive.
6.5.1. What MOS Actually Is
Model Output Statistics is a statistical post-processing technique applied to numerical
weather prediction model output. The NWS runs a deterministic forecast model — the GFS,
the NAM — which produces gridded fields of atmospheric variables at regular intervals out
to some forecast horizon. Those raw model fields have systematic biases: the model might
run consistently too warm at certain stations, or too wet in complex terrain, or have poor
skill at certain forecast lead times for certain variables. MOS corrects for those biases by
developing statistical regression equations at each forecast station that relate the model’s
large-scale output fields to the observed surface conditions at that station.
The equations are developed separately for each station, each variable, each season, and each
forecast projection (the 6-hour, 12-hour, 24-hour, 48-hour forecast, and so on). The result is
astation-specificbiascorrectionthatgivesyouastatisticallycalibratedpointforecastateach
location, derived from the model run but adjusted for that station’s historical relationship
with the model.
The practical difference between a raw GFS temperature forecast and GFS-MOS at Harris-
burg: the raw GFS is interpolating from a large-scale grid cell that may not capture the
Susquehanna Valley’s cold-air pooling behavior in winter. The GFS-MOS equations learned
from years of GFS runs and Harrisburg observations that the model needs to be adjusted
downward by X degrees on calm clear nights in January, and the output reflects that. For
temperature, precipitation type, and ceiling/visibility forecasts at ASOS locations, MOS
has historically been competitive with or better than human forecasters at 12–24 hour lead
times.

| Mastering | the Mesonet  |          |     |     |     | 60  |
| --------- | ------------ | -------- | --- | --- | --- | --- |
| 6.5.2.    | What the IEM | Archives |     |     |     |     |
The IEM’s MOS archive covers nine model configurations, with the following active archive
| dates confirmed | as of March  | 2026:        |               |             |          |     |
| --------------- | ------------ | ------------ | ------------- | ----------- | -------- | --- |
|                 | Model        | Abbreviation | Archive Start | Status      |          |     |
|                 | AVN          | AVN          | 1 June 2000   | Ended 16    | Dec 2003 |     |
|                 | ETA          | ETA          | 24 Feb 2002   | Ended 9 Dec | 2008     |     |
|                 | GFS          | GFS          | 16 Dec 2003   | Real-time   |          |     |
|                 | GFS LAMP     | LAV          | 12 Jul 2020   | Real-time   |          |     |
|                 | GFS Extended | MEX          | 12 Jul 2020   | Real-time   |          |     |
|                 | NAM          | NAM          | 9 Dec 2008    | Real-time   |          |     |
|                 | NBS          | NBS          | 7 Nov 2018    | Real-time   |          |     |
|                 | NBE          | NBE          | 23 Jul 2020   | Real-time   |          |     |
The GFS archive is the deepest operationally useful record, running continuously from
December 2003 to present. The older AVN archive (predecessor to GFS) pushes the
continuous record back to June 2000, meaning you have over two decades of consistent
GFS-lineage MOS forecasts at every ASOS station in the country. That is a substantial
| verification | dataset.     |             |        |              |     |     |
| ------------ | ------------ | ----------- | ------ | ------------ | --- | --- |
| GFS vs.      | NAM vs. LAMP | vs. NBS/NBE | — what | is each for? |     |     |
The GFS MOS is the standard medium-range product, with projections from 6 hours out to
192 hours at 6-hour intervals for the first 72 hours and 12-hour intervals beyond. It is the
workhorse.
The NAM MOS covers shorter projections — out to 60 hours — at the same 6-hour interval.
NAM MOS tends to outperform GFS MOS at short ranges (6–24 hours) in complex terrain
situations because the NAM runs at higher horizontal resolution over the CONUS and its
| mesoscale | features are better | resolved. |     |     |     |     |
| --------- | ------------------- | --------- | --- | --- | --- | --- |
GFS LAMP (Local Analysis and Prediction System, abbreviated LAV in the IEM archive)
is a very-short-range product, producing hourly projections out to 25 hours, updated every
hour. It bridges the gap between the 6-hourly MOS guidance and the current observation.
If you are doing hour-by-hour forecast verification or want the most frequently updated
| statistical | guidance, LAMP | is what you | want. |     |     |     |
| ----------- | -------------- | ----------- | ----- | --- | --- | --- |
NBS (National Blend of Models Statistics) and NBE (National Blend of Models Extended)
are the successors to the GFS and MEX products respectively, blending multiple model
inputs rather than relying on a single model. NBS runs from 2018 and represents the
NWS’s current operational statistical guidance. It uses the same MOS framework but with
a multi-model ensemble as input rather than a single deterministic run.

Mastering the Mesonet 61
MEX (GFS Extended) covers projections beyond 72 hours, out to 192 hours (eight days), at
12-hour intervals. Useful for extended-range verification work.
6.5.3. Using the MOS Archive
The most intuitive interface is the Interactive MOS Tables at mesonet.agron.ias-
tate.edu/mos/table.phtml. You enter a four-character station identifier (KMDT for
Harrisburg, KIPT for Williamsport, etc.), select a model, select a variable, and choose a
date range. The table shows you how the model’s forecast for that variable evolved across
successive model runs for that period — each row is a different run time, each column is
a different forecast projection. This is the interface to use when you want to see how a
specific forecast evolved in time: did the GFS MOS temperature guidance for the day of a
major winter storm flip dramatically 48 hours out? Did it nail the precipitation type, or
was it wrong all the way through?
The raw ASCII MOS data is accessible through the text archive via the AFOS/AWIPS
identifier system. Every MOS product is assigned a six-character identifier following the
pattern <model><3-char station>. For GFS MOS at Harrisburg (MDT), that is GFSMDT.
For NAM MOS at Harrisburg, NAMMDT. For LAMP at Harrisburg, LAVMDT. You pull these
through the same text archive interface used for any NWS text product, covered in Chapter
7.
For programmatic access, the API endpoint at /api/1/mos.json accepts station, model,
and runtime parameters and returns clean JSON. An example call pulling the most recent
GFS MOS run for Harrisburg:
https://mesonet.agron.iastate.edu/api/1/mos.json?station=KMDT&model=GFS
The MOS data download form at /fe.phtml (linked from the MOS mainpage) lets you pull
the raw MOS data for any station and time period in CSV format, with all variables for all
forecast projections in a flat table. This is the format to use for bulk verification work.
Autoplot chart q=37 (MOS Forecasts vs. Actual Observations) gives you a visual monthly
comparison of any MOS variable against the observed values at any ASOS station. For
temperature verification, this is an excellent way to spot seasonal bias patterns — GFS
MOS has historically run warm in winter at inland mid-Atlantic stations during cold-air
damming events, for reasons that are directly legible in the chart when you look at January
and February.

| Mastering | the Mesonet |        |                |          |     | 62  |
| --------- | ----------- | ------ | -------------- | -------- | --- | --- |
| 6.5.4. A  | Note        | on MOS | Wind Direction | Encoding |     |     |
The MOS archive documentation flags one encoding issue worth knowing: wind direction
(wdr in the database) is stored as the raw value from the text product, which is the true
direction divided by 10. A wdr value of 27 means 270 degrees (west). This is documented in
the MOS mainpage notes, but it is easy to miss if you are parsing the data without reading
| the documentation |     | first.  |        |     |     |     |
| ----------------- | --- | ------- | ------ | --- | --- | --- |
| 6.6. Sounding     |     | Archive | (RAOB) |     |     |     |
mesonet.agron.iastate.edu/archive/raob/
The IEM’s sounding archive covers rawinsonde (RAOB) data for US and Canadian upper-air
stations, twice-daily. The primary source is the Storm Prediction Center’s sounding archive,
supplemented by additional backfill sources that extend some station records to the 1940s.
The standard archive depth for most active stations runs from approximately the 1950s to
real-time, with the twice-daily 00Z and 12Z launches from each upper-air station.
The download form at the archive URL accepts a station identifier (three or four characters
— for Pittsburgh’s sounding site, that is PIT; for Wallops Island, WAL; for Albany, ALB), a
start time, and an end time, and returns a CSV file with all available pressure levels. The
columns are station, valid UTC time, pressure in millibars, height in meters, temperature
in Celsius, dew point in Celsius, wind direction, wind speed in knots, and optional balloon
| bearing and | range | where | available. |     |     |     |
| ----------- | ----- | ----- | ---------- | --- | --- | --- |
The JSON API endpoint at /json/raob.py offers the same data with additional query flex-
ibility. You can pull a specific pressure level across a date range — useful for examining, say,
500 hPa temperature anomalies at Albany over a specific season — rather than downloading
| full sounding | profiles | and | filtering yourself. |     |     |     |
| ------------- | -------- | --- | ------------------- | --- | --- | --- |
Formid-Atlanticupper-airwork,therelevantstationsareDIX(Upton/NewYork),IAD(Ster-
ling/Washington DC), PIT (Pittsburgh), and WAL (Wallops Island, VA). The Pittsburgh
and Wallops soundings together bracket central Pennsylvania, with Pittsburgh capturing the
western approach flow and Wallops representing the coastal marine environment. The IAD
sounding at Sterling is particularly useful for mid-Atlantic cold-air damming analysis — the
850 hPa temperature inversion structure at Sterling during CAD events has been studied
| and is directly | readable |     | in the IEM sounding | archive. |     |     |
| --------------- | -------- | --- | ------------------- | -------- | --- | --- |
Special soundings — launches outside the standard 00Z and 12Z schedule issued during
| severe weather | events | —   | are included | in the archive | where available. |     |
| -------------- | ------ | --- | ------------ | -------------- | ---------------- | --- |

Mastering the Mesonet 63
6.7. Rainfall Data and MRMS
mesonet.agron.iastate.edu/rainfall/
The Rainfall Data entry in the Datasets menu points to the IEM’s GIS Rainfall portal,
which provides access to gridded precipitation analysis products at hourly and daily time
steps. The primary source is NCEP Stage IV, the NWS’s multi-sensor precipitation analysis
that blends NEXRAD radar estimates with rain gauge observations and quality-controls the
result.
Stage IV data is available from approximately 2002 onward. The IEM archives the hourly
Stage IV grib files at /archive/data/YYYY/MM/DD/ under the stage4/ subdirectory, and
provides derived daily and multi-day accumulation maps through the Autoplot interface
(q=84 for precipitation maps, q=86 for daily gridded variable maps). For precipitation
analysis during a specific event, the combination of Stage IV from the IEM and gauge
observations from CoCoRaHS and ASOS gives you the most complete picture available from
free sources.
The MRMS (Multi-Radar/Multi-Sensor) dataset is also archived. MRMS is the successor
to Stage IV for real-time QPE — it runs at higher resolution (0.01 degree, roughly 1 km)
and updates every 2 minutes rather than hourly. The IEM archives MRMS daily totals in
NetCDF format at /onsite/mrms/, and the IEMRE system uses MRMS as a supplemental
precipitation source. For event analysis where sub-hourly precision matters — a convective
storm with sharp gradients — the MRMS archive is substantially more useful than Stage
IV.
6.8. Soil Moisture Satellite
mesonet.agron.iastate.edu/smos/
The SMOS (Soil Moisture and Ocean Salinity) satellite dataset entry is a niche product for
most weather enthusiasts — it provides passive microwave-derived soil moisture estimates
from ESA’s SMOS satellite. The IEM archives and displays these for agricultural and
hydrological research applications. For climate hobbyists, this is a dataset to know exists
rather than one you will use regularly.

Mastering the Mesonet 64
6.9. What to Watch Out For
The MOS archive has a backfill boundary. The IEM news post announcing MOS
archiving in January 2009 noted that the archive was complete back to December 2008 at
that point, with the possibility of further backfill. The GFS archive ultimately extends to
December 2003. There is no MOS data at the IEM for anything before that, and the period
between late 2003 and late 2008 may have occasional gaps depending on when different
models entered the archive. For verification studies that need to go back before 2003, the
NWS MDL maintains its own archives through a separate access pathway.
IEMRE values change retroactively. As noted above, the IEMRE pipeline replaces
provisionalestimateswithbetteranalysisproductsastheybecomeavailable. Ifyoudownload
IEMRE data today for a date six months ago, the values may differ slightly from what
you would have downloaded six months ago for that same date. This is by design but it
matters for reproducibility — if you are building a research pipeline, either snapshot the
data at a point in time or use a stable product like ERA5-Land where retroactive updates
are versioned and documented.
RAOB data is not radar-verified. The sounding archive represents what the radiosonde
actually measured as the balloon ascended. It is not quality-controlled against radar wind
profilers or other independent measurements. Gross outliers do exist in the record —
occasional instrument failures, balloon drift issues, or data transmission errors. For research
applications involving the sounding archive, independent QC is good practice.
Daily summaries and COOP observation time. The IEM’s daily summary dataset
uses a fixed 24-hour UTC period for its computations, which does not always match the
observation time of the COOP reporter at that station. A COOP observer who takes their
reading at 7 AM local time is reporting the 24-hour period ending at 7 AM, not the calendar
day. This can create apparent discrepancies between the IEM daily summary and the
raw COOP observation, particularly for precipitation and temperature extremes on days
with overnight events. The COOP observation time (TOBS) is documented in the station
metadata and is the key to resolving these discrepancies when they appear.
6.10. Workflow 1 — Looking Up Period-of-Record Daily Extremes
for a COOP Station
The question: What is the all-time record high temperature for January 17th at your local
COOP station? What year did it occur?

| Mastering   | the Mesonet                                         |     |     |     |     | 65  |
| ----------- | --------------------------------------------------- | --- | --- | --- | --- | --- |
| Start here: | https://mesonet.agron.iastate.edu/COOP/extremes.php |     |     |     |     |     |
The page presents a simple form: select a state and a date. The state dropdown defaults to
Iowa — change it to Pennsylvania (or whichever state you are working in). Set the month
| and day | to January | 17. | Submit. |     |     |     |
| ------- | ---------- | --- | ------- | --- | --- | --- |
What you get back is a table of every COOP station in that state with records for that
date — station ID, station name, record high temperature, record low temperature, record
precipitation, and the year each record was set. The table is sortable by any column, which
is useful if you want to quickly scan for the most extreme values across the state rather than
| looking | at a specific | station. |     |     |     |     |
| ------- | ------------- | -------- | --- | --- | --- | --- |
To get the full annual record for a single station, click the station ID in the table. This takes
you to a station-specific view showing every calendar day of the year with its record high,
record low, and record precipitation, all drawn from the COOP archive for that station. For
a station like Harrisburg with records going back to the late nineteenth century, this is a
genuinely rich historical document — you can see the depth of the record and the years in
| which the | extremes | were | set. |     |     |     |
| --------- | -------- | ---- | ---- | --- | --- | --- |
A few things to watch for: this tool covers the COOP network, not ASOS. The COOP record
at a given location may extend back further than the ASOS record, but it is a once-daily
observation rather than hourly. If you are looking for extreme hourly values — record hourly
precipitation, record sustained wind — you will need Autoplot rather than this tool. Also
note the “unofficial” label: these are IEM-computed records from the COOP archive, not
| the formally | certified | NWS | climate | records | for the station. |     |
| ------------ | --------- | --- | ------- | ------- | ---------------- | --- |
| 6.11.        | Key URLs  | —   | Chapter | 6       |                  |     |
| Page         |           |     |         |         | URL              |     |
Daily Climatology / COOP Extremes mesonet.agron.iastate.edu/COOP/ex-
tremes.php
| COOP | Normals | Download |     |     | mesonet.agron.iastate.edu/COOP/dl/nor- |     |
| ---- | ------- | -------- | --- | --- | -------------------------------------- | --- |
mals.phtml
| Daily Observations |     | Download |     |     | mesonet.agron.iastate.edu/re- |     |
| ------------------ | --- | -------- | --- | --- | ----------------------------- | --- |
quest/daily.phtml
Dataset Documentation mesonet.agron.iastate.edu/info/datasets/
| Variables | Reference |     |     |     | mesonet.agron.iastate.edu/info/vari- |     |
| --------- | --------- | --- | --- | --- | ------------------------------------ | --- |
ables.phtml
| IEM Reanalysis |     | (IEMRE) |     |     | mesonet.agron.iastate.edu/iemre/ |     |
| -------------- | --- | ------- | --- | --- | -------------------------------- | --- |

| Mastering | the Mesonet |     | 66  |
| --------- | ----------- | --- | --- |
| Page      |             | URL |     |
IEMRE CONUS NetCDF Files mesonet.agron.iastate.edu/onsite/iemre/
| IEMRE | Daily API | mesonet.agron.ias- |     |
| ----- | --------- | ------------------ | --- |
tate.edu/iemre/daily/{date}/{lat}/{lon}/json
| IEMRE | Multiday API | mesonet.agron.iastate.edu/iemre/multi- |     |
| ----- | ------------ | -------------------------------------- | --- |
day/{date1}/{date2}/{lat}/{lon}/json
| Model | Output Statistics | mesonet.agron.iastate.edu/mos/ |     |
| ----- | ----------------- | ------------------------------ | --- |
MOS Interactive Table mesonet.agron.iastate.edu/mos/table.phtml
| MOS API | (JSON/CSV) | mesonet.agron.iastate.edu/api/1/docs#/de- |     |
| ------- | ---------- | ----------------------------------------- | --- |
fault/service_mos__fmt__get
| MOS Raw | Download | mesonet.agron.iastate.edu/fe.phtml |     |
| ------- | -------- | ---------------------------------- | --- |
MOS vs. Observations Chart (q=37) mesonet.agron.iastate.edu/plot-
ting/auto/?q=37
| Sounding | Archive  | mesonet.agron.iastate.edu/archive/raob/ |     |
| -------- | -------- | --------------------------------------- | --- |
| RAOB     | JSON API | mesonet.agron.ias-                      |     |
tate.edu/json/raob.py?help=
Rainfall / Stage IV Portal mesonet.agron.iastate.edu/rainfall/
| MRMS     | NetCDF Archive | mesonet.agron.iastate.edu/onsite/mrms/   |     |
| -------- | -------------- | ---------------------------------------- | --- |
| Stage IV | Archive        | mesonet.agron.iastate.edu/onsite/stage4/ |     |
NEXRAD Mosaic Documentation mesonet.agron.iastate.edu/docs/nexrad_mo-
saic/
Soil Moisture Satellite (SMOS) mesonet.agron.iastate.edu/smos/
| Climodat | Reports | mesonet.agron.iastate.edu/climodat/ |     |
| -------- | ------- | ----------------------------------- | --- |

| 7. Chapter |     | 7   | — NWS |          | Data:    | Warnings, |
| ---------- | --- | --- | ----- | -------- | -------- | --------- |
| Forecasts, |     |     | and   | Official | Products |           |
Every other chapter in this guide has been about observational data — what the atmosphere
actually did, as measured by sensors and reported by observers. This chapter is different.
The NWS Data section of the IEM is an archive of decisions: what forecasters thought was
happening, what they warned the public about, when they issued those warnings relative to
the event, and what language they used to justify the call. That is a fundamentally different
kind of record, and it requires a different frame of mind to use effectively.
The NWS Mainpage at mesonet.agron.iastate.edu/nws/ is the hub for all of it. It is one of
the most link-dense pages on the IEM — dozens of individual tools organized by category
— and one of the easiest places to feel lost. This chapter works through it systematically,
with the deepest treatment reserved for VTEC, which is the structural backbone that makes
| almost everything | else | here     | possible. |     |             |         |
| ----------------- | ---- | -------- | --------- | --- | ----------- | ------- |
| 7.1. VTEC:        | The  | Backbone |           | of  | the Warning | Archive |
Before touching any individual tool, you need to understand VTEC — not because it is
complicated, but because once you do understand it, every warning archive tool on the IEM
| suddenly makes | sense. |     |     |     |     |     |
| -------------- | ------ | --- | --- | --- | --- | --- |
VTEC stands for Valid Time Event Code. It is the structured metadata system the NWS
began embedding in its watch, warning, and advisory products in 2005. Before VTEC, a
tornado warning was just a text product with a start time and a geographic area. There
was no systematic way to track whether that warning was extended, updated, cancelled,
or superseded by a new issuance. Post-event analysis required reading each text product
| manually and | reconstructing |     | the timeline |     | by hand. |     |
| ------------ | -------------- | --- | ------------ | --- | -------- | --- |
VTEC changed that by requiring each significant weather product to carry a machine-
parseable code block that encodes everything needed to track the full lifecycle of that event.
| A typical VTEC | string | looks | like this: |     |     |     |
| -------------- | ------ | ----- | ---------- | --- | --- | --- |
67

Mastering the Mesonet 68
/O.NEW.KCTP.TO.W.0012.240615T2031Z-240615T2200Z/
Reading left to right: the /O. indicates this is an operational (not test) product. NEW is
the action code — this is a new issuance. KCTP is the four-character WFO identifier (State
College, Pennsylvania). TO is the phenomena code — tornado. W is the significance —
Warning (as opposed to A for Watch, Y for Advisory, or S for Statement). 0012 is the Event
Tracking Number (ETN) — the twelfth tornado warning issued by CTP in this calendar year.
240615T2031Z is the event begin time in UTC, and 240615T2200Z is the initial expiration
time.
When forecasters update a warning — to extend its coverage, extend its time, or cancel it
before the original expiration — they issue a follow-up product with its own VTEC string
using action codes like CON (continued), EXT (extended), CAN (cancelled), or EXP (expired
naturally). The IEM tracks all of these and links them together by ETN, giving you the
complete lifecycle of every VTEC event in its archive rather than a pile of disconnected text
products.
7.1.1. What the ETN Tells You
The Event Tracking Number is unique per WFO, per phenomena/significance combination,
per calendar year. CTP’s twelfth tornado warning of 2024 is always CTP-TO.W-0012-2024,
regardless of which county it covered or which day it was issued. This means ETNs reset
on January 1 of each year, which has an important practical implication: when you are
searching across a year boundary, you need to specify the year explicitly. A search for “CTP
tornado warnings” without a year constraint will return results across all years, and the
ETN numbering starts over each time.
The maximum ETN issued by a WFO in a given year is a rough proxy for event frequency.
The IEM has a page at /vtec/maxetn.php that shows the highest ETN reached by each
WFO each year for any phenomena/significance type. If you want to know whether 2024
was an unusually active tornado warning year for a specific WFO, this is the fastest way to
check.
7.1.2. Phenomena and Significance Codes
The phenomena code is always two letters. The most common ones for weather enthusiasts:
TO (Tornado), SV (Severe Thunderstorm), FF (Flash Flood), FA (Areal Flood), FL (Flood),
WS (Winter Storm), WW (Winter Weather), BZ (Blizzard), IS (Ice Storm), ZR (Freezing Rain),
WI (Wind), SC (Small Craft), FW (Fire Weather), HU (Hurricane), TS (Tropical Storm), SS
(Storm Surge). The significance codes: W (Warning), A (Watch), Y (Advisory), S (Statement),
O (Outlook), N (Synopsis), F (Forecast).

Mastering the Mesonet 69
So SV.A is a Severe Thunderstorm Watch, WS.W is a Winter Storm Warning, FF.W is a Flash
Flood Warning, and ZR.Y is a Freezing Rain Advisory. Once you have internalized this
two-part structure, every IEM warning search interface becomes immediately legible.
7.2. The VTEC Browser
mesonet.agron.iastate.edu/vtec/
The VTEC Browser is the IEM’s event-level interface to the warning archive. It was
substantially rewritten in June 2025, so if you have used it before and things look different,
that is why. The interface asks you to select a WFO, a phenomena type, a significance, and
a year and event number, then loads a complete event record with six tabs: Help, Event
Info, Text Data, Interactive Map, Storm Reports, and List Events.
The power is in what each tab shows. Event Info gives you the structured metadata: issue
time, expiration time, the full list of counties/parishes/zones included in the product, the
polygon geometry if it is a storm-based warning, and the area in square kilometers. Text
Data shows you the full raw text of every product associated with that event — the initial
issuance and every subsequent update or cancellation in chronological order. Interactive
Map overlays the warning polygon on an archival radar composite at the time of issuance —
the IEM fetches the appropriate NEXRAD mosaic for the event time automatically. Storm
Reports shows all Local Storm Reports within the warning’s political coverage area (the
zone or county), and — for storm-based warnings — also filters the subset of LSRs that fall
within the actual warning polygon. List Events shows every event of the selected type and
year for that WFO, so you can browse and click through the season’s entire record.
The URL structure for a specific event is clean and bookmarkable: /vtec/YYYY-O-NEW-
KWFO-PH-SIG-NNNN where KWFO is the four-character WFO, PH is phenomena, SIG is
significance, and NNNN is the zero-padded ETN. For CTP’s twelfth tornado warning of
2024: /vtec/2024-O-NEW-KCTP-TO-W-0012. That URL takes you directly to that event
— no navigation required. This makes it easy to construct links to specific events when
discussing them on a forum.

| Mastering    | the Mesonet |        |     |     |     |     | 70  |
| ------------ | ----------- | ------ | --- | --- | --- | --- | --- |
| 7.3. Warning |             | Search |     |     |     |     |     |
mesonet.agron.iastate.edu/vtec/search.php
Where the VTEC Browser navigates event by event, the Warning Search is how you query
the archive at scale. You can filter by WFO, phenomena type, significance, date range,
and geography — either by selecting a state and county or by clicking a point on the map.
Results return a table of matching events with their issue time, expiration, ETN, and area,
| each row | linking directly | into | the | VTEC Browser |     | for that event. |     |
| -------- | ---------------- | ---- | --- | ------------ | --- | --------------- | --- |
The geographic point search is particularly powerful for personal-use questions: “how many
tornado warnings have covered my town in the last twenty years?” Click your location on
the map, set the date range and the phenomena filter, and the IEM returns every VTEC
event whose polygon or county/zone coverage included that point. This is the tool to reach
for when a forum discussion turns to “how warning-prone is this area” and you want to
| answer with | actual | data rather | than | anecdote. |     |     |     |
| ----------- | ------ | ----------- | ---- | --------- | --- | --- | --- |
The search also supports the reverse question: “show me everything CTP issued in June
2024.” Set the WFO to CTP, leave geography open, set the date range to June 2024, and
select all warning types. The result is a complete operational log of that month’s warning
| activity         | for that office, | sortable | by  | time, type, | or  | area. |     |
| ---------------- | ---------------- | -------- | --- | ----------- | --- | ----- | --- |
| 7.4. Storm-Based |                  | Warnings |     | and         | IEM | Cow   |     |
Before October 1, 2007, NWS warnings were issued for entire counties. A tornado warning
for Lancaster County, Pennsylvania covered all 946 square miles of it, regardless of where
the storm was actually tracking. On that date, the NWS switched to Storm-Based Warnings
(SBW)—polygonalareasdrawntocovertheactualstormtrack, typicallymuchsmallerthan
a county, updated in real time as the storm moves. The IEM archives both the pre-SBW
county-based warnings and the post-SBW polygon warnings, and the distinction matters
| enormously | for verification |     | work. |     |     |     |     |
| ---------- | ---------------- | --- | ----- | --- | --- | --- | --- |
IEM Cow (Convective Warning Verification) at mesonet.agron.iastate.edu/cow/ is the tool
built specifically to work with the SBW polygon archive. Its name is not an acronym —
it is just a cow. The tool lets you select a WFO, a date range, and a warning type, and it
computes verification statistics by comparing issued warning polygons against Local Storm
Reports.
The core metrics Cow produces: probability of detection (POD, the fraction of LSRs inside
a warning polygon), false alarm ratio (FAR, the fraction of warnings with no confirming

| Mastering | the Mesonet |     |     | 71  |
| --------- | ----------- | --- | --- | --- |
LSR inside the polygon), and critical success index (CSI, which combines both). It also
reports lead time — the median number of minutes between warning issuance and the first
confirming LSR — and the area-weighted coverage statistics. These are the same metrics
used in published NWS verification studies, so Cow results are directly comparable to the
| peer-reviewed | literature | on warning performance. |     |     |
| ------------- | ---------- | ----------------------- | --- | --- |
A few things to understand about interpreting Cow results. LSRs are the verification ground
truth, which means Cow inherits all the limitations of the LSR network: spotter coverage is
uneven, nighttime and rural events are underreported, and some event types (particularly
wind damage) are systematically under-LSR’d in low-population areas. A high FAR on
a rural WFO’s tornado warnings may reflect poor spotter coverage as much as it reflects
poor warning skill. Cow is an excellent tool for trend analysis and comparative studies, but
interpreting the absolute numbers requires contextual judgment about the LSR network’s
| completeness | in the area | being studied. |     |     |
| ------------ | ----------- | -------------- | --- | --- |
Cow works for dates after June 8, 2005, with the SBW polygon verification only meaningful
after October 2007 when polygons became the operational standard. For dates before
| October 2007, | the application | runs in county-based | mode. |     |
| ------------- | --------------- | -------------------- | ----- | --- |
ThecompaniontoolIEMRaccoonatmesonet.agron.iastate.edu/raccoon/generatesMicrosoft
PowerPoint presentations of storm-based warning records for a WFO and radar site, useful
for training materials or post-event briefings where you want visual documentation of the
| full warning | sequence. |         |     |     |
| ------------ | --------- | ------- | --- | --- |
| 7.5. Local   | Storm     | Reports |     |     |
mesonet.agron.iastate.edu/lsr/
Local Storm Reports are the NWS’s real-time field observations of weather impacts: tornado
touchdowns and paths, hail size and location, measured or estimated wind gusts, wind
damage, flooding, waterspouts, and other significant phenomena. They are issued by WFO
meteorologists and their spotter networks throughout an event and archived by the IEM in
real time.
TheLSRAppat/lsr/letsyouquerythearchivebyWFO,daterange,eventtype,magnitude
thresholds(minimumhailsize, minimumwindspeed), andgeographicextent. Resultsdisplay
on an interactive map and in a sortable table, with each report showing the reporting source
(trained spotter, law enforcement, public, emergency management, etc.), the time, the
| location, | and any magnitude | values. |     |     |
| --------- | ----------------- | ------- | --- | --- |

| Mastering | the Mesonet |     |     | 72  |
| --------- | ----------- | --- | --- | --- |
For archived LSRs as shapefiles — useful for GIS analysis — the download portal is at
/request/gis/lsrs.phtml, which covers the archive back to 2003. For the past 24 hours, a
live shapefile, CSV, and GeoJSON are always available at static URLs in the IEM data
directory:
| • Shapefile: | /data/gis/shape/4326/us/lsr_24hour.zip     |     |     |     |
| ------------ | ------------------------------------------ | --- | --- | --- |
| • CSV:       | /data/gis/shape/4326/us/lsr_24hour.csv     |     |     |     |
| • GeoJSON:   | /data/gis/shape/4326/us/lsr_24hour.geojson |     |     |     |
These files update every five minutes and are the fastest way to get a current snapshot of
| field reports | during an active | event. |     |     |
| ------------- | ---------------- | ------ | --- | --- |
What LSRs are not: they are not a complete record of impacts. They reflect what
spotters and observers happened to report, which means sparsely populated areas, events
that happen at night, and event types that do not produce easily visible damage are all
systematically underrepresented. The IEM’s LSR Snowfall Analysis (Autoplot q=207) is
one of the more instructive examples of this gap — the snowfall LSR map for any given
winter storm will show dense reporting near population centers and conspicuous holes in
rural areas where snowfall may have been just as heavy but no one submitted a report.
| 7.6. The | Text Archive |     |     |     |
| -------- | ------------ | --- | --- | --- |
mesonet.agron.iastate.edu/nws/text.php
The IEM archives essentially the full NOAAPORT text product feed — every text product
transmitted by the NWS, going back to the mid-2000s for most product types. This
includes Area Forecast Discussions (AFDs), Public Information Statements, Special Weather
Statements (SPS), CLI daily climate summaries, CF6 monthly climate reports, hydro
products, terminal forecasts, and the full body of watch and warning text. If the NWS
transmitted it over NOAAPORT, there is a high probability the IEM has it.
| 7.6.1. The | AFOS/AWIPS | Identifier | System |     |
| ---------- | ---------- | ---------- | ------ | --- |
Every text product in the archive has an AFOS/AWIPS identifier — a 3 to 6 character code
that uniquely identifies the product type and issuing center. The pattern is TTSSSS where
the first two or three characters identify the product type and the remaining characters
identify the WFO or center. Examples: AFDCTP is the Area Forecast Discussion from State
College (CTP). TORDMX is a Tornado Warning from Des Moines (DMX). CFWCTP is a Coastal
Flood Watch from CTP. RWRKCI is the Regional Weather Roundup from Kansas City.

| Mastering | the Mesonet |     |     |     | 73  |
| --------- | ----------- | --- | --- | --- | --- |
The IEM assigns its own longer internal identifier to each product in the format
YYYYmmddHHMM-CCCC-TTAAII-AFOSID, where the timestamp is UTC, CCCC is the issuing
center, TTAAII is the WMO header, and AFOSID is the AFOS identifier. You can paste
this full identifier directly into the IEM search box and land immediately on that product —
useful when someone shares a specific product ID and you want to pull it up quickly.
| 7.6.2. The | AFOS | Product Finder |     |     |     |
| ---------- | ---- | -------------- | --- | --- | --- |
The primary interface for text retrieval is the AFOS Product Finder at mesonet.agron.ias-
tate.edu/wx/afos/. You enter an AFOS identifier and optionally a date range, and it returns
all matching products in reverse chronological order, each one displaying the full raw text.
For AFD research — reading what CTP forecasters were thinking during a specific event
— this is the tool. Enter AFDCTP, set a date range around the event, and read every AFD
| issued during | the period. |     |     |     |     |
| ------------- | ----------- | --- | --- | --- | --- |
The bulk retrieval API at /cgi-bin/afos/retrieve.py accepts date-range queries by
AWIPS ID and returns the raw text, making it straightforward to collect a full season’s
AFDs for text analysis without clicking through hundreds of individual products.
The List Products by WFO page at /wx/afos/list.phtml shows all products issued by a
given WFO on a given date, organized by product type. If you know the date but not which
| specific products | you      | want, this is | the browsable | starting point. |     |
| ----------------- | -------- | ------------- | ------------- | --------------- | --- |
| 7.6.3. Area       | Forecast | Discussions   |               |                 |     |
AFDs deserve special mention because they are arguably the most valuable product in
the text archive for weather enthusiasts trying to understand not just what happened but
why. The AFD is where the forecaster exposes their reasoning — the synoptic pattern they
are tracking, the model guidance they trust and distrust, the mesoscale features they are
watching, the uncertainty in the forecast, and the specific thresholds that would trigger a
warning or advisory upgrade. Reading AFDs for an event you lived through is the closest
| thing to sitting | in the | forecast office | with the | meteorologist. |     |
| ---------------- | ------ | --------------- | -------- | -------------- | --- |
For the Pennsylvania forecast region, CTP’s AFDs at AFDCTP are the primary product.
Events that spanned multiple WFO boundaries — a major nor’easter, a line of severe
thunderstorms moving east from the Ohio Valley — are illuminated by reading adjacent
office AFDs alongside CTP’s: AFDPHI (Mount Holly, NJ), AFDPBZ (Pittsburgh), AFDLWX
(Baltimore/Washington), AFDBGM (Binghamton). The AFD record for the most operationally
interesting storms in the mid-Atlantic region is one of the richer archives of applied mesoscale
| reasoning | that exists | in any publicly | accessible | form. |     |
| --------- | ----------- | --------------- | ---------- | ----- | --- |

Mastering the Mesonet 74
7.6.4. CLI and CF6: Daily Climate Products
Two text product types are particularly useful for historical climate research. The CLI
(Climate Report) is issued daily by each WFO for its primary ASOS stations and summarizes
the previous day’s temperature, precipitation, and snowfall against the normal and record
values. The IEM parses these and provides interactive tables and maps: the CLI interactive
map is at /nws/climap.php and the text table at /nws/clitable.php. For any ASOS station
that a WFO designates as a climate site, the CLI provides the official daily climate summary
including the departure from normal and the record comparison.
The CF6 (Monthly/Daily Climate Data) is the monthly version, summarizing the calendar
month’s climate statistics at each climate site. The IEM parses CF6 products and makes
them available in tabular form at /nws/cf6table.php. For Harrisburg (KMDT), the CF6
archive going back through the IEM’s text product archive gives you the official monthly
climate summary — maximum and minimum temperature, heating and cooling degree days,
precipitation total and departure, snowfall total — in a consistent format across years.
7.7. SPC Products
The NWS Data section gives substantial coverage to Storm Prediction Center products, and
for weather enthusiasts focused on severe weather climatology, these are essential.
Convective outlooks are archived in shapefile format at /request/gis/spc_outlooks.phtml.
The outlook search by point at /nws/spc_outlook_search/ answers the question “when was
my location last under a Moderate or High risk?” — which is a surprisingly hard question
to answer from any other free source. Set your location, select the outlook category, and the
IEM returns every instance going back through the archived record.
Mesoscale Convective Discussions (MCDs) are available as shapefiles at /re-
quest/gis/spc_mcd.phtml. MCDs are the products SPC issues when conditions are evolving
and they want to flag forecasters and the public ahead of a potential watch. Reading the
MCD text alongside the subsequent watch issuance (or non-issuance, when the situation
does not materialize) gives you the SPC’s real-time situational awareness for a given event.
SPC Watches are archived at /request/gis/spc_watch.phtml and displayed interactively at
/GIS/apps/rview/watch.phtml. The watch archive includes the polygon geometry, the issue
and expiration times, and the watch type (Tornado Watch, Severe Thunderstorm Watch,
PDS Watch). A listing of all SPC watches by year with their ETNs is at /nws/watches.php,
and PDS watches specifically are listed at /nws/pds_watches.php.

| Mastering | the Mesonet |     |     |     |     |     |     |     |     | 75  |
| --------- | ----------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
The WPC (Weather Prediction Center) has analogous products for the precipita-
tion side of operations. WPC Mesoscale Precipitation Discussions (MPDs) are at
/request/gis/wpc_mpd.phtml, and the WPC outlook search by point at /nws/wpc_out-
look_search/ answers the equivalent question for excessive rainfall outlooks.
| 7.8. Special   |     | Weather |        | Statements |          |      | and Warning |              | Tags |     |
| -------------- | --- | ------- | ------ | ---------- | -------- | ---- | ----------- | ------------ | ---- | --- |
| Two additional |     | tools   | on the | NWS        | Mainpage | that | are easy    | to overlook: |      |     |
Special Weather Statement (SPS) search at /nws/sps_search/ lets you find SPSs
by point, which is useful because SPSs are not VTEC-coded and therefore not searchable
through the main warning archive tools. SPSs cover significant weather that does not meet
warning criteria — an approaching squall line, an area of locally dense fog, a wind event
that is significant but below advisory thresholds. They often contain the most operationally
| useful text | for | understanding |     | borderline | events. |     |     |     |     |     |
| ----------- | --- | ------------- | --- | ---------- | ------- | --- | --- | --- | --- | --- |
SVR and TOR warning tags at /nws/list_tags.php lists the damage indicator and
tornado rating tags embedded in Severe Thunderstorm and Tornado Warnings by WFO and
year. When the NWS began tagging tornado warnings with the expected maximum EF
scale, hail warnings with the maximum expected hail size, and severe thunderstorm warnings
with the maximum expected wind speed, the IEM began archiving those tags. This page
lets you browse what tags a specific WFO has used, which provides a quick proxy for event
| severity          | distribution |     | across   | years. |        |     |     |     |     |     |
| ----------------- | ------------ | --- | -------- | ------ | ------ | --- | --- | --- | --- | --- |
| 7.9. Verification |              |     | Autoplot |        | Charts |     |     |     |     |     |
Several Autoplot charts work directly with the VTEC archive for warning climatology
analysis:
q=44 — Accumulated WFO Watch/Warning/Advisory totals. Plots the cumulative count
of a specific warning type by WFO over a season or date range. Useful for comparing how
| active a | particular | warning |     | type | has been | relative | to prior | years. |     |     |
| -------- | ---------- | ------- | --- | ---- | -------- | -------- | -------- | ------ | --- | --- |
q=52 — Warning Gantt chart. Shows the timeline of all warnings of a given type from a
WFO across a season, one row per event, colored by phenomena. The Gantt format makes
patterns in warning clustering and seasonal distribution immediately visible.

| Mastering | the Mesonet |     |     |     | 76  |
| --------- | ----------- | --- | --- | --- | --- |
q=92 — Days since last VTEC product. A map showing, for each WFO, how many days
have elapsed since a specific warning type was last issued. Useful during quiet periods
to contextualize how long the current stretch of inactivity is relative to the climatological
distribution.
q=109 — Number of VTEC events by WFO. A choropleth map of warning counts by
WFO for any selected type and time period — the fastest way to visualize the geographic
| distribution | of warning | activity | across | the country. |     |
| ------------ | ---------- | -------- | ------ | ------------ | --- |
q=211 — Warning lead time distribution. A histogram of lead times (minutes between
issuanceandfirstconfirmingLSR)fortornadoorseverethunderstormwarnings,byWFOand
year. This is the visualization most directly connected to the Cow verification statistics.
| 7.10. | River and | Hydrology |     | Products |     |
| ----- | --------- | --------- | --- | -------- | --- |
The NWS Mainpage has a hydrology section that is often overlooked by severe weather-
| focused | users but is | valuable | during | flood events. |     |
| ------- | ------------ | -------- | ------ | ------------- | --- |
The River Forecast Point Monitor at mesonet.agron.iastate.edu/river/ summarizes
Flood Stage Forecasts (FLS statements) by river and by WFO or state. It provides a tabular
view of all river forecast points, their current stage versus action/flood/major/record stage,
and the trend. For a flooding event, this is the IEM equivalent of the NWS’s Advanced
Hydrologic Prediction Service (AHPS) viewer — organized differently but drawing from the
| same FLS | product archive. |     |     |     |     |
| -------- | ---------------- | --- | --- | --- | --- |
HML (Hydrometric Message Language) data is available as archived processed
products at /request/hml.php, giving you the numeric river forecast data behind the FLS
textproducts. Autoplotq=160renderstheseasinteractiveplotsofforecastedversusobserved
stage at any river forecast point — the same view the hydrologist at the WFO is looking at
| when they | issue a flood | statement. |     |     |     |
| --------- | ------------- | ---------- | --- | --- | --- |
| 7.11.     | What to       | Watch      | Out | For |     |
Pre-2005 warnings lack VTEC. The NWS began operational VTEC in 2005. Products
before that date are in the text archive but have no structured VTEC metadata, meaning
the Browser and Cow tools do not work with them. For historical warning research before

| Mastering | the Mesonet |     |     |     |     | 77  |
| --------- | ----------- | --- | --- | --- | --- | --- |
2005, you are working with raw text files and NCEI’s Storm Events Database, not IEM’s
| structured | tools. |     |     |     |     |     |
| ---------- | ------ | --- | --- | --- | --- | --- |
Pre-2007 polygon geometry. Storm-Based Warning polygons became operational in
October 2007. Before that date, even post-VTEC warnings are county-based, and the
polygon geometry in the VTEC Browser will show the county boundary rather than a
storm-tracking polygon. Cow treats this correctly — it runs in county mode for pre-October
2007 dates automatically — but be aware of the shift when working across that boundary.
ETN resets and year-boundary searches. As noted above, ETNs reset on January
1. A search that spans December into January will return warning events with ETNs that
restart at 1 in the new year. This is expected behavior, not a data error, but it can confuse
| automated | analysis | if you are | not handling | it explicitly. |     |     |
| --------- | -------- | ---------- | ------------ | -------------- | --- | --- |
LSR incompleteness as a verification floor. Because Cow and the VTEC Browser both
use LSRs as the ground truth for verification, every caveat about LSR completeness applies
to all derived statistics. An unusually high FAR for a specific WFO or year may reflect poor
spotter coverage as much as poor warning accuracy. Context always matters.
The text archive has product type gaps. Not every product type has been archived
continuously since 2005. Some product categories have gaps, particularly for the period
2005–2008 during the IEM’s early text archiving work. If you cannot find a specific product
that you know was issued, check the IEM news archive for notes about that product type’s
| ingestion | history. |                 |     |                |           |     |
| --------- | -------- | --------------- | --- | -------------- | --------- | --- |
| 7.12.     | Workflow | 3 — Researching |     | a Past Warning | Event End | to  |
End
The question: On a specific date, a Tornado Warning was issued for Dauphin County,
Pennsylvania. What was the lead time? What did the polygon look like? Were there any
| storm reports? | What                                              | did the warning | text | say? |     |     |
| -------------- | ------------------------------------------------- | --------------- | ---- | ---- | --- | --- |
| Start here:    | https://mesonet.agron.iastate.edu/vtec/search.php |                 |      |      |     |     |
The VTEC search page lets you find NWS warnings by county or by geographic point,
filtered by phenomena type and date range. To find a Tornado Warning for Dauphin County,
PA: select Pennsylvania from the state menu, select Dauphin County from the county menu,
set the phenomena to Tornado Warning (TO.W), and set your date range. Submit.

| Mastering | the Mesonet |     |     |     |     | 78  |
| --------- | ----------- | --- | --- | --- | --- | --- |
The results table shows every Tornado Warning that touched Dauphin County within your
date range — each row shows the issuing WFO (PHI or CTP for central Pennsylvania), the
event date, the VTEC Event Tracking Number (ETN), the issuance time, the expiration
time, and whether it was a storm-based warning with a polygon. Click the event link to go
| to the individual | event | page. |     |     |     |     |
| ----------------- | ----- | ----- | --- | --- | --- | --- |
The event page is where the full picture assembles. At the top you get the warning metadata:
issue time, expire time, phenomena and significance codes, WFO, ETN. Below that is the
storm-based warning polygon rendered on a map, showing exactly what area was under the
warning. Below the map is the raw NWS text product — the warning as it was originally
| transmitted, | in full, with | the original | VTEC line | intact. |     |     |
| ------------ | ------------- | ------------ | --------- | ------- | --- | --- |
From the event page, two additional tools are one click away. The IEM Cow link (at
https://mesonet.agron.iastate.edu/cow/) provides verification statistics for that warning —
whether a storm report fell within the polygon, what the lead time was to any confirmed
tornado, and how the warning’s performance compares to the WFO’s averages. The Local
Storm Reports link takes you to all LSRs within a user-specified buffer radius of the warning
polygon around the time of the event, giving you the observed tornado touchdowns, hail
| reports, | or wind damage | reports that | the warning | was issued | for. |     |
| -------- | -------------- | ------------ | ----------- | ---------- | ---- | --- |
One important constraint to know before you start: the IEM VTEC archive has no known
gaps since November 12, 2005. Before that date, coverage depends on what was available
for retroactive assignment. Tornado and Severe Thunderstorm Warnings before 2005 are
partially present — IEM retroactively assigned VTEC identifiers using available data — but
the completeness of pre-2005 warning events is variable and should not be assumed complete
| for any      | specific event. |           |     |                                 |     |     |
| ------------ | --------------- | --------- | --- | ------------------------------- | --- | --- |
| 7.13.        | Key URLs        | — Chapter | 7   |                                 |     |     |
| Page         |                 |           |     | URL                             |     |     |
| NWS Mainpage |                 |           |     | mesonet.agron.iastate.edu/nws/  |     |     |
| VTEC         | Browser         |           |     | mesonet.agron.iastate.edu/vtec/ |     |     |
Warning Search by Point/County mesonet.agron.iastate.edu/vtec/search.php
| IEM Cow | (SBW Verification) |     |     | mesonet.agron.iastate.edu/cow/ |     |     |
| ------- | ------------------ | --- | --- | ------------------------------ | --- | --- |
IEM Raccoon (SBW PowerPoints) mesonet.agron.iastate.edu/raccoon/
| Local Storm | Report App |     |     | mesonet.agron.iastate.edu/lsr/ |     |     |
| ----------- | ---------- | --- | --- | ------------------------------ | --- | --- |
| LSR Archive | Download   |     |     | mesonet.agron.iastate.edu/re-  |     |     |
quest/gis/lsrs.phtml
Text Archives Mainpage mesonet.agron.iastate.edu/nws/text.php

| Mastering | the Mesonet    |      |                                    | 79  |
| --------- | -------------- | ---- | ---------------------------------- | --- |
| Page      |                |      | URL                                |     |
| AFOS      | Product Finder |      | mesonet.agron.iastate.edu/wx/afos/ |     |
| Products  | by WFO by      | Date | mesonet.agron.ias-                 |     |
tate.edu/wx/afos/list.phtml
| AFOS | Bulk Retrieve API |     | mesonet.agron.iastate.edu/cgi- |     |
| ---- | ----------------- | --- | ------------------------------ | --- |
bin/afos/retrieve.py?help
| CLI Interactive | Map |     | mesonet.agron.iastate.edu/nws/climap.php |     |
| --------------- | --- | --- | ---------------------------------------- | --- |
CF6 Monthly Climate Table mesonet.agron.iastate.edu/nws/cf6table.php
SPC Outlook Search by Point mesonet.agron.iastate.edu/nws/spc_out-
look_search/
| SPC Outlook | / MCD | Shapefile | mesonet.agron.iastate.edu/re- |     |
| ----------- | ----- | --------- | ----------------------------- | --- |
quest/gis/spc_outlooks.phtml
| SPC Watch | Shapefile |     | mesonet.agron.iastate.edu/re- |     |
| --------- | --------- | --- | ----------------------------- | --- |
quest/gis/spc_watch.phtml
SPC Watches by Year mesonet.agron.iastate.edu/nws/watches.php
| SPC PDS | Watch Listing |     | mesonet.agron.ias- |     |
| ------- | ------------- | --- | ------------------ | --- |
tate.edu/nws/pds_watches.php
| SPC MCD | Shapefile |     | mesonet.agron.iastate.edu/re- |     |
| ------- | --------- | --- | ----------------------------- | --- |
quest/gis/spc_mcd.phtml
| WPC MPD | Shapefile |     | mesonet.agron.iastate.edu/re- |     |
| ------- | --------- | --- | ----------------------------- | --- |
quest/gis/wpc_mpd.phtml
WPC Outlook Search by Point mesonet.agron.iastate.edu/nws/wpc_out-
look_search/
SPS Search by Point mesonet.agron.iastate.edu/nws/sps_search/
| SVR/TOR | Warning Tags | by WFO | mesonet.agron.ias- |     |
| ------- | ------------ | ------ | ------------------ | --- |
tate.edu/nws/list_tags.php
Max ETN by WFO by Year mesonet.agron.iastate.edu/vtec/maxetn.php
| VTEC | Events by Year | Table | mesonet.agron.ias- |     |
| ---- | -------------- | ----- | ------------------ | --- |
tate.edu/vtec/yearly_counts.php
Tornado/FF Emergency Listing mesonet.agron.iastate.edu/vtec/emergen-
cies.php
| PDS Warning | Listing           |      | mesonet.agron.iastate.edu/vtec/pds.php |     |
| ----------- | ----------------- | ---- | -------------------------------------- | --- |
| Warning     | Polygons (current | WWA) | mesonet.agron.iastate.edu/re-          |     |
quest/gis/watchwarn.phtml
| River Forecast | Monitor  |     | mesonet.agron.iastate.edu/river/          |     |
| -------------- | -------- | --- | ----------------------------------------- | --- |
| HML Data       | Download |     | mesonet.agron.iastate.edu/request/hml.php |     |
HML Forecast/Obs Plot (q=160) mesonet.agron.iastate.edu/plot-
ting/auto/?q=160
Autoplot — Warning Gantt (q=52) mesonet.agron.iastate.edu/plot-
ting/auto/?q=52

Mastering the Mesonet 80
Page URL
Autoplot — VTEC Counts Map (q=109) mesonet.agron.iastate.edu/plot-
ting/auto/?q=109
Autoplot — Days Since WWA (q=92) mesonet.agron.iastate.edu/plot-
ting/auto/?q=92
Autoplot — Accumulated WWA (q=44) mesonet.agron.iastate.edu/plot-
ting/auto/?q=44

|      |       | Part | III.   |             |
| ---- | ----- | ---- | ------ | ----------- |
| Part | III — | Data | Access | and Quality |
81

8. Chapter 8 — Downloading Data: Every
Portal Explained
At some point, browsing the IEM’s interactive tools stops being enough. You want the
numbers — a CSV you can open in Python or Excel, a time series you can run statistics
on, a dataset you can join against something else. The IEM has more download pathways
than almost any free weather data source, which is its strength and also its main source of
confusion. Knowing which endpoint to use for a given task is not always obvious, because
several of them overlap, several of them are labeled for something slightly different from
what they actually do, and a few of the most powerful ones have no front-end interface at
all.
This chapter provides a working taxonomy. The goal is not to document every parameter of
every endpoint — the IEM’s own help pages already do that, and they are genuinely good.
The goal is to give you a mental model so that when you have a specific data need, you
immediately know which pathway to reach for and why.
8.1. The Four Tiers
The IEM’s download infrastructure divides into four tiers, each with a different character:
Tier 1 — UI download portals. These are web forms — select a station, choose a date
range, pick your variables, click Get Data. No programming required. The output is a CSV
or Excel file that downloads to your browser. Most IEM users never leave this tier.
Tier 2 — CGI/bulk services. These are the backends that power the UI portals, exposed
directly as scriptable HTTP endpoints. They take the same parameters as the web forms,
but via URL query strings instead of form fields. You can call them from Python, R, curl,
or anything that makes HTTP requests. Output is CSV. This is where serious workflow
automation starts.
Tier 3 — JSON/GeoJSON ad-hoc services. A large collection of JSON endpoints,
most serving structured metadata, current conditions, or event-based data. Not all of these
82

| Mastering | the Mesonet |     |     |     |     | 83  |
| --------- | ----------- | --- | --- | --- | --- | --- |
have UI wrappers. Many are used internally by IEM applications and have never been
| prominently | advertised, | but they | all have | help pages | at ?help=. |     |
| ----------- | ----------- | -------- | -------- | ---------- | ---------- | --- |
Tier 4 — API v1. The formal REST API, built on FastAPI with Swagger documentation
at mesonet.agron.iastate.edu/api/1/docs. Designed for smaller, fast requests — MOS data,
station metadata, VTEC events, soundings. Returns JSON Table Schema responses. This is
the cleanest, most stable interface, but it covers a narrower range of datasets than the CGI
tier.
The IEM’s own API documentation page is refreshingly honest about the hierarchy. It notes
the CGI services are “2000s era” and not amenable to sub-second response times, and it
points to Tier 4 for anything that needs to run fast. That honesty is useful: if you need a
year of hourly ASOS data, you want Tier 2. When you need the current MOS guidance for
| a station,             | you want | Tier 4.     |          |         |     |     |
| ---------------------- | -------- | ----------- | -------- | ------- | --- | --- |
| 8.2. Tier              | 1: The   | UI Download |          | Portals |     |     |
| 8.2.1. ASOS/AWOS/METAR |          |             | Download |         |     |     |
mesonet.agron.iastate.edu/request/download.phtml
This is the portal most people mean when they say they downloaded data from the IEM.
It covers the global ASOS/AWOS/METAR archive — airport weather stations across the
entire world, not just the US — with hourly and special observations going back in some
cases to 1900, though the continuous reliable record for most US stations starts in the early
1970s. The UI walks you through seven steps: network selection, station selection, variable
selection, date range, timezone, output format, and report type filtering.
Thevariablelistonthisportaliscomprehensiveandworthreadingonceinfull. Thestandard
set is temperature in Fahrenheit or Celsius, dew point, relative humidity, wind direction
and speed, altimeter and sea level pressure, 1-hour precipitation, visibility, wind gusts, sky
coverage at up to four levels with cloud base heights, present weather codes, ice accretion at
1/3/6 hours, peak wind gust with direction and time (from the PK WND METAR remark),
snow depth, and the raw METAR string. All of these are available simultaneously with the
| “All Available”         | option, | or you     | can select | a subset. |           |     |
| ----------------------- | ------- | ---------- | ---------- | --------- | --------- | --- |
| A few variable-specific |         | notes that | matter     | for real  | analysis: |     |
Precipitation (p01i) is the one-hour incremental bucket reading — the amount that fell
in the hour preceding the observation time. It is not a daily total. Summing p01i across
24 hours gives you a daily total, but the effective reset timing can vary slightly by station,

Mastering the Mesonet 84
and missing observations can create holes that are not always obvious in a simple sum. The
trace precipitation convention — 0.0001 inches — is used when precipitation is reported as
Trace in the original METAR.
Sky coverage (skyc1 through skyc4) uses METAR codes: CLR, FEW, SCT, BKN, OVC,
VV (vertical visibility). The corresponding height fields (skyl1–skyl4) are the cloud base
altitudes in feet AGL. These are the raw decoded values from the METAR remark, not
derived ceiling values — if you want a ceiling field, you need to derive it yourself as the
lowest BKN or OVC layer.
Present weather codes (wxcodes) are space-separated strings of METAR weather codes:
RA (rain), SN (snow), FG (fog), BR (mist), TS (thunderstorm), FZRA (freezing rain), PL
(ice pellets), GR (hail), and their intensity modifiers (+, -) and descriptors (MI, BC, DR,
BL, SH, TS, FZ, PR). For precipitation-type analysis, these codes are the closest thing to
ground truth in the archive, combining automated sensing with human observation when
available.
Report type filtering (Step 6 in the UI) is worth paying attention to. The options are
MADISHFMETAR/5-MinuteASOS, Routine/Once Hourly, and Specials. Formost analysis,
you want both Routine and Specials — specials are the intermediate observations triggered
by significant changes in conditions (a rapid temperature drop, a wind shift, the onset of
precipitation). Excluding specials gives you a cleaner hourly record but loses the precise
timing of significant weather events. The 5-Minute ASOS data is a separate product from
MADIS and covers US stations from approximately 2000 onward; it is not available for
international stations.
The aggregate request limit is 1,000 station-years. For context, that means one station for
1,000 years, or 100 stations for 10 years, or 1,000 stations for one year. This is a generous
limit but it is enforced, so queries asking for many stations over long periods will fail if they
exceed it.
8.2.2. ASOS 1-Minute Download
mesonet.agron.iastate.edu/request/asos/1min.phtml
Separate from the standard ASOS portal, the 1-minute data archive covers US ASOS
stations from approximately 2000 to present. At this resolution, you can see the actual
minute-by-minute wind, temperature, and precipitation evolution within an event. For
post-chase analysis, front-passage timing, or extracting the exact minute of a convective peak
wind observation, this is the dataset. The Iowa AWOS 1-minute archive covers a different
set of stations (Iowa AWOS only) for the period 1995–2011 and is at a separate portal at
/request/awos/1min.php.

| Mastering   | the Mesonet |          |     |     | 85  |
| ----------- | ----------- | -------- | --- | --- | --- |
| 8.2.3. COOP | / Climodat  | Download |     |     |     |
mesonet.agron.iastate.edu/request/coop/fe.phtml
The Climodat download portal serves the long-period daily climate record from the NWS
COOP network and the IEM’s processed Climodat stations. This is the dataset for any
analysis that needs daily max/min temperature, precipitation, and snowfall going back
decades. Climodat data at some stations extends to the 1880s. The download provides the
IEM’sQC’dandprocesseddailyvalues,notrawCOOPobserversubmissions—stationmoves,
missing observations, and some systematic biases have been addressed in the processing.
The companion portal for truly raw COOP observations — the daily reports as submitted
by observers before IEM processing — is at /request/coop/obs-fe.phtml. If you are doing
your own QC or want to understand exactly what the observer reported (including the
observation time, which is essential for TOBS-aware analysis), use the raw portal. If you
want the IEM’s processed daily climatology, with missing values filled where applicable and
| QC already   | applied,     | use the Climodat | portal.  |            |     |
| ------------ | ------------ | ---------------- | -------- | ---------- | --- |
| 8.2.4. Daily | Observations | (IEM             | Computed | Summaries) |     |
mesonet.agron.iastate.edu/request/daily.phtml
Covered in Chapter 6 as a dataset — this is the UI wrapper for the IEM’s computed daily
summariesacrossallnetworks. Onerowperstationperday,withtheIEM’sderivedmax/min
temperature, precipitation, peak wind, and other variables. The network selector is the key:
choose PA_ASOS for Pennsylvania airport stations, PACLIMATE for Pennsylvania COOP
| climate stations, | and      | so on. |     |     |     |
| ----------------- | -------- | ------ | --- | --- | --- |
| 8.2.5. RWIS       | Download |        |     |     |     |
mesonet.agron.iastate.edu/request/rwis/fe.phtml
Roadway Weather Information System observations — atmospheric variables plus up to
four pavement temperature sensors plus subsurface temperature and pavement condition
codes. Separate portals exist for the soil data at /request/rwis/soil.phtml and traffic data at
/request/rwis/traffic.phtml.

| Mastering  | the Mesonet |      |          |     |     | 86  |
| ---------- | ----------- | ---- | -------- | --- | --- | --- |
| 8.2.6. DCP | /           | HADS | Download |     |     |     |
mesonet.agron.iastate.edu/request/dcp/fe.phtml
River gauge and DCP station data, organized by SHEF variable codes. If you want river
stage or discharge data from the IEM’s DCP archive rather than USGS, this is the portal.
The SHEF variable selection is extensive — the HADS CGI endpoint also handles this
dataset programmatically.
| 8.2.7. Other | Network |     | Portals |     |     |     |
| ------------ | ------- | --- | ------- | --- | --- | --- |
Additional UI download portals cover USCRN (/request/uscrn.php), Hourly Precipitation
(/request/asos/hourlyprecip.phtml),andTAFforecasts(/request/taf.php). TheTemperature
and Winds Aloft portal at /request/tempwind_aloft.php gives you the NWS winds aloft
| forecast data | for | any station | and | date range. |     |     |
| ------------- | --- | ----------- | --- | ----------- | --- | --- |
| 8.3. Tier     | 2:  | CGI/Bulk    |     | Services    |     |     |
The CGI services are the scriptable equivalents of the UI portals, all documented at
mesonet.agron.iastate.edu/api/. Each one has a ?help parameter that returns the full
parameter documentation. These are the endpoints to use when you are automating a
workflow, running a pipeline, or pulling data for more stations or longer periods than you
| want to click | through | in  | a form. |     |     |     |
| ------------- | ------- | --- | ------- | --- | --- | --- |
LIGHTBULB Non-Programmer’s Bridge — Using Tier 2 and Tier 3 Without Code
The CGI and JSON endpoints in Tiers 2 and 3 look like code, but you do not need to
| be a programmer |     | to  | use them. | A URL like: |     |     |
| --------------- | --- | --- | --------- | ----------- | --- | --- |
https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=MDT&year1=2023&month1=1&day1=1&year2=2023&month2=12&day2=31&data=tmpf&format=comma
is just a web address with instructions attached. Paste it directly into Chrome, Firefox,
or Edge and hit Enter — your browser acts as the API client and downloads the CSV
| file to your | desktop. |     | No Python, | no terminal, | no setup required. |     |
| ------------ | -------- | --- | ---------- | ------------ | ------------------ | --- |
If you later decide to automate repeated downloads, these three lines of Python are all
| you need | to start: |     |     |     |     |     |
| -------- | --------- | --- | --- | --- | --- | --- |
| import   | requests  |     |     |     |     |     |
url = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=MDT&year1=2023&month1=1&day1=1&year2=2023&month2=12&day2=31&data=tmpf&format=comma"
| open("mdt_2023.csv", |     |     | "wb").write(requests.get(url).content) |     |     |     |
| -------------------- | --- | --- | -------------------------------------- | --- | --- | --- |

| Mastering | the | Mesonet |     |     |     |     |     | 87  |
| --------- | --- | ------- | --- | --- | --- | --- | --- | --- |
That is the entire download. You do not need to understand it to use it — copy, paste,
| change   | the       | station | ID and | dates,      | run | it.        |     |     |
| -------- | --------- | ------- | ------ | ----------- | --- | ---------- | --- | --- |
| The most | important |         | ones   | for weather |     | hobbyists: |     |     |
/cgi-bin/request/asos.py — the backend for the ASOS download portal, accepting
all the same parameters as the UI form via query string. The help page at /cgi-
bin/request/asos.py?help documents every parameter. A typical programmatic call
| for a year | of  | Harrisburg | hourly |     | data in | UTC looks | like: |     |
| ---------- | --- | ---------- | ------ | --- | ------- | --------- | ----- | --- |
https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?
station=MDT&
data=tmpf&data=dwpf&data=sknt&data=drct&data=p01i&data=vsby&
year1=2024&month1=1&day1=1&
year2=2025&month2=1&day2=1&
tz=UTC&
format=onlycomma&
latlon=no&
missing=M&
trace=T&
direct=no
The data= parameter can be repeated for multiple variables, or data=all returns everything.
Theformat=onlycommaoptionreturnscleanCSVwithoutthedebugheaders; format=comma
| includes | headers | that | explain | the | data | but are | messier to parse. |     |
| -------- | ------- | ---- | ------- | --- | ---- | ------- | ----------------- | --- |
/cgi-bin/request/coop.py — IEM Climodat (COOP) data programmatically. Accepts
network,station,daterange,andvariableselection. TheequivalentoftheClimodatdownload
| portal as | a callable | endpoint. |     |     |     |     |     |     |
| --------- | ---------- | --------- | --- | --- | --- | --- | --- | --- |
/cgi-bin/request/daily.py — IEM computed daily summaries for any network, program-
matically.
/cgi-bin/request/hads.py — HADS/DCP/SHEF data, accepting SHEF variable codes.
| This is | the scriptable |     | path | to river | gauge | data. |     |     |
| ------- | -------------- | --- | ---- | -------- | ----- | ----- | --- | --- |
/cgi-bin/request/hourlyprecip.py — hourly precipitation data specifically, useful when
you want the precipitation record without all the other ASOS variables.
/cgi-bin/request/raob.py — RAOB sounding data programmatically, equivalent to the
| archive | portal | covered | in Chapter |     | 6.  |     |     |     |
| ------- | ------ | ------- | ---------- | --- | --- | --- | --- | --- |
/cgi-bin/request/gis/watchwarn.py — NWS watch/warning/advisory polygons as
shapefile output, parameterized by date range, WFO, and phenomena type. The
programmatic path to the warning archive that powers much of Chapter 7.

Mastering the Mesonet 88
/cgi-bin/request/mos.py — MOS data as CSV for any station, model, and date range.
The full CGI service list on the API page also includes endpoints for RWIS, SCAN, USCRN,
NLAE flux, Iowa soil moisture (ISUSM), SPC outlooks, SPC watches, MCDs, WPC MPDs,
PIREPs, SIGMETs, G-AIRMETs, CWAs, LSRs, NEXRAD storm attributes, TAFs, tem-
perature/winds aloft, and climate normals. Each has its own ?help page. The pattern is
consistent: understand the ASOS CGI endpoint well and you understand all of them.
8.4. Tier 3: JSON/GeoJSON Ad-Hoc Services
The JSON services catalog at mesonet.agron.iastate.edu/api/ lists roughly 50 endpoints
organized by category: IEM data and metadata, aviation, NWS products, NWS warnings,
and miscellaneous. Unlike the CGI services, these return structured JSON or GeoJSON
rather than CSV, making them appropriate for mapping applications, real-time pipelines,
and programmatic workflows where you want to parse structured data rather than parse
CSV.
Several of these are particularly useful for weather enthusiasts:
Current observations (/json/current.py) returns the most recent observation for any
station in JSON format. The equivalent of the sortable currents table, but as machine-
readable structured data.
Network GeoJSON (/geojson/network.py) returns station metadata for any IEM net-
work as a GeoJSON FeatureCollection — station IDs, names, coordinates, and attribute
flags. The fastest way to get a complete station list with coordinates for spatial analysis.
VTEC events — a family of endpoints: by point (/json/vtec_events_bypoint.py),
by UGC (/json/vtec_events_byugc.py), by WFO (/json/vtec_events_bywfo.py), by
state (/json/vtec_events_bystate.py). These return structured warning event data in
JSON, the programmatic equivalent of the VTEC Browser.
Storm Based Warnings GeoJSON (/geojson/sbw.py) returns the actual polygon
geometry for storm-based warnings for a given time window, making it straightforward to
plot or analyze warning coverage spatially without downloading shapefiles.
SPC outlooks, watches, and MCDs (/json/spcoutlook.py, /json/spcwatch.py,
/json/spcmcd.py) return structured JSON for SPC products — useful for building auto-
mated pipelines around convective outlook data.
RAOB data (/json/raob.py) returns sounding data in JSON format with query flexibility
for specific pressure levels across date ranges, complementing the CSV portal.

| Mastering | the Mesonet |     |     | 89  |
| --------- | ----------- | --- | --- | --- |
Stage IV and PRISM (/json/stage4.py, /json/prism.py) return point-sample values
from gridded products at specified coordinates — the programmatic equivalent of clicking
| on a map | to get a precipitation | estimate. |     |     |
| -------- | ---------------------- | --------- | --- | --- |
| 8.5.     | Tier 4: API            | v1        |     |     |
mesonet.agron.iastate.edu/api/1/docs
The formal API is built on FastAPI and exposes its full Swagger documentation at the
docs URL. It is the right choice when you need fast, small responses — pulling the current
MOS run for a single station, querying VTEC events for a specific county, retrieving station
metadata. It returns JSON Table Schema responses with consistent structure, and the
Swagger docs include a live request tester you can use directly in the browser.
The API v1 endpoints of most relevance to weather enthusiasts include MOS data (covered
in Chapter 6), VTEC event data, station metadata and neighbor searches, and RAOB data.
The source code for all of these lives in the iem-web-services repository on GitHub, which is
worth knowing about if you want to understand exactly what a query is doing or if you find
| a bug and | want to report | it precisely. |               |     |
| --------- | -------------- | ------------- | ------------- | --- |
| 8.6.      | Two Special    | Services      | Worth Knowing |     |
8.6.1. MaxCSV
mesonet.agron.iastate.edu/request/maxcsv.py?help
MaxCSV is a single-variable snapshot tool — it returns the current value of one variable
for all stations in a network as a CSV with station ID, latitude, longitude, and the variable
value. One HTTP request, one variable, all stations simultaneously. For real-time mapping
or quick tabular situational awareness, this is often faster than any other pathway. Example:
| current | temperature | for all PA ASOS | stations in one call: |     |
| ------- | ----------- | --------------- | --------------------- | --- |
https://mesonet.agron.iastate.edu/request/maxcsv.py?network=PA_ASOS&var=tmpf

| Mastering | the Mesonet |                  |     |     |     |     | 90  |
| --------- | ----------- | ---------------- | --- | --- | --- | --- | --- |
| 8.6.2.    | Gibson      | Ridge Placefiles |     |     |     |     |     |
mesonet.agron.iastate.edu/request/grx/
If you use GR2Analyst, GRLevel3, or any other Gibson Ridge radar application, the IEM’s
placefile service provides live IEM data feeds that load directly into the radar display.
Placefiles are available for current ASOS observations, RWIS pavement temperatures, active
warning polygons, LSRs, HADS river data, CoCoRaHS precipitation, and others. The
placefile URL for each product auto-updates; you configure it once in GR2Analyst and it
stays current. For real-time storm analysis overlaying IEM network data on radar imagery,
| this is | the pathway | with      | no programming | required. |     |     |     |
| ------- | ----------- | --------- | -------------- | --------- | --- | --- | --- |
| 8.7.    | A Decision  | Framework |                |           |     |     |     |
When you need data from the IEM, the question to ask is: what kind of data, at what
| time resolution, |     | for how | many stations, | and | in what | format? |     |
| ---------------- | --- | ------- | -------------- | --- | ------- | ------- | --- |
If you want hourly or sub-hourly observations from ASOS for one to a few stations,
the UI portal at /request/download.phtml is fastest. For many stations or automation,
| use the | CGI endpoint | /cgi-bin/request/asos.py |     |     | directly. |     |     |
| ------- | ------------ | ------------------------ | --- | --- | --------- | --- | --- |
If you want daily climate data going back decades, use the Climodat por-
tal at /request/coop/fe.phtml for processed data, or the raw COOP portal at
/request/coop/obs-fe.phtml if you need observation times or unprocessed values.
If you want a derived statistic — a trend, a period average, a comparison to normals —
check Autoplot first. Download the chart’s CSV export rather than doing the computation
yourself.
If you want warning or NWS event data in a programmatic format, the JSON VTEC
services or the CGI watchwarn endpoint are the right paths, depending on whether you need
polygon geometry (JSON GeoJSON path) or tabular event metadata (CGI or API v1).
If you want gridded data sampled at a point, the IEMRE JSON API (/iemre/daily/)
| and the | Stage IV | or PRISM | JSON endpoints | are | the fastest | paths. |     |
| ------- | -------- | -------- | -------------- | --- | ----------- | ------ | --- |
If you want real-time current observations in bulk, MaxCSV is the fastest single-request
option. For a structured streaming workflow, iembot or the LDM feed are the appropriate
tools.

Mastering the Mesonet 91
8.8. What to Watch Out For
Time zone handling is not uniform across portals. The ASOS download portal lets
you specify any timezone, and the timestamps in the output reflect that choice. Some JSON
services return timestamps in UTC with explicit Z suffixes. Others return local standard
time without a timezone indicator. Always check the timestamp format in the output before
assuming UTC or local time. For any analysis that spans a DST transition, using UTC
throughout and converting only at the final display step is the only safe approach.
Precipitation requires accumulation, not just download. The p01i variable in ASOS
data is an incremental one-hour bucket reading, not a daily total. Gaps in the hourly record
— missing observations, station outages — will silently undercount daily totals if you simply
sum across 24 hours. A daily total computed from hourly ASOS data should be treated
with suspicion at any station with frequent missing observations. The IEM’s daily summary
portal computes these totals using its own methods, which may handle gaps differently from
a naive sum.
The 1,000 station-year limit is a real constraint. A request for all US ASOS stations
(roughly 1,700) for even a single year exceeds the limit. For multi-station bulk downloads,
use the CGI endpoint in batches by state or network, or consider whether the daily summary
portal — which aggregates to one row per station per day — reduces the data volume
enough to fit within a single query.
CGI services are not versioned. The IEM’s statement on API stability is accurate but
sobering: they try not to break things, but they make no guarantee. If you are building a
pipeline against a CGI endpoint, build in error handling and periodic checks that the output
format has not changed. The API v1 endpoints are more stable but cover a narrower range
of data.
Missing data representations vary. The ASOS download portal lets you choose whether
missingvaluesarerepresentedasM,null,orblankstrings. TraceprecipitationcanbeT,null,
blank, or 0.0001 (the numeric equivalent). These choices affect how you handle missing
data downstream. Set them explicitly when you configure the download, and document
which convention you used.

Mastering the Mesonet 92
8.9. Workflow 4 — Downloading a Year of Hourly ASOS Data
The question: You want the full 2023 hourly record for KMDT — temperature, dew point,
wind speed, wind direction, and precipitation — in a CSV file you can open in Excel or
analyze in Python.
Start here: https://mesonet.agron.iastate.edu/request/download.phtml
The ASOS download portal opens with a network selector at the top. From the network
dropdown, select PA_ASOS (Pennsylvania ASOS). The station list on the left will populate
with all Pennsylvania ASOS stations. Click MDT (Harrisburg International) to select it; it
will move to the selected stations panel on the right.
Set the date range. For a full calendar year of 2023, enter January 1, 2023 as the start date
and December 31, 2023 as the end date. The portal defaults to UTC timestamps; if you want
observationsinlocaltime, lookforthetimezoneselectorandswitchittoAmerica/New_York
(Eastern time). Be aware that ASOS stations operate on local standard time year-round, so
during daylight saving time the apparent local timestamps will be one hour off civil clock
time — the data is internally consistent, but the relationship to calendar dates requires care
if you are computing daily totals.
In the variable selection panel, check the variables you want. For temperature and dew point:
tmpf (temperature in °F) and dwpf (dew point in °F). For wind: sknt (wind speed in knots)
and drct (wind direction in degrees). For precipitation: p01i (precipitation accumulation
over the past hour, in inches). Check the box to include the station identifier and timestamp
in the output.
Select CSV as the output format. Click the download button. For a full year at a single
station,expectafilewithsomewherearound8,700rows—oneperhour,withsomeadditional
rows from special observations (SPECIs) triggered by significant weather changes. This is a
normal ASOS archive; do not be alarmed by rows between the standard hourly marks.
AfewvariablesworthknowingaboutintheASOSdownload: vsbyisvisibilityinstatutemiles,
wxcodes carries the present weather group from the METAR (which encodes precipitation
type, fog, thunderstorm, etc.), and peak_wind_gust and peak_wind_drct capture the peak
wind speed and direction within each observation period when they were recorded. If you
are doing wind analysis, the peak gust columns are more useful than the instantaneous wind
reading for capturing convective or frontal wind events.
The download portal has a practical rate limit: a request for more than 1,000 station-
years worth of data will be rejected with an HTTP 422 response. For a single sta-
tion over a single year this is irrelevant. For large bulk downloads across many sta-
tions, you will need to either split the request or use the CGI scripting interface at
https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py directly.

| Mastering | the Mesonet |         |     | 93  |
| --------- | ----------- | ------- | --- | --- |
| 8.10.     | Key URLs —  | Chapter | 8   |     |
| Portal    | / Service   |         | URL |     |
ASOS/AWOS/METAR Download (UI) mesonet.agron.iastate.edu/request/down-
load.phtml
| ASOS CGI | Backend (scriptable) |     | mesonet.agron.iastate.edu/cgi- |     |
| -------- | -------------------- | --- | ------------------------------ | --- |
bin/request/asos.py?help
| ASOS 1-Minute | Download |     | mesonet.agron.iastate.edu/re- |     |
| ------------- | -------- | --- | ----------------------------- | --- |
quest/asos/1min.phtml
| Iowa AWOS | 1-Minute Download |     | mesonet.agron.iastate.edu/re- |     |
| --------- | ----------------- | --- | ----------------------------- | --- |
quest/awos/1min.php
Climodat / COOP Download (processed) mesonet.agron.iastate.edu/re-
quest/coop/fe.phtml
COOP Raw Observations Download mesonet.agron.iastate.edu/request/coop/obs-
fe.phtml
| Daily Summaries | Download |     | mesonet.agron.iastate.edu/re- |     |
| --------------- | -------- | --- | ----------------------------- | --- |
quest/daily.phtml
| Hourly | Precip Download |     | mesonet.agron.iastate.edu/re- |     |
| ------ | --------------- | --- | ----------------------------- | --- |
quest/asos/hourlyprecip.phtml
| RWIS Download |     |     | mesonet.agron.iastate.edu/re- |     |
| ------------- | --- | --- | ----------------------------- | --- |
quest/rwis/fe.phtml
| RWIS Soil | Download |     | mesonet.agron.iastate.edu/re- |     |
| --------- | -------- | --- | ----------------------------- | --- |
quest/rwis/soil.phtml
| DCP/HADS | Download |     | mesonet.agron.iastate.edu/re- |     |
| -------- | -------- | --- | ----------------------------- | --- |
quest/dcp/fe.phtml
| USCRN | Download |     | mesonet.agron.iastate.edu/re- |     |
| ----- | -------- | --- | ----------------------------- | --- |
quest/uscrn.php
TAF Forecast Download mesonet.agron.iastate.edu/request/taf.php
Temp/Winds Aloft Download mesonet.agron.iastate.edu/request/temp-
wind_aloft.php
HML River Data Download mesonet.agron.iastate.edu/request/hml.php
Warning Polygons (GIS shapefile) mesonet.agron.iastate.edu/re-
quest/gis/watchwarn.phtml
| LSR Archive | Download |     | mesonet.agron.iastate.edu/re- |     |
| ----------- | -------- | --- | ----------------------------- | --- |
quest/gis/lsrs.phtml
NEXRAD Storm Attributes Download mesonet.agron.iastate.edu/re-
quest/gis/nexrad_storm_attrs.php

| Mastering   | the Mesonet |                               | 94  |
| ----------- | ----------- | ----------------------------- | --- |
| Portal /    | Service     | URL                           |     |
| SPC Outlook | Shapefile   | mesonet.agron.iastate.edu/re- |     |
quest/gis/spc_outlooks.phtml
| SPC Watch | Shapefile | mesonet.agron.iastate.edu/re- |     |
| --------- | --------- | ----------------------------- | --- |
quest/gis/spc_watch.phtml
| SPC MCD | Shapefile | mesonet.agron.iastate.edu/re- |     |
| ------- | --------- | ----------------------------- | --- |
quest/gis/spc_mcd.phtml
| WPC MPD | Shapefile | mesonet.agron.iastate.edu/re- |     |
| ------- | --------- | ----------------------------- | --- |
quest/gis/wpc_mpd.phtml
| PIREP | Shapefile | mesonet.agron.iastate.edu/re- |     |
| ----- | --------- | ----------------------------- | --- |
quest/gis/pireps.php
| API Mainpage | (all tiers)  | mesonet.agron.iastate.edu/api/       |     |
| ------------ | ------------ | ------------------------------------ | --- |
| API v1       | Swagger Docs | mesonet.agron.iastate.edu/api/1/docs |     |
MaxCSV (quick network snapshot) mesonet.agron.iastate.edu/re-
quest/maxcsv.py?help
Gibson Ridge Placefiles mesonet.agron.iastate.edu/request/grx/
| OGC Web | Services | mesonet.agron.iastate.edu/ogc/ |     |
| ------- | -------- | ------------------------------ | --- |

9. Chapter 9 — Webcams
The IEM webcam tools are a small corner of the site, but they fill a gap that most weather
data platforms never bother with: the ability to go back and see what conditions looked
like at a specific place and time. Not inferred from sensor readings, not reconstructed from
radar — actually see it, the way a camera sees it. If you have ever wanted to settle a dispute
about when snow started accumulating on a particular stretch of highway, or verify what
the sky looked like during the warm sector of a winter storm, this is where you go.
The webcam system is not glamorous. The cameras are not high-definition streaming feeds.
The coverage is heavily weighted toward Iowa and the upper Midwest, which means if you
are primarily a Mid-Atlantic observer the network will feel thin. But the archival depth and
the integration with other IEM tools — particularly RWIS station data — make it genuinely
useful when the conditions are right.
9.1. What the Network Actually Is
The IEM webcam archive draws from several distinct sources. The core of it is the Iowa
DOT Roadway Weather Information System (RWIS) network, which the IEM has been
archiving since December 2009. Beyond RWIS, the network has historically included feeds
from several Iowa television stations — KCRG-TV’s CityCam network, KCCI-TV, and
KELO-TV — along with select ISU campus cameras. The TV station cameras are notable
because they skew toward populated areas and scenic vantage points rather than highway
infrastructure, which means they occasionally catch dramatic storm shots that the RWIS
network misses entirely.
The whole thing is federated. IEM is not operating these cameras — it is archiving their
outputs and making them searchable. This matters because camera availability changes
without notice and individual feeds go offline permanently without any announcement. What
you find when you navigate to the viewer on any given day reflects what the source operators
have kept running, not what IEM has decided to maintain.
Archiving cadence is worth understanding. Under normal conditions, IEM captures an image
from each camera every five minutes. During active weather events, the interval drops to
95

Mastering the Mesonet 96
one minute. The practical implication is that if you are stepping through archived frames
and find a gap, it is almost certainly a five-minute interval, not missing data — unless you
are in a period of interesting weather, in which case the archive may be dense enough to
reconstruct several events per hour.
9.2. The Webcam Viewer
ThemaininterfaceistheIEMWebcamViewerathttps://mesonet.agron.iastate.edu/current/
viewer.phtml. This is the tool you want for both real-time viewing and archive browsing.
The viewer runs in two modes. In realtime mode, it refreshes automatically and shows
the most recent available image from each camera along with a live NEXRAD composite
and any active NWS warnings for the area. In archive mode, you set a specific date and
time and the viewer assembles the scene as it appeared at that moment — archived webcam
image, radar composite, warning overlays, and an indication of which direction each camera
was pointed. The archived views generate stable URLs you can bookmark or share, which is
useful when you want to point someone in a forum thread to a specific moment.
Cameraselectionishandledthroughaninteractivemap. Camerasshowupasiconsindicating
their pointing direction, though the site notes with admirable candor that the pointing
arrows are sometimes wrong. Clicking a camera loads its image history and lets you step
forward or backward in time. The RWIS cameras are particularly well represented because
of the long continuous archive; for many Iowa RWIS stations you can pull imagery going
back to December 2009.
The viewer also maintains a separate page for ISU campus cameras at https://mesonet.agron.
iastate.edu/current/isucams.phtml, which covers a handful of fixed vantage points around
the Ames campus. These see heavy use during convective events because the ISU Agronomy
Hall rooftop camera has produced some memorable tornado shots over the years.
9.3. RWIS Cameras and the Data Combination
The most meteorologically useful cameras in the IEM archive are the RWIS feeds, and the
reason is not the images themselves — it is the pairing. Every RWIS station that has a
camera also has sensors reporting air temperature, pavement temperature, surface condition
(dry, wet, snow-covered, icy), and in many cases wind speed and precipitation intensity. IEM

| Mastering | the Mesonet |     |     |     |     |     |     |     | 97  |
| --------- | ----------- | --- | --- | --- | --- | --- | --- | --- | --- |
integrates all of this. You can look at a camera image and simultaneously see the pavement
| temperature | from | the | co-located | sensor. |     |     |     |     |     |
| ----------- | ---- | --- | ---------- | ------- | --- | --- | --- | --- | --- |
In winter weather operations, this combination is unusually powerful. Radar tells you where
precipitation is falling. Surface observations tell you temperature. The RWIS camera tells
you what is actually happening on the pavement — and there is often a meaningful lag
between when radar shows a band moving over an RWIS location and when the road surface
transitions from wet to snow-covered. That lag is not consistently captured by any sensor
| reading | alone. | The visual | confirmation |     | fills | the gap. |     |     |     |
| ------- | ------ | ---------- | ------------ | --- | ----- | -------- | --- | --- | --- |
ThededicatedRWIScamerapageathttps://mesonet.agron.iastate.edu/RWIS/camera.phtml
provides access specifically to the RWIS archive, with the start date of each individual
camera’s archive shown in the selection menu. For Midwest-focused research, this is a cleaner
| entry point   | than | the main   | viewer | if  | you know | which | station you | want. |     |
| ------------- | ---- | ---------- | ------ | --- | -------- | ----- | ----------- | ----- | --- |
| 9.4. Building |      | Time-Lapse |        |     | Loops    |       |             |       |     |
The Webcams menu links to a lapse builder at https://mesonet.agron.iastate.edu/current/
bloop.phtml. This tool lets you specify a camera and a time window and generates an
animated sequence from the archived frames — essentially reconstructing the visual record
of any period the camera was active. The interface is UI-driven; you pick a camera from the
available list, set your start and end times, and the lapse assembles from the archive.
There is also a separate page for recent pre-built movies at https://mesonet.agron.iastate.
edu/current/camlapse/. For the TV station camera networks — KCCI, KCRG, and KELO
— IEM generates five standard timelapses per day automatically, covering specific periods
that match the morning, afternoon, and evening news cycles. These are used by the stations
on-air, and the most recent lapse from each is available online. The camlapse page is where
| you find | those | pre-built | loops | without | having | to  | construct your | own. |     |
| -------- | ----- | --------- | ----- | ------- | ------ | --- | -------------- | ---- | --- |
If you want to reconstruct something specific — a squall line passage, an overnight snowfall
accumulation sequence, the onset of freezing rain — the bloop builder is the right tool. Start
with the archived still images in the main viewer to find your camera and confirm the archive
coverage for your time window, then move to the lapse builder to assemble the sequence.

Mastering the Mesonet 98
9.5. The Cool Lapses Archive
The Cool Lapses page at https://mesonet.agron.iastate.edu/cool/ is a curated collection of
the best lapse sequences produced from the IEM archive over the years. These are linked to
Daryl Herzmann’s YouTube channel rather than hosted directly on the IEM servers. The
collection includes some genuine showpieces — a gravity wave sequence from near Tama,
Iowa has accumulated over a million views on YouTube, and the 2005 tornado captured from
the ISU Agronomy Hall rooftop camera is the kind of footage that gets cited in teaching
materials.
The Cool Lapses page is not updated constantly, but the historical catalog is worth knowing
about. If you are looking for specific weather phenomena on camera and your target event
was somewhere in Iowa over the past fifteen-plus years, there is a reasonable chance a lapse
of it exists in this collection. It is also a useful benchmark for what the camera system
can capture when everything comes together — good camera placement, active weather,
one-minute archive intervals, and someone paying attention.
9.6. Coverage Limitations
For readers who are primarily Mid-Atlantic or Northeast observers, the honest assessment is
that the IEM webcam system will rarely be your primary resource. The RWIS archive is
concentrated in Iowa and the upper Midwest. The TV station camera networks are similarly
Iowa-centric. PennsylvaniaandthesurroundingregionhavededicatedDOTcameraresources
— PennDOT’s 511PA system maintains an extensive network — that are not integrated into
the IEM archive and will almost always offer better coverage of your target area.
Where the IEM system earns its keep for non-Iowa users is in post-event research on
significant nationwide events, in the RWIS pavement sensor integration that few other
platforms attempt, and in the archival depth going back to 2009 for the RWIS network
specifically. IfyoureventhappenedinIowaoryouneedthesensor-plus-visualcombinationfor
a winter weather case, it is the right tool. For real-time situation awareness in Pennsylvania,
treat it as a supplemental resource rather than a primary one.

| Mastering | the Mesonet |     |     | 99  |
| --------- | ----------- | --- | --- | --- |
| 9.7. What | to Watch    | Out | For |     |
Camera availability is unstable. Individual feeds go offline permanently, sometimes entire
network partnerships end, and there is no notification system. The pointing direction arrows
in the viewer are sometimes wrong; take them as approximate guides rather than precise
indicators. Timestamp accuracy is generally good, but image intervals can be irregular near
the transition between five-minute and one-minute archiving cadence — you may see a gap
that looks like missing data but is simply the standard inter-frame interval.
The lapse builder can be slow to assemble sequences from older archive dates, particularly if
you are spanning more than a few hours. Start with a short window to confirm the archive
is present for your camera and time period before querying a longer sequence.
| 9.8. Key | URLs — | Chapter | 9   |     |
| -------- | ------ | ------- | --- | --- |
Tool URL
Webcam Viewer (realtime + archive) https://mesonet.agron.iastate.edu/cur-
rent/viewer.phtml
| RWIS Archived | Webcam | Imagery | https://mesonet.agron.ias- |     |
| ------------- | ------ | ------- | -------------------------- | --- |
tate.edu/RWIS/camera.phtml
Lapse Builder https://mesonet.agron.iastate.edu/cur-
rent/bloop.phtml
Recent Pre-Built Lapses https://mesonet.agron.iastate.edu/cur-
rent/camlapse/
| Cool Lapses | Archive |     | https://mesonet.agron.iastate.edu/cool/ |     |
| ----------- | ------- | --- | --------------------------------------- | --- |
| ISU Campus  | Webcams |     | https://mesonet.agron.iastate.edu/cur-  |     |
rent/isucams.phtml
| Webcam | Project Overview |     | https://mesonet.agron.ias- |     |
| ------ | ---------------- | --- | -------------------------- | --- |
tate.edu/projects/webcam.php

10. Chapter 10 — Understanding Data
Quality
Every piece of data on the IEM carries an implicit question: how much should you trust it?
The answer is not uniform. It depends on the network, the variable, the time period, and
sometimes a specific quirk in how a particular station’s data has been ingested, processed,
or stored. This chapter is about developing the instincts to ask that question productively
— and knowing where on IEM to look for the answer.
This is not a catalog of everything that can go wrong. That would be both exhausting and
discouraging. It is a practical orientation to the most consequential data quality issues you
are likely to encounter as a serious weather enthusiast working with IEM data, with enough
explanation of the underlying mechanics that you can recognize problems when you see
them rather than waiting to be surprised.
10.1. The “Unofficial” Label
The word unofficial appears throughout the IEM — in chart titles, in download headers, in
the daily features on the homepage. It is worth understanding precisely what it means and,
equally importantly, what it does not mean.
IEM is not a National Weather Service office. It is not NCEI. It is an academic mesonet
operated out of Iowa State University, and the data it archives, processes, and displays has
not gone through the formal QC and certification pipeline that transforms raw observations
into the official climate record. When IEM applies its own computed products — daily
summaries, areal averages, derived statistics — those products are labeled unofficial because
they are: they reflect IEM’s best processing of available data, not a federally certified
observation.
Whatunofficialdoesnot meaniswrong, orunreliable, orexperimental. Therawobservations
feeding IEM’s archive are the same observations flowing to NCEI and NWS. The ASOS
data ingested by IEM comes from the same NOAAPort satellite feed and NCEI data sources
that official archives draw from. The processing IEM applies is documented, the methods
100

Mastering the Mesonet 101
are published in journal papers, and the results have been used in peer-reviewed research.
Unofficial is a legal and institutional designation, not a quality judgment.
The practical implication is simple: if you are doing research that will be cited, published,
or submitted to a formal climate record, cross-check your IEM-derived results against
NCEI’s official products. For forum discussions, personal research, forecast verification, and
operational awareness — which covers the vast majority of what weather enthusiasts do
with this data — the unofficial label should not give you pause.
10.2. How IEM Handles Quality Control
IEM runs automated QC checks on incoming data from its various networks. The specific
checks vary by network, but the general approach includes range testing (is this temperature
physically plausible?), rate-of-change testing (did this sensor just jump 30 degrees in five
minutes?),andspatialconsistencytesting(doesthisstation’sreadingagreewithitsneighbors
within reasonable bounds?).
Beyond automated checks, IEM participates in the MADIS (Meteorological Assimilation
Data Ingest System) QC framework for several networks. The MADIS QC page at https://
mesonet.agron.iastate.edu/QC/madis/network.phtml lets you browse QC status by network,
showing you which stations are currently flagged and for what reason.
The QC mainpage at https://mesonet.agron.iastate.edu/QC/ provides links to all the QC
products IEM generates. The most immediately useful for a working weather enthusiast is
the offline station list at https://mesonet.agron.iastate.edu/QC/offline.php, which shows
stations that are currently not reporting or have been flagged as having data problems.
10.2.1. The Public QC Ticket System
IEM maintains a public trouble ticket log at https://mesonet.agron.iastate.edu/QC/tickets.
phtml. This is worth knowing about for two reasons. First, it is a window into the kinds of
problems the IEM team actually encounters and how they handle them — which gives you
a more realistic picture of data reliability than any documentation page alone. Second, it is
genuinely bidirectional: the IEM team reads submissions, and if you identify what looks like
a data quality problem while working with a specific station, you can flag it there.
The tickets range from straightforward sensor outages to more complex ingestion problems
— cases where data was received but processed incorrectly, or where a network partner
changed their data format and the IEM ingestor had not yet caught up. Reading through a

Mastering the Mesonet 102
few months of tickets gives you a healthy sense of the kinds of edge cases that exist even in
well-maintained systems.
10.3. ASOS Temperature Storage: The Whole-Degree Problem
This is the single most counterintuitive data quality issue in the ASOS record, and it trips
up experienced analysts who do not know to look for it.
Here is the chain of events, as IEM’s own dataset documentation describes it. ASOS stations
in the United States internally record temperature in whole degrees Fahrenheit. A sensor
reading of 78°F is stored as 78. This is not ideal precision for climate analysis, but it is the
base reality. The problem arises during transmission. METAR format transmits temperature
in degrees Celsius. When the station converts 78°F to Celsius for the METAR, it gets
25.56°C, which it rounds to 26°C for transmission. Now IEM receives 26°C and converts it
back to Fahrenheit: 26°C = 78.8°F, which rounds to 79°F. The station observed 78°F; the
database records 79°F. A one-degree error has been introduced entirely by the round-trip
unit conversion.
The fix is the METAR T-group — a supplemental field in METAR format that provides
temperature to one-tenth of a degree Celsius precision. When the T-group is present, IEM
can convert back to Fahrenheit with enough precision to recover the original whole-degree
value reliably. IEM’s processing explicitly prioritizes data sources that include the T-group,
and the NOAAPort feed — IEM’s primary ASOS source — does include it for most US
stations most of the time.
What this means in practice: for most routine ASOS observations at most US airports, the
temperature record in IEM is accurate to the original whole-degree Fahrenheit. But “most
of the time” is doing real work in that sentence. In older archived data, in observations
from certain auxiliary sources, and particularly in data from the MADIS high-frequency feed
(which transfers temperature in Celsius without adequate precision), you may encounter
the one-degree-off error. For a forum discussion about yesterday’s high temperature, this is
irrelevant. For research computing climatological normals or extreme temperature statistics,
it is something to be aware of and to validate against authoritative sources.
The one-minute ASOS data available through IEM carries an additional version of this
problem: the NCEI one-minute data files are processed with a known Celsius precision
issue in the FAA data transfer chain. IEM has documented this explicitly in its news
archive. If you are pulling one-minute ASOS data for temperature analysis, read the dataset
documentation at https://mesonet.agron.iastate.edu/info/datasets/metar.html before you
begin.

| Mastering | the Mesonet   |      |                | 103 |
| --------- | ------------- | ---- | -------------- | --- |
| 10.4.     | COOP Data and | Time | of Observation |     |
TheNWSCooperativeObservernetworkhasbeentakingdailytemperatureandprecipitation
readings since the 1880s at some stations. That longevity is exactly what makes COOP data
irreplaceable for climatological research — and exactly why TOBS (Time of Observation)
| matters | so much. |     |     |     |
| ------- | -------- | --- | --- | --- |
COOP observers take their readings once per day, at a time they choose. Some observe at 7
AM. Some at 5 PM. Some at midnight. The recorded high and low temperatures for a given
calendar date represent the extremes during the 24-hour period ending at observation time,
not the calendar midnight-to-midnight period. An observer who takes readings at 7 AM on
the 15th is recording the high and low that occurred between 7 AM on the 14th and 7 AM
| on the 15th | — and attributing | those values | to the 15th. |     |
| ----------- | ----------------- | ------------ | ------------ | --- |
This creates what climate scientists call the time-of-observation bias. Morning observers (7
AM) are less likely to inadvertently count the same extreme twice across adjacent calendar
days than afternoon observers (5 PM). The 5 PM observer who records an exceptionally hot
afternoon might count that same hot afternoon in two consecutive daily records if the heat
lingered past midnight. At a network scale, these observation time differences can inflate or
suppress apparent monthly means by a fraction of a degree — enough to matter for trend
| analysis | over long records. |     |     |     |
| -------- | ------------------ | --- | --- | --- |
IEM’s COOP pages note this directly. The COOP daily observations page warns that for
observations made at 7 AM, the data covers a 24-hour period ending at that time, not the
local calendar date. This is not IEM’s choice or problem to fix — it is the fundamental
structure of how COOP data is collected. But it is something to know when you are
comparing COOP daily records to ASOS records, which observe on a different and more
consistent time basis, or when you are comparing COOP stations to each other across
| different | observation time regimes. |     |     |     |
| --------- | ------------------------- | --- | --- | --- |
For most forum-level discussions — “what was the daily high at this COOP station?”
— TOBS is background noise. For research examining trends across long periods, or for
comparingCOOPagainstothernetworks,itrequireseitherawarenessorexplicitcorrection.

Mastering the Mesonet 104
10.5. Trace Precipitation
Across IEM’s download portals, you will encounter precipitation values stored as 0.0001
inches. This is not a measurement artifact or a rounding error. It is a deliberate encoding
convention meaning Trace — precipitation was observed but too small to measure. In the
COOP and ASOS networks, a Trace is officially defined as measurable precipitation below
0.005 inches (the minimum readable increment of a standard rain gauge).
When you download COOP or ASOS precipitation data from IEM and see 0.0001 in your
spreadsheet, treat it as a qualitative flag — precipitation occurred — not as a quantitative
measurement. Summing these values, computing monthly totals that include trace days, or
doing statistics that treat 0.0001 as a real measurement will introduce errors that compound
across long records.
The practical test: if you are computing wet-day frequency, a 0.0001 is correctly counted as
a wet day. If you are computing seasonal totals, it should either be set to zero or excluded
from the numeric sum. Most research-grade precipitation analyses use a threshold (often
0.01 inches) that naturally excludes trace amounts, but if you are working with raw IEM
downloads, the convention is worth knowing explicitly.
10.6. Missing Data Codes
The specific value used to indicate missing data in IEM downloads varies by format and by
download portal, and this inconsistency has caught many users off guard.
In CSV downloads from the ASOS download portal, missing temperature and dew point
values typically appear as a blank field or as the string M. In the daily summary download,
they may appear as None (Python-style null) or as an empty string depending on the output
format selected. In JSON API responses, missing values are usually returned as null. In
some older COOP archive formats, 999.9 or -99 appear as sentinel values for missing data
— a legacy of pre-digital encoding conventions that occasionally survived into digitized
records.
The safest approach when writing any code or script that processes IEM data: do not assume
you know what the missing value sentinel will be. Check the first few rows of your download
for unexpected values before computing statistics, and review the dataset documentation at
https://mesonet.agron.iastate.edu/info/datasets/ for the specific format you are working
with.

| Mastering | the Mesonet |           |         |               |             | 105 |
| --------- | ----------- | --------- | ------- | ------------- | ----------- | --- |
| 10.7.     | What a      | Real Data | Quality | Investigation | Looks Like: | MDT |
and CXY
Abstract discussion of data quality issues only goes so far. Here is what it looks like when
| you actually | find something. |     |     |     |     |     |
| ------------ | --------------- | --- | --- | --- | --- | --- |
Harrisburg, Pennsylvania has two ASOS stations within a few miles of each other: KMDT
(Harrisburg International Airport, in Middletown) and KCXY (Capital City Airport, in New
Cumberland). Both have long continuous records. Both are official FAA ASOS installations.
On paper they should agree reasonably well for most variables, given their proximity and
| shared | climate regime. |     |     |     |     |     |
| ------ | --------------- | --- | --- | --- | --- | --- |
A comparison of precipitation records between these two stations over a multi-year period
reveals a persistent and substantial difference: KCXY runs approximately 11% wetter than
KMDT on an annual basis. This is not noise. Eleven percent is well outside what you would
expect from two stations separated by a few miles in flat valley terrain with no significant
| orographic | difference | between them. |     |     |     |     |
| ---------- | ---------- | ------------- | --- | --- | --- | --- |
What causes this? The most likely explanation is gauge siting and local exposure differences
rather than instrument malfunction. ASOS tipping-bucket rain gauges are sensitive to
wind effects at the orifice — a gauge in a more sheltered location will catch slightly more
precipitation than one exposed to stronger winds, all else equal. Small differences in nearby
obstructions, prevailing wind direction during precipitation events, and gauge height above
grade can all contribute to systematic biases that are real, repeatable, and entirely invisible
to automated QC systems that are checking for gross errors rather than subtle inter-station
biases.
The lesson is not that one of these stations is wrong. Both stations are reporting what their
gauges observe. The lesson is that gauge measurements are point observations of a physical
process that has local variability — and that two official ASOS stations a few miles apart
can have genuinely different precipitation climatologies that reflect their specific exposure
| rather than | instrument | error. |     |     |     |     |
| ----------- | ---------- | ------ | --- | --- | --- | --- |
This kind of investigation — running a long-period comparison between nearby stations and
looking for systematic divergence — is exactly the type of work IEM makes straightforward.
Autoplot chart q=12 (precipitation summary comparisons), the daily summary download
portal, and Climodat all provide the raw material. The MDT/CXY comparison illustrates
both the power of having dense, long-record station networks and the caution required when
| interpreting | any single | station’s | record in | isolation. |     |     |
| ------------ | ---------- | --------- | --------- | ---------- | --- | --- |

Mastering the Mesonet 106
10.8. Station Metadata: Moves, Equipment Changes, and Archive
Gaps
A station’s observational record is not just its data — it is the history of its physical location,
its equipment, and its observation practices. ASOS stations have been relocated. Their
shelter configurations have changed. The transition from manual to automated observation
happened at different times for different stations. COOP observers change, and with them,
the specific protocols a station follows.
IEM’s station information page, accessible through the Station Locator at https://mesonet.
agron.iastate.edu/sites/locate.php, provides metadata for every station in the network —
location history, network membership, archive start and end dates, and any documented
notes about the station’s history. For research involving long records, this page is where you
start, not where you end up accidentally after finding something strange in your data.
Whena COOPstationmovesevena fractionof amile, its exposure tolocaldrainage, coldair
pooling, or orographic effects can change enough to introduce a detectable discontinuity in
its temperature or precipitation record. These discontinuities are documented in the station
metadata when they are known, but not all station moves are formally recorded in every
archive. The variables reference at https://mesonet.agron.iastate.edu/info/variables.phtml
is the companion document — it explains what each variable in IEM’s database actually
represents, which is its own form of data quality documentation.
10.9. What to Watch Out For
A few practical rules that have come out of the issues covered in this chapter:
When computing temperature statistics from ASOS data, especially extremes, validate
against the official CF6 climate summaries or NCEI monthly reports for the same station
when the result seems surprising. A one-degree discrepancy from the whole-degree storage
issue can occasionally push a computed extreme in or out of record territory.
When working with long COOP records, be aware that apparent trends may partially reflect
changes in observation time rather than actual climate change. The TOBS adjustment is
well-studied in the scientific literature, and the GHCN dataset applies it; raw COOP data
as downloaded from IEM does not.
When comparing precipitation between nearby stations, an 11% systematic difference is not
automatically a QC problem — it may be a real exposure difference worth understanding

| Mastering | the Mesonet |     |     |     |     | 107 |
| --------- | ----------- | --- | --- | --- | --- | --- |
rather than correcting. But a 50% difference sustained over multiple years probably warrants
| a closer look | at the gauge | siting | and maintenance |     | history. |     |
| ------------- | ------------ | ------ | --------------- | --- | -------- | --- |
When you encounter an anomalous value in any IEM download, the QC ticket system at
https://mesonet.agron.iastate.edu/QC/tickets.phtml is the right place to report it. The
IEM team is small, they cannot actively audit every observation across every network, and
| user-flagged | issues have | led to real | corrections |     | in the archive.                       |     |
| ------------ | ----------- | ----------- | ----------- | --- | ------------------------------------- | --- |
| 10.10.       | Key URLs    | — Chapter   |             | 10  |                                       |     |
| Resource     |             |             |             |     | URL                                   |     |
| QC Mainpage  |             |             |             |     | https://mesonet.agron.iastate.edu/QC/ |     |
QC Trouble Tickets (public) https://mesonet.agron.iastate.edu/QC/tick-
ets.phtml
Currently Offline Stations https://mesonet.agron.iastate.edu/QC/of-
fline.php
| MADIS | Network QC |     |     |     | https://mesonet.agron.ias- |     |
| ----- | ---------- | --- | --- | --- | -------------------------- | --- |
tate.edu/QC/madis/network.phtml
| METAR/ASOS | Dataset | Documentation |     |     | https://mesonet.agron.ias- |     |
| ---------- | ------- | ------------- | --- | --- | -------------------------- | --- |
tate.edu/info/datasets/metar.html
| Dataset | Documentation | Index |     |     | https://mesonet.agron.ias- |     |
| ------- | ------------- | ----- | --- | --- | -------------------------- | --- |
tate.edu/info/datasets/
Variables Reference https://mesonet.agron.iastate.edu/info/vari-
ables.phtml
Station Locator / Metadata https://mesonet.agron.iastate.edu/sites/lo-
cate.php

| 11. | Chapter |     |         | 11  | — Getting |          | the Most | Out of |
| --- | ------- | --- | ------- | --- | --------- | -------- | -------- | ------ |
|     | IEM:    |     | Putting |     | It All    | Together |          |        |
The preceding chapters have covered the IEM from the outside in — what it is, how it is
organized, what each section contains, and how to get data out of it. The practical workflows
that demonstrate these tools in action have been embedded directly in the chapters where
| the | relevant | tools live: |     |     |     |     |     |     |
| --- | -------- | ----------- | --- | --- | --- | --- | --- | --- |
• Workflow 1 — COOP Daily Extremes is in Chapter 6, immediately after the
|     | Daily Climatology |     | section |     |     |     |     |     |
| --- | ----------------- | --- | ------- | --- | --- | --- | --- | --- |
• Workflow 2 — Building a Custom Autoplot Chart is in Chapter 4, at the end
|     | of the Autoplot |     | section |     |     |     |     |     |
| --- | --------------- | --- | ------- | --- | --- | --- | --- | --- |
• Workflow 3 — Researching a Past Warning Event is in Chapter 7, following
|     | the VTEC | Browser |     | section |     |     |     |     |
| --- | -------- | ------- | --- | ------- | --- | --- | --- | --- |
• Workflow 4 — Downloading a Year of Hourly ASOS Data is in Chapter 8, at
|     | the end | of the | download | portals | chapter |     |     |     |
| --- | ------- | ------ | -------- | ------- | ------- | --- | --- | --- |
• Workflow 5 — Building a Wind Rose is in Chapter 4, alongside Workflow 2
This chapter steps back and addresses the broader question: once you know how the
| individual | tools | work, | how | do you | combine    | them effectively? |     |     |
| ---------- | ----- | ----- | --- | ------ | ---------- | ----------------- | --- | --- |
| 11.1.      | Using | the   | IEM | as     | a Research | System            |     |     |
The IEM’s real power emerges when you stop treating its tools as isolated point-and-click
applications and start treating them as components of a connected research pipeline. A
| typical | investigation |     | moves | through | several | layers: |     |     |
| ------- | ------------- | --- | ----- | ------- | ------- | ------- | --- | --- |
Orientation — Start with current conditions or the Daily Feature archive to understand
what the IEM is showing you about the present moment or a recent event. The Daily
Feature in particular is worth browsing regularly — it demonstrates what the tools can
produce and gives you directly re-runnable Autoplot configurations for every chart.
Event identification — Use the VTEC Browser or the NWS warning search to pin down
the exact timing, polygon, and metadata for a past event. The ETN gives you a unique
handle on the specific warning that you can carry forward into every subsequent query.
108

| Mastering | the Mesonet |     |     | 109 |
| --------- | ----------- | --- | --- | --- |
Data retrieval — Use the appropriate download tier for what you need. Tier 1 portals
for straightforward single-station CSV downloads. Tier 2 CGI endpoints for bulk or multi-
parameter pulls. The API for programmatic access. Remember the 1,000 station-year
processing limit on the ASOS download portal and plan your queries accordingly.
Quality assessment—Beforedrawingconclusions, reviewthedataqualitycaveatsrelevant
toyournetwork. ASOStemperaturedatacarriesthewhole-degreeroundingartifactdescribed
in Chapter 2 and Chapter 10. COOP data carries TOBS offsets described in Chapter 6
and Chapter 10. Cross-check your downloaded values against Autoplot charts of the same
station and period — discrepancies often surface systemic issues before they contaminate an
analysis.
Visualization and verification — Use Autoplot to visualize what you downloaded. The
chart library covers nearly every combination of variable, time scale, and network that the
IEMsupports. Ifyoucannotfindachartthatshowswhatyouneed, theJSONoutputformat
from most CGI endpoints will feed directly into a Python or R visualization pipeline.
| 11.2. | A Note on | Using These | Tools Together |     |
| ----- | --------- | ----------- | -------------- | --- |
The IEM’s tools were not designed as a unified application — they grew organically over
two decades as separate modules addressing specific needs. This means there is no single
dashboard that connects everything. The connection happens in your head and in your
workflow.
The most effective IEM users develop a personal map of the site: a set of bookmarked
Autoplot configurations, a saved set of CGI URL templates, a mental model of which
download portal serves which data type. Building that map takes time. The Daily Feature
archive, browsed regularly over months, is probably the fastest path to it — every entry is a
demonstration of a tool applied to a real problem, with a re-runnable link attached.
| 11.3.        | Key URLs | — Chapter | 11                                 |     |
| ------------ | -------- | --------- | ---------------------------------- | --- |
| Resource     |          |           | URL                                |     |
| IEM Homepage |          |           | https://mesonet.agron.iastate.edu/ |     |
Daily Feature Archive https://mesonet.agron.iastate.edu/onsite/
features/past.php
| Daily Feature | Tags |     | https://mesonet.agron.iastate.edu/onsite/ |     |
| ------------- | ---- | --- | ----------------------------------------- | --- |
features/tags/
| Autoplot |     |     | https: |     |
| -------- | --- | --- | ------ | --- |
//mesonet.agron.iastate.edu/plotting/auto/

| Mastering | the Mesonet | 110 |
| --------- | ----------- | --- |
Resource URL
VTEC Browser https://mesonet.agron.iastate.edu/vtec/
ASOS Download Portal https://mesonet.agron.iastate.edu/request/
download.phtml
| IEM API | v1 https://mesonet.agron.iastate.edu/api/1/ |     |
| ------- | ------------------------------------------- | --- |

Part IV.
Back Matter
111

Glossary
Thefollowingtermsappearthroughoutthisguide. DefinitionsarewrittenintheIEMcontext
— what each term means for someone using this website, not as standalone meteorological
or regulatory definitions.
AFOS — Automation of Field Operations and Services. The legacy message-routing system
the NWS used before the internet era, and whose product identifiers it never stopped using.
On IEM, you will encounter AFOS whenever you are working with raw NWS text products.
Every product — Area Forecast Discussion, Hazardous Weather Outlook, Local Storm
Report, public zone forecast — has an AFOS PIL (see PIL) that uniquely identifies it. IEM’s
text product archive at /wx/afos/p.php is organized around these identifiers. If you know
the PIL, you can retrieve any NWS product IEM has ever received.
ASOS — Automated Surface Observing System. The primary airport weather observation
network in the United States, operated jointly by the NWS, FAA, and Department of
Defense. ASOS stations report every hour and, at most sites, every minute, measuring
temperature, dew point, wind speed and direction, visibility, precipitation, sky condition,
and pressure. On IEM, ASOS is the workhorse: it is the network behind most of the hourly
download portals, most of the climate charts in Autoplot, and most of the long-term station
records available for your airport. The IEM ASOS archive runs from approximately 1973 at
the longest-serving stations. Understanding ASOS’s known limitations — particularly its
tendency to undercount light snowfall and its whole-degree Fahrenheit internal temperature
storage — matters when you are doing precision climatology.
AWOS — Automated Weather Observing System. A family of FAA-operated automated
stations at smaller airports that do not qualify for full ASOS instrumentation. AWOS
stations vary significantly in what they measure: AWOS-1 gives only wind and altimeter;
112

Mastering the Mesonet 113
AWOS-3 adds visibility and sky; AWOS-3P adds a precipitation sensor. IEM ingests AWOS
data alongside ASOS but the two networks have different capabilities, different QC histories,
and different archive depths. When you pull data from a small general aviation airport and
find gaps or suspect readings, the first question is whether it is an AWOS site and which
tier.
CAI — Climate Averages and Indices. A term IEM uses for the derived climatological
products computed from long-period COOP station records. When you are working with
IEM’s normals data — 30-year averages for temperature, precipitation, heating degree days
— you are working with CAI products. The distinction matters when you are downloading
data: CAI fields are computed summaries, not raw observations.
CF6 — NWS Climate Form 6. The monthly summary climate product that NWS forecast
offices issue at the end of each month for each of their official climate stations. A CF6
contains the daily maximum and minimum temperature, precipitation, snowfall, snow depth,
and departures from normal for every day of the month, plus monthly totals and records.
IEM archives CF6 products as text and in database form. When there is a discrepancy
betweenwhatastationofficiallyreportedinagivenmonthandwhatappearsinASOShourly
data, the CF6 is often the authoritative record because it reflects any observer corrections
applied after the automated data was ingested.
CDD — Cooling Degree Day. A measure of how much cooling demand a day creates,
calculated as the number of degrees by which the daily mean temperature exceeds a base
of 65°F. A day with a mean temperature of 80°F produces 15 CDDs. On IEM, CDDs
appear in Autoplot charts focused on agricultural and energy applications, alongside HDDs
and GDDs. IEM computes daily degree days from ASOS and COOP station data and
archives them in the daily summary database, accessible through the daily download portal
at /request/daily.phtml.

Mastering the Mesonet 114
CLI — CLImatological report. The daily climate product issued each morning by NWS
forecast offices for their official climate stations. A CLI includes yesterday’s high and low
temperature, precipitation, snowfall, and comparisons to the record and normal for that
date. IEM receives and archives CLI products as they come off the LDM. The text products
are retrievable by AFOS PIL (typically CLI followed by the three-letter city identifier, such
as CLIMDT for Harrisburg).
CoCoRaHS — Community Collaborative Rain, Hail and Snow Network. A citizen science
precipitation observation network operated through Colorado State University, in which
volunteerstakedailyprecipitationreadingsusingstandardizedgaugesatprecisemeasurement
times. On IEM, CoCoRaHS data is ingested from the national CoCoRaHS database and
presented alongside the COOP and ASOS networks. The key advantage of CoCoRaHS
is density: in a typical Pennsylvania county there may be one ASOS station and two
COOP stations, but twenty or more CoCoRaHS observers. For studying spatial variability in
precipitation—particularlysnowfall, whichASOSnotoriouslyundermeasures—CoCoRaHS
is often the most valuable network IEM aggregates.
COOP — Cooperative Observer Program. The NWS volunteer observer network that
has been collecting daily temperature and precipitation data across the United States for
well over a century. COOP observers take a once-daily reading — at a locally consistent
time, traditionally early morning — of maximum temperature, minimum temperature,
precipitation, snowfall, and snow depth. The network’s value on IEM is its historical depth:
COOPstationsinPennsylvaniaoftenhavecontinuousrecordsbacktothe1880s,farpredating
any ASOS data. That longevity comes with tradeoffs: observer changes, station relocations,
instrument upgrades, and time-of-observation differences all create inhomogeneities that
require care when building long-period trends.
DCP — Data Collection Platform. The generic term for NWS-operated automated river,
stream, and environmental monitoring sites that transmit data via GOES satellite. On IEM,
DCP refers to the network of hydrological observation stations — stream gauges, reservoir
sensors, soil moisture sites — that report through the HADS system. DCP data on IEM
includes river stage, streamflow, precipitation from co-located rain gauges, and in some cases
soil temperature and moisture. Archive depth varies widely by station: some Pennsylvania
DCP sites have continuous records going back to the 1970s; others are recently installed.

Mastering the Mesonet 115
ETN — Event Tracking Number. The sequential number assigned by a WFO to each VTEC
event within a phenomena-significance category within a calendar year. An ETN resets to 1
every January 1 at each office. On IEM’s warning search, an ETN is what allows you to
track a single warning event across multiple WFO-issued updates — the initial issuance, any
extensions, and the cancellation or expiration all share the same ETN. Combining WFO
identifier + phenomena code + significance code + ETN + year gives you a globally unique
identifier for any NWS warning event, which is why IEM’s VTEC search is far more powerful
than searching by date or county alone.
GDD — Growing Degree Day. A heat accumulation unit used in agricultural science
to predict crop and pest development. Calculated as the number of degrees by which a
day’s mean temperature exceeds a crop-specific base temperature (commonly 50°F for corn,
32°F for wheat), subject to minimum and maximum caps that prevent extreme days from
distorting the calculation. IEM is deeply invested in GDD data because of its land-grant
agricultural mission: the Autoplot chart library includes multiple GDD charts, and the
IEM Pest Maps and Ag Weather tools are built directly on accumulated GDD values. For
weather enthusiasts in Pennsylvania, GDD also serves as a proxy for seasonal progression —
you can compare GDD accumulation to normal as a way of quantifying how “behind” or
“ahead” a spring is running.
G-AIRMET — Graphical AIRMET. The graphical successor to the text-format AIRMET
(Airman’s Meteorological Information) product issued by the NWS Aviation Weather Center
for significant en-route flight hazards below 18,000 feet MSL. G-AIRMETs cover turbulence,
icing, and instrument meteorological conditions across geographic polygons rather than the
textual regions used in the legacy format. On IEM, G-AIRMETs are available as down-
loadable GIS shapefiles at /request/gis/awc_gairmets.phtml, making them useful for
anyone studying aviation weather patterns or correlating flight delay data with atmospheric
conditions.
HADS — Hydrometeorological Automated Data System. The NWS system that ingests,
processes, and distributes GOES-transmitted DCP observations to end users. HADS is
the plumbing behind the DCP network: when a stream gauge transmits its reading to a

Mastering the Mesonet 116
GOES satellite, HADS routes that data to NWS systems and eventually to IEM. On IEM,
references to HADS typically appear in the DCP network context — if data is tagged as
coming through HADS, it originates from a GOES-transmitting sensor site.
HDD — Heating Degree Day. The mirror of CDD: the number of degrees by which a
day’s mean temperature falls below the 65°F base. A day with a mean of 30°F produces
35 HDDs. HDD accumulation through a winter is a standard proxy for heating energy
demand. IEM archives HDDs in the daily summary database and includes them in Autoplot
temperature and energy charts. Like CDDs and GDDs, HDDs are available for download at
/request/daily.phtml.
IBW — Impact-Based Warning. An NWS warning format introduced in the early 2010s
that adds structured tags to tornado and severe thunderstorm warnings indicating the
expected intensity, likely damage, and who is at risk. IBW tags appear in the text of the
warning product and are also coded in the VTEC header. On IEM, IBW tags are captured
in the warning database, so Autoplot charts and VTEC searches that work with tornado
and severe thunderstorm warnings can filter or color-code by tag level. If you are doing
post-event analysis and want to know whether a warning that produced significant damage
was tagged accordingly, IEM’s VTEC archive is where to check.
IEMRE — IEM Reanalysis. IEM’s own gridded analysis product, which blends station
observations from the ASOS, COOP, and other networks onto a 0.125 × 0.125 degree grid
covering the contiguous United States. IEMRE is updated daily and extends back to 1950,
making it one of the longer gridded datasets covering the period before the modern reanalysis
era. It is most useful when you need a gridded estimate of temperature or precipitation at a
location without a nearby station — or when you want to compare a specific station’s recent
values against a regional background field. IEMRE’s resolution and methodology differ from
products like PRISM and ERA5; it is an IEM-specific product, which means its strengths
and limitations are distinct from more widely used gridded datasets.

Mastering the Mesonet 117
LDM — Local Data Manager. The Unidata software system that powers IEM’s real-time
data ingestion. The LDM is a distributed data subscription and relay network: IEM
subscribes to feeds from the NWS Family of Services, ASOS networks, and other providers,
and the LDM delivers those data streams in real time to IEM’s database systems. From a
user perspective, the LDM is invisible — it is the reason IEM has NWS products within
seconds of issuance and ASOS observations within minutes of the observation time. For
advanced users, IEM exposes a data request interface at /request/ldm.php that allows
bulk retrieval of LDM-delivered product streams.
LSR — Local Storm Report. The structured NWS text product issued by forecast offices
to document significant weather observations: storm damage, large hail, measured wind
gusts, tornadoes, flash flooding, heavy snowfall. LSRs are issued in real time during events
and are the primary source for IEM’s storm event database. On IEM, LSRs are searchable
at /lsr/ and downloadable as shapefiles at /request/gis/lsrs.phtml. Because LSRs are
issued by human forecasters making real-time decisions about what to document, they are a
qualitative record rather than a complete inventory: an unmeasured hail event in a cornfield
gets no LSR; a 1.75-inch stone that breaks a windshield in a parking lot often does.
MCD—MesoscaleConvectiveDiscussion. TheStormPredictionCenter’sreal-timeproduct
issued when a watch is possible or a developing weather situation warrants detailed analysis
but does not yet rise to the level of a watch. MCDs are the SPC forecasters’ running
commentary during active weather — often dense with technical meteorological reasoning
about shear profiles, CAPE, and boundary locations. On IEM, MCDs are archived and
downloadable as GIS shapefiles at /request/gis/spc_mcd.phtml. They are particularly
useful for post-event analysis because they document SPC’s thinking at the time, not after
the fact.
MOS — Model Output Statistics. A statistical post-processing technique that translates
raw numerical model output into station-specific forecast guidance by applying regression
equations derived from years of matched model-output/observation pairs. On IEM, MOS
is the entire content of the Datasets → MOS section: a deep archive of operational MOS
guidance going back decades, covering multiple NWS forecast models. What makes IEM’s
MOS archive genuinely useful is its historical depth — you can retrieve GFS-MOS guidance
issued on any date back to the 1990s and compare it against what actually happened, which
is the foundation of any serious forecast verification project. Models archived include AVN,
GFS, ETA, NAM, NBS, NBE, ECM, LAV (LAMP), and MEX.

Mastering the Mesonet 118
OGC — Open Geospatial Consortium. The standards body that defines interoperability
protocols for geographic information systems, including WMS (Web Map Service), WFS
(Web Feature Service), and WCS (Web Coverage Service). On IEM, OGC refers specifically
to the /ogc/ endpoint that exposes IEM’s spatial data layers in standard OGC formats. If
you use QGIS, ArcGIS, or any other GIS software that can consume WMS or WFS feeds, the
IEM OGC service lets you load live and historical IEM data — warning polygons, NEXRAD
composites, station observations — directly into your mapping environment.
PDS — Particularly Dangerous Situation. An NWS designation applied to tornado watches
when atmospheric conditions suggest an elevated risk of long-track, violent tornadoes —
EF4 and EF5 events. PDS watches carry the phrase “Particularly Dangerous Situation”
in the watch product text and are coded in the VTEC header. On IEM, PDS status is
captured in the VTEC warning database, so you can filter the historical tornado watch
archive to identify PDS events for any WFO’s area. They are rare: a PDS tornado watch in
a mid-Atlantic WFO’s area may appear only once or twice per decade.
PIL — Product Identifier Locator. The AFOS identifier that uniquely identifies any NWS
text product: a six-character string combining a three-character category code (such as
AFD for Area Forecast Discussion) and a three-character location identifier (such as CTP
for State College). On IEM, PILs are how you retrieve specific NWS text products from the
archive. The text product search at /wx/afos/p.php takes a PIL and returns the full text
of the product, including historical versions. Knowing the PIL structure — and the fact
that it is consistent across all NWS offices — is what makes IEM’s text product archive
navigable rather than a flat dump of thousands of files.
PIREP — Pilot Report. An aviation weather observation made by a flight crew and
transmittedto the NWS AviationWeatherCenter. PIREPs report actual in-flightconditions:
turbulence intensity and altitude, icing conditions and altitude, sky condition, and visibility
aloft. Unlike surface observations, PIREPs provide direct measurement of atmospheric
conditions at altitude — which is why they remain valuable for verifying numerical model
forecasts of upper-tropospheric turbulence and icing. On IEM, PIREPs are available as a
GIS shapefile download at /request/gis/pireps.php and appear in the Datasets menu.

Mastering the Mesonet 119
QC — Quality Control. In the IEM context, the suite of automated and manual processes
applied to incoming observation data to detect and flag erroneous values. IEM uses multiple
QClayers: automatedrangechecks,consistencychecksbetweenneighboringstations,MADIS
network QC from the NWS, and human review logged in the public QC ticket system at
/QC/tickets.phtml. Data that has failed one or more QC checks is flagged rather than
deleted; the flag allows downstream users to decide whether to include or exclude the value.
Understanding IEM’s QC flags — and the distinction between “flagged” and “removed”
data — matters whenever you are building a dataset for analysis.
SHEF — Standard Hydrometeorological Exchange Format. The data encoding format
used throughout the NWS hydrology community to transmit river and environmental sensor
observations. SHEF encodes time series of observed values with physical element codes and
quality flags in a compact text format. On IEM, SHEF appears primarily in the DCP/HADS
context: river gauge and soil sensor data often arrives at IEM encoded in SHEF, and some
IEM download portals allow retrieval in SHEF format for users whose analysis software
expects it.
SIGMET — Significant Meteorological Information. An aviation weather advisory issued
by the NWS Aviation Weather Center for meteorological conditions considered hazardous
to all aircraft: severe or extreme turbulence, severe icing not associated with thunder-
storms, widespread dust storms or sandstorms, and volcanic ash. In the U.S., SIGMETs
also include Convective SIGMETs for large convective areas, embedded thunderstorms,
and tornadoes. On IEM, SIGMETs are archived and downloadable as GIS shapefiles at
/request/gis/awc_sigmets.phtml.
SPC — Storm Prediction Center. The NWS national center in Norman, Oklahoma,
responsible for convective outlooks, tornado and severe thunderstorm watches, and mesoscale
discussions. On IEM, SPC products are woven throughout: Autoplot has multiple charts
derived from SPC watch and outlook data, the GIS shapefile downloads include SPC
convective outlooks, SPC watches, and SPC MCDs, and the VTEC archive integrates
SPC-issued watch polygons alongside WFO-issued local warnings. The IEM VTEC system
treats SPC watches as VTEC events in their own right, with ETNs that track each watch
from issuance through cancellation.

Mastering the Mesonet 120
SPS — Special Weather Statement. The NWS text product used for weather situations that
aresignificantbutdonotrisetothelevelrequiringaformalwatchorwarning. AnSPSmight
cover a brief period of locally dense fog, a wind advisory situation that does not quite meet
advisory thresholds, or significant but not severe weather. On IEM, SPS products are in
the text archive and are also downloadable as GIS shapefiles at /request/gis/sps.phtml.
The shapefile version is useful because SPS polygons, like all VTEC-encoded NWS products,
carry geographic boundaries that let you map where the statement applied.
TAF — Terminal Aerodrome Forecast. The NWS aviation point forecast issued for airports,
coveringa24-or30-hourperiodinastructuredformatthatspecifiesexpectedwind, visibility,
weather phenomena, and sky condition in coded groups. TAFs are issued by NWS Weather
ForecastOfficesfourtimesdailyandaretheprimaryaviationforecastproductforinstrument
flight planning. On IEM, TAF data is archived and downloadable at /request/taf.php,
making it possible to retrieve historical TAF guidance for any airport and compare forecast
conditions against the ASOS observations that were actually recorded.
Trace — The IEM convention for precipitation amounts too small to be measured but not
zero. IEM represents trace precipitation as 0.0001 inches in numerical fields — enough to be
nonzero in calculations and queries, and distinguishable from missing data, but below the
0.01-inch threshold of measurability. This convention is important when you are working
with precipitation frequency statistics: days with trace amounts should typically be excluded
from analyses of “measurable precipitation” but should not be treated as dry days. When
you download ASOS or COOP precipitation data from IEM and see 0.0001 in a daily or
hourly column, that is a trace observation, not a rounding artifact.
UGC — Universal Geographic Code. The NWS coding system for identifying the forecast
zones and counties to which warnings and advisories apply. A UGC code is a six-character
identifier: a two-letter state abbreviation, a one-letter type indicator (Z for forecast zone, C
for county/parish), and a three-digit number. On IEM, UGC codes are the mechanism by
whichVTECwarningsarelinkedtogeographicareas: whenyousearchIEM’swarningarchive
by county or zone, you are querying on UGC codes. Understanding UGC is important when
you want to analyze warning statistics for a specific county or group of counties, because
the county and the forecast zone do not always overlap cleanly.

Mastering the Mesonet 121
USCRN—U.S.ClimateReferenceNetwork. TheNWSnetworkofhigh-precisionautomated
climate monitoring stations sited specifically to provide long-term climate change detection
with minimalsiting bias and no urban heat island contamination. USCRN stations use triple-
redundant temperature sensors, weighing-bucket precipitation gauges, and solar radiation
sensors, and are sited in rural locations away from human infrastructure. On IEM, USCRN
data is available at /uscrn/ and downloadable at /request/uscrn.php. For climate trend
analysis where siting quality matters, USCRN is the most defensible network IEM provides
access to — the tradeoff is that there are far fewer stations than ASOS or COOP.
VTEC — Valid Time Event Code. The structured coding system the NWS embeds in every
watch, warning, and advisory product. A VTEC string encodes the issuing office, the action
being taken (new issuance, update, cancellation, expiration), a two-letter phenomena code
(TO for tornado, SV for severe thunderstorm, FF for flash flood), a one-letter significance
code (W for warning, A for advisory, Y for watch), and an Event Tracking Number. On IEM,
VTEC is the backbone of the entire warning archive: every event has a unique identifier
assembled from these components, which is what makes it possible to search for all tornado
warnings issued by a specific office in a specific year, or to retrieve the full lifecycle —
issuance, updates, verification, expiration — of any individual warning event. Understanding
VTEC is what separates using IEM’s warning tools from just reading storm reports on a
news site.
WFO — Weather Forecast Office. The local NWS offices responsible for issuing watches,
warnings, advisories, and forecasts for their county warning areas. The contiguous U.S. has
122 WFOs. On IEM, the WFO is the fundamental unit of the warning archive: every VTEC
event belongs to one WFO, warnings are organized by WFO, and most Autoplot charts
that show warning statistics present data at the WFO level. Pennsylvania falls under four
WFOs — State College (CTP), Philadelphia (PHI), Pittsburgh (PBZ), and Mount Holly, NJ
(PHI) — with BWI occasionally relevant for southernmost counties. Knowing your WFO’s
identifier is the starting point for most VTEC searches on IEM.

| Mastering | the Mesonet |     |     | 122 |
| --------- | ----------- | --- | --- | --- |
WPC — Weather Prediction Center. The NWS national center in College Park, Maryland,
responsiblefornationalquantitativeprecipitationforecasts(QPF),excessiverainfalloutlooks,
and Mesoscale Precipitation Discussions (MPDs). On IEM, WPC products appear in two
places: the MPD shapefiles, downloadable at /request/gis/wpc_mpd.phtml, which are
essential for analyzing the forecaster reasoning around significant precipitation events; and
the Autoplot chart library, which includes charts derived from WPC QPF data. For anyone
studying heavy precipitation events in Pennsylvania — a region where WPC watches closely
because of its complex terrain and frequent high-impact rainfall — the WPC MPD archive
| on IEM | is a frequently | underused | resource. |     |
| ------ | --------------- | --------- | --------- | --- |

| Appendix | A   | — Network |     | Quick | Reference |     |
| -------- | --- | --------- | --- | ----- | --------- | --- |
This table covers the major observing networks accessible through the IEM. Network
IDs follow IEM conventions (state-prefixed where applicable; the examples below use
Pennsylvania). Archive depth reflects typical record start dates; individual stations vary.
Use the station locator at mesonet.agron.iastate.edu/sites/locate.php to check the actual
| begin date | and coverage | flags for any  | specific | station.      |              |         |
| ---------- | ------------ | -------------- | -------- | ------------- | ------------ | ------- |
| Network    | ID           |                |          |               |              |         |
| (PA        |              | What           | It       | Archive       | Update       | Key IEM |
| example)   | Full Name    | Measures       |          | Depth         | Frequency    | URL     |
| PA_ASOS    | Pennsylvania | Temp,          | dew      | ~1928 at      | Hourly (plus | /ASOS/  |
|            | ASOS         | point,         | wind,    | major         | specials);   |         |
|            |              | visibility,    |          | airports;     | 1-minute     |         |
|            |              | ceiling,       |          | ~1994–1996    | archive at   |         |
|            |              | precipitation, |          | at most       | select sites |         |
|            |              | pressure       |          | stations      |              |         |
| PACLI-     | PA           | Daily          |          | ~1888–present | Once daily   | /COOP/  |
| MATE       | Long-Term    | max/min        |          | at longest-   | (observer-   |         |
|            | Climate      | temp,          |          | running       | reported)    |         |
|            | (COOP)       | precipitation, |          | stations      |              |         |
snowfall,
|          |            | snow           | depth  |               |            |            |
| -------- | ---------- | -------------- | ------ | ------------- | ---------- | ---------- |
| PA_COCO- | PA         | Daily          |        | ~2007–present | Once daily | /cocorahs/ |
| RAHS     | CoCoRaHS   | precipitation, |        |               | (observer- |            |
|          |            | snowfall,      | hail   |               | reported)  |            |
| PA_DCP   | PA Data    | River          | stage, | Varies by     | Hourly;    | /DCP/      |
|          | Collection | streamflow,    |        | station; some | varies by  |            |
|          | Platforms  | soil           |        | back to       | station    |            |
|          | (HADS)     | temp/mois-     |        | 1970s         |            |            |
|          |            | ture,          | remote |               |            |            |
precip
123

| Mastering | the Mesonet |          |         |           | 124     |
| --------- | ----------- | -------- | ------- | --------- | ------- |
| Network   | ID          |          |         |           |         |
| (PA       |             | What It  | Archive | Update    | Key IEM |
| example)  | Full Name   | Measures | Depth   | Frequency | URL     |
PA_RWIS PA Roadway Temp, wind, ~2000–present Every 20–60 /RWIS/
|     | Weather     | pavement |     | minutes |     |
| --- | ----------- | -------- | --- | ------- | --- |
|     | Information | temp,    |     |         |     |
|     | Systems     | pavement |     |         |     |
condition,
road cameras
PA_AWOS Pennsylvania Temp, wind, ~1993–present Varies by /AWOS/
|     | AWOS | altimeter;    |     | tier;     |     |
| --- | ---- | ------------- | --- | --------- | --- |
|     |      | precipitation |     | typically |     |
|     |      | and sky at    |     | hourly    |     |
AWOS-3P
sites
| IACLIMATE | Iowa COOP | Same as       | ~1873–present | Once daily | /COOP/ |
| --------- | --------- | ------------- | ------------- | ---------- | ------ |
| (Iowa     | Long-Term | COOP;         |               |            |        |
| example)  |           | Iowa-specific |               |            |        |
archive
| ISUSM | ISU Soil | Soil temp    | ~2012–present | Hourly | /agclimate/ |
| ----- | -------- | ------------ | ------------- | ------ | ----------- |
|       | Moisture | and moisture |               |        |             |
|       | Network  | at multiple  |               |        |             |
depths, air
temp, solar
radiation,
ET
| SCAN | USDA      | Soil temp    | ~2000–present | Hourly | /scan/ |
| ---- | --------- | ------------ | ------------- | ------ | ------ |
|      | NRCS Soil | and moisture | at most sites |        |        |
|      | Climate   | at multiple  |               |        |        |
|      | Analysis  | depths, air  |               |        |        |
|      | Network   | temp, wind,  |               |        |        |
solar
radiation,
precipitation

| Mastering | the Mesonet  |           |               |           | 125     |
| --------- | ------------ | --------- | ------------- | --------- | ------- |
| Network   | ID           |           |               |           |         |
| (PA       |              | What It   | Archive       | Update    | Key IEM |
| example)  | Full Name    | Measures  | Depth         | Frequency | URL     |
| USCRN     | U.S. Climate | Triple-   | ~2002–present | Hourly    | /uscrn/ |
|           | Reference    | redundant |               |           |         |
|           | Network      | temp,     |               |           |         |
precipitation,
solar
radiation,
wind, soil
temp/mois-
ture
| NLAE | NLAE Flux | Eddy          | Varies by | Sub-hourly | /nstl_flux/ |
| ---- | --------- | ------------- | --------- | ---------- | ----------- |
|      | Tower     | covariance    | tower     |            |             |
|      | Network   | flux measure- |           |            |             |
ments
|     |     | (energy, CO�, |     |     |     |
| --- | --- | ------------- | --- | --- | --- |
water vapor),
micromet
| SCHOOL- | TV Station  | Temp, dew      | ~2000–present | Typically | /other/ |
| ------- | ----------- | -------------- | ------------- | --------- | ------- |
| NET     | Schoolnet / | point, wind,   | at oldest     | hourly    |         |
|         | WeatherNet  | precipitation; | stations      |           |         |
varies by
station
| HADS       | Hydrometeo- | River stage  | Varies | Hourly to | /DCP/ |
| ---------- | ----------- | ------------ | ------ | --------- | ----- |
| (national) | rological   | (HP),        |        | 6-hourly  |       |
|            | Automated   | streamflow   |        |           |       |
|            | Data System | (QR), precip |        |           |       |
(PC), soil
temp (TS);
SHEF-coded
| IEMRE     | IEM        | Gridded | 1893–present | Daily update | /iemre/ |
| --------- | ---------- | ------- | ------------ | ------------ | ------- |
| (gridded) | Reanalysis | temp,   |              |              |         |
precipitation,
solar
|     |     | radiation — |     |     |     |
| --- | --- | ----------- | --- | --- | --- |
¼° grid,
CONUS

| Mastering | the Mesonet |     |          |       |     |     |     |     |     |     | 126 |
| --------- | ----------- | --- | -------- | ----- | --- | --- | --- | --- | --- | --- | --- |
| Notes     | on Network  |     | Coverage | Flags |     |     |     |     |     |     |     |
When you pull up any ASOS or AWOS station page, the attribute flags below tell you what
data is actually available beyond the basic hourly observation. These flags appear in the
station metadata and matter when you are deciding which station to anchor an analysis
on.
| Flag      |     |     |     |     | Meaning  |      |         |     |           |           |     |
| --------- | --- | --- | --- | --- | -------- | ---- | ------- | --- | --------- | --------- | --- |
| HAS1MIN=1 |     |     |     |     | 1-minute | ASOS | archive |     | available | (download |     |
at /request/asos/1min.phtml)
| HAS_PHOUR=1 |     |     |     |     | Hourly   | precipitation |     | bucket    | data | available |     |
| ----------- | --- | --- | --- | --- | -------- | ------------- | --- | --------- | ---- | --------- | --- |
| HASTAF=1    |     |     |     |     | Terminal | Aerodrome     |     | Forecasts |      | issued    | for |
this station
| IS_AWOS=1 |     |     |     |     | Station | is AWOS, |     | not ASOS | —   | check | tier |
| --------- | --- | --- | --- | --- | ------- | -------- | --- | -------- | --- | ----- | ---- |
for capability
| GHCNH_ID |     |     |     |     | Corresponding |     | GHCN-Hourly |     |     | identifier |     |
| -------- | --- | --- | --- | --- | ------------- | --- | ----------- | --- | --- | ---------- | --- |
(NCEI cross-reference)
| FLOOR        |            |     |     |          | Earliest      | date  | IEM    | considers     | reliable |        | for this |
| ------------ | ---------- | --- | --- | -------- | ------------- | ----- | ------ | ------------- | -------- | ------ | -------- |
|              |            |     |     |          | station       | — may | differ | from          | archive  | begin  |          |
| SHEF_6HR_SRC |            |     |     |          | DCP           | gauge | used   | to supplement |          | 6-hour |          |
|              |            |     |     |          | precipitation |       | totals |               |          |        |          |
| Network      | Comparison |     | at  | a Glance |               |       |        |               |          |        |          |
Historical
| Network |     | Depth     |            | Spatial    | Density | Precip     | Quality   |     | Best         | Use       | Case    |
| ------- | --- | --------- | ---------- | ---------- | ------- | ---------- | --------- | --- | ------------ | --------- | ------- |
| ASOS    |     | High      | (80+ years | Low–Medium |         | Good;      | known     |     | Hourly       |           |         |
|         |     | at major  |            | (airports  | only)   | snowfall   |           |     | climatology, |           |         |
|         |     | airports) |            |            |         | undercount |           |     | event        | timing,   |         |
|         |     |           |            |            |         |            |           |     | standard     |           | obs     |
| COOP    |     | Very      | High       | Medium     |         | Good;      | observer- |     | Long-term    |           |         |
|         |     | (130+     | years at   |            |         | consistent |           |     | climate      |           | trends, |
|         |     | oldest    | sites)     |            |         |            |           |     | daily        | extremes, |         |
normals

| Mastering | the Mesonet |     |     |     |     | 127 |
| --------- | ----------- | --- | --- | --- | --- | --- |
Historical
| Network  | Depth |         | Spatial Density | Precip Quality | Best Use      | Case |
| -------- | ----- | ------- | --------------- | -------------- | ------------- | ---- |
| CoCoRaHS | Low   | (~2007) | Very High       | Good;          | Precipitation |      |
|          |       |         | (volunteer      | standardized   | spatial       |      |
|          |       |         | density)        | gauge          | variability,  |      |
storm totals
| DCP/HADS | Medium          |     | Low             | Variable | River stage, |     |
| -------- | --------------- | --- | --------------- | -------- | ------------ | --- |
|          | (1970s–present) |     | (river/remote   |          | hydrology,   |     |
|          |                 |     | sites)          |          | remote area  | obs |
| RWIS     | Medium          |     | Low–Medium      | Poor     | Pavement     |     |
|          | (~2000)         |     | (highway sites) |          | conditions,  |     |
winter event
analysis
| USCRN | Low | (~2002) | Very Low (~130  | Excellent | Climate    | trend   |
| ----- | --- | ------- | --------------- | --------- | ---------- | ------- |
|       |     |         | national sites) |           | detection, |         |
|       |     |         |                 |           | reference  | quality |
obs
| SCAN | Low | (~2000) | Very Low         | High | Soil        |     |
| ---- | --- | ------- | ---------------- | ---- | ----------- | --- |
|      |     |         | (research sites) |      | temperature |     |
and moisture,
agricultural
research
| IEMRE | Very   | High     | Complete (¼° | Derived | Gap-filling, |     |
| ----- | ------ | -------- | ------------ | ------- | ------------ | --- |
|       | (1893; | gridded) | grid)        |         | regional     |     |
background
fields
| Finding | Network | Station | Lists |     |     |     |
| ------- | ------- | ------- | ----- | --- | --- | --- |
Every IEM network has a station table listing all member stations with coordinates, archive
dates, and attributes. The network tables are at mesonet.agron.iastate.edu/sites/net-
works.php — select your state and network from the dropdown. The full table can be
exported as CSV or shapefile for use in GIS software or analysis scripts.
For single-station lookup by name, coordinates, or state, use the station locator at
mesonet.agron.iastate.edu/sites/locate.php.

| Appendix | B — | Complete | URL Directory |
| -------- | --- | -------- | ------------- |
AllURLsverifiedMarch2026. TheIEMbaseURLishttps://mesonet.agron.iastate.edu.
Paths below are relative to that base unless noted otherwise. In the HTML and EPUB
| versions, every | entry is a | live hyperlink. |     |
| --------------- | ---------- | --------------- | --- |
URLs are organized by function, not by menu location. Where a tool appears in multiple
contexts throughout the guide, it is listed under its primary use category.
| 1. Current       | Conditions |     |                                    |
| ---------------- | ---------- | --- | ---------------------------------- |
| Description      |            |     | URL                                |
| Current Mainpage |            |     | mesonet.agron.iastate.edu/current/ |
Current Temperature Map mesonet.agron.iastate.edu/current/in-
dex.phtml/air_temperature
Current Precipitation Map mesonet.agron.iastate.edu/current/in-
dex.phtml/precipitation
Current Station Plot Map mesonet.agron.iastate.edu/current/in-
dex.phtml/station_plot
Sortable Currents / My Favorites mesonet.agron.iastate.edu/my/current.phtml
Sortable Currents by NWS WFO mesonet.agron.iastate.edu/nws/obs.php
Sortable Currents by State mesonet.agron.iastate.edu/current/all.phtml
| ASOS Current | Conditions |     | mesonet.agron.iastate.edu/ASOS/cur- |
| ------------ | ---------- | --- | ----------------------------------- |
rent.phtml
RWIS Current Surface Conditions mesonet.agron.iastate.edu/RWIS/cur-
rentSF.phtml
| RWIS Current | Traffic |     | mesonet.agron.iastate.edu/RWIS/traf- |
| ------------ | ------- | --- | ------------------------------------ |
fic.phtml
| IEM One (Radar | + Warnings) |     | mesonet.agron.iastate.edu/one/ |
| -------------- | ----------- | --- | ------------------------------ |
Severe Weather Mainpage mesonet.agron.iastate.edu/current/se-
vere.phtml
Convective Watches Overview mesonet.agron.iastate.edu/current/sel.phtml
128

| Mastering   | the Mesonet |     |     | 129 |
| ----------- | ----------- | --- | --- | --- |
| Description |             |     | URL |     |
Hourly Precip (current) mesonet.agron.iastate.edu/rainfall/ob-
hour.phtml
DCP Current Map (by SHEF code) mesonet.agron.iastate.edu/DCP/map.php
| River Forecast  | Monitor   |        | mesonet.agron.iastate.edu/river/ |     |
| --------------- | --------- | ------ | -------------------------------- | --- |
| Current Warning | Shapefile | (live) | mesonet.agron.ias-               |     |
tate.edu/data/gis/shape/4326/us/cur-
rent_ww.zip
| Current NEXRAD | Storm | Attributes (live) | mesonet.agron.ias- |     |
| -------------- | ----- | ----------------- | ------------------ | --- |
tate.edu/data/gis/shape/4326/us/cur-
rent_nexattr.zip
| Current 24-hr | LSR Shapefile | (live) | mesonet.agron.ias- |     |
| ------------- | ------------- | ------ | ------------------ | --- |
tate.edu/data/gis/shape/4326/us/lsr_24hour.zip
| 2. Station      | Networks |     |                                            |     |
| --------------- | -------- | --- | ------------------------------------------ | --- |
| Description     |          |     | URL                                        |     |
| Station Locator |          |     | mesonet.agron.iastate.edu/sites/locate.php |     |
| Network         | Tables   |     | mesonet.agron.iastate.edu/sites/net-       |     |
works.php
| ASOS/AWOS | Mainpage |     | mesonet.agron.iastate.edu/ASOS/ |     |
| --------- | -------- | --- | ------------------------------- | --- |
ASOS Monthly Precip Tables mesonet.agron.iastate.edu/ASOS/re-
ports/mon_prec.php
| ASOS Recent | Observations |     | mesonet.agron.iastate.edu/ASOS/re- |     |
| ----------- | ------------ | --- | ---------------------------------- | --- |
cent.phtml
| AWOS Mainpage |     |     | mesonet.agron.iastate.edu/AWOS/ |     |
| ------------- | --- | --- | ------------------------------- | --- |
| COOP Mainpage |     |     | mesonet.agron.iastate.edu/COOP/ |     |
COOP Current Observations mesonet.agron.iastate.edu/COOP/cur-
rent.phtml
COOP 12Z Daily Reports mesonet.agron.iastate.edu/COOP/12z.php
| COOP Station | Map |     | mesonet.agron.iastate.edu/COOP/map/ |     |
| ------------ | --- | --- | ----------------------------------- | --- |
COOP Daily Records / Extremes mesonet.agron.iastate.edu/COOP/ex-
tremes.php
COOP Freeze Date Statistics mesonet.agron.iastate.edu/COOP/freez-
ing.php

| Mastering   | the Mesonet    |     |     |                    | 130 |
| ----------- | -------------- | --- | --- | ------------------ | --- |
| Description |                |     |     | URL                |     |
| COOP Snow   | Depth Duration |     |     | mesonet.agron.ias- |     |
tate.edu/COOP/snowd_duration.phtml
COOP Hourly Precip (HPD) mesonet.agron.iastate.edu/COOP/hpd.php
| COOP Period | Analysis |     |     | mesonet.agron.iastate.edu/COOP/peri- |     |
| ----------- | -------- | --- | --- | ------------------------------------ | --- |
ods.phtml
COOP Station Catalog mesonet.agron.iastate.edu/COOP/cat.phtml
| CoCoRaHS | Mainpage |     |     | mesonet.agron.iastate.edu/cocorahs/ |     |
| -------- | -------- | --- | --- | ----------------------------------- | --- |
CoCoRaHS Current Observations mesonet.agron.iastate.edu/cocorahs/cur-
rent.phtml
| CoCoRaHS | Observation | Listing |     | mesonet.agron.iastate.edu/coco- |     |
| -------- | ----------- | ------- | --- | ------------------------------- | --- |
rahs/obs.phtml
| DCP/HADS    | Mainpage     |     |     | mesonet.agron.iastate.edu/DCP/     |     |
| ----------- | ------------ | --- | --- | ---------------------------------- | --- |
| DCP Current | Observations |     |     | mesonet.agron.iastate.edu/DCP/cur- |     |
rent.phtml
DCP Station Site Page mesonet.agron.iastate.edu/DCP/site.phtml
DCP Tomb (unidentified stations) mesonet.agron.iastate.edu/DCP/tomb.phtml
| RWIS Mainpage |            |     |     | mesonet.agron.iastate.edu/RWIS/     |     |
| ------------- | ---------- | --- | --- | ----------------------------------- | --- |
| RWIS Current  | Conditions |     |     | mesonet.agron.iastate.edu/RWIS/cur- |     |
rent.phtml
| RWIS Road | Cameras |     |     | mesonet.agron.iastate.edu/RWIS/cam- |     |
| --------- | ------- | --- | --- | ----------------------------------- | --- |
era.phtml
ISU Soil Moisture Network mesonet.agron.iastate.edu/agclimate/
| SCAN Network   |               |     |     | mesonet.agron.iastate.edu/scan/      |     |
| -------------- | ------------- | --- | --- | ------------------------------------ | --- |
| USCRN          | Network       |     |     | mesonet.agron.iastate.edu/uscrn/     |     |
| NLAE Flux      | Tower Network |     |     | mesonet.agron.iastate.edu/nstl_flux/ |     |
| Other Networks |               |     |     | mesonet.agron.iastate.edu/other/     |     |
| Wind Rose      | by Station    |     |     | mesonet.agron.iastate.edu/sites/win- |     |
drose.phtml
| 3. Historical | and      | Climate | Data |                                        |     |
| ------------- | -------- | ------- | ---- | -------------------------------------- | --- |
| Description   |          |         |      | URL                                    |     |
| Climate       | Mainpage |         |      | mesonet.agron.iastate.edu/climate/     |     |
| COOP Normals  | Download |         |      | mesonet.agron.iastate.edu/COOP/dl/nor- |     |
mals.phtml

| Mastering   | the Mesonet |     |                                     | 131 |
| ----------- | ----------- | --- | ----------------------------------- | --- |
| Description |             |     | URL                                 |     |
| Climodat    | Application |     | mesonet.agron.iastate.edu/climodat/ |     |
Climodat Monitor (departures) mesonet.agron.iastate.edu/climodat/moni-
tor.php
IEM Explorer (interactive station browser) mesonet.agron.iastate.edu/explorer/
Autoplot (all charts) mesonet.agron.iastate.edu/plotting/auto/
| IEM Reanalysis | (IEMRE) |     | mesonet.agron.iastate.edu/iemre/ |     |
| -------------- | ------- | --- | -------------------------------- | --- |
IEMRE CONUS NetCDF Files mesonet.agron.iastate.edu/onsite/iemre/
| IEMRE | Daily API |     | mesonet.agron.ias- |     |
| ----- | --------- | --- | ------------------ | --- |
tate.edu/iemre/daily/{date}/{lat}/{lon}/json
| IEMRE | Multiday | API | mesonet.agron.iastate.edu/iemre/multi- |     |
| ----- | -------- | --- | -------------------------------------- | --- |
day/{date1}/{date2}/{lat}/{lon}/json
| Model | Output Statistics | (MOS) | mesonet.agron.iastate.edu/mos/ |     |
| ----- | ----------------- | ----- | ------------------------------ | --- |
MOS Interactive Table mesonet.agron.iastate.edu/mos/table.phtml
| MOS API | (JSON/CSV) |     | mesonet.agron.iastate.edu/api/1/docs#/de- |     |
| ------- | ---------- | --- | ----------------------------------------- | --- |
fault/service_mos__fmt__get
Sounding Archive (RAOB) mesonet.agron.iastate.edu/archive/raob/
| RAOB | Listing |     | mesonet.agron.ias- |     |
| ---- | ------- | --- | ------------------ | --- |
tate.edu/archive/raob/list.phtml
| RAOB | JSON API |     | mesonet.agron.ias- |     |
| ---- | -------- | --- | ------------------ | --- |
tate.edu/json/raob.py?help=
| Archive | Mainpage |     | mesonet.agron.iastate.edu/archive/ |     |
| ------- | -------- | --- | ---------------------------------- | --- |
Raw File Archive (date tree) mesonet.agron.iastate.edu/archive/data/
| Archive | Directory | Schema | mesonet.agron.ias- |     |
| ------- | --------- | ------ | ------------------ | --- |
tate.edu/archive/schema.php
Raw SAO/METAR Text Archive mesonet.agron.iastate.edu/archive/raw/sao/
NEXRAD Mosaic Documentation mesonet.agron.iastate.edu/docs/nexrad_mo-
saic/
| MRMS     | NetCDF Archive |     | mesonet.agron.iastate.edu/onsite/mrms/   |     |
| -------- | -------------- | --- | ---------------------------------------- | --- |
| Stage IV | Archive        |     | mesonet.agron.iastate.edu/onsite/stage4/ |     |
Rainfall / Stage IV Portal mesonet.agron.iastate.edu/rainfall/
Soil Moisture Satellite (SMOS) mesonet.agron.iastate.edu/smos/
| MTarchive | (BUFKIT | / model data) | mtarchive.geol.iastate.edu |     |
| --------- | ------- | ------------- | -------------------------- | --- |
Dataset Documentation mesonet.agron.iastate.edu/info/datasets/
| Variables | Reference |     | mesonet.agron.iastate.edu/info/vari- |     |
| --------- | --------- | --- | ------------------------------------ | --- |
ables.phtml
| Daily Feature | Archive |     | mesonet.agron.iastate.edu/onsite/fea- |     |
| ------------- | ------- | --- | ------------------------------------- | --- |
tures/past.php
Daily Feature Tags Index mesonet.agron.iastate.edu/onsite/fea-
tures/tags/
Time Machine (replay any IEM product) mesonet.agron.iastate.edu/timemachine/

| Mastering        | the Mesonet |     |                                      | 132 |
| ---------------- | ----------- | --- | ------------------------------------ | --- |
| Description      |             |     | URL                                  |     |
| Drought          | Monitor     |     | mesonet.agron.iastate.edu/dm/        |     |
| Ag Weather       | Portal      |     | mesonet.agron.iastate.edu/agweather/ |     |
| AgClimate        | Network     |     | mesonet.agron.iastate.edu/agclimate/ |     |
| Soil Temperature | Map         |     | mesonet.agron.iastate.edu/agcli-     |     |
mate/soilt.php
Soil Temp Probabilities mesonet.agron.iastate.edu/agclimate/soilt-
prob.php
| Soil Moisture | Time Series |     | mesonet.agron.iastate.edu/agcli- |     |
| ------------- | ----------- | --- | -------------------------------- | --- |
mate/smts.php
| AgClimate | Daily Download |     | mesonet.agron.iastate.edu/agcli- |     |
| --------- | -------------- | --- | -------------------------------- | --- |
mate/hist/dailyRequest.php
| AgClimate | Hourly Download |     | mesonet.agron.iastate.edu/agcli- |     |
| --------- | --------------- | --- | -------------------------------- | --- |
mate/hist/hourlyRequest.php
| Freeze | Map |     | mesonet.agron.ias- |     |
| ------ | --- | --- | ------------------ | --- |
tate.edu/GIS/apps/iem/freeze.phtml
Plant Hardiness Zones mesonet.agron.iastate.edu/topics/hardiness/
Pest Maps / GDD Forecasting mesonet.agron.iastate.edu/topics/pests/
COOP GIS Duration Apps mesonet.agron.iastate.edu/GIS/apps/coop/
| NEXRAD | by Year |     | mesonet.agron.iastate.edu/GIS/rad-by-year- |     |
| ------ | ------- | --- | ------------------------------------------ | --- |
fe.phtml
IEM Data in Published Research mesonet.agron.iastate.edu/info/refs.php
| 4. NWS       | / Warnings           | / VTEC |                                 |     |
| ------------ | -------------------- | ------ | ------------------------------- | --- |
| Description  |                      |        | URL                             |     |
| NWS Mainpage |                      |        | mesonet.agron.iastate.edu/nws/  |     |
| VTEC         | Browser (event view) |        | mesonet.agron.iastate.edu/vtec/ |     |
Warning Search by Point / County mesonet.agron.iastate.edu/vtec/search.php
| IEM Cow | (SBW Verification) |     | mesonet.agron.iastate.edu/cow/ |     |
| ------- | ------------------ | --- | ------------------------------ | --- |
IEM Raccoon (SBW PowerPoints) mesonet.agron.iastate.edu/raccoon/
| Local Storm | Report App |     | mesonet.agron.iastate.edu/lsr/ |     |
| ----------- | ---------- | --- | ------------------------------ | --- |
Text Archives Mainpage mesonet.agron.iastate.edu/nws/text.php
| AFOS     | Product Finder |     | mesonet.agron.iastate.edu/wx/afos/ |     |
| -------- | -------------- | --- | ---------------------------------- | --- |
| Products | by WFO by Date |     | mesonet.agron.ias-                 |     |
tate.edu/wx/afos/list.phtml

| Mastering   | the Mesonet       |     |                                | 133 |
| ----------- | ----------------- | --- | ------------------------------ | --- |
| Description |                   |     | URL                            |     |
| AFOS        | Bulk Retrieve API |     | mesonet.agron.iastate.edu/cgi- |     |
bin/afos/retrieve.py?help
| CLI Interactive | Map |     | mesonet.agron.iastate.edu/nws/climap.php |     |
| --------------- | --- | --- | ---------------------------------------- | --- |
CF6 Monthly Climate Table mesonet.agron.iastate.edu/nws/cf6table.php
SPC Outlook Search by Point mesonet.agron.iastate.edu/nws/spc_out-
look_search/
SPC Watches by Year mesonet.agron.iastate.edu/nws/watches.php
| SPC PDS | Watch Listing |     | mesonet.agron.ias- |     |
| ------- | ------------- | --- | ------------------ | --- |
tate.edu/nws/pds_watches.php
WPC Outlook Search by Point mesonet.agron.iastate.edu/nws/wpc_out-
look_search/
SPS Search by Point mesonet.agron.iastate.edu/nws/sps_search/
| SVR/TOR | Warning Tags | by WFO | mesonet.agron.ias- |     |
| ------- | ------------ | ------ | ------------------ | --- |
tate.edu/nws/list_tags.php
Max ETN by WFO by Year mesonet.agron.iastate.edu/vtec/maxetn.php
| VTEC | Events by Year | Table | mesonet.agron.ias- |     |
| ---- | -------------- | ----- | ------------------ | --- |
tate.edu/vtec/yearly_counts.php
Tornado / Flash Flood Emergencies mesonet.agron.iastate.edu/vtec/emergen-
cies.php
| PDS Warning | Listing |     | mesonet.agron.iastate.edu/vtec/pds.php |     |
| ----------- | ------- | --- | -------------------------------------- | --- |
HML River Data Download mesonet.agron.iastate.edu/request/hml.php
HML Forecast vs. Obs Plot (q=160) mesonet.agron.iastate.edu/plot-
ting/auto/?q=160
Autoplot — Warning Gantt (q=52) mesonet.agron.iastate.edu/plot-
ting/auto/?q=52
Autoplot — VTEC Counts Map (q=109) mesonet.agron.iastate.edu/plot-
ting/auto/?q=109
Autoplot — Days Since WWA (q=92) mesonet.agron.iastate.edu/plot-
ting/auto/?q=92
Autoplot — Accumulated WWA (q=44) mesonet.agron.iastate.edu/plot-
ting/auto/?q=44
Autoplot — Lead Time Dist. (q=211) mesonet.agron.iastate.edu/plot-
ting/auto/?q=211
5. Downloads

| Mastering   | the Mesonet |     | 134 |
| ----------- | ----------- | --- | --- |
| Description |             | URL |     |
ASOS/AWOS/METAR Download (UI) mesonet.agron.iastate.edu/request/down-
load.phtml
| ASOS CGI | Backend (scriptable) | mesonet.agron.iastate.edu/cgi- |     |
| -------- | -------------------- | ------------------------------ | --- |
bin/request/asos.py?help
| ASOS 1-Minute | Download | mesonet.agron.iastate.edu/re- |     |
| ------------- | -------- | ----------------------------- | --- |
quest/asos/1min.phtml
| Iowa AWOS | 1-Minute Download | mesonet.agron.iastate.edu/re- |     |
| --------- | ----------------- | ----------------------------- | --- |
quest/awos/1min.php
Climodat / COOP Download (processed) mesonet.agron.iastate.edu/re-
quest/coop/fe.phtml
COOP Raw Observations Download mesonet.agron.iastate.edu/request/coop/obs-
fe.phtml
| Daily Summaries | Download | mesonet.agron.iastate.edu/re- |     |
| --------------- | -------- | ----------------------------- | --- |
quest/daily.phtml
| Hourly | Precip Download | mesonet.agron.iastate.edu/re- |     |
| ------ | --------------- | ----------------------------- | --- |
quest/asos/hourlyprecip.phtml
| RWIS Download |     | mesonet.agron.iastate.edu/re- |     |
| ------------- | --- | ----------------------------- | --- |
quest/rwis/fe.phtml
| RWIS Soil | Download | mesonet.agron.iastate.edu/re- |     |
| --------- | -------- | ----------------------------- | --- |
quest/rwis/soil.phtml
RWIS Traffic Download mesonet.agron.iastate.edu/request/rwis/traf-
fic.phtml
| DCP/HADS | Download | mesonet.agron.iastate.edu/re- |     |
| -------- | -------- | ----------------------------- | --- |
quest/dcp/fe.phtml
| USCRN | Download | mesonet.agron.iastate.edu/re- |     |
| ----- | -------- | ----------------------------- | --- |
quest/uscrn.php
TAF Forecast Download mesonet.agron.iastate.edu/request/taf.php
Temperature / Winds Aloft Download mesonet.agron.iastate.edu/request/temp-
wind_aloft.php
| WMO | BUFR Surface Download | mesonet.agron.iastate.edu/re- |     |
| --- | --------------------- | ----------------------------- | --- |
quest/wmo_bufr_srf.php
| Warning | Polygons Shapefile | mesonet.agron.iastate.edu/re- |     |
| ------- | ------------------ | ----------------------------- | --- |
quest/gis/watchwarn.phtml
| LSR Archive | Shapefile | mesonet.agron.iastate.edu/re- |     |
| ----------- | --------- | ----------------------------- | --- |
quest/gis/lsrs.phtml
NEXRAD Storm Attributes Download mesonet.agron.iastate.edu/re-
quest/gis/nexrad_storm_attrs.php
| SPC Outlook | Shapefile | mesonet.agron.iastate.edu/re- |     |
| ----------- | --------- | ----------------------------- | --- |
quest/gis/spc_outlooks.phtml

| Mastering   | the Mesonet |                               | 135 |
| ----------- | ----------- | ----------------------------- | --- |
| Description |             | URL                           |     |
| SPC Watch   | Shapefile   | mesonet.agron.iastate.edu/re- |     |
quest/gis/spc_watch.phtml
| SPC MCD | Shapefile | mesonet.agron.iastate.edu/re- |     |
| ------- | --------- | ----------------------------- | --- |
quest/gis/spc_mcd.phtml
| WPC MPD | Shapefile | mesonet.agron.iastate.edu/re- |     |
| ------- | --------- | ----------------------------- | --- |
quest/gis/wpc_mpd.phtml
Special Weather Statement Shapefile mesonet.agron.iastate.edu/re-
quest/gis/sps.phtml
| CWA Shapefile |     | mesonet.agron.iastate.edu/re- |     |
| ------------- | --- | ----------------------------- | --- |
quest/gis/cwas.phtml
| SIGMET | Shapefile | mesonet.agron.iastate.edu/re- |     |
| ------ | --------- | ----------------------------- | --- |
quest/gis/awc_sigmets.phtml
| G-AIRMET | Shapefile | mesonet.agron.iastate.edu/re- |     |
| -------- | --------- | ----------------------------- | --- |
quest/gis/awc_gairmets.phtml
| PIREP | Shapefile | mesonet.agron.iastate.edu/re- |     |
| ----- | --------- | ----------------------------- | --- |
quest/gis/pireps.php
| Miscellaneous | GIS Downloads | mesonet.agron.iastate.edu/re- |     |
| ------------- | ------------- | ----------------------------- | --- |
quest/gis/misc.phtml
| GeoTIFF | Rasters | mesonet.agron.iastate.edu/GIS/rasters.php |     |
| ------- | ------- | ----------------------------------------- | --- |
MaxCSV (quick network snapshot) mesonet.agron.iastate.edu/re-
quest/maxcsv.py?help
Gibson Ridge Placefiles mesonet.agron.iastate.edu/request/grx/
| 6. Services  | and APIs     |                                          |     |
| ------------ | ------------ | ---------------------------------------- | --- |
| Description  |              | URL                                      |     |
| API Mainpage |              | mesonet.agron.iastate.edu/api/           |     |
| API v1       | Swagger Docs | mesonet.agron.iastate.edu/api/1/docs     |     |
| OGC Web      | Services     | mesonet.agron.iastate.edu/ogc/           |     |
| GIS Mainpage |              | mesonet.agron.iastate.edu/GIS/           |     |
| GOES         | GIS Products | mesonet.agron.iastate.edu/GIS/goes.phtml |     |
| NEXRAD       | RadView      | mesonet.agron.iastate.edu/GIS/rad-       |     |
view.phtml
| RadMap | API | mesonet.agron.ias- |     |
| ------ | --- | ------------------ | --- |
tate.edu/GIS/radmap_api.phtml

| Mastering   | the Mesonet           |                    | 136 |
| ----------- | --------------------- | ------------------ | --- |
| Description |                       | URL                |     |
| Radar       | + Warnings GIS Viewer | mesonet.agron.ias- |     |
tate.edu/GIS/apps/rview/warnings.phtml
| Watches | GIS Viewer | mesonet.agron.ias- |     |
| ------- | ---------- | ------------------ | --- |
tate.edu/GIS/apps/rview/watch.phtml
| Station | Comparison GIS | mesonet.agron.ias- |     |
| ------- | -------------- | ------------------ | --- |
tate.edu/GIS/apps/rview/compare.phtml
| RAOB | JSON API | mesonet.agron.ias- |     |
| ---- | -------- | ------------------ | --- |
tate.edu/json/raob.py?help=
| MOS API |     | mesonet.agron.iastate.edu/api/1/docs#/de- |     |
| ------- | --- | ----------------------------------------- | --- |
fault/service_mos__fmt__get
| MOS Raw | Download | mesonet.agron.iastate.edu/fe.phtml |     |
| ------- | -------- | ---------------------------------- | --- |
iembot (real-time data feed) mesonet.agron.iastate.edu/projects/iembot/
| LDM Data | Request | mesonet.agron.iastate.edu/request/ldm.php |     |
| -------- | ------- | ----------------------------------------- | --- |
7. Webcams
| Description |     | URL |     |
| ----------- | --- | --- | --- |
Webcam Viewer (realtime + archive) mesonet.agron.iastate.edu/cur-
rent/viewer.phtml
Webcam Project Overview mesonet.agron.iastate.edu/projects/web-
cam.php
RWIS Archived Webcam Imagery mesonet.agron.iastate.edu/RWIS/cam-
era.phtml
| ISU Campus | Webcams | mesonet.agron.iastate.edu/current/isu- |     |
| ---------- | ------- | -------------------------------------- | --- |
cams.phtml
| Lapse Builder |     | mesonet.agron.iastate.edu/cur- |     |
| ------------- | --- | ------------------------------ | --- |
rent/bloop.phtml
Recent Pre-Built Lapses mesonet.agron.iastate.edu/current/cam-
lapse/
| Cool Lapses | Archive | mesonet.agron.iastate.edu/cool/ |     |
| ----------- | ------- | ------------------------------- | --- |

| Mastering    | the Mesonet |                |                            | 137 |
| ------------ | ----------- | -------------- | -------------------------- | --- |
| 8. Admin,    | Info, and   | Site Resources |                            |     |
| Description  |             |                | URL                        |     |
| IEM Homepage |             |                | mesonet.agron.iastate.edu/ |     |
About / Applications Mainpage mesonet.agron.iastate.edu/apps.php
| QC Mainpage |     |     | mesonet.agron.iastate.edu/QC/ |     |
| ----------- | --- | --- | ----------------------------- | --- |
Public QC Ticket Log mesonet.agron.iastate.edu/QC/tickets.phtml
MADIS Network QC Overview mesonet.agron.iastate.edu/QC/madis/net-
work.phtml
Currently Offline Stations mesonet.agron.iastate.edu/QC/offline.php
| Variables | Reference |     | mesonet.agron.iastate.edu/info/vari- |     |
| --------- | --------- | --- | ------------------------------------ | --- |
ables.phtml
Dataset Documentation mesonet.agron.iastate.edu/info/datasets/
IEM Data in Published Research mesonet.agron.iastate.edu/info/refs.php
| IEM News | Archive |     | mesonet.agron.iastate.edu/on- |     |
| -------- | ------- | --- | ----------------------------- | --- |
site/news.phtml

| Appendix | C — | Autoplot |     | Chart |     | Reference |     |     |     |
| -------- | --- | -------- | --- | ----- | --- | --------- | --- | --- | --- |
All 260 Autoplot charts, organized by the category groupings used in the IEM’s own
interface. Charts are numbered q=1 through q=262, with gaps at q=214 and q=222
| (retired). Descriptions | are | drawn directly | from | the chart | source | code. |     |     |     |
| ----------------------- | --- | -------------- | ---- | --------- | ------ | ----- | --- | --- | --- |
Accessanychartat:
https://mesonet.agron.iastate.edu/plotting/auto/?q={number}
To download the data behind any chart, replace .png with .csv or .xlsx in the chart image
URL, or look for the CSV Data / Excel Download links below any generated chart.
Charts marked � are highlighted in the guide as particularly useful for weather hobbyists.
Daily
| q     |     | Title          |           |       |     | Description         |          |               |        |
| ----- | --- | -------------- | --------- | ----- | --- | ------------------- | -------- | ------------- | ------ |
| 51 �  |     | Accumulated    | Station   |       |     | This plot           | presents |               |        |
|       |     | Departures     | of        |       |     | accumulated         |          | totals        | and    |
|       |     | Precip/GDD/SDD |           |       |     | departures          | of       | growing       | degree |
|       |     | (Automated     | Stations) |       |     | days, precipitation |          |               | and    |
|       |     |                |           |       |     | stress degree       |          | days.         |        |
| 108 � |     | Accumulated    | Station   |       |     | This plot           | presents |               |        |
|       |     | Departures     | of        |       |     | accumulated         |          | totals        | and    |
|       |     | Precip/GDD/SDD |           | (Long |     | departures          | of       | growing       | degree |
|       |     | Term Climate)  |           |       |     | days (GDD),         |          | precipitation |        |
|       |     |                |           |       |     | and stress          | degree   | days          |        |
(SDD).
| 172 � |     | Accumulated   | Year        | to       | Date | / This chart     | presents |         | year to  |
| ----- | --- | ------------- | ----------- | -------- | ---- | ---------------- | -------- | ------- | -------- |
|       |     | Period Precip | /           | Snowfall | /    | date accumulated |          |         | variable |
|       |     | CDD /         | GDD /       | HDD      |      | for a station    |          | of your | choice.  |
| 149   |     | Aridity       | Index (High |          |      | This plot        | presents |         | a time   |
|       |     | Temperature   | minus       | Precip   |      | series of        | Aridity  | Index.  |          |
Departures)
138

| Mastering | the Mesonet |                        |               |           |         |              |               |               |                 | 139        |
| --------- | ----------- | ---------------------- | ------------- | --------- | ------- | ------------ | ------------- | ------------- | --------------- | ---------- |
| q         |             | Title                  |               |           |         | Description  |               |               |                 |            |
| 11        |             | ASOS                   | Daily Min/Max |           | Dew     | This         | plot          | presents      |                 | the range  |
|           |             | Point/Temp/Feels       |               | Like/RH   |         | between      |               | the           | min and         |            |
|           |             | for a Year             |               |           |         | maximum      |               | observation   |                 | of         |
|           |             |                        |               |           |         | your         | choice        | for           | a given         |            |
|           |             |                        |               |           |         | station      |               | and a         | given           | year.      |
| 94        |             | Bias of                | 24 Hour       | High+Low  |         | This         | plot          | looks         | at              | the effect |
|           |             | Computation            |               | by Hour   |         | of           | splitting     | a             | 24 hour         | period     |
|           |             |                        |               |           |         | at           | different     | hours         | of              | the day.   |
| 96        |             | Bias of                | 24 Hour       | Precip    |         | This         | plot          | looks         | at              | the bias   |
|           |             | Computation            |               | by Hour   |         | associated   |               | with          | computing       |            |
|           |             |                        |               |           |         | 24           | hour          | precipitation |                 | totals     |
|           |             |                        |               |           |         | using        | a             | given         | hour            | of the day |
|           |             |                        |               |           |         | as           | the           | delimiter.    |                 |            |
| 82        |             | Calendar               | of Daily      |           |         | This         | chart         | presents      |                 | a series   |
|           |             | Observations           | from          |           |         | of           | daily         | summary       | data            | as a       |
|           |             | Automated              | or            | Climate   | Sites   | calendar.    |               |               |                 |            |
| 218       |             | Daily NWS              | CLImate       |           | Report  | This         | produces      |               | an infographic  |            |
|           |             | Infographic            |               |           |         | with         | some          | of            | the information |            |
|           |             |                        |               |           |         | found        | presented     |               | in              | NWS        |
|           |             |                        |               |           |         | CLI          | reports.      |               |                 |            |
| 180       |             | Daily Temperature/Pre- |               |           |         | This         | application   |               | plots           | daily      |
|           |             | cip/Snowfall           | Climatology   |           |         | climatology  |               | for           | a location      | or         |
|           |             |                        |               |           |         | two          | of            | your choice.  |                 |            |
| 32 �      |             | Daily Departures       |               | /         |         | This         | plot          | presents      |                 | a daily    |
|           |             | Percentiles            | / Ranges      |           | for One | time         | series        | of            | variable        | of         |
|           |             | Year                   |               |           |         | your         | choice.       |               |                 |            |
| 21        |             | Change                 | in NCEI       | 1991-2020 |         | This         | autoplot      |               | intends         | to         |
|           |             | Daily Climatology      |               | over      | X       | show         | the           | spatial       | distribution    |            |
|           |             | Days                   |               |           |         | of           | the change    |               | in temperature  |            |
|           |             |                        |               |           |         | or           | precipitation |               | climatology     |            |
|           |             |                        |               |           |         | over         | a             | given         | period          | of days.   |
| 174       |             | Compare                | Daily         | High/Low  |         | This         | application   |               | generates       | a          |
|           |             | Temps                  | for ASOS      | Stations  |         | comparison   |               | of            | daily           | high and   |
|           |             |                        |               |           |         | low          | temperatures  |               | between         |            |
|           |             |                        |               |           |         | two          | automated     |               | ASOS            | sites      |
|           |             |                        |               |           |         | of           | your          | choosing.     |                 |            |
| 215       |             | Compare                | Daily         | High/Low  |         | This         | autoplot      |               | generates       |            |
|           |             | Temps                  | Distributions |           | over    | some         | metrics       |               | on the          |            |
|           |             | Two Periods            | of            | Years     |         | distribution |               | of            | temps           | over a     |
|           |             |                        |               |           |         | given        | period        |               | of years.       |            |

| Mastering | the Mesonet |       |     |     |     |             |     |     |     | 140 |
| --------- | ----------- | ----- | --- | --- | --- | ----------- | --- | --- | --- | --- |
| q         |             | Title |     |     |     | Description |     |     |     |     |
91 Consecutive Day Statistics of This plot produces statistics
|     |     | High+Low        | Temps       | /              | Precip | on        | min,  | max,          | and average |           |
| --- | --- | --------------- | ----------- | -------------- | ------ | --------- | ----- | ------------- | ----------- | --------- |
|     |     |                 |             |                |        | values    | of    | a variable    |             | over a    |
|     |     |                 |             |                |        | window    |       | of days.      |             |           |
| 66  |     | Consecutive     |             | Days Frequency |        | This      | chart | presents      |             | the daily |
|     |     | by DOY          | for         |                |        | frequency |       | of the        | given       | date      |
|     |     | High/Low/Precip |             |                |        | having    | the   | prescribed    |             |           |
|     |     | Above/Below     |             | Threshold      |        | number    |       | of previous   |             | days      |
|     |     |                 |             |                |        | above     | or    | below         | some        |           |
|     |     |                 |             |                |        | provided  |       | treshold.     |             |           |
| 216 |     | Consecutive     |             | Days by        | Year   | This      | chart | presents      |             | the       |
|     |     | with Daily      | Summary     |                |        | longest   |       | daily streaks |             | of        |
|     |     | Variable        | Above/Below |                |        | having    | some  | threshold     |             | meet.     |
Threshold
| 9   |     | Cooling/Growing/Heat- |                 |     |       | This  | chart       | produces   |     | the     |
| --- | --- | --------------------- | --------------- | --- | ----- | ----- | ----------- | ---------- | --- | ------- |
|     |     | ing/Stress            | Degree          | Day | Daily | daily | climatology |            | of  | Degree  |
|     |     | Values                | and Climatology |     |       | Days  | for         | a location |     | of your |
choice.
| 49    |     | Daily/Multi-Day      |                 | Frequency |     | This        | plot  | presents     | the      |         |
| ----- | --- | -------------------- | --------------- | --------- | --- | ----------- | ----- | ------------ | -------- | ------- |
|       |     | of Some              | Threshold/Range |           |     | observed    |       | frequency    |          | of some |
|       |     | (snow,               | precip,         | temps)    |     | daily       | event | happening.   |          |         |
| 113 � |     | Daily Climatology    |                 |           |     | Presents    |       | the simple   |          | daily   |
|       |     |                      |                 |           |     | climatology |       | as           | computed | by      |
|       |     |                      |                 |           |     | period      | of    | record       | data.    |         |
| 176   |     | Daily/Monthly/Yearly |                 |           |     | This        | chart | shows        | the      | margin  |
|       |     | Records              | Beat            | Margin    |     | by          | which | a new        | daily    | high    |
|       |     |                      |                 |           |     | and         | low   | temperatures |          | record  |
|       |     |                      |                 |           |     | beat        | the   | previously   |          | set     |
record.
| 5 � |     | Daily Records |             | for each |         | This        | plot   | displays   | the    | dates    |
| --- | --- | ------------- | ----------- | -------- | ------- | ----------- | ------ | ---------- | ------ | -------- |
|     |     | month         | of year     |          |         | with        | the    | monthly    | record | of       |
|     |     |               |             |          |         | your        | choice | displayed. |        |          |
| 31  |     | Extreme       | Jumps       | or       | Dips in | This        | chart  | attempts   |        | to       |
|     |     | High/Low      | Temperature |          | over    | assess      | by     | now        | much   | the high |
|     |     | X days        |             |          |         | temperature |        | can        | change |          |
|     |     |               |             |          |         | between     |        | two or     | three  | periods  |
|     |     |               |             |          |         | of          | time.  |            |        |          |

| Mastering | the Mesonet |                   |           |                |          |               |               |                |            | 141   |
| --------- | ----------- | ----------------- | --------- | -------------- | -------- | ------------- | ------------- | -------------- | ---------- | ----- |
| q         |             | Title             |           |                |          | Description   |               |                |            |       |
| 147       |             | Frequency         | of        | One Station    |          | This plot     | presents      |                | the daily  |       |
|           |             | Warmer/Wetter     |           | than           |          | frequency     | of            | the first      | station    |       |
|           |             | Another           |           |                |          | having        | a higher      | value          | than       |       |
|           |             |                   |           |                |          | the second    | station.      |                |            |       |
| 205       |             | Frequency         | of        | Daily          |          | The IEM       | computes      |                | daily      |       |
|           |             | Summary           | Variables | for            |          | summaries     | of            | ASOS           | station    |       |
|           |             | Automated         | Stations  |                |          | data based    | on            | available      |            |       |
|           |             |                   |           |                |          | station       | summaries     |                | and        |       |
|           |             |                   |           |                |          | computed      | summaries     |                | based      |       |
|           |             |                   |           |                |          | on available  |               | hourly         | data.      |       |
| 252       |             | Frequency         | of        | Daily Variable |          | This autoplot |               | generates      |            | a     |
|           |             | Above/Below       |           | Threshold      | over     | map of        | the frequency |                | of         |       |
|           |             | period            | of days   | (map)          |          | having        | at least      | one            | day        |       |
|           |             |                   |           |                |          | at-or-above   | or            | below          | a          | given |
|           |             |                   |           |                |          | threshold     | between       |                | an         |       |
|           |             |                   |           |                |          | inclusive     | period        | of             | days.      |       |
| 7         |             | Growing           | Degree    | Day            | Periods  | This plot     | presents      |                | the period |       |
|           |             | for One           | Year      | by Planting    |          | over which    | growing       |                | degree     |       |
|           |             | Date              |           |                |          | days were     | accumulated   |                |            |       |
|           |             |                   |           |                |          | between       | the           | two thresholds |            |       |
|           |             |                   |           |                |          | provided      | by            | the user.      |            |       |
| 240       |             | Growing           | Degree    | Day            | Obs +    | This autoplot |               | combines       |            |       |
|           |             | Near Term         | Forecast  |                |          | growing       | degree        | day            |            |       |
|           |             |                   |           |                |          | observations  |               | along          | with       | a     |
|           |             |                   |           |                |          | near term     | forecast      |                | from       | the   |
|           |             |                   |           |                |          | deterministic |               | GFS            | and        | NWS   |
|           |             |                   |           |                |          | NDFD          | models.       |                |            |       |
| 204       |             | Heatmap           | of        | Daily /        | Trailing | This app      | generates     |                | a          |       |
|           |             | Daily Temperature |           | /              | Precip   | heatmap-like  |               | presentation   |            | of    |
|           |             |                   |           |                |          | daily climate |               | data           | of your    |       |
choice.
| 225 |     | Heatmap     | of         | Distribution | of    | Departure        | from            | climatology |           |     |
| --- | --- | ----------- | ---------- | ------------ | ----- | ---------------- | --------------- | ----------- | --------- | --- |
|     |     | Trailing    | Departures |              |       | metrics          | have            | an annual   |           |     |
|     |     |             |            |              |       | signal           | that is         | a function  |           | of  |
|     |     |             |            |              |       | the climatology. |                 |             |           |     |
| 61  |     | High/Low    | Temp       |              |       | This plot        | presents        |             | the       |     |
|     |     | above/below |            | avg OR       | dry   | current          | streak          | of days     | with      | a   |
|     |     | streaks     | by NWS     | CLI          | Sites | high or          | low temperature |             |           |     |
|     |     |             |            |              |       | above            | or at-below     |             | the daily |     |
|     |     |             |            |              |       | average          | temperature.    |             |           |     |

| Mastering | the Mesonet |                      |               |             |       |                  |               |              |           | 142    |
| --------- | ----------- | -------------------- | ------------- | ----------- | ----- | ---------------- | ------------- | ------------ | --------- | ------ |
| q         |             | Title                |               |             |       | Description      |               |              |           |        |
| 19        |             | Histogram            | (weathergami) |             | of    | This             | chart         | displays     | a         |        |
|           |             | Daily High/Low       |               | Temps       | +     | histogram        |               | of daily     | high      | and    |
|           |             | Ranges               |               |             |       | low temperatures |               |              | for       | a      |
|           |             |                      |               |             |       | station          | of            | your choice. |           |        |
| 35        |             | Histogram            | of            | X Hour      |       | This             | plot presents |              | a         |        |
|           |             | Temp/RH/Dew/Pressure |               |             |       | histogram        |               | of the       | change    | in     |
|           |             | Changes              |               |             |       | some             | observed      | variable     |           | over   |
|           |             |                      |               |             |       | a given          | number        |              | of hours. |        |
| 60        |             | Hourly               | Variable      |             |       | This             | plot presents |              | hourly    |        |
|           |             | Frequencies/Min/Max  |               |             | by    | variable         | metrics       |              | from      |        |
|           |             | Week of              | Year          |             |       | automated        |               | stations.    |           |        |
| 86 �      |             | IEMRE                | Daily         | Reanalysis  |       | This             | map           | presents     | a daily   |        |
|           |             | Plots                |               |             |       | IEM              | ReAnalysis    |              | variable  | of     |
|           |             |                      |               |             |       | your             | choice.       |              |           |        |
| 249       |             | IEMRE                | Hourly        | Reanalysis  |       | This             | map           | presents     | an        | hourly |
|           |             | Plots                |               |             |       | IEM              | ReAnalysis    |              | variable  | of     |
|           |             |                      |               |             |       | your             | choice.       |              |           |        |
| 139       |             | Largest              | / Smallest    |             | Local | This             | table         | presents     | the       | 10     |
|           |             | Calendar             | Day           | Temperature |       | largest          | or            | smallest     |           |        |
|           |             | Differences          |               |             |       | differences      |               | between      | the       |        |
|           |             |                      |               |             |       | lowest           | and           | highest      | air       |        |
|           |             |                      |               |             |       | temperature      |               | for          | a local   |        |
|           |             |                      |               |             |       | calendar         | day.          |              |           |        |
168 Latest Date of Year for High This chart presents the last
|     |     | Temperature  |        |               |      | date        | of fall     | or first    | date     | of     |
| --- | --- | ------------ | ------ | ------------- | ---- | ----------- | ----------- | ----------- | -------- | ------ |
|     |     |              |        |               |      | spring      | that        | a given     |          |        |
|     |     |              |        |               |      | temperature |             | threshold   |          | was    |
|     |     |              |        |               |      | last        | or first    | reached.    |          |        |
| 255 |     | Leaky Bucket |        | Model         | for  | This        | autoplot    | implemments |          |        |
|     |     | Daily Precip |        | + Evaporation |      | a simple    | model       | known       |          | as the |
|     |     |              |        |               |      | leaky       | bucket      | model.      |          |        |
| 229 |     | Lightning    | Stroke | Density       |      | This        | data        | is courtesy |          | of     |
|     |     | Maps         |        |               |      | Vaisala     | NLDN        | .           |          |        |
| 262 |     | Top 15       | Events | for Daily     |      | This        | autoplot    | lists       | out      | daily  |
|     |     | Variables    | after  | Offset        | Days | climate     | observation |             | extremes |        |
|     |     | of certain   | event  |               |      | for a       | given       | combination |          | of     |
|     |     |              |        |               |      | variable    | threshold   |             | and      | day    |
offset.

| Mastering | the Mesonet |             |                       |     |     |              |             |            | 143 |
| --------- | ----------- | ----------- | --------------------- | --- | --- | ------------ | ----------- | ---------- | --- |
| q         |             | Title       |                       |     |     | Description  |             |            |     |
| 207 �     |             | Local Storm | Report                |     | +   | Generates    | an          | analysis   | map |
|           |             | COOP        | Rainfall/Snowfall/Ice |     |     | of rainfall, | snowfall,   |            | or  |
|           |             | Analysis    | Maps                  |     |     | freezing     | rain        | data based | on  |
|           |             |             |                       |     |     | NWS          | Local Storm | Reports,   |     |
|           |             |             |                       |     |     | NWS          | COOP        | Data,      | and |
CoCoRaHS.
| 206 |     | Map of      | Daily            | Automated |      | Generates        | analysis   | maps     | of     |
| --- | --- | ----------- | ---------------- | --------- | ---- | ---------------- | ---------- | -------- | ------ |
|     |     | Station     | Summaries        |           |      | ASOS             | station    | data for | a      |
|     |     |             |                  |           |      | given            | date.      |          |        |
| 97  |     | Map of      | Departures/Stats |           |      | This application |            | plots    | an     |
|     |     | over One    | Period           | of Days   |      | analysis         | of station | data     | for a  |
|     |     |             |                  |           |      | period           | of your    | choice.  |        |
| 34  |     | Max Stretch | of               | Days      | with | This plot        | displays   | the      |        |
|     |     | High/Low    | Above/Below      |           |      | maximum          | number     | of       | consec |
|     |     | Threshold   | or Climatology   |           |      | days above       | or         | below    | some   |
|     |     |             |                  |           |      | threshold        | for        | high or  | low    |
temperature.
| 26   |     | Min Daily  | Low            | after       | 1 July | / This plot      | presents         | the         |          |
| ---- | --- | ---------- | -------------- | ----------- | ------ | ---------------- | ---------------- | ----------- | -------- |
|      |     | Max Daily  | High           | for         | year   | climatology      | and              | actual      |          |
|      |     |            |                |             |        | year’s           | progression      | of          |          |
|      |     |            |                |             |        | warmest          | to date          | or coldest  |          |
|      |     |            |                |             |        | to date          | temperature.     |             |          |
| 126  |     | Mixing     | Ratio          | / Vapor     |        | This plot        | presents         | one         | of two   |
|      |     | Pressure   | Deficit        | Climatology |        | metrics          | indicating       | daily       |          |
|      |     | and Yearly | Timeseries     |             | Plot   | humidity         | levels           | as reported |          |
|      |     |            |                |             |        | by a surface     | weather          |             | station. |
| 84 � |     | MRMS       | / PRISM        | / Stage     | IV     | This application |                  | generates   |          |
|      |     | / IFC /    | IEM Reanalysis |             |        | maps             | of precipitation |             | daily    |
|      |     | Estimated  | Precip         | (multiday   |        | or multi-day     |                  | totals.     |          |
summaries/departures)
| 185 |     | Number     | of Days | to     |     | This application |        | will          | make a |
| --- | --- | ---------- | ------- | ------ | --- | ---------------- | ------ | ------------- | ------ |
|     |     | Accumulate | an      | Amount | of  | map with         | the    | number        | of     |
|     |     | Precip     | (MRMS)  |        |     | days it          | takes  | to accumulate |        |
|     |     |            |         |        |     | a given          | amount | of            |        |
precipitation.

| Mastering | the Mesonet |                   |             |                |                  | 144      |
| --------- | ----------- | ----------------- | ----------- | -------------- | ---------------- | -------- |
| q         |             | Title             |             | Description    |                  |          |
| 256       |             | NWS Regional      | Temperature | Due to         | various software | and      |
|           |             | and Precipitation | (RTP)       | support        | issues at the    |          |
|           |             | Reports           | by IEM      | National       | Weather          | Service, |
|           |             |                   |             | they generally | stopped          | the      |
|           |             |                   |             | generation     | of Regional      |          |
|           |             |                   |             | Temperature    | and              |          |
|           |             |                   |             | Precipitation  | (RTP)            | reports  |
during 2024.
| 164 |     | Percentage      | of NWS CLI | This chart    | presents     | a simple   |
| --- | --- | --------------- | ---------- | ------------- | ------------ | ---------- |
|     |     | Sites Reporting | Daily      | accounting    | of the       | percentage |
|     |     | Above/Below     | Temps or   | of first      | order NWS    | climate    |
|     |     | Precip/Snow     |            | sites that    | are either   | above or   |
|     |     |                 |            | below average | or reporting |            |
|     |     |                 |            | precipitation | / snow       | each       |
day.
| 22  |     | Percentage        | of Years within    | This plot       | displays         | the        |
| --- | --- | ----------------- | ------------------ | --------------- | ---------------- | ---------- |
|     |     | Temperature       | Range from         | frequency       | of a daily       | high or    |
|     |     | Averages          |                    | low temperature | being            |            |
|     |     |                   |                    | within          | a certain bounds | of         |
|     |     |                   |                    | the long        | term NCEI        |            |
|     |     |                   |                    | climatology     | for the          | location.  |
| 83  |     | Period Averages   | or Totals of       | This plot       | compares         | a period   |
|     |     | X days            | around a given day | of days         | prior to a       | specified  |
|     |     | of the year       |                    | date to         | the same number  | of         |
|     |     |                   |                    | days after      | a date.          |            |
| 140 |     | Period Statistics | of                 | This plot       | presents         | statistics |
|     |     | Temp/Precip/Wind  | for a              | for a period    | of days          | each       |
|     |     | date period       | each year          | year provided   | your             | start      |
|     |     | [ASOS/Automated   | Stations]          | date and        | number           | of days    |
|     |     |                   |                    | after that      | date.            |            |
| 107 |     | Period Statistics | of                 | This plot       | presents         | aggregate  |
|     |     | Temp/Precip       | for a date         | statistics      | by year for      | a date     |
|     |     | period each       | year               | period          | of your choice.  |            |
|     |     | [COOP/Climate     | Sites]             |                 |                  |            |

| Mastering | the Mesonet |            |                 |                  |                   | 145     |
| --------- | ----------- | ---------- | --------------- | ---------------- | ----------------- | ------- |
| q         |             | Title      |                 | Description      |                   |         |
| 182       |             | Precip     | (MRMS) Coverage | This application | attempts          | to      |
|           |             | Efficiency | by State        | assess           | the effectiveness | of a    |
|           |             |            |                 | calendar         | day’s rainfall    | based   |
|           |             |            |                 | on where         | the rain          | fell in |
|           |             |            |                 | relation         | to a previous     | period  |
|           |             |            |                 | of days          | departure         | from    |
climatology.
| 110 |     | Precip          | Frequency Bins by | This plot      | presents       | the      |
| --- | --- | --------------- | ----------------- | -------------- | -------------- | -------- |
|     |     | Climate         | Week (climodat)   | weekly         | percentage     | of       |
|     |     |                 |                   | precipitation  | events         | within a |
|     |     |                 |                   | given rainfall | bin.           |          |
| 241 |     | Real-Time       | Mesoscale         | NCEP’s         | Real-Time      |          |
|     |     | Analysis        | (RTMA) Max/Min    | Mesoscale      | Analysis       | (RTMA)   |
|     |     | Air Temperature |                   | provides       | a fine scale   | hourly   |
|     |     |                 |                   | or in the      | case of the    | RTMA     |
|     |     |                 |                   | Rapid-Update   | (RTMA-RU),     |          |
|     |     |                 |                   | 15 minute      | interval       | analysis |
|     |     |                 |                   | of a number    | of atmospheric |          |
variables.
| 43 � |     | Recent     | (Past 2-3 Days)   | This plot  | presents       | a time     |
| ---- | --- | ---------- | ----------------- | ---------- | -------------- | ---------- |
|      |     | Timeseries | (Meteogram)       | series of  | observations.  |            |
| 157  |     | Relative   | Humidity, Feels   | Based      | on available   | hourly or  |
|      |     | Like, Dew  | Point Climatology | better     | observations,  | the IEM    |
|      |     | by Day     | of Year           | computes   | local calendar | day        |
|      |     |            |                   | statistics | for variables  | like       |
|      |     |            |                   | relative   | humidity,      | dew point, |
|      |     |            |                   | and feels  | like (read:    |            |
|      |     |            |                   | windchill  | or heat index) |            |
temperature.
| 62  |     | Snow Depth |     | This chart | presents | the daily |
| --- | --- | ---------- | --- | ---------- | -------- | --------- |
|     |     |            |     | snow depth | reports  | as a      |
image.
| 199 |     | ISU Soil        | Moisture Network | This application | generates |           |
| --- | --- | --------------- | ---------------- | ---------------- | --------- | --------- |
|     |     | Daily Plots     |                  | maps of          | daily ISU | Soil      |
|     |     |                 |                  | Moisture         | Network   | Data.     |
| 38  |     | Solar Radiation | Estimates        | This plot        | presents  | daily     |
|     |     | ERA5Land,       | HRRR,            | estimates        | of solar  | radiation |
|     |     | MERRAv2,        | NARR             | for a given      | year for  | the       |
|     |     |                 |                  | ‘climodat’       | stations  | tracked   |
by the IEM.

| Mastering | the Mesonet |                  |          |             |     |              |          |             |          | 146  |
| --------- | ----------- | ---------------- | -------- | ----------- | --- | ------------ | -------- | ----------- | -------- | ---- |
| q         |             | Title            |          |             |     | Description  |          |             |          |      |
| 25        |             | Spread           | of Daily | High        | and | This plot    | displays |             | the      |      |
|           |             | Low Temperatures |          |             |     | distribution |          | of observed |          |      |
|           |             |                  |          |             |     | daily        | high and | low         |          |      |
|           |             |                  |          |             |     | temperatures |          | for a       | given    | day  |
|           |             |                  |          |             |     | and given    | state    | or          | station. |      |
| 137       |             | Start Date       | of       | Spring/Fall |     | This plot    | displays |             | some     |      |
|           |             | with Statistics  |          |             |     | metrics      | about    | the         | start    | date |
|           |             |                  |          |             |     | and duration |          | of the      | spring   | or   |
fall season.
| 4   |     | State Areal | Coverage  |      | of     | Using      | the gridded |       | IEM |     |
| --- | --- | ----------- | --------- | ---- | ------ | ---------- | ----------- | ----- | --- | --- |
|     |     | Precip      | Intensity | over | X Days | ReAnalysis | of          | daily |     |     |
precipitation.
| 89  |     | State Areal         |     |     |     | This is   | a complex |          | plot to |     |
| --- | --- | ------------------- | --- | --- | --- | --------- | --------- | -------- | ------- | --- |
|     |     | Coverage/Efficiency |     |     | of  | describe! | For       | each     | 24 hour |     |
|     |     | Precip              |     |     |     | period    | (roughly  | ending   |         | 7   |
|     |     |                     |     |     |     | AM),      | the IEM   | computes |         | a   |
gridded precipitation
estimate.
| 81  |     | Standard     | Deviation |     | of Daily | This chart | presents |             | two |     |
| --- | --- | ------------ | --------- | --- | -------- | ---------- | -------- | ----------- | --- | --- |
|     |     | Temperatures |           |     |          | measures   | of       | temperature |     |     |
variability.
| 28  |     | Trailing | Number | of   | Days | This plot         | presents |          | trailing |     |
| --- | --- | -------- | ------ | ---- | ---- | ----------------- | -------- | -------- | -------- | --- |
|     |     | Precip   | Total  | Rank |      | day precipitation |          | metrics. |          |     |
228 Trailing Standardized Precip This visualization mashes up
|     |     | (SPI) + | Drought | Monitor |     | the US           | Drought  | Monitor       |          |     |
| --- | --- | ------- | ------- | ------- | --- | ---------------- | -------- | ------------- | -------- | --- |
|     |     |         |         |         |     | and three        | trailing |               | day      |     |
|     |     |         |         |         |     | standardized     |          | precipitation |          |     |
|     |     |         |         |         |     | index            | of your  | choice        | within   | a   |
|     |     |         |         |         |     | map presentation |          | for           | a single |     |
state.
| 142 |     | Trailing    | X Number |            | of Days | This plot   | presents |                  | the     |     |
| --- | --- | ----------- | -------- | ---------- | ------- | ----------- | -------- | ---------------- | ------- | --- |
|     |     | Temp/Precip |          | Departures |         | trailing    | X number |                  | of days |     |
|     |     |             |          |            |         | temperature |          | or precipitation |         |     |
|     |     |             |          |            |         | departure   | from     | long             | term    |     |
average.
| 132 |     | Top 10 | Precip/Temperature |     |     | This plot  | displays |         | the top |     |
| --- | --- | ------ | ------------------ | --- | --- | ---------- | -------- | ------- | ------- | --- |
|     |     | Values | by Month/Season    |     |     | ten events | for      | a given | site    |     |
|     |     |        |                    |     |     | and period | of       | your    | choice. |     |

| Mastering | the Mesonet |               |          |             |             | 147      |
| --------- | ----------- | ------------- | -------- | ----------- | ----------- | -------- |
| q         |             | Title         |          | Description |             |          |
| 190       |             | Year of Daily | High/Low | This chart  | presents    | the year |
|           |             | Temperature   | Record   | that the    | present day |          |
|           |             |               |          | climatology | record      | resides. |
Monthly
| q   |     | Title       |              | Description  |                  |        |
| --- | --- | ----------- | ------------ | ------------ | ---------------- | ------ |
| 130 |     | Average     | High/Low     | This chart   | presents         | violin |
|     |     | Temperature | with/without | plots of     | the distribution | of     |
|     |     | Snowcover   |              | daily high   | and low          |        |
|     |     |             |              | temperatures | on dates         | with   |
|     |     |             |              | and without  | snow cover       | by     |
month.
| 125 |     | Climatological          | Maps           | of This application | produces           |           |
| --- | --- | ----------------------- | -------------- | ------------------- | ------------------ | --------- |
|     |     | Period Averages         |                | map analysis        | of                 |           |
|     |     |                         |                | climatological      | averages.          |           |
| 1   |     | Comparison              | of Multi-Month | This app            | allows the         | arbitrary |
|     |     | Totals/Averages         |                | comparison          | of months          |           |
|     |     |                         |                | against             | other months.      |           |
| 55  |     | Daily Climatology       |                | This plot           | displays a         |           |
|     |     | Comparison              |                | comparison          | of various         | daily     |
|     |     |                         |                | temperature         | climatologies.     |           |
| 17  |     | Daily High/Low          | Temps          | or Daily plot       | of observed        | daily     |
|     |     | Precip with             | Climatology    | summary             | variables          | along     |
|     |     |                         |                | with the            | daily climatology  |           |
|     |     |                         |                | for the             | nearest (sometimes |           |
|     |     |                         |                | same)               | location.          |           |
| 129 |     | Daily Observation       |                | This chart          | plots the          | monthly   |
|     |     | Percentiles/Frequencies |                | by percentiles      | that a given       | daily     |
|     |     | Month                   |                | value has.          |                    |           |
| 15  |     | Daily Temperature       | Change         | This plot           | displays the       |           |
|     |     | Frequencies             | by Month       | directional         | frequency          | of day    |
|     |     |                         |                | to day              | changes in high    | or        |
|     |     |                         |                | low temperature     | summarized         |           |
|     |     |                         |                | by month.           |                    |           |

| Mastering | the Mesonet |                 |              |                |       |                  |                 |                 | 148     |
| --------- | ----------- | --------------- | ------------ | -------------- | ----- | ---------------- | --------------- | --------------- | ------- |
| q         |             | Title           |              |                |       | Description      |                 |                 |         |
| 71        |             | Daily Wind      | Speed,       |                | Gust, | This plot        | displays        | daily           |         |
|           |             | and Direction   |              | for Single     |       | average          | wind            | speeds          | for a   |
|           |             | Month           |              |                |       | given year       | and             | month           | of      |
|           |             |                 |              |                |       | your choice.     |                 |                 |         |
| 98        |             | Day of          | Month        | Frequency      | of    | This plot        | produces        | the             | daily   |
|           |             | meeting         | temp/precip  |                |       | frequency        | of a            | given criterion |         |
|           |             | threshold       |              |                |       | being meet       | for             | a station       | and     |
|           |             |                 |              |                |       | month            | of your         | choice.         |         |
| 65        |             | Day of          | the Month    | with           | the   | This plot        | displays        | the             |         |
|           |             | coldest/warmest |              |                |       | frequency        | of              | a given         | day in  |
|           |             | temperature     |              |                |       | the month        | having          | the             | coldest |
|           |             |                 |              |                |       | high or          | low temperature |                 | of      |
|           |             |                 |              |                |       | that month       | for             | a year.         |         |
| 161       |             | Days per        | month/season |                |       | This application |                 | plots           | the     |
|           |             | above/below     |              | some threshold |       | number           | of days         | for a           | given   |
|           |             |                 |              |                |       | month            | or period       | of months       |         |
|           |             |                 |              |                |       | that a           | given variable  |                 | was     |
|           |             |                 |              |                |       | above or         | below           | some            |         |
threshold.
| 29  |     | Frequency       | of          | Hourly    |         | This plot   | presents    | the          |          |
| --- | --- | --------------- | ----------- | --------- | ------- | ----------- | ----------- | ------------ | -------- |
|     |     | Variable        | within      | Range     | by      | frequency   | of          | a given      | hourly   |
|     |     | Month           |             |           |         | variable    | being       | between      | two      |
|     |     |                 |             |           |         | inclusive   | thresholds. |              |          |
| 116 |     | Cooling/Heating |             | Degree    |         | This chart  | presents    | monthly      |          |
|     |     | Days monthly    |             | totals    |         | cooling     | degree      | days or      |          |
|     |     |                 |             |           |         | heating     | degree      | days         | for a 20 |
|     |     |                 |             |           |         | year period | of          | your choice. |          |
| 42  |     | Consecutive     | Hours       | /         | Streaks | Based       | on hourly   | or better    |          |
|     |     | Above/Below     |             | Threshold |         | METAR       | reports,    | this         | plot     |
|     |     |                 |             |           |         | displays    | the longest |              | periods  |
|     |     |                 |             |           |         | above or    | below       | a given      |          |
|     |     |                 |             |           |         | temperature |             | threshold.   |          |
| 154 |     | Hourly          | Temperature |           |         | This chart  | presents    | an           |          |
|     |     | Averages        | by Month    |           |         | average     | hourly      | value        | for a    |
|     |     |                 |             |           |         | given month |             | or season    | over     |
|     |     |                 |             |           |         | the years   | covering    | the          | period   |
|     |     |                 |             |           |         | of record   | for         | the site.    |          |

| Mastering | the Mesonet |           |             |        |             |             |            | 149 |
| --------- | ----------- | --------- | ----------- | ------ | ----------- | ----------- | ---------- | --- |
| q         |             | Title     |             |        | Description |             |            |     |
| 85        |             | Hourly    | Frequencies | / Last | Based       | on IEM      | archives   | of  |
|           |             | Occurence | by Month    |        | METAR       | reports,    | this       |     |
|           |             |           |             |        | application | produces    | the        |     |
|           |             |           |             |        | hourly      | frequency   | of a given |     |
|           |             |           |             |        | variable    | at or above | or below   |     |
a threshold.
| 20  |     | Hours of | Precip by | Month | This         | chart displays | the        |     |
| --- | --- | -------- | --------- | ----- | ------------ | -------------- | ---------- | --- |
|     |     |          |           |       | number       | of hourly      |            |     |
|     |     |          |           |       | observations | each           | month      |     |
|     |     |          |           |       | that         | reported       | measurable |     |
precipitation.
| 177 |     | ISU Soil   | Moisture | Network | This | application   | generates |      |
| --- | --- | ---------- | -------- | ------- | ---- | ------------- | --------- | ---- |
|     |     | Timeseries | Plots    |         | time | series charts | using     | data |
|     |     |            |          |         | from | the ISU Soil  | Moisture  |      |
Network.
| 115 |     | Monthly | Heatmap | of  | This   | reports presents | simple  |     |
| --- | --- | ------- | ------- | --- | ------ | ---------------- | ------- | --- |
|     |     | Summary | Totals  |     | monthy | and yearly       | summary |     |
statistics.
| 2   |     | Month                 | Precip vs | Month     | This             | plot compares  | the          |       |
| --- | --- | --------------------- | --------- | --------- | ---------------- | -------------- | ------------ | ----- |
|     |     | Growing               | Degree    | Day       | growing          | degree         | day vs       |       |
|     |     | Departures            |           |           | precipitation    | departure      |              | for a |
|     |     |                       |           |           | given            | month and      | station.     |       |
| 223 |     | Monthly/Seasonal      |           | Partition | This             | chart presents | the          |       |
|     |     | of Temperature/Precip |           |           | monthly/seasonal |                | partition    |       |
|     |     | Reports               |           |           | of how           | a daily        | observed     |       |
|     |     |                       |           |           | climate          | variable       | is observed. |       |
| 57  |     | Monthly               |           |           | This             | plot displays  | the          |       |
|     |     | Precip/Temperature    |           | Records   | monthly          | records        | or           |       |
|     |     | or Climatology        |           |           | climatology      | for            | a station    | of    |
your choice.
| 95  |     | Monthly            |                    |         | This          | chart displays | the          |      |
| --- | --- | ------------------ | ------------------ | ------- | ------------- | -------------- | ------------ | ---- |
|     |     | Precip/Temperature |                    | with El | combination   | of             | average      |      |
|     |     | Nino SOI           | Index Relationship |         | temperature   | and            | total        |      |
|     |     |                    |                    |         | precipitation | for            | one or       | more |
|     |     |                    |                    |         | months        | of your        | choice.      |      |
| 24  |     | Monthly            |                    |         | The map       | presents       | IEM          |      |
|     |     | Precip/Temperature |                    | Climate | computed      | climate        | district     | or   |
|     |     | District           | / Statewide        |         | statewide     | values         | for a metric |      |
|     |     | Ranks/Aridity      |                    |         | of your       | choice.        |              |      |

| Mastering | the Mesonet |                    |               |             |           |                     |              |                  | 150        |
| --------- | ----------- | ------------------ | ------------- | ----------- | --------- | ------------------- | ------------ | ---------------- | ---------- |
| q         |             | Title              |               |             |           | Description         |              |                  |            |
| 3         |             | Monthly/Yearly     |               |             |           | This plot           | displays     |                  | a single   |
|           |             | Precip/Temperature |               |             |           | month’s             | worth        | of               | data over  |
|           |             | Statistics         | by            | Year        |           | all of the          | years        | in               | the period |
|           |             |                    |               |             |           | of record.          |              |                  |            |
| 6         |             | Monthly            |               |             |           | This application    |              | plots            | out        |
|           |             | Precip/Temperature |               |             |           | the distribution    |              | of               | some       |
|           |             | Distributions      |               |             |           | monthly             | metric       | for              | single     |
|           |             |                    |               |             |           | month               | for all      | tracked          | sites      |
|           |             |                    |               |             |           | within              | one state.   |                  |            |
| 8         |             | Monthly            | Precip        | Reliability |           | This plot           | presents     |                  | the        |
|           |             |                    |               |             |           | frequency           | of           | having           | a          |
|           |             |                    |               |             |           | month’s             | preciptation |                  | at or      |
|           |             |                    |               |             |           | above some          |              | threshold.       |            |
| 23        |             | Monthly            | Station       | Departures  |           | This plot           | presents     |                  | the        |
|           |             | + El Nino          | 3.4           | Index       | Time      | combination         |              | of monthly       |            |
|           |             | Series             |               |             |           | temperature         |              | or precipitation |            |
|           |             |                    |               |             |           | departures          | and          | El               | Nino       |
|           |             |                    |               |             |           | index values.       |              |                  |            |
| 36        |             | Month              | warmer/wetter |             | than      | This plot           | summarizes   |                  | the        |
|           |             | other Month        |               | for Year    |           | frequency           | of           | one month        |            |
|           |             |                    |               |             |           | being warmer/wetter |              |                  | than       |
|           |             |                    |               |             |           | another             | month        | for              | that       |
|           |             |                    |               |             |           | calendar            | year.        |                  |            |
| 58        |             | One Day’s          | Precip        | Greater     |           | Displays            | the          | number           | of         |
|           |             | than X             | percentage    |             | of        | times that          | a            | single           | day’s      |
|           |             | Monthly            | Total         |             |           | precipitation       |              | was              | greater    |
|           |             |                    |               |             |           | than some           | portion      |                  | of the     |
|           |             |                    |               |             |           | monthly             | total.       |                  |            |
| 41        |             | Quantile           | / Quantile    |             | Plot of   | This plot           | compares     |                  | the        |
|           |             | Daily Temperatures |               |             | for Two   | distribution        |              | of daily         |            |
|           |             | Months/Periods     |               |             |           | temperatures        |              | for two          | months     |
|           |             |                    |               |             |           | or periods          | for          | a single         |            |
|           |             |                    |               |             |           | station             | of your      | choice.          |            |
| 47        |             | Snowfall           | vs Precip     |             | Total for | This chart          | displays     |                  | the        |
|           |             | a Month            |               |             |           | combination         |              | of liquid        |            |
|           |             |                    |               |             |           | precipitation       |              | with             | snowfall   |
|           |             |                    |               |             |           | totals for          | a given      |                  | month.     |

| Mastering | the Mesonet |           |               |       |             |               |          | 151   |
| --------- | ----------- | --------- | ------------- | ----- | ----------- | ------------- | -------- | ----- |
| q         |             | Title     |               |       | Description |               |          |       |
| 39        |             | Scenarios | for this      | month | This        | plot compares |          | the   |
|           |             | besting   | some previous | month | month       | to date       | average  |       |
|           |             |           |               |       | temperature |               | of this  | month |
|           |             |           |               |       | against     | any           | previous | month |
of your choice.
| 138 |     | Wind Speed  | and      | Wind | This    | graph    | presents        | monthly |
| --- | --- | ----------- | -------- | ---- | ------- | -------- | --------------- | ------- |
|     |     | Direction   | Monthly  |      | average | wind     | speed           | values  |
|     |     | Climatology |          |      | along   | with     | vector-averaged |         |
|     |     |             |          |      | average | wind     | direction.      |         |
| 173 |     | Wind Speed  | Hourly   |      | This    | chart    | presents        | the     |
|     |     | Climatology | by Month | or   | hourly  | average  | wind            | speeds  |
|     |     | Period      |          |      | by      | month of | the year        | or by   |
custom periods.
Yearly
| q   |     | Title          |                    |          | Description    |               |                |         |
| --- | --- | -------------- | ------------------ | -------- | -------------- | ------------- | -------------- | ------- |
| 135 |     | Accumulated    | Days               | with     | This           | plot displays | the            |         |
|     |     | High/Low       | Above/Below        |          | accumulated    |               | number         | of days |
|     |     | Threshold      |                    |          | that           | the high      | or low         |         |
|     |     |                |                    |          | temperature    |               | was above      | or      |
|     |     |                |                    |          | below          | some          | threshold.     |         |
| 246 |     | Accumulated    | GDD/Precip         |          | This           | autoplot      | generates      | a       |
|     |     | Threshold      | Frequency          | by Day   | probability    |               | of a specified |         |
|     |     | of Year        |                    |          | accumulation   |               | threshold      |         |
|     |     |                |                    |          | being          | reached       | by the         | given   |
|     |     |                |                    |          | calendar       | date.         |                |         |
| 76  |     | Dew Point      | / Vapor            | Pressure | Simple         | plot          | of yearly      | average |
|     |     | Deficit        | / RH Distributions |          | dew            | points        | by year,       | season, |
|     |     | by Year        | or Season          |          | or month.      |               |                |         |
| 125 |     | Climatological | Maps               | of       | This           | application   | produces       |         |
|     |     | Annual/Monthly |                    | Averages | map            | analysis      | of             |         |
|     |     |                |                    |          | climatological |               | averages.      |         |

| Mastering | the Mesonet |             |                  |             |                | 152         |
| --------- | ----------- | ----------- | ---------------- | ----------- | -------------- | ----------- |
| q         |             | Title       |                  | Description |                |             |
| 151       |             | Difference  | between two      | This        | autoplot can   | either      |
|           |             | periods     | or single period | of produce  | a plot of      | averages    |
|           |             | years [map] |                  | for a       | given period   | or annual   |
|           |             |             |                  | over        | a period of    | years; or a |
|           |             |             |                  | difference  | between        | a second    |
|           |             |             |                  | set of      | years.         |             |
| 187       |             | Compare     | one station      | yearly This | chart presents | the rank    |
|           |             | summary     | vs entire state  | a station’s | yearly         | summary     |
|           |             |             |                  | value       | has against    | an          |
|           |             |             |                  | unweighted  | population     | of          |
|           |             |             |                  | available   | observations   | in the      |
state.
| 244  |     | Compare      | NCEI Climdiv | to The        | IEM attempts     | to create |
| ---- | --- | ------------ | ------------ | ------------- | ---------------- | --------- |
|      |     | IEM Climodat | Statewide    | areal         | averaged climate | values    |
|      |     | Values       |              | akin          | to what NCEI     | has with  |
|      |     |              |              | its “Climdiv” | dataset.         |           |
| 128  |     | Comparison   | of Yearly    | This          | chart compares   | yearly    |
|      |     | Summaries    | between      | two summaries | between          | two long  |
|      |     | stations     |              | term          | climate sites.   |           |
| 99 � |     | Daily High   | + Low        | This          | plot produces    | a time    |
|      |     | Temperatures | with         | series        | difference       | between   |
|      |     | Departures   |              | daily         | high and low     |           |
|      |     |              |              | temperatures  | against          |           |
climatology.
| 12  |     | Days per        | year and         | This          | plot presents         | the yearly  |
| --- | --- | --------------- | ---------------- | ------------- | --------------------- | ----------- |
|     |     | first/latest    | date above/below | first         | or last date          | of a given  |
|     |     | given threshold |                  | high          | or low temperature    |             |
|     |     |                 |                  | along         | with the number       | of          |
|     |     |                 |                  | days          | that year above/below |             |
|     |     |                 |                  | the threshold | along                 | with the    |
|     |     |                 |                  | cumulative    | distribution          |             |
|     |     |                 |                  | function      | for the               | first date! |
|     |     |                 |                  | When          | you select            | a low       |
temperatur
| 184 |     | Days per    | year with High | This        | plot shows  | the number |
| --- | --- | ----------- | -------------- | ----------- | ----------- | ---------- |
|     |     | Temperature | above          | of days     | with a high |            |
|     |     | temperature | thresholds     | temperature | at          | or above a |
|     |     |             |                | given       | threshold.  |            |

| Mastering | the Mesonet |                      |             |             |        |             |             |            |             | 153     |
| --------- | ----------- | -------------------- | ----------- | ----------- | ------ | ----------- | ----------- | ---------- | ----------- | ------- |
| q         |             | Title                |             |             |        | Description |             |            |             |         |
| 74        |             | Days per             | year        | by season   | or     | The         | number      | of         | days        | for a   |
|           |             | year with            | temperature |             |        | given       | season      | that       | are         | either  |
|           |             | above/below          |             | threshold   |        | above       | or          | below      | some        |         |
|           |             |                      |             |             |        | temperature |             | threshold. |             |         |
| 181       |             | Days per             | year        | with        |        | This        | application |            | plots       |         |
|           |             | temp/precip/snowfall |             |             | within | frequencies |             | of a       | variable    | of      |
|           |             | ranges               |             |             |        | your        | choice      | for        | five bins   | of      |
|           |             |                      |             |             |        | your        | choice.     |            |             |         |
| 13        |             | End/Start            | Date        | of Summer   |        | This        | chart       | presents   | the         | start   |
|           |             | (warmest             | 91          | day period) | per    | or end      | date        | of         | the warmest |         |
|           |             | Year                 |             |             |        | 91          | day period  | each       | year.       |         |
| 27        |             | First Fall           | Temp        | Below       |        | This        | chart       | presents   | the         | date    |
|           |             | Threshold            | (First      |             |        | of the      | first       | fall       | (date       | after 1 |
|           |             | Freeze/Frost)        |             |             |        | July)       | temperature |            | below       |         |
|           |             |                      |             |             |        | threshold   |             | 1 and      | then        | the     |
|           |             |                      |             |             |        | number      | of          | days       | after       | that    |
|           |             |                      |             |             |        | date        | until       | threshold  |             | 2 was   |
reached.
| 165 |     | First /     | Last        | Date of     | Air/Soil | This        | app           | generates  | a            | map    |
| --- | --- | ----------- | ----------- | ----------- | -------- | ----------- | ------------- | ---------- | ------------ | ------ |
|     |     | Temperature |             | Threshold   |          | showing     | either        |            | an explicit  |        |
|     |     | [map]       |             |             |          | year’s      | first         | or last    | date         | or     |
|     |     |             |             |             |          | the         | given         | percentile |              |        |
|     |     |             |             |             |          | (observed   |               | frequency) |              | date   |
|     |     |             |             |             |          | over        | all available |            | years        | of a   |
|     |     |             |             |             |          | given       | temperature   |            | threshold.   |        |
| 119 |     | Frequency   | of          | First/Last  | Fall     | This        | chart         | presents   | the          |        |
|     |     | High/Low    | Temp        | by          | Day of   | accumulated |               | frequency  |              | of a   |
|     |     | Year        |             |             |          | temperature |               | threshold  |              | being  |
|     |     |             |             |             |          | the         | first time    | observed   |              | or     |
|     |     |             |             |             |          | last        | time          | observed   | during       |        |
|     |     |             |             |             |          | the         | fall season.  |            |              |        |
| 120 |     | Frequency   | of          | Last Spring |          | This        | chart         | presents   | the          |        |
|     |     | High/Low    | Temperature |             | by       | accumulated |               | frequency  |              | of     |
|     |     | Day of      | Year        |             |          | having      | the           | last       | spring       |        |
|     |     |             |             |             |          | temperature |               | at         | or below     | a      |
|     |     |             |             |             |          | given       | threshold.    |            |              |        |
| 189 |     | General     | yearly      | totals      | with     | Create      | plots         | of         | yearly       | totals |
|     |     | trend line  | fitted      |             |          | and         | optionally    |            | fit a linear |        |
trendline.

| Mastering | the Mesonet |             |              |             |         |               |             |           |              | 154    |
| --------- | ----------- | ----------- | ------------ | ----------- | ------- | ------------- | ----------- | --------- | ------------ | ------ |
| q         |             | Title       |              |             |         | Description   |             |           |              |        |
| 179       |             | Growing     | Degree       | Day         |         | This          | application |           | creates      | two    |
|           |             | Scenarios   | For          | This        | Year    | 2-D           | histograms  |           | of GDD       |        |
|           |             |             |              |             |         | accumulation  |             |           | frequencies. |        |
| 152       |             | Growing     | Season       | Differences |         | This          | map         | produces  |              | an     |
|           |             | Map between |              | Two         | Periods | analysis      |             | of change | in           | the    |
|           |             |             |              |             |         | number        |             | of days   | for          | the    |
|           |             |             |              |             |         | growing       |             | season.   |              |        |
| 148       |             | Holiday     | or Same      | Day         | Daily   | This          | plot        | presents  | a            | daily  |
|           |             | Weather     | Observations |             | each    | observation   |             |           | for a site   | and    |
|           |             | year        |              |             |         | year          | on          | a given   | date         | /      |
|           |             |             |              |             |         | holiday       |             | date      | each year.   |        |
| 53        |             | Hourly      | Frequency    |             | of      | Based         |             | on hourly |              |        |
|           |             | Variable    | within       | Certain     |         | observations, |             |           | this plot    |        |
|           |             | Ranges      |              |             |         | displays      |             | the       | frequency    | of a   |
|           |             |             |              |             |         | given         | variable    |           | falling      | within |
a set of thresholds.
| 10  |     | Last Spring      |     | and First | Fall  | This    | plot   | presents    | the         | period    |
| --- | --- | ---------------- | --- | --------- | ----- | ------- | ------ | ----------- | ----------- | --------- |
|     |     | Date above/below |     |           | given | between |        | the         | first or    | last date |
|     |     | threshold        |     |           |       | for     | spring | and         | fall season |           |
|     |     |                  |     |           |       | that    | the    | temperature |             | was       |
|     |     |                  |     |           |       | above   |        | or below    | some        |           |
threshold.
| 64  |     | Last or           | First    | Snowfall    | of    | This     | chart | displays    |             | either     |
| --- | --- | ----------------- | -------- | ----------- | ----- | -------- | ----- | ----------- | ----------- | ---------- |
|     |     | Each Winter       |          | Season      |       | the      | first | or last     | date        | of the     |
|     |     |                   |          |             |       | winter   |       | season      | with        | a          |
|     |     |                   |          |             |       | snowfall |       | of a        | given       | intensity. |
| 33  |     | Maximum           | Low      | Temperature |       | This     | plot  | presents    | the         | largest    |
|     |     | Drop              |          |             |       | drop     | in    | low         | temperature |            |
|     |     |                   |          |             |       | during   |       | a period    | between     | 1          |
|     |     |                   |          |             |       | July     | and   | 30          | June of     | the next   |
|     |     |                   |          |             |       | year,    | but   | not         | including   | the        |
|     |     |                   |          |             |       | July     | data  | of          | that year.  |            |
| 188 |     | Max/Min           | High/Low |             | after | This     | plot  | presents    | the         | yearly     |
|     |     | first temperature |          | exceedence  |       | minimum  |       | temperature |             | after      |
|     |     | of season         |          |             |       | the      | first | spring      | temperature |            |
|     |     |                   |          |             |       | above    |       | a given     | value       | or the     |
|     |     |                   |          |             |       | maximum  |       | temperature |             | after      |
|     |     |                   |          |             |       | the      | first | fall        | temperature |            |
|     |     |                   |          |             |       | below    |       | a given     | value.      |            |

| Mastering | the Mesonet |            |             |             |       |                  |                 |             | 155     |
| --------- | ----------- | ---------- | ----------- | ----------- | ----- | ---------------- | --------------- | ----------- | ------- |
| q         |             | Title      |             |             |       | Description      |                 |             |         |
| 105       |             | Maximum    | Period      | between     |       | This plot        | presents        | three       |         |
|           |             | Precip     | Amounts     |             |       | precipitation    | metrics         |             | for a   |
|           |             |            |             |             |       | site of          | your choice.    |             |         |
| 46        |             | Minimum    | Wind        | Chill       | / Max | This chart       | presents        |             | the     |
|           |             | Heat Index | Temperature |             |       | frequency        | of observed     |             |         |
|           |             |            |             |             |       | minimum          | wind            | chill       | or      |
|           |             |            |             |             |       | maximum          | heat            | index       | over    |
|           |             |            |             |             |       | the period       | of              | record      | for the |
|           |             |            |             |             |       | observation      | site.           |             |         |
| 30        |             | Monthly    | Temperature |             | Range | This chart       | presents        |             | the     |
|           |             |            |             |             |       | range between    |                 | the warmest |         |
|           |             |            |             |             |       | high temperature |                 | and         | the     |
|           |             |            |             |             |       | coldest          | low temperature |             | for     |
|           |             |            |             |             |       | a given          | month           | for each    | year.   |
| 44 �      |             | NWS Office |             | Accumulated |       | This plot        | displays        | an          |         |
|           |             | SVR+TOR    | Warnings    |             |       | accumulated      | total           | of          | office  |
|           |             |            |             |             |       | issued           | watch,          | warning,    |         |
advisories.
| 69  |     | Percentage                   | of          | Days | each    | The frequency   |           | of days     | per     |
| --- | --- | ---------------------------- | ----------- | ---- | ------- | --------------- | --------- | ----------- | ------- |
|     |     | Year Above/Below             |             |      | Average | year that       | the       | temperature |         |
|     |     |                              |             |      |         | was above/below |           | average.    |         |
| 77  |     | Period                       | between     | Last | and     | For each        | year,     | the average |         |
|     |     | First High                   | Temperature |      | for     | first and       | last date | of          | a given |
|     |     | Year                         |             |      |         | temperature     | is        | computed.   |         |
| 134 |     | Period                       | each year   | that | was     | This plot       | displays  | the         | period  |
|     |     | warmest/coldest/wettest/dri- |             |      |         | of consecutive  |           | days each   | year    |
|     |     | est                          |             |      |         | with the        | extreme   | criterion   |         |
meet.
| 75 � |     | Precip      | Totals | by  |     | Simple          | plot of |               |     |
| ---- | --- | ----------- | ------ | --- | --- | --------------- | ------- | ------------- | --- |
|      |     | Season/Year |        |     |     | seasonal/yearly |         | precipitation |     |
totals.
| 63 � |     | Records | Set     | by Year | (Max | This chart    | plots   | the     | number |
| ---- | --- | ------- | ------- | ------- | ---- | ------------- | ------- | ------- | ------ |
|      |     | High /  | Min Low | /       | Max  | of daily      | maximum | high    |        |
|      |     | Precip) |         |         |      | temperatures, |         | minimum | low    |
|      |     |         |         |         |      | temperatures  |         | and     |        |
|      |     |         |         |         |      | precipitation | records |         | set by |
year.

| Mastering | the Mesonet |                  |        |            |      |              |          |             |           | 156    |
| --------- | ----------- | ---------------- | ------ | ---------- | ---- | ------------ | -------- | ----------- | --------- | ------ |
| q         |             | Title            |        |            |      | Description  |          |             |           |        |
| 144       |             | Soil Temperature |        | Periods    |      | This         | plot     | uses        | hourly    | 4 inch |
|           |             | Above/Below      |        | Threshold  | in   | depth        | soil     | temperature |           |        |
|           |             | Spring           |        |            |      | observations |          | from        | the       | ISU    |
|           |             |                  |        |            |      | Soil         | Moisture |             | Network.  |        |
| 145       |             | Soil Temperature |        | / Moisture |      | This         | chart    | presents    |           | daily  |
|           |             | Daily Time       | Series | by         | Year | timeseries   |          | of soil     |           |        |
|           |             |                  |        |            |      | temperature  |          | or          | moisture. |        |
| 175       |             | Snow Coverage    |        | Percentage |      | This         | chart    | displays    |           |        |
|           |             | for State        | For    | One Winter |      | estimated    |          | areal       | coverage  | of     |
|           |             |                  |        |            |      | snow         | cover    | for         | a single  | state. |
133 Snowfall Season Totals Split This plot displays the total
|       |     | by Date     | within   | Season      |          | reported    |                | snowfall    | for         | a        |
| ----- | --- | ----------- | -------- | ----------- | -------- | ----------- | -------------- | ----------- | ----------- | -------- |
|       |     |             |          |             |          | period      | prior          | to          | a given     | date     |
|       |     |             |          |             |          | and         | then           | after       | the date    | for      |
|       |     |             |          |             |          | the         | winter         | season.     |             |          |
| 103   |     | Step Ups    | in High  | Temp        | /        | This        | plot           | analyzes    | the         |          |
|       |     | Step Downs  | in       | Low Temp    | by       | number      | of             | steps       | down        | in low   |
|       |     | Year        |          |             |          | temperature |                | during      |             | the fall |
|       |     |             |          |             |          | season      | and            | the         | number      | of       |
|       |     |             |          |             |          | steps       | up             | in high     | temperature |          |
|       |     |             |          |             |          | during      | the            | spring      | season.     |          |
| 100 � |     | Temperature |          | / Precip    |          | This        | plot           | displays    | a           | metric   |
|       |     | Statistics  | by Year  |             |          | for         | each           | year.       |             |          |
| 136   |     | Time per    | Winter   | Season      |          | This        | plot           | displays    | the         |          |
|       |     | below Wind  | Chill    | Threshold   |          | number      | of             | accumulated |             |          |
|       |     |             |          |             |          | hours       | below          | a           | given       | wind     |
|       |     |             |          |             |          | chill       | temperature    |             | threshold   |          |
|       |     |             |          |             |          | by          | season.        |             |             |          |
| 104   |     | Trailing    | X day    | temp/precip |          | This        | plot           | presents    | the         | time     |
|       |     | departures  | (weather |             | cycling) | series      | of             | trailing    | X           | number   |
|       |     |             |          |             |          | of          | day departures |             | evaluated   |          |
|       |     |             |          |             |          | every       | Y days         | forward     |             | in       |
time.
| 14  |     | Yearly   | Precip | Contributions |     | Using         | long          | term | data, | five   |
| --- | --- | -------- | ------ | ------------- | --- | ------------- | ------------- | ---- | ----- | ------ |
|     |     | by Daily | Totals |               |     | precipitation |               | bins | are   |        |
|     |     |          |        |               |     | constructed   |               | such | that  | each   |
|     |     |          |        |               |     | bin           | contributes   |      | 20%   | to the |
|     |     |          |        |               |     | annual        | precipitation |      |       | total. |

| Mastering | the Mesonet |             |             |                  |               | 157       |
| --------- | ----------- | ----------- | ----------- | ---------------- | ------------- | --------- |
| Hydrology | / Drought   | Monitor     | Plots       |                  |               |           |
| q         |             | Title       |             | Description      |               |           |
| 160 �     |             | River Gauge | Obs and     | This page        | presents      | a         |
|           |             | Forecasts   | from HML    | sphagetti        | plot of river | stage     |
|           |             | Products    |             | and forecasts.   |               |           |
| 178       |             | NWS RFC     | Flash Flood | This application | plots         | Flash     |
|           |             | Guidance    | Plots       | Flood            | Guidance for  | a time of |
your choice.
| 183 |     | US Drought | Monitor Areal | This plot | presents       | a time   |
| --- | --- | ---------- | ------------- | --------- | -------------- | -------- |
|     |     | Coverage   | by State      | series of | areal coverage | of       |
|     |     |            |               | United    | States Drought |          |
|     |     |            |               | Monitor   | for a given    | state of |
your choice.
| 186 |     | US Drought | Monitor Change    | This plot        | shows the        | weekly   |
| --- | --- | ---------- | ----------------- | ---------------- | ---------------- | -------- |
|     |     | in Areal   | Coverage by State | change           | in drought       | monitor  |
|     |     |            |                   | intensity        | expressed        | in terms |
|     |     |            |                   | of category      | change           | over the |
|     |     |            |                   | area of          | the selected     | state.   |
| 194 |     | US Drought | Monitor Time      | This application | generates        | a        |
|     |     | Duration   | over Period Maps  | heatmap          | of the frequency | of       |
a given drought
classification.
| 193 |     | US Drought     | Monitor +           | Generates     | a map of      | WPC       |
| --- | --- | -------------- | ------------------- | ------------- | ------------- | --------- |
|     |     | Weather        | Prediction Center   | Quantitative  | Precipitation |           |
|     |     | (WPC)          | Forecast Rain (QPF) | Forecast      | (QPF) and     | most      |
|     |     |                |                     | recent        | US Drought    | Monitor   |
|     |     |                |                     | to the        | date choosen  | to plot   |
|     |     |                |                     | the WPC       | forecast      |           |
| 231 |     | Weekly         | Statewide SPI       | This autoplot | produces      | an        |
|     |     | Changes        | and Drought         | infographic   | for a given   | state     |
|     |     | Classification |                     | with some     | diagnostics   | on the    |
|     |     |                |                     | weekly        | change in     |           |
|     |     |                |                     | Standardized  | Precipitation |           |
|     |     |                |                     | Index (SPI)   | over a        | given day |
interval.
| METAR | ASOS Special | Plots |     |     |     |     |
| ----- | ------------ | ----- | --- | --- | --- | --- |

| Mastering | the Mesonet |                 |        |            |       |                 |       |             |           | 158     |
| --------- | ----------- | --------------- | ------ | ---------- | ----- | --------------- | ----- | ----------- | --------- | ------- |
| q         |             | Title           |        |            |       | Description     |       |             |           |         |
| 78        |             | Average         | Dew    | Point/RH%  | by    | This            | plot  | displays    | the       |         |
|           |             | Air Temperature |        | by         | Month | average         | dew   | point       | at        | a given |
|           |             | or Season       | or     | Year       |       | air temperature |       |             | along     | with    |
|           |             |                 |        |            |       | the envelope    |       | between     |           | the     |
|           |             |                 |        |            |       | 5th and         | 95th  | percentile. |           |         |
| 40        |             | Cloud           | Amount | and        | Level | This            | chart | is an       | attempted |         |
|           |             | Timeseries      | /      | Visibility | for   | illustration    |       | of the      | amount    | of      |
|           |             | One Month       |        |            |       | cloudiness      |       | that        | existed   | at a    |
|           |             |                 |        |            |       | METAR           | site  | for         | a given   |         |
month.
| 88  |     | Cloudiness | Impact       |     | on  | This       | plot | attempts      | to  | show |
| --- | --- | ---------- | ------------ | --- | --- | ---------- | ---- | ------------- | --- | ---- |
|     |     | Hourly     | Temperatures |     |     | the impact |      | of cloudiness |     | on   |
temperatures.
| 214 |     | Combos       | of Hourly |               |     |             |      |          |     |     |
| --- | --- | ------------ | --------- | ------------- | --- | ----------- | ---- | -------- | --- | --- |
|     |     | Observations |           | Var Vs        | Var |             |      |          |     |     |
| 59  |     | Daily u      | and       | vs Wind       |     | This        | plot | presents | a   |     |
|     |     | Component    |           | Climatologies |     | climatology |      | of wind  |     |     |
observations.
| 79  |     | Dew Point      | Distribution |         | by       | This       | plot        | displays         | the   |         |
| --- | --- | -------------- | ------------ | ------- | -------- | ---------- | ----------- | ---------------- | ----- | ------- |
|     |     | Wind Direction |              | by      | Month or | average    | dew         | point            | at    | a given |
|     |     | Season         | or Year      |         |          | wind       | direction.  |                  |       |         |
| 54  |     | Difference     | between      |         | morning  | This       | application |                  | plots | the     |
|     |     | low or         | afternoon    | high    |          | difference |             | in morning       |       | low or  |
|     |     | temperature    |              | between | two      | afternoon  |             | high temperature |       |         |
|     |     | sites          |              |         |          | between    | two         | sites            | of    | your    |
choice.
| 250 |     | Difference | between    |           | two   | This      | autoplot  | presents   |             | some |
| --- | --- | ---------- | ---------- | --------- | ----- | --------- | --------- | ---------- | ----------- | ---- |
|     |     | ASOS/METAR |            | stations  | for   | metrics   | when      | comparing  |             | a    |
|     |     | a given    | hourly     | variable  |       | single    | variable  | between    |             | two  |
|     |     |            |            |           |       | airport   | weather   |            | stations.   |      |
| 167 |     | Flight     | / Aviation | Condition |       | This      | chart     | summarizes |             |      |
|     |     | (VFR,      | MVFR,      | IFR,      | LIFR) | Flight    | Category  |            | by hour     | and  |
|     |     | hourly     | for one    | month     |       | day of    | a given   | month.     |             |      |
| 87  |     | Frequency  | of         | METAR     | Code  | Frequency |           | plot       | partitioned |      |
|     |     | (Thunder,  | etc)       | by week   | or    | by hour   | and       | day        | or week     | of   |
|     |     | day by     | hour       |           |       | the year  | for       | a given    | METAR       |      |
|     |     |            |            |           |       | code      | to appear |            | in the      |      |
|     |     |            |            |           |       | present   | weather.  |            |             |      |

| Mastering | the Mesonet |              |         |             |        |             |         |                |              | 159      |
| --------- | ----------- | ------------ | ------- | ----------- | ------ | ----------- | ------- | -------------- | ------------ | -------- |
| q         |             | Title        |         |             |        | Description |         |                |              |          |
| 131       |             | Frequency    | of      | Overcast    |        | This        | plot    | displays       |              | the      |
|           |             | Clouds       | / Clear | Skies       | by Air | frequency   |         | of             | having       | overcast |
|           |             | Temperature  |         | by          |        | or          | clear   | sky conditions |              |          |
|           |             | month/season |         |             |        | reported    |         | by air         | temperature. |          |
| 93        |             | Heat Index   | /       | Temperature |        | / Caution:  |         | This           | plot         | takes a  |
|           |             | Dew Point    | /       | Wind        | Chill  | bit         | of time | to             | generate.    |          |
Hourly Histogram
| 192 |     | Hourly           | Analysis  | Maps          | of     | Generates   |           | analysis      |            | maps of   |
| --- | --- | ---------------- | --------- | ------------- | ------ | ----------- | --------- | ------------- | ---------- | --------- |
|     |     | ASOS/METAR       |           | Stations      |        | ASOS        |           | station       | data.      |           |
| 153 |     | Hourly           | Extremes  | by            |        | This        | table     | presents      |            | the       |
|     |     | Month/Season/Day |           |               |        | extreme     |           | hourly        | value      | of some   |
|     |     | Period/Year      |           |               |        | variable    |           | of your       | choice     | based     |
|     |     |                  |           |               |        | on          | available | observations  |            |           |
|     |     |                  |           |               |        | maintained  |           | by            | the        | IEM.      |
| 159 |     | Hourly           | Frequency | /             |        | Based       |           | on available  |            | hourly    |
|     |     | Histogram        | by        | year          | and by | observation |           | reports       |            | by        |
|     |     | hour of          | day       |               |        | METAR       |           | stations,     |            | this      |
|     |     |                  |           |               |        | application |           | presents      |            | the       |
|     |     |                  |           |               |        | frequency   |           | of            | number     | of        |
|     |     |                  |           |               |        | hours       | for       | a given       | month      | or        |
|     |     |                  |           |               |        | season      |           | at a given    | threshold. |           |
| 106 |     | Hourly           | variable  | distributions |        | This        | plot      | displays      |            | hourly    |
|     |     | on days          | exceeding | threshold     |        | variable    |           | distributions |            | on        |
|     |     |                  |           |               |        | dates       | that      | meet          | the        | criterion |
|     |     |                  |           |               |        | for         | having    | at            | least      | one       |
|     |     |                  |           |               |        | observation |           | at            | the        | given     |
threshold.
| 202 |     | Hourly  | variable | comparison |        | This       | application |           | presents |        |
| --- | --- | ------- | -------- | ---------- | ------ | ---------- | ----------- | --------- | -------- | ------ |
|     |     | between | two      | hours      | on one | daily      | comparisons |           |          | of an  |
|     |     | day     |          |            |        | automation |             | station’s |          | hourly |
data.
| 169 |     | Largest   | Rise/Drop      |     | in   | This     | chart   | presents |             | the      |
| --- | --- | --------- | -------------- | --- | ---- | -------- | ------- | -------- | ----------- | -------- |
|     |     | Temp/Dew  | Point/Pressure |     |      | largest  |         | change   | in some     |          |
|     |     | over X    | Hours          |     |      | observed |         | variable | over        | a        |
|     |     |           |                |     |      | given    | number  |          | of hours.   |          |
| 18  |     | Long term | observation    |     | time | This     | chart   | displays |             | a simple |
|     |     | series    |                |     |      | time     | series  | of       | an observed |          |
|     |     |           |                |     |      | variable |         | for a    | location    | of       |
|     |     |           |                |     |      | your     | choice. |          |             |          |

| Mastering | the Mesonet |          |              |             |               | 160 |
| --------- | ----------- | -------- | ------------ | ----------- | ------------- | --- |
| q         |             | Title    |              | Description |               |     |
| 45        |             | Monthly  | Frequency of | Computes    | the frequency | of  |
|           |             | Overcast | Conditions   | having      | an overcast   | sky |
reported.
| 170 |     | Monthly | Frequency of       | This chart    | totals the        | number  |
| --- | --- | ------- | ------------------ | ------------- | ----------------- | ------- |
|     |     | Present | Weather Code in    | of distinct   | calendar          | days or |
|     |     | METAR   | Report             | hours per     | month that        | a       |
|     |     |         |                    | given present | weather           |         |
|     |     |         |                    | condition     | is reported       | within  |
|     |     |         |                    | the METAR     | data              | feed.   |
| 67  |     | Monthly | Frequency of Wind  | This plot     | displays          | the     |
|     |     | Speeds  | by Air Temperature | frequency     | of having         | a       |
|     |     |         |                    | reported      | wind speed        | be      |
|     |     |         |                    | above         | a given threshold | by      |
|     |     |         |                    | reported      | temperature       | and by  |
month.
| 37 � |     | MOS Forecast | Ranges +       | This chart       | displays         | the        |
| ---- | --- | ------------ | -------------- | ---------------- | ---------------- | ---------- |
|      |     | ASOS         | Observations   | combination      | of Model         |            |
|      |     |              |                | Output           | Statistics (MOS) |            |
|      |     |              |                | forecasts        | and actual       |            |
|      |     |              |                | observations     | by the           |            |
|      |     |              |                | automated        | station          | the MOS    |
|      |     |              |                | forecast         | is for.          |            |
| 211  |     | One Minute   | Interval Plots | This application | generates        |            |
|      |     |              |                | charts           | of 1 minute      | interval   |
|      |     |              |                | ASOS             | data, where      | available. |
| 222  |     | One Minute   | Precip During  |                  |                  |            |
Severe Weather
| 162 |     | Cloud       | Ceilings 2D       | This plot        | presents          | a 2-D   |
| --- | --- | ----------- | ----------------- | ---------------- | ----------------- | ------- |
|     |     | Histogram   | (Level by Week)   | histogram        | of reported       | cloud   |
|     |     |             |                   | ceilings         | as inferred       | by the  |
|     |     |             |                   | METAR            | cloud amount      |         |
|     |     |             |                   | reports          | of at least       | BKN     |
|     |     |             |                   | (broken)         | or OVC (overcast) |         |
|     |     |             |                   | from the         | automated         | sensor. |
| 213 |     | Percentiles | of Hourly ASOS    | This application | generates         |         |
|     |     | Data by     | Day, Week, Month, | percentiles      | based on          |         |
|     |     | or Year     |                   | available        | data from         | the     |
|     |     |             |                   | selected         | station.          |         |

| Mastering | the Mesonet |             |        |           |     |              |                 |      | 161  |
| --------- | ----------- | ----------- | ------ | --------- | --- | ------------ | --------------- | ---- | ---- |
| q         |             | Title       |        |           |     | Description  |                 |      |      |
| 146       |             | Temperature |        | Frequency | by  | This chart   | displays        | the  |      |
|           |             | Week        | During | Precip    |     | frequency    | of having       |      |      |
|           |             |             |        |           |     | measurable   | precipitation   |      |      |
|           |             |             |        |           |     | reported     | by an           | ASOS | site |
|           |             |             |        |           |     | and the      | air temperature |      | that |
|           |             |             |        |           |     | was reported | at              | the  | same |
time.
| 155  |            | Top       | 10     | / Most Recent     |      | Based on         | available | hourly     |         |
| ---- | ---------- | --------- | ------ | ----------------- | ---- | ---------------- | --------- | ---------- | ------- |
|      |            | Hourly    |        | Reports from      | ASOS | observation      | reports   | by         |         |
|      |            | Stations  |        |                   |      | METAR            | stations, | this       |         |
|      |            |           |        |                   |      | application      | presents  |            | the top |
|      |            |           |        |                   |      | 10 events        | for a     | given      | metric  |
|      |            |           |        |                   |      | of your          | choice.   |            |         |
| 16   |            | Wind      | Rose   | when specified    |      | This application |           | generates  | a       |
|      |            | criterion |        | is meet           |      | wind rose        | for       | a given    |         |
|      |            |           |        |                   |      | criterion        | being     | meet.      |         |
| NASS | Quickstats | (USDA     | Crop   | Statistics)       |      |                  |           |            |         |
| q    |            | Title     |        |                   |      | Description      |           |            |         |
| 238  |            | NASS      | County | Yield             | Maps | This app         | generates | maps       | of      |
|      |            |           |        |                   |      | yearly USDA      |           | NASS       | county  |
|      |            |           |        |                   |      | yield estimates. |           |            |         |
| 239  |            | NASS      | County | Yields            | +    | This autoplot    |           | combines   | the     |
|      |            | Weather   |        | Station Summaries |      | USDA             | NASS      | county     | yield   |
|      |            |           |        |                   |      | estimates        | with      | summarized |         |
|      |            |           |        |                   |      | weather          | variables | from       | a       |
|      |            |           |        |                   |      | single weather   |           | station.   |         |
| 156  |            | NASS      | Crop   | Condition         | by   | This chart       | presents  | crop       |         |
|      |            | Year      | for    | Six States        |      | condition        | reports   | from       |         |
USDA/NASS.
| 127 |     | NASS    | Crop | Progress | by    | This chart     | presents | the   | crop   |
| --- | --- | ------- | ---- | -------- | ----- | -------------- | -------- | ----- | ------ |
|     |     | Year    |      |          |       | progress       | by year. |       |        |
| 197 |     | NASS    | Crop | Progress | State | This generates |          | a map |        |
|     |     | Average |      | Map      |       | showing        | USDA     | NASS  | weekly |
statistics.

| Mastering   | the Mesonet |            |             |            |                  |               |           | 162        |
| ----------- | ----------- | ---------- | ----------- | ---------- | ---------------- | ------------- | --------- | ---------- |
| q           |             | Title      |             |            | Description      |               |           |            |
| 209         |             | NASS Crop  | Progress    | Weekly     | This             | plot presents |           | the        |
|             |             | Change     |             |            | weekly           | change        | in        | a given    |
|             |             |            |             |            | USDA             | NASS          | Crop      | Progress   |
|             |             |            |             |            | report           | variable.     |           |            |
| NWS Warning | Plots       |            |             |            |                  |               |           |            |
| q           |             | Title      |             |            | Description      |               |           |            |
| 196         |             | ASOS/METAR |             | Heat Index | / This           | plot presents |           | a          |
|             |             | Wind Chill | Frequencies |            | by frequency     |               | of having | either a   |
|             |             | NWS Alert  | Headline    |            | heat             | index         | or wind   | chill      |
|             |             |            |             |            | advisory/warning |               |           | active for |
|             |             |            |             |            | a given          | computed      |           | feels like |
temperature.
| 232 |     | ASOS/METAR     |           | Time        | Series This | app plots   |              |           |
| --- | --- | -------------- | --------- | ----------- | ----------- | ----------- | ------------ | --------- |
|     |     | during         | NWS Alert | Headline    | ASOS/METAR  |             | data         | during    |
|     |     | (Blizzard      | / Fire    | / Fog       | / a period  | of          | your choice  | and       |
|     |     | Wind /         | Heat /    | Wind Chill) | overlays    | NWS         | Watch,       |           |
|     |     |                |           |             | Warning,    | and         | Advisory     | data.     |
| 191 |     | Calendar       | Plot      | of          | This        | application | presents     | a         |
|     |     | Watch/Warn/Adv |           | Daily       | calendar    | of          | daily counts | of        |
|     |     | Counts         |           |             | the number  |             | of watch,    |           |
|     |     |                |           |             | warning,    | advisories  |              | issued by |
day.
| 253  |     | NWS Damage             |        | Assessment | This      | autoplot   | combines   |            |
| ---- | --- | ---------------------- | ------ | ---------- | --------- | ---------- | ---------- | ---------- |
|      |     | Toolkit                | (DAT)  | Tornado    | NWS       | Damage     | Assessment |            |
|      |     | Tracks                 | + Lead | Time       | Toolkit   | (DAT)      | tornado    |            |
|      |     |                        |        |            | tracks    | (lines)    | with       | Tornado    |
|      |     |                        |        |            | Warning   | (polygons) |            | to         |
|      |     |                        |        |            | provide   | along      | track      |            |
|      |     |                        |        |            | estimates | of         | lead time. |            |
| 92 � |     | Days since             | Last   |            | This      | map        | depicts    | the        |
|      |     | Watch/Warning/Advisory |        |            | by number | of         | days since | a          |
|      |     | WFO                    |        |            | Weather   | Forecast   |            | Office has |
|      |     |                        |        |            | issued    | a given    | VTEC       |            |
product.

| Mastering | the Mesonet |                          |        |             |               | 163   |
| --------- | ----------- | ------------------------ | ------ | ----------- | ------------- | ----- |
| q         |             | Title                    |        | Description |               |       |
| 72        |             | Frequency                | of     | This chart  | presents      | a     |
|           |             | Watch/Warning/Advisories |        | histogram   | of the Watch, |       |
|           |             | by Time                  | of Day | Warning,    | Advisory      | valid |
time.
| 50   |     | Frequency                | of Hail/Wind     | This app     | produces        | a table of |
| ---- | --- | ------------------------ | ---------------- | ------------ | --------------- | ---------- |
|      |     | Tags used                | in Severe TStorm | frequencies  | of wind         | and hail   |
|      |     | Warnings                 |                  | tags used    | in NWS          | Severe     |
|      |     |                          |                  | Thunderstorm | Warnings.       |            |
| 52 � |     | Gantt                    | Chart of         | Gantt        | chart of watch, |            |
|      |     | Watch/Warning/Advisories |                  | warning,     | and advisories  |            |
|      |     | by WFO                   | or UGC           | (WaWa)       | issued by       | an NWS     |
|      |     |                          |                  | Forecast     | Office for      | a start    |
|      |     |                          |                  | date and     | number          | of days of |
your choice.
| 245 |     | Local Storm | Reports by     | This chart    | presents       | the total |
| --- | --- | ----------- | -------------- | ------------- | -------------- | --------- |
|     |     | Month/Year  | + Top 10 Daily | number        | of Local Storm |           |
|     |     |             |                | Reports       | disseminated   | by the    |
|     |     |             |                | NWS by        | month and      | year.     |
| 234 |     | Local Storm | Reports        | This autoplot | generates      | a         |
|     |     | Calendar    | Counts         | calendar      | showing        | calendar  |
|     |     |             |                | day Local     | Storm Report   |           |
|     |     |             |                | totals by     | NWS Weather    |           |
|     |     |             |                | Forecast      | Office (WFO)   | or        |
State.
| 163 |     | Local Storm  | Reports Issued | This application | generates       | a       |
| --- | --- | ------------ | -------------- | ---------------- | --------------- | ------- |
|     |     | by WFO/State | [map]          | map displaying   | the             | number  |
|     |     |              |                | of LSRs          | issued between  | a       |
|     |     |              |                | period           | of your choice. |         |
| 102 |     | Local Storm  | Report Source  | The National     | Weather         |         |
|     |     | Type Ranks   | by Year        | Service          | issues Local    | Storm   |
|     |     |              |                | Reports          | (LSRs) with     | a label |
|     |     |              |                | associated       | with each       | report  |
|     |     |              |                | indicating       | the source      | of the  |
report.
| 237 |     | Map of        | WFO/CWSU     | This autoplot | is a        | bit of a |
| --- | --- | ------------- | ------------ | ------------- | ----------- | -------- |
|     |     | Miscellaneous | Event Counts | catch-all     | for mapping | event    |
|     |     | (SPS/CWA)     |              | counts        | at a WFO    | or CWSU  |
map unit.

| Mastering | the Mesonet |                          |             |                        |                 | 164       |
| --------- | ----------- | ------------------------ | ----------- | ---------------------- | --------------- | --------- |
| q         |             | Title                    |             | Description            |                 |           |
| 260       |             | Map of                   | WFO         | This autoplot          | maps            | out the   |
|           |             | Watch/Warning/Advisories |             | issued                 | NWS             |           |
|           |             | over a                   | Time Period | Watch/Warning/Advisory |                 |           |
|           |             |                          |             | events                 | over a given    | time      |
|           |             |                          |             | period                 | of your choice. |           |
| 44 �      |             | NWS Office               | Accumulated | This plot              | displays        | an        |
|           |             | Watch/Warning/Advisories |             | accumulated            | total           | of office |
|           |             | by Year                  |             | issued                 | watch, warning, |           |
advisories.
| 68  |     | Number                   | of Distinct | This chart   | shows the      | number   |
| --- | --- | ------------------------ | ----------- | ------------ | -------------- | -------- |
|     |     | Phenomena/Significance   |             | of VTEC      | phenomena      | and      |
|     |     | VTEC                     | per Year    | significance | combinations   |          |
|     |     |                          |             | issued       | by a NWS       | Forecast |
|     |     |                          |             | Office       | for a given    | year.    |
| 73  |     | Number                   | of          | This chart   | displays       | the      |
|     |     | Watch/Warning/Advisories |             | number       | of products    | issued   |
|     |     | Issued                   | per Year    | by a NWS     | Office or      | state by |
|     |     |                          |             | year for     | a given watch, |          |
|     |     |                          |             | warning,     | or advisory    | of your  |
choice.
| 171 |     | Number                   | of                 | This chart    | displays       | the      |
| --- | --- | ------------------------ | ------------------ | ------------- | -------------- | -------- |
|     |     | Watch/Warning/Advisories |                    | monthly       | number of      | distinct |
|     |     | Issued                   | per Year per Month | + NWS Office  | issued         | watch /  |
|     |     | Top 10                   | Daily              | warning       | / advisory     | product. |
| 247 |     | NWS Watch                | Warning            | This autoplot | generates      | a        |
|     |     | Advisory                 | (WaWa) Map         | + map of      | active NWS     | Watch,   |
|     |     | Population               | Stats              | Warnings,     | and Advisories |          |
|     |     |                          |                    | active        | at the given   |          |
timestamp.
| 251 |     | NWS Warning | Load Time         | The purpose    | of this        | autoplot  |
| --- | --- | ----------- | ----------------- | -------------- | -------------- | --------- |
|     |     | Series      |                   | is to generate | a time         | series    |
|     |     |             |                   | of NWS         | warning load   | with      |
|     |     |             |                   | time for       | short fuse     | warnings. |
| 70  |     | Period      | between First and | This chart     | attempts       | to        |
|     |     | Last VTEC   | Product Each      | display        | the period     | between   |
|     |     | Year        |                   | the first      | and last VTEC  |           |
|     |     |             |                   | enabled        | watch, warning | or        |
|     |     |             |                   | advisory       | issuance       | by year.  |

| Mastering | the Mesonet |                |     |           |             |          |           |              | 165      |
| --------- | ----------- | -------------- | --- | --------- | ----------- | -------- | --------- | ------------ | -------- |
| q         |             | Title          |     |           | Description |          |           |              |          |
| 248       |             | Period between |     | First and | This        | chart    | displays  |              | the      |
|           |             | Last SPC/WPC   |     | Outlook   | period      |          | each year | between      |          |
|           |             | each Year      |     |           | the         | first    | and       | last SPC/WPC |          |
|           |             |                |     |           | outlook     |          | type      | for a given  |          |
|           |             |                |     |           | NWS         | forecast |           | office,      | state or |
county.
| 224 |     | Population/Area        |     | under | This      | autoplot |         | attempts | to  |
| --- | --- | ---------------------- | --- | ----- | --------- | -------- | ------- | -------- | --- |
|     |     | NWS                    |     |       | estimate  |          | the     | number   | of  |
|     |     | Watch/Warning/Advisory |     |       | at people |          | or area | in the   | US  |
|     |     | Time                   |     |       | under     | a        | given   | NWS      |     |
Watch/Warning/Advisory
(WaWA).
| 203 |     | Storm Based         |             | Warning      | This         | application |            | generates   | a       |
| --- | --- | ------------------- | ----------- | ------------ | ------------ | ----------- | ---------- | ----------- | ------- |
|     |     | Polygon             | Visual      | Summary      | visual       | summary     |            | of polygons |         |
|     |     |                     |             |              | issued       | for         | a given    | UTC         | date.   |
| 195 |     | Storm Motion        |             | distribution | Some         | of          | the        | warnings    | that    |
|     |     | based on            | NWS         | Warnings     | the          | National    |            | Weather     |         |
|     |     |                     |             |              | Service      |             | issues     | includes    | a       |
|     |     |                     |             |              | storm        | motion      |            | vector.     |         |
| 201 |     | SPC Convective/Fire |             | Wx           | or This      | application |            | presents    | a       |
|     |     | WPC Excessive       |             | Rainfall     | calendar     |             | of Storm   | Prediction  |         |
|     |     | Outlook             | Calendar    |              | Center       |             | or Weather |             |         |
|     |     |                     |             |              | Prediction   |             | Center     | outlooks    |         |
|     |     |                     |             |              | by           | state,      | WFO,       | or county.  |         |
| 258 |     | SPC Convective/Fire |             | Wx           | or This      | tool        | generates  |             | an      |
|     |     | WPC Excessive       |             | Rainfall     | info-graphic |             |            | with the    |         |
|     |     | Outlook             | Progression | for          | progression  |             | of         | outlooks    | for a   |
|     |     | Lat/Lon             |             |              | given        | point       | and        | date.       |         |
| 230 |     | SPC Convective/Fire |             | Wx           | or This      | application |            | presents    | an      |
|     |     | WPC Excessive       |             | Rainfall     | infographic  |             | showing    |             | the     |
|     |     | Last Event          | Infographic |              | most         | recent      |            | date of     | a given |
|     |     |                     |             |              | SPC          | outlook     |            | threshold   | as      |
|     |     |                     |             |              | per          | IEM         | unofficial | archives.   |         |
| 200 |     | SPC +               | WPC         | Outlook      | This         | application |            | generates   |         |
|     |     | Heatmap             |             |              | heatmaps     |             | of         | Storm       |         |
|     |     |                     |             |              | Prediction   |             | Center     | convective  |         |
outlooks.

| Mastering | the Mesonet |               |         |            |             |               |            | 166 |
| --------- | ----------- | ------------- | ------- | ---------- | ----------- | ------------- | ---------- | --- |
| q         |             | Title         |         |            | Description |               |            |     |
| 143       |             | Special       | Weather | Statements | The NWS     | issues        | Special    |     |
|           |             | (SPS) Polygon |         | Count by   | Weather     | Statements    | (SPS)      |     |
|           |             | Year by       | Month   |            | products    | that often    | cover      |     |
|           |             |               |         |            | events      | that are      | just below |     |
|           |             |               |         |            | severe      | limits and/or | not        |     |
|           |             |               |         |            | covered     | by other      | headline   |     |
products.
| 233 |     | Special       | Weather    | Statements   | This calendar | presents         |            | the    |
| --- | --- | ------------- | ---------- | ------------ | ------------- | ---------------- | ---------- | ------ |
|     |     | (SPS) Polygon |            | Calendar of  | number        | of Special       | Weather    |        |
|     |     | Daily Counts  |            |              | Statements    | that             | contain    |        |
|     |     |               |            |              | polygons      | issued           | per day.   |        |
| 166 |     | Storm         | Prediction | Center       | This plot     | presents         | a          |        |
|     |     | (SPC) Watches |            | per Year for | summary       | of the           | number     | of     |
|     |     | a State       |            |              | year to       | date watches     |            | issued |
|     |     |               |            |              | by the        | Storm Prediction |            |        |
|     |     |               |            |              | Center        | and the          | percentage | of     |
|     |     |               |            |              | those watches | that             | at         | least  |
|     |     |               |            |              | touched       | the given        | state,     |        |
|     |     |               |            |              | county        | warning          | area,      | or     |
fema region.
| 210 |     | Text Product |          | Frequency | This application |            | generates | a      |
| --- | --- | ------------ | -------- | --------- | ---------------- | ---------- | --------- | ------ |
|     |     | Maps         |          |           | map of           | the per    | WFO       | office |
|     |     |              |          |           | usage of         | a given    | text      |        |
|     |     |              |          |           | product          | identifier | based     | on     |
|     |     |              |          |           | unofficial       | IEM        | archives  | of     |
|     |     |              |          |           | NWS Text         | Product    | data.     |        |
| 235 |     | Text Product |          | Issuance  | This autoplot    | presents   |           | the    |
|     |     | Counts       | by Month | + Year    | total number     | of         | text      |        |
|     |     |              |          |           | products         | issued     | by UTC    |        |
|     |     |              |          |           | month            | and year.  |           |        |
| 261 |     | Text Product |          | Issuance  | This chart       | presents   | a         |        |
|     |     | Heatmap      | by Hour  | / Day     | heatmap          | of the     | issuance  |        |
|     |     |              |          |           | hour of          | a given    | NWS       | Text   |
Product.
| 48  |     | Time of       | Day Frequency | for   | For a given            |             |         |      |
| --- | --- | ------------- | ------------- | ----- | ---------------------- | ----------- | ------- | ---- |
|     |     | Given Warning |               | / UGC | watch/warning/advisory |             |         |      |
|     |     |               |               |       | type and               | forecast    | zone,   | what |
|     |     |               |               |       | is the frequency       |             | by time | of   |
|     |     |               |               |       | day that               | the product |         | was  |
valid.

| Mastering | the Mesonet |                        |               |               |                 | 167       |
| --------- | ----------- | ---------------------- | ------------- | ------------- | --------------- | --------- |
| q         |             | Title                  |               | Description   |                 |           |
| 80        |             | Time Duration          | of a          | This plot     | presents        | the       |
|           |             | Watch/Warning/Advisory |               | accumulated   | frequency       | of        |
|           |             | for a UGC/WFO          |               | duration      | for a given     | NWS       |
|           |             |                        |               | VTEC          | Watch, Warning, |           |
|           |             |                        |               | Advisory      | product.        |           |
| 243       |             | Top 10                 | VTEC Event    | This autoplot | prints          | out the   |
|           |             | Days/Multi-Day         | by            | top 10        | dates for       | number of |
|           |             | Year/Month             |               | VTEC          | events issued.  |           |
| 101       |             | Top 25                 | Most Frequent | This chart    | displays        | the       |
|           |             | VTEC                   | Products by   | relative      | frequency       | of VTEC   |
|           |             | Office/NWS             |               | products.     |                 |           |
| 259       |             | UGC Geometry           | Change        | This tool     | generates       | a         |
|           |             | Diagnostic             |               | diagnostic    | plot of         | how a     |
|           |             |                        |               | given         | NWS UGC         | geometry  |
|           |             |                        |               | has changed   | over            | time.     |
| 56        |             | Weekly/Daily/Monthly   |               | This chart    | shows           | the time  |
|           |             | Frequency              | of a          | partitioned   | frequency       | of        |
|           |             | Watch/Warning/Advisory |               | having        | at least one    |           |
watch/warning/advisory
|             |       |                        |                  | (WWA)            | issued by     | the         |
| ----------- | ----- | ---------------------- | ---------------- | ---------------- | ------------- | ----------- |
|             |       |                        |                  | Weather          | Forecast      | Office (top |
|             |       |                        |                  | plot) and        | the overall   | number      |
|             |       |                        |                  | of WWA           | issued        | events      |
|             |       |                        |                  | (bottom          | plot).        |             |
| 109 �       |       | WFO /                  | State VTEC Event | This application |               | generates   |
|             |       | Counts/Time            | Coverage         | per WFO          | or state      | maps of     |
|             |       | Percent/Num            | Days for         | a VTEC           | event counts. |             |
|             |       | Given Period           | (map)            |                  |               |             |
| 208         |       | WFO VTEC               | Single Event     | This application |               | generates a |
|             |       | Map Plot               | (map)            | map showing      | the           | coverage of |
|             |       |                        |                  | a given          | VTEC alert.   |             |
| 90          |       | UGC or                 | Polygon SBW      | This application |               | has a       |
|             |       | Statistics             | for              | considerable     | and           | likely      |
|             |       | Watch/Warning/Advisory |                  | by confusing     | amount        | of          |
|             |       | state/wfo              |                  | configuration    | options.      |             |
| Tall Towers | Plots |                        |                  |                  |               |             |

| Mastering | the Mesonet |             |              |            |     |             |       |                 |          | 168     |
| --------- | ----------- | ----------- | ------------ | ---------- | --- | ----------- | ----- | --------------- | -------- | ------- |
| q         |             | Title       |              |            |     | Description |       |                 |          |         |
| 158       |             | Tall Towers |              | - 1 Second |     | This        | plot  | presents        | one      |         |
|           |             | Interval    | Time         | Series     |     | second      |       | data from       | the      | Iowa    |
|           |             |             |              |            |     | Atmospheric |       | Observatory     |          |         |
|           |             |             |              |            |     | Tall-Towers |       | sites           | overseen | by      |
|           |             |             |              |            |     | Dr          | Gene  | Takle.          |          |         |
| Upper     | Air / RAOB  | Sounding    | Plots        |            |     |             |       |                 |          |         |
| q         |             | Title       |              |            |     | Description |       |                 |          |         |
| 198       |             | Monthly     | Max/Min/Avgs |            | for | This        | plot  | presents        | a simple |         |
|           |             | Sounding    | Parameter    | or         |     | average     |       | of a given      | sounding |         |
|           |             | Variable    | at Given     | Level      |     | variable    |       | of your         | choice.  |         |
| 150       |             | Single      | Sounding     | Mandatory  |     | This        | plot  | presents        |          |         |
|           |             | Level       | Percentile   | Ranks      |     | percentiles |       | of observations |          |         |
|           |             |             |              |            |     | from        | a     | given sounding  |          | profile |
|           |             |             |              |            |     | against     |       | the long        | term     | record  |
|           |             |             |              |            |     | for         | the   | site.           |          |         |
| 212       |             | Sounding    | Parameter    | /          |     | This        | plot  | presents        | the      | daily   |
|           |             | Variable    | Yearly       | Timeseries |     | climatology |       | range           | of a     |         |
|           |             |             |              |            |     | sounding    |       | variable        | along    | with    |
|           |             |             |              |            |     | a           | given | year’s values.  |          |         |
Miscellaneous
| q   |     | Title   |               |          |     | Description   |       |             |         |     |
| --- | --- | ------- | ------------- | -------- | --- | ------------- | ----- | ----------- | ------- | --- |
| 226 |     | Center  | Weather       | Advisory |     | This          | plot  | is not      | meant   | for |
|     |     | (CWA)   | Map           |          |     | interactive   |       | use,        | but a   |     |
|     |     |         |               |          |     | backend       |       | for CWA     | plots.  |     |
| 257 |     | HRRR    | Comprehensive |          |     | This          | tool  | plots       | the     |     |
|     |     | Climate | Index         | (CCI)    |     | Comprehensive |       |             | Climate |     |
|     |     |         |               |          |     | Index         | (CCI) | based       | on      |     |
|     |     |         |               |          |     | HRRR          |       | model data. |         |     |

| Mastering | the Mesonet |          |              |      |             |                    |           | 169 |
| --------- | ----------- | -------- | ------------ | ---- | ----------- | ------------------ | --------- | --- |
| q         |             | Title    |              |      | Description |                    |           |     |
| 221       |             | HRRR     | Time-Lagged  |      | The         | NCEP deterministic |           |     |
|           |             | Ensemble | Reflectivity | Plot | HRRR        | model forecast     |           |     |
|           |             |          |              |      | produces    | a post             | processed |     |
|           |             |          |              |      | field       | that is meant      | to        |     |
|           |             |          |              |      | resemble    | RADAR              |           |     |
reflectivity.
| 242 |     | Local Storm | Report | (LSR) | Presently, | this           | autoplot     | is a  |
| --- | --- | ----------- | ------ | ----- | ---------- | -------------- | ------------ | ----- |
|     |     | Simple      | Map    |       | backend    | for generating |              | Local |
|     |     |             |        |       | Storm      | Report         | social media |       |
graphics.
| 254 |     | NEXRAD        | Level | III Latency | Map       | of NEXRAD | Level    | III |
| --- | --- | ------------- | ----- | ----------- | --------- | --------- | -------- | --- |
|     |     | over NOAAPort |       |             | Latencies | over      | NOAAPort | or  |
Realtime-ness.
| 227 |     | NWEM     | / NWS Non-VTEC |      | This        | plot is not       | meant  | for |
| --- | --- | -------- | -------------- | ---- | ----------- | ----------------- | ------ | --- |
|     |     | Products | containing     | a    | interactive | use,              | but a  |     |
|     |     | polygon  |                |      | backend     | for NWEM          | plots. |     |
| 236 |     | PIREP    | Daily Counts   | by   | This        | autoplot presents |        | a   |
|     |     | ARTCC    | / Alaska       | Zone | time        | series of UTC     | daily  |     |
|     |     |          |                |      | PIREP       | totals by         | ARTCC  | or  |
Alaska Zone.
| 220 |     | SPC Convective |         | / Fire    | This         | app generates |           |     |
| --- | --- | -------------- | ------- | --------- | ------------ | ------------- | --------- | --- |
|     |     | Weather        | / WPC   | Excessive | infographics | for           | the Storm |     |
|     |     | Rainfall       | Outlook | Graphics  | Prediction   | Center        | or        |     |
|     |     |                |         |           | Weather      | Prediction    | Center    |     |
outlooks.
| 217 |     | SPS Special | Weather           |     | This         | plot is not   | meant    | for |
| --- | --- | ----------- | ----------------- | --- | ------------ | ------------- | -------- | --- |
|     |     | Statement   | Maps              |     | interactive  | use,          | but a    |     |
|     |     |             |                   |     | backend      | for SPS       | plots.   |     |
| 219 |     | Terminal    | Aerodrome         |     | This         | app generates |          |     |
|     |     | Forecast    | (TAF) Infographic |     | infographics | for           | Terminal |     |
|     |     |             |                   |     | Aerodrome    | Forecasts     | (TAF).   |     |

| Appendix | D — | GIS Shapefile | Download |     |
| -------- | --- | ------------- | -------- | --- |
Reference
All 13 IEM GIS download endpoints under /request/gis/, plus related spatial download
resources. These portals produce shapefiles, CSVs, and GeoJSON files suitable for use in
QGIS, ArcGIS, Python (geopandas), R (sf), or any GIS-capable application.
All endpoints are at https://mesonet.agron.iastate.edu + the path shown.
| /request/gis/    | Endpoints |               |              |               |
| ---------------- | --------- | ------------- | ------------ | ------------- |
| Endpoint         | Data Type | Output Format | Date Range   | Notes         |
| /re-             | NWS Watch | / Shapefile   | 2005–present | Includes full |
| quest/gis/watch- | Warning   | /             | (VTEC era)   | VTEC          |
| warn.phtml       | Advisory  |               |              | metadata:     |
|                  | polygons  |               |              | phenomena,    |
significance,
ETN, WFO,
issuance and
expiration times.
Pre-2007 events
use county
boundaries
rather than
storm-based
polygons.
170

| Mastering                   | the Mesonet |           |                    |             | 171 |
| --------------------------- | ----------- | --------- | ------------------ | ----------- | --- |
| Endpoint                    | Data Type   | Output    | Format Date Range  | Notes       |     |
| /re-                        | Local Storm | Shapefile | / CSV 2003–present | Point data. |     |
| quest/gis/lsrs.phtmRleports |             |           |                    | Filterable  | by  |
event type
|     |     |     |     | (tornado, | hail, |
| --- | --- | --- | --- | --------- | ----- |
wind, flood,
snow, etc.),
magnitude
threshold,
|     |     |     |     | WFO, and | date |
| --- | --- | --- | --- | -------- | ---- |
range.
| /re-                       | SPC Convective | Shapefile | ~2002–present | Includes    | Day 1, |
| -------------------------- | -------------- | --------- | ------------- | ----------- | ------ |
| quest/gis/spc_out-Outlooks |                |           |               | Day 2,      | Day 3  |
| looks.phtml                |                |           |               | categorical | and    |
probabilistic
|     |     |     |     | outlooks. | Also |
| --- | --- | --- | --- | --------- | ---- |
covers Fire
Weather
|     |     |     |     | outlooks. | One |
| --- | --- | --- | --- | --------- | --- |
|     |     |     |     | shapefile | per |
outlook
day/category.
| /re-                               | SPC Tornado  | Shapefile | 1986–present | Includes     | ETN, |
| ---------------------------------- | ------------ | --------- | ------------ | ------------ | ---- |
| quest/gis/spc_watcahn.dphStemvlere |              |           |              | issuance     | and  |
|                                    | Thunderstorm |           |              | expiration   |      |
|                                    | Watches      |           |              | times, watch |      |
|                                    |              |           |              | type, and    | PDS  |
flag. Watch
|     |     |     |     | polygons | are |
| --- | --- | --- | --- | -------- | --- |
the county-list-
|     |     |     |     | based areas, | not |
| --- | --- | --- | --- | ------------ | --- |
the
parallelogram
watch boxes.

| Mastering                         | the Mesonet   |               |               |            | 172  |
| --------------------------------- | ------------- | ------------- | ------------- | ---------- | ---- |
| Endpoint                          | Data Type     | Output Format | Date Range    | Notes      |      |
| /re-                              | SPC Mesoscale | Shapefile     | ~2003–present | Polygon    |      |
| quest/gis/spc_mcdC.pohntvmecltive |               |               |               | boundaries | of   |
|                                   | Discussions   |               |               | each MCD   | with |
|                                   |               |               |               | issuance   | time |
and MCD
|     |     |     |     | number.        | Text of |
| --- | --- | --- | --- | -------------- | ------- |
|     |     |     |     | the discussion | is      |
|     |     |     |     | not included   | in      |
the shapefile
but retrievable
|     |     |     |     | from the     | IEM |
| --- | --- | --- | --- | ------------ | --- |
|     |     |     |     | text archive | by  |
PIL.
| /re-                          | Special Weather | Shapefile | ~2007–present | Polygon-bearing |     |
| ----------------------------- | --------------- | --------- | ------------- | --------------- | --- |
| quest/gis/sps.phtmSltatements |                 |           |               | SPS products    |     |
|                               |                 |           |               | only. Not       | all |
SPS products
contain
|     |     |     |     | polygons; | this |
| --- | --- | --- | --- | --------- | ---- |
endpoint
|     |     |     |     | captures | those |
| --- | --- | --- | --- | -------- | ----- |
that do.
| /re-                                 | WPC Mesoscale | Shapefile | ~2003–present | Polygon    |      |
| ------------------------------------ | ------------- | --------- | ------------- | ---------- | ---- |
| quest/gis/wpc_mpPd.rpehcitpmitlation |               |           |               | boundaries | with |
|                                      | Discussions   |           |               | issuance   | time |
and MPD
|     |     |     |     | number.   | Pairs |
| --- | --- | --- | --- | --------- | ----- |
|     |     |     |     | well with | the   |
|     |     |     |     | WPC QPF   | data  |
for precipitation
event analysis.

| Mastering                      | the Mesonet    |               |               |           | 173    |
| ------------------------------ | -------------- | ------------- | ------------- | --------- | ------ |
| Endpoint                       | Data Type      | Output Format | Date Range    | Notes     |        |
| /re-                           | Center Weather | Shapefile     | ~2008–present | Aviation  |        |
| quest/gis/cwas.phtmAdlvisories |                |               |               | product.  |        |
|                                |                |               |               | Polygons  | issued |
|                                |                |               |               | by ARTCCs | for    |
significant
in-flight
|     |     |     |     | weather. | Useful |
| --- | --- | --- | --- | -------- | ------ |
for correlating
flight delays
with
atmospheric
hazards.
| /re-               | SIGMETs | Shapefile | ~2008–present | Aviation      |        |
| ------------------ | ------- | --------- | ------------- | ------------- | ------ |
| quest/gis/awc_sig- |         |           |               | product.      | Covers |
| mets.phtml         |         |           |               | both domestic |        |
and
international
SIGMETs,
including
Convective
SIGMETs.
|     |     |     |     | Polygon | or line |
| --- | --- | --- | --- | ------- | ------- |
geometry
|                              |           |           |               | depending     | on  |
| ---------------------------- | --------- | --------- | ------------- | ------------- | --- |
|                              |           |           |               | product type. |     |
| /re-                         | G-AIRMETs | Shapefile | ~2008–present | Aviation      |     |
| quest/gis/awc_gairmets.phtml |           |           |               | product.      |     |
Graphical
|     |     |     |     | AIRMETs | for |
| --- | --- | --- | --- | ------- | --- |
turbulence,
|     |     |     |     | icing, and | IFR |
| --- | --- | --- | --- | ---------- | --- |
conditions
below 18,000
feet MSL.
|     |     |     |     | Replaced | text |
| --- | --- | --- | --- | -------- | ---- |
AIRMETs
|     |     |     |     | operationally | in  |
| --- | --- | --- | --- | ------------- | --- |
2017.

| Mastering                       | the Mesonet |           |                     |             | 174   |
| ------------------------------- | ----------- | --------- | ------------------- | ----------- | ----- |
| Endpoint                        | Data Type   | Output    | Format Date Range   | Notes       |       |
| /re-                            | NEXRAD      | Shapefile | / CSV ~2010–present | Point data. | One   |
| quest/gis/nexrad_sSttoorrmm_at- |             |           |                     | point per   |       |
| trs.php                         | Attributes  |           |                     | tracked     | storm |
cell per volume
scan, with
attributes
including
|     |     |     |     | estimated | hail |
| --- | --- | --- | --- | --------- | ---- |
size, probability
|     |     |     |     | of severe   | hail  |
| --- | --- | --- | --- | ----------- | ----- |
|     |     |     |     | (POSH),     | storm |
|     |     |     |     | top height, | and   |
rotation
(azimuthal
shear). Updated
approximately
every 5–6
|     |     |     |     | minutes | during |
| --- | --- | --- | --- | ------- | ------ |
active periods.
Also available
as a live
|     |     |     |     | shapefile | at  |
| --- | --- | --- | --- | --------- | --- |
/data/gis/shape/4326/us/current_nexattr.zip.
/re- Pilot Reports Shapefile / CSV ~2005–present Point data at
| quest/gis/pireps.php |     |     |     | the reported |     |
| -------------------- | --- | --- | --- | ------------ | --- |
aircraft position.
Attributes
include altitude,
turbulence
|     |     |     |     | intensity, | icing |
| --- | --- | --- | --- | ---------- | ----- |
|     |     |     |     | intensity, | sky   |
|     |     |     |     | condition, | and   |
visibility.

| Mastering               | the Mesonet |               |               |            |         | 175           |
| ----------------------- | ----------- | ------------- | ------------- | ---------- | ------- | ------------- |
| Endpoint                |             | Data Type     | Output Format | Date Range | Notes   |               |
| /re-                    |             | Miscellaneous | Various       | Varies     | A       | catch-all for |
| quest/gis/misc.phtmGlIS |             | Products      |               |            | spatial | products      |
|                         |             |               |               |            | that    | do not fit    |
|                         |             |               |               |            | the     | other         |
categories.
|     |     |     |     |     | Contents | vary;    |
| --- | --- | --- | --- | --- | -------- | -------- |
|     |     |     |     |     | check    | the page |
|     |     |     |     |     | directly | for      |
current
offerings.
| Related | Spatial | Downloads |     |     |     |     |
| ------- | ------- | --------- | --- | --- | --- | --- |
These endpoints produce spatial data but live outside the /request/gis/ tree.
| Resource |     | URL | Format |     | Notes |     |
| -------- | --- | --- | ------ | --- | ----- | --- |
Current warning /data/gis/shape/4326/uSsh/acupre-file Updated
| polygons | (live) | rent_ww.zip |     |     | continuously. | All    |
| -------- | ------ | ----------- | --- | --- | ------------- | ------ |
|          |        |             |     |     | currently     | active |
NWS watch/warn-
ing/advisory
|     |     |     |     |     | polygons | in a single |
| --- | --- | --- | --- | --- | -------- | ----------- |
file.
Current 24-hr LSRs /data/gis/shape/4326/uSsh/alspr_efi2l4ehour.zip Rolling 24-hour
| (live) |     |     |     |     | window | of Local |
| ------ | --- | --- | --- | --- | ------ | -------- |
Storm Reports.
|     |     |     |     |     | Updated | as new |
| --- | --- | --- | --- | --- | ------- | ------ |
LSRs arrive.
Current NEXRAD /data/gis/shape/4326/uSsh/acupre-file Current volume scan
| storm attributes |     | rent_nexattr.zip |     |     | storm attributes | for    |
| ---------------- | --- | ---------------- | --- | --- | ---------------- | ------ |
| (live)           |     |                  |     |     | all active       | NEXRAD |
|                  |     |                  |     |     | sites. Updated   | every  |
~5 minutes.

| Mastering | the Mesonet |                  |         |             |               | 176           |
| --------- | ----------- | ---------------- | ------- | ----------- | ------------- | ------------- |
| Resource  |             | URL              | Format  |             | Notes         |               |
| GeoTIFF   | rasters     | /GIS/rasters.php | GeoTIFF |             | NEXRAD        |               |
|           |             |                  |         |             | composites,   | GOES          |
|           |             |                  |         |             | satellite     | products,     |
|           |             |                  |         |             | and MRMS      | fields        |
|           |             |                  |         |             | available     | as            |
|           |             |                  |         |             | georeferenced | raster        |
|           |             |                  |         |             | files for     | GIS import.   |
| OGC Web   | Services    | /ogc/            | WMS     | / WFS / TMS | Standard      | OGC           |
|           |             |                  |         |             | service       | endpoints for |
|           |             |                  |         |             | loading       | IEM layers    |
|           |             |                  |         |             | directly      | into QGIS,    |
|           |             |                  |         |             | ArcGIS,       | or any        |
|           |             |                  |         |             | WMS-capable   | GIS           |
client. Covers
|     |     |     |     |     | NEXRAD  | mosaics,  |
| --- | --- | --- | --- | --- | ------- | --------- |
|     |     |     |     |     | warning | polygons, |
station observations,
|            |        |                |        |     | and GOES     | channels.     |
| ---------- | ------ | -------------- | ------ | --- | ------------ | ------------- |
| IEMRE      | NetCDF | /onsite/iemre/ | NetCDF |     | Annual       | gridded files |
| files      |        |                |        |     | for the      | IEMRE         |
|            |        |                |        |     | reanalysis   | product.      |
|            |        |                |        |     | Loadable     | with          |
|            |        |                |        |     | xarray,      | QGIS (via     |
|            |        |                |        |     | GDAL),       | or any        |
|            |        |                |        |     | NetCDF-aware | tool.         |
| Coordinate | System |                |        |     |              |               |
All IEM shapefiles use EPSG:4326 (WGS84 geographic coordinates, decimal degrees).
No reprojection is needed for web mapping or for loading into GIS software that handles
projection on-the-fly. If your workflow requires a projected coordinate system (e.g., for area
| calculations | or distance | measurements), | reproject after | download. |     |     |
| ------------ | ----------- | -------------- | --------------- | --------- | --- | --- |

| Mastering | the Mesonet | 177 |
| --------- | ----------- | --- |
| Attribute | Fields      |     |
Shapefile attribute field names are truncated to 10 characters per the DBF format specifica-
tion. The IEM’s own dataset documentation at /info/datasets/ and variables reference at
/info/variables.phtml are the authoritative references for field name definitions when the
| truncated | names are not self-explanatory. |     |
| --------- | ------------------------------- | --- |
For the warning polygon shapefile specifically, the key fields are: PHENOMENA (2-letter code),
SIGNIFICANCE (1-letter code), ETN (event tracking number), WFO (4-character office ID),
ISSUED and EXPIRED (UTC timestamps), and WINDTAG, HAILTAG, TORNTAG for impact-based
| warning tags | where applicable. |     |
| ------------ | ----------------- | --- |
