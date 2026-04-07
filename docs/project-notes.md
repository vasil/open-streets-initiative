# Open Streets Initiative: Project Notes

## Purpose

This project is a local-first system for collecting, storing, visualizing, and analyzing wheelchair travel data.

The goal is not only to archive Strava activities, but to build data-driven advocacy evidence about:

- road quality
- pavement and curb danger
- vibration and instability
- wheelchair burden
- accessibility problems in the town and wider area

This project is based on lived travel and repeated real-world route coverage.

## Main Idea

The system will combine:

- Strava activities
- phone sensor recordings
- local storage
- Google Maps visualization

The long-term purpose is to convert movement data into evidence for accessibility advocacy.

## Data Sources

### 1. Strava

Strava will be used for:

- authentication
- activity metadata
- route geometry
- distance
- duration
- timestamps

Each activity should be downloaded and stored locally as its own JSON file.

Strava should remain the primary GPS and route source.

### 2. Phone Sensor Data

Sensor recordings are collected on a mobile phone mounted on the right side of the wheelchair.

The sensor data includes:

- accelerometer X, Y, Z
- gyroscope X, Y, Z
- timestamp for each sample

Sensor data is exported as CSV.

The current recording resolution is about 10 ms per sample. Raw data should be kept unchanged, even if later analysis uses downsampled data.

These sensor recordings augment the route data from Strava with richer evidence about:

- vibration
- shocks and bumps
- rotational instability
- wheelchair burden during movement

They are not secondary decoration. They are a core part of how the project will evaluate the real-world quality of roads and pavements.

## Core Principles

- Local-first from the beginning
- Keep all raw data locally
- One JSON file per Strava activity
- Keep raw sensor CSV files unchanged
- Use Strava as the primary GPS source
- Treat sensor logs as the primary road-quality measurement source
- Match sensor data to activities by timestamp
- Build a simple, working version 1 before advanced analytics
- Keep the system extensible for later advocacy features

## Project Direction

This is not only a Strava viewer. It is a wheelchair burden and accessibility evidence system.

The app should eventually help answer questions like:

- Which streets are roughest?
- Which routes create the highest burden?
- Where are the biggest shocks and instability events?
- Which streets repeatedly create problems over time?
- How often does travel through certain areas create a high burden?

## Local-First Architecture

Recommended structure:

```text
open-streets-initiative/
  data/
    strava/
      activities/
    sensors/
      accelerometer/
      gyroscope/
    derived/
  tokens/
  cache/
  viewer/
  src/
  docs/
```

## Version 1 Scope

The first working version should do only the following:

1. Authenticate with Strava
2. Download all activities locally
3. Store one JSON file per activity
4. Avoid duplicate downloads
5. Import local sensor CSV recordings
6. Match one CSV recording to one activity by timestamp
7. Show a left sidebar with activity titles and basic metadata
8. Draw the selected activity route on Google Maps
9. Show basic sensor chart data for the selected activity
10. Compute a first simple route burden score

## User Interface Direction

The first UI should have:

- a left sidebar
- activity titles
- date
- type
- distance
- search and basic filters
- a main Google Map on the right
- selected activity highlighted on the map

This should be usable locally before any cloud publishing or sharing.

## Google Maps

Google Maps should be used from the start instead of building a custom map system.

The map viewer will:

- show the selected route
- later support multiple routes
- later support filters
- later support route burden overlays

## Relative Fatigue Cost

One planned core metric is:

`RFC = Relative Fatigue Cost`

This should not be presented as a medical diagnosis. It should be presented as a relative measured burden score for wheelchair travel.

RFC should eventually estimate route burden using measured signals such as:

- vibration intensity
- shocks and bumps
- rotational instability
- exposure duration

Later versions may add more advanced weighting and route-segment analysis.

## Advocacy Purpose

This project is intended for data-driven analytics advocacy.

The app should eventually support:

- personal route analysis
- repeated-route comparison
- worst-street identification
- accessibility evidence gathering
- maps and summaries for advocacy
- later public-facing reporting

## Later AI Work

AI-assisted querying can be added later, but it is not a priority for the current phase.

The current focus should stay on:

- collecting the data
- aligning Strava activities with sensor logs
- building the map and analysis pipeline
- producing defensible accessibility evidence

If AI is added later, it should query local processed data, not guess from raw files alone.

## Important Notes

- Raw data is the source of truth
- Processed data can be regenerated
- Timestamp accuracy is critical
- Segment-level analytics can come after activity-level analytics
- Version 1 should stay simple and practical

## Existing Lead

Earlier Strava-related exploratory code exists in:

- `/home/vasil/Projects/strava/strava_activities_town_filter.py`
- `/home/vasil/Projects/mould/strava.js`

These are references, not the main project repository going forward.

## Next Step

The next planning step is to define the first simple route burden formula in plain terms so that version 1 can calculate a defensible score per activity.
