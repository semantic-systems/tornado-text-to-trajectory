# tornado-text-to-trajectory

Code and notes for collecting surveyed tornado path geometries as reference data for ongoing work on reconstructing tornado trajectories and impact corridors from natural language reports.

## Data source

This repository currently uses the NOAA Damage Assessment Toolkit FeatureServer.

Damage Assessment Toolkit GUI  
https://apps.dat.noaa.gov/stormdamage/damageviewer/

Post-Storm Data Acquisition document  
https://www.weather.gov/media/directives/010_pdfs/pd01016004curr.pdf

## Repository contents

- `extract_noaa_polygons.py`  
  Script for downloading tornado path geometries from the NOAA DAT FeatureServer
- `README.md`  
  Short project description and links

## What the script does

The script can

- query the NOAA DAT FeatureServer
- download path lines, polygons, or both
- filter by date range
- optionally require a non-empty field such as comments
- export results as JSON

The current configuration includes `geometry_type`, `start_date`, `end_date`, `non_empty_field`, and `output_dir` in the config block at the top of the script :contentReference[oaicite:0]{index=0}. The script writes JSON exports containing layer metadata and the downloaded features :contentReference[oaicite:1]{index=1}.

## Setup

```bash
pip install requests tqdm