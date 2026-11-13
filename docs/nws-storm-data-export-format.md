Storm Data Export Format
Event Details File (named event_details_YYYYMM.csv):
last_date_modified Ex: 4/4/2012 11:05:44 PM, 5/3/2012 5:10:49 AM
MM/DD/YYYY 12 hour time AM/PM
The last date of modification by NWS. Any corrections to the storm event/episode in question
are made solely by NWS and the person that actually entered the event/episode.
last_date_certified Ex: 5/10/2012 9:10:51 AM, 5/18/2012 12:21:15 AM
MM/DD/YYYY 12 hour time AM/PM
The last date of certification by NWS. Any corrections to the storm event/episode in question
are made solely by NWS and the person that actually entered the event/episode.
episode_id Ex: 61280, 62777, 63250
(ID assigned by NWS to denote the storm episode; links the event details file with the location
& fatality files)
The occurrence of storms and other significant weather phenomena having sufficient intensity
to cause loss of life, injuries, significant property damage, and/or disruption to commerce.
Rare, unusual, weather phenomena that generate media attention, such as snow flurries in South
Florida or the San Diego coastal area; and Other significant meteorological events, such as
record maximum or minimum temperatures or precipitation that occur in connection with
another event.
event_id Ex: 383097, 374427, 364175
(Primary database key field)
(ID assigned by NWS to note a single, small part that goes into a specific storm episode; links
the storm episode between the three files downloaded from SPC’s website)
state Ex: GEORGIA, WYOMING, COLORADO
The state name where the event occurred (no State ID’s are included here; State Name is
spelled out in ALL CAPS)
state_fips Ex: 45, 30, 12
A unique number (State Federal Information Processing Standard) is assigned to the county by
the National Institute for Standards and Technology (NIST).
year Ex: 2000, 2006, 2012
Four digit year for the event in this record

month_name  Ex: January, February, March
Name of the month for the event in this record (spelled out; not abbreviated)

event_type  Ex: Hail, Thunderstorm Wind, Snow, Ice (spelled out; not abbreviated)

The only events permitted in Storm Data are listed in Table 1 of Section 2.1.1 of NWS
Directive 10-1605 at http://www.nws.noaa.gov/directives/sym/pd01016005curr.pdf. The
chosen event name should be the one that most accurately describes the meteorological event
leading to fatalities, injuries, damage, etc. However, significant events, such as tornadoes,
having no impact or causing no damage, should also be included in Storm Data.

From Section 2.1.1 of NWS Directive 10-1605:
Event Name    Designator (County or Zone)   Event Name    Designator (County or
Zone)
| Astronomical Low Tide         | Z   | Marine Hail    M                |
| ----------------------------- | --- | ------------------------------- |
| Avalanche    Z                |     | Marine High Wind   M            |
| Blizzard    Z                 |     | Marine Strong Wind   M          |
| Coastal Flood   Z             |     | Marine Thunderstorm Wind   M    |
| Cold/Wind Chill   Z           |     | Rip Current    Z                |
| Debris Flow    C              |     | Seiche     Z                    |
| Dense Fog    Z                |     | Sleet      Z                    |
| Dense Smoke   Z               |     | Storm Surge/Tide   Z            |
| Drought    Z                  |     | Strong Wind    Z                |
| Dust Devil    C               |     | Thunderstorm Wind   C           |
| Dust Storm    Z               |     | Tornado    C                    |
| Excessive Heat   Z            |     | Tropical Depression   Z         |
| Extreme Cold/Wind Chill   Z   |     | Tropical Storm   Z              |
| Flash Flood    C              |     | Tsunami    Z                    |
| Flood     C                   |     | Volcanic Ash   Z                |
| Frost/Freeze    Z             |     | Waterspout    M                 |
| Funnel Cloud   C              |     | Wildfire    Z                   |
| Freezing Fog   Z              |     | Winter Storm   Z                |
| Hail     C                    |     | Winter Weather   Z              |
Heat      Z
Heavy Rain    C
Heavy Snow    Z
High Surf    Z
High Wind    Z
Hurricane (Typhoon)   Z
Ice Storm    Z
Lake-Effect Snow   Z
Lakeshore Flood   Z
Lightning    C

