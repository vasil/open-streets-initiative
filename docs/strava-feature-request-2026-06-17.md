# Strava Feature Request — Road Surface Quality Map Type

Draft date: 2026-06-17
Author: Vasil Taneski (vasil@taneski.com), Open Streets Initiative
Status: ready to send

---

## Channels to send to (pick one or both)

1. **Email**: developers@strava.com — appropriate because the ask
   involves extending the GPX schema Strava ingests.
2. **Community Hub**: https://communityhub.strava.com/ — feature-suggestion
   forum. Post the same body, slightly trimmed if there's a length limit.

If neither responds in 4 weeks, escalate to Strava's product
contact form at https://www.strava.com/contact.

---

## Subject

Feature Request: Road Surface Quality Map Type for Wheelchair and Vulnerable Road User Activities

---

## Body

Hello Strava product team,

I'm writing on behalf of the Open Streets Initiative
(https://github.com/vasil/open-streets-initiative), a wheelchair-user-led
project documenting urban road accessibility in North Macedonia.

Strava already offers several map types that color a route by a single
metric — Time, Elevation, Gradient, Pace, Activity Replay, 3D, Winter
3D. I'd like to propose a new one: **Road Surface Quality**.

The idea is to color the GPS track by surface roughness, derived from
the rider's phone or watch accelerometer. The primary number is the
ISO 2631-1 Wk-weighted vertical RMS in a sliding window:

  - green   smooth          (RMS < 1.0 m/s²)
  - yellow  rough           (RMS 1.0–5.0)
  - orange  severe          (RMS 5.0–15.0)
  - red     critical damage (RMS > 15.0)

The same data unlocks four widely-used metrics that all derive from the
same Wk-weighted vertical signal — Strava could expose any subset of
them:

  - **RMS (m/s²)** — ISO 2631-1 comfort and health-risk basis.
  - **VDV (m/s¹·⁷⁵)** — Vibration Dose Value, the ISO 2631-1
    health-risk dose used in occupational vibration exposure law.
  - **ISO 8608 class A–H** — the standard road-roughness class,
    computed from the displacement PSD at reference spatial frequency
    n₀ = 0.1 cycles/m.
  - **RFC (J/m)** — resistive vibration force per meter; the work
    integral of the vibration force on the rolling mass, divided by
    distance pushed. Useful for comparing energy cost across routes.
  - **IRI proxy (m/km)** — heuristic 12× scaling of windowed RMS, a
    cheap stand-in for the full quarter-car IRI until road-profile
    displacement is available.

### Why this matters

Every Strava user already records GPS. A surface-quality layer would
help:

  - wheelchair users plan routes around damaged pavement;
  - cyclists avoid streets that wreck wheels and forks;
  - runners avoid surfaces that cause repetitive impact injuries;
  - elderly walkers and people with strollers avoid trip hazards;
  - and city governments see, on a public map, which streets need repair.

It would make Strava the first mainstream fitness platform to document
road-surface accessibility at scale.

### What we already have

The Open Streets Initiative has built a working sensor pipeline
(WayTrace, https://github.com/vasil/WayTrace) that records 125 Hz IMU
data and computes the ISO 2631-1 Wk-weighted RMS / VDV plus ISO 8608
class and the resistive-force metric per GPS point. Sample numbers from
a single 6.96 km push through Prilep yesterday:

  - ISO 8608 class = E ("very poor surface")
  - RMS (Wk-vertical) = 2.90 m/s²
  - VDV (Wk-vertical) = 45.3 (HIGH health risk per ISO 2631-1)
  - VDV after seat-geometry correction = 22.6 (still HIGH)
  - RFC = 4.5 J/m (78 kg rolling mass)
  - 6,993 bumps ≥ 12 m/s²; 683 heavy bumps ≥ 18 m/s²
  - peak impact 82.3 m/s²

Across 16 sessions in Skopje and Prilep we have ~40,000 covered GPS
points, each tagged with all of the above. The pipeline is open
source and works today.

### Proposed implementation path

1. Accept an extended GPX extension element per trackpoint, e.g.
   `<extensions><wt:rms>2.4</wt:rms><wt:vdv>0.18</wt:vdv></extensions>`
   on upload. Strava already preserves heart-rate and cadence in similar
   GPX extensions, so the ingestion change is mechanical.
2. Add "Surface" as a selectable map type alongside Elevation and
   Gradient, using the colour scale above.
3. Optional: aggregate the score per street segment across all
   contributing users to build a crowdsourced road-quality layer
   visible on the global heatmap. One wheelchair user's data is
   anecdote; ten thousand cyclists pooling theirs is infrastructure.

We're happy to share the WayTrace pipeline, the GPX extension schema
we already emit, and our calibration dataset — anything that would help
your team prototype this.

Thank you for reading.

Kind regards,
Vasil Taneski
Open Streets Initiative
Prilep, North Macedonia
vasil@taneski.com

---

## Notes to self

- Length: ~530 words. Trim to ~300 if posting in a community forum that
  has a hard character limit.
- The pipeline numbers above are from ART-202606161340 (today's push).
- The GitHub repo URLs assume both repos are public. Verify before
  sending — if `open-streets-initiative` is still private, change to
  "available on request" or make it public first.
