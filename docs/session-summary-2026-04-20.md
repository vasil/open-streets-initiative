# Session Summary — 2026-04-20

## 1. Project Status Recap — Open Streets Initiative

**Path:** `/home/vasil/Projects/open-streets-initiative`

**What it is:** Local-first Python/Typer CLI combining Strava GPS data with sensor telemetry to measure road roughness and wheelchair burden — building evidence for accessibility advocacy.

**Working:**
- Strava OAuth authentication
- Activity fetch (~1,400 JSON files downloaded locally)

**Not yet implemented (stubs):**
- `sensors.py` — import sensor recordings
- `match.py` — match sensor data to Strava activities by timestamp
- `analyze.py` — compute RFC (Relative Fatigue Cost) scores per street segment

---

## 2. Today's Plan (saved in docs/plan-2026-04-20.md)

Three tasks for today:

1. **Sensor Import** — ingest accelerometer/gyroscope recordings into `data/sensors/`
2. **Activity–Sensor Matching** — link sensor sessions to Strava activities by timestamp overlap, write index to `data/matches/`
3. **Analysis** — compute vibration magnitude (√(x²+y²+z²)) per GPS segment, output scored JSON

**Guiding principles:** local-first, timestamps are the link, evidence over opinion.

---

## 3. Advocacy Statement (saved in docs/advocacy-statement-2026-04-20.md)

Written in two versions. Key points:

- Vasil fell from his wheelchair on a broken pavement in the town center while navigating around a parked car
- Broke his arm
- Reported it to the police with medical documentation, photographs, and a formal written account
- No response

**Legal grounding:**
- UN Convention on the Rights of Persons with Disabilities (ratified — binding, not optional)
- Article 9: accessibility of physical environment
- Article 12: equal recognition before the law
- Article 13: access to justice
- Inaccessible infrastructure = discrimination under international law
- Government inaction after a formal report = second violation compounding the first

**Core message:** We are not asking. The law already says our cities must include us. We are holding governments to the promise they made to the United Nations.

---

## 4. Files Created Today

| File | Description |
|------|-------------|
| `docs/plan-2026-04-20.md` | Today's implementation plan for the CLI |
| `docs/advocacy-statement-2026-04-20.md` | Personal advocacy text with legal references |
| `docs/session-summary-2026-04-20.md` | This file — full session summary |

---

## 5. Next Steps

- Implement sensor import in `sensors.py`
- Build the case document from the police report file already on Vasil's computer
- Continue developing the advocacy statement for specific audiences (city council, press, social media)