cz_type Ex: C, Z , M
Indicates whether the event happened in a (C) county/parish, (Z) zone or (M) marine
cz_fips Ex: 245, 003, 155
The county FIPS number is a unique number assigned to the county by the National Institute
for Standards and Technology (NIST) or NWS Forecast Zone Number (See addendum)
cz_name Ex: AIKEN, RICHMOND, BAXTER (County/Parish, Zone or Marine Name
assigned to the county FIPS number or NWS Forecast Zone)
wfo Ex: CAE, BYZ, GJT (National Weather Service Forecast Office’s area of responsibility
(County Warning Area) in which the event occurred)
begin_date_time Ex: 4/1/2012 20:48
MM/DD/YYYY 24 hour time AM/PM
cz_timezone Ex: EST-5, MST-7, CST-6
(Time Zone for the County/Parish, Zone or Marine Name)
Eastern Standard Time (EST), Central Standard Time (CST), Mountain Standard Time (MST),
etc.
end_date_time Ex: 4/1/2012 21:03
MM/DD/YYYY 24 hour time AM/PM
injuries_direct Ex: 1, 0, 56
The number of injuries directly related to the weather event
injuries_indirect Ex: 0, 15, 87
The number of injuries indirectly related to the weather event
deaths_direct Ex: 0, 45, 23
The number of deaths directly related to the weather event.
deaths_indirect Ex: 0, 4, 6
The number of deaths indirectly related to the weather event
damage_property Ex: 10.00K, 0.00K, 10.00M
The estimated amount of damage to property incurred by the weather event. (e.g. 10.00K =
$10,000; 10.00M = $10,000,000)
damage_crops Ex: 0.00K, 500.00K, 15.00M
The estimated amount of damage to crops incurred by the weather event (e.g. 10.00K =
$10,000; 10.00M = $10,000,000)

source Ex: Public, Newspaper, Law Enforcement, Broadcast Media, ASOS, Park and Forest
Service, Trained Spotter, CoCoRaHS, etc. (can be any entry; isn’t restricted in what’s
allowed)
Source reporting the weather event
magnitude Ex: 0.75, 60, 0.88, 2.75
measured extent of the magnitude type ~ only used for wind speeds and hail size (e.g. 0.75” of
hail; 60 mph winds)
magnitude_type Ex: EG, MS, MG, ES
EG = Wind Estimated Gust; ES = Estimated Sustained Wind; MS = Measured Sustained Wind;
MG = Measured Wind Gust (no magnitude is included for instances of hail)
flood_cause Ex: Ice Jam, Heavy Rain, Heavy Rain/Snow Melt
Reported or estimated cause of the flood
category Ex:
Unknown (During the time of downloading this particular file, NCDC has never seen anything
provided within this field.)
tor_f_scale Ex: EF0, EF1, EF2, EF3, EF4, EF5
Enhanced Fujita Scale describes the strength of the tornado based on the amount and type of
damage caused by the tornado. The F-scale of damage will vary in the destruction area;
therefore, the highest value of the F-scale is recorded for each event.
EF0 – Light Damage (40 – 72 mph)
EF1 – Moderate Damage (73 – 112 mph)
EF2 – Significant damage (113 – 157 mph)
EF3 – Severe Damage (158 – 206 mph)
EF4 – Devastating Damage (207 – 260 mph)
EF5 – Incredible Damage (261 – 318 mph)
tor_length Ex: 0.66, 1.05, 0.48
Length of the tornado or tornado segment while on the ground (minimal of tenths of miles)
tor_width Ex: 25, 50, 1760, 10
Width of the tornado or tornado segment while on the ground (in whole yards)
tor_other_wfo Ex: DDC, ICT, TOP,OAX
Indicates the continuation of a tornado segment as it crossed from one National Weather
Service Forecast Office to another. The subsequent WFO identifier is provided within this
field.
tor_other_cz_state Ex: KS, NE, OK
The two character representation for the state name of the continuing tornado segment as it
crossed from one county or zone to another. The subsequent 2-Letter State ID is provided
within this field.

tor_other_cz_fips Ex: 41, 127, 153
The FIPS number of the county entered by the continuing tornado segment as it crossed from
one county to another. The subsequent FIPS number is provided within this field.
tor_other_cz_name Ex: DICKINSON, NEMAHA, SARPY
The FIPS name of the county entered by the continuing tornado segment as it crossed from one
county to another. The subsequent county or zone name is provided within this field in ALL
CAPS.
episode_narrative (The episode narrative depicting the general nature and overall activity of
the episode. The narrative is created by NWS.) Ex: A strong upper level system over the
southern Rockies lifted northeast across the plains causing an intense surface low pressure
system and attendant warm front to lift into Nebraska.
event_narrative (The event narrative provides more specific details of the individual event .
The event narrative is provided by NWS.) Ex: Heavy rain caused flash flooding across parts of
Wilber. Rainfall of 2 to 3 inches fell across the area.
Storm Data Location File (named event_locations_YYYYMM.csv):

episode_id Ex: 60904 (ID assigned by NWS to denote the storm episode; links the storm
episode with the information within the event details file) An Episode may contain several
different events.
event_id Ex: 364000, 364001, 364002, 364003 (ID assigned by NWS to note a single, small
part that goes into a specific storm episode; links the storm episode between the three files
downloaded from SPC’s website)
location_index Ex: 1-x (Number assigned by NWS to specific locations within the same Storm
event. Each event’s sequentially increasing location index number will have a corresponding
lat/lon point)
range Ex: 0.59, 0.69, 4.84, 1.17 (A hydro-meteorological event will be referenced, minimally,
to the nearest tenth of a mile, to the geographical center (not from the village/city boundaries or
limits) of a particular village/city, airport, or inland lake, providing that the reference point is
documented in the Storm Data software location database.)
azimuth Ex: ENE, NW, WSW, S (16-point compass direction from a particular village/city,
airport, or inland lake, providing that the reference point is documented in the Storm Data
software location database of > 130,000 locations.)
location Ex: PINELAND, CENTER, ORRS, RUSK (center from which the range and the
azimuth is calculated)
lat Ex: 31.25, 31.79, 32.76, 31.80
The latitude where the event occurred (rounded to the hundredths in decimal degrees; includes an
‘-‘ if it’s S of the Equator)
lon Ex: -93.97, -94.18, -94.52, -95.13
The longitude where the event occurred (rounded to the hundredths in decimal degrees; includes
an ‘-‘ if it’s W of the Prime Meridian)
Storm Data Fatality File (named event_fatalities_YYYYMM.csv):

fatality_id Ex: 17582, 17590, 17597, 18222 (ID assigned by NWS to denote the individual
fatality that occurred within a storm event)
event_id Ex: 364302, 365560, 365945, 367330 (ID assigned by NWS to note a single, small
part that goes into a specific storm episode; links the storm episode between the three files
downloaded from SPC’s website)
fatality_type Ex: D , I (D = Direct Fatality; I = Indirect Fatality; assignment of this is
determined by NWS software; details below are from NWS Directve 10-1605 at
http://www.nws.noaa.gov/directives/sym/pd01016005curr.pdf, Section 2.6)
● Direct Fatality: “A direct fatality or injury is defined as a fatality or injury directly
attributable to the hydro-meteorological event itself, or impact by airborne/falling/moving
debris, i.e., missiles generated by wind, water, ice, lightning, tornado, etc. “
● Indirect Fatality: “Fatalities and injuries, occurring in the vicinity of a
hydrometeorological event, or after it has ended, but not directly caused by impact or
debris from the event (weather event was a passive entity), are classified as indirect.”
fatality_date Ex: 4/3/2012 12:00:00 AM, 4/11/2012 12:00:00 AM
MM/DD/YYYY 12 hour time AM/PM
fatality_age Ex: 38, 25, 69, 54
The age of the fatalities
fatality_sex Ex: M, F
The gender of the fatalities
fatality_location Ex: (UT) Under Tree, (BO) Boating, (VE) Vehicle/Towed Trailer
Direct Fatality Location Table
BF Ball Field MH Mobile/Trailer Home
BO Boating OT Other/Unknown
BU Business OU Outside/Open Areas
CA Camping PH Permanent Home
CH Church PS Permanent Structure
EQ Heavy Equip/Construction SC School
GF Golfing TE Telephone
IW In Water UT Under Tree
LS Long Span Roof VE Vehicle and/or Towed Trailer
