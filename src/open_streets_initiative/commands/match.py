from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich import print

from ..paths import ACTIVITIES_DIR, MATCHES_DIR, SENSORS_DIR


app = typer.Typer(help="Match sensor sessions to Strava activities.")


def _parse_utc(iso: str) -> float:
    """Return Unix epoch seconds from an ISO 8601 UTC string."""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def _count_csv_rows(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # subtract header


@app.command("sessions")
def sessions() -> None:
    """Match each sensor session to a Strava activity by timestamp overlap."""
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)

    # Load all sensor sessions
    sensor_sessions = []
    for session_file in sorted(SENSORS_DIR.glob("*/session.json")):
        session = json.loads(session_file.read_text(encoding="utf-8"))
        start_s = session["start_epoch_ms"] / 1000

        # Estimate end time from row count * sample rate
        accel_csv = session_file.parent / "Accelerometer.csv"
        if accel_csv.exists():
            row_count = _count_csv_rows(accel_csv)
            duration_s = row_count * session["sample_rate_ms"] / 1000
        else:
            duration_s = 0

        sensor_sessions.append({
            **session,
            "start_s": start_s,
            "end_s": start_s + duration_s,
        })

    if not sensor_sessions:
        print("No sensor sessions found in data/sensors/.")
        raise typer.Exit()

    # Load all activity summaries
    activities = []
    for act_file in ACTIVITIES_DIR.glob("*.json"):
        act = json.loads(act_file.read_text(encoding="utf-8"))
        start_s = _parse_utc(act["start_date"])
        activities.append({
            "id": act["id"],
            "name": act.get("name", ""),
            "start_utc": act["start_date"],
            "start_s": start_s,
            "end_s": start_s + act.get("elapsed_time", 0),
        })

    written = 0
    unmatched = 0

    for sess in sensor_sessions:
        matched = []
        for act in activities:
            # Overlap: sensor window and activity window intersect
            if sess["start_s"] <= act["end_s"] and sess["end_s"] >= act["start_s"]:
                offset_s = act["start_s"] - sess["start_s"]
                matched.append({**act, "offset_seconds": round(offset_s, 3)})

        if not matched:
            print(f"[yellow]No match found for session: {sess['recording_id']}[/yellow]")
            unmatched += 1
            continue

        # Take the best match (smallest absolute offset)
        best = min(matched, key=lambda a: abs(a["offset_seconds"]))

        match_data = {
            "recording_id": sess["recording_id"],
            "activity_id": best["id"],
            "activity_name": best["name"],
            "sensor_start_utc": sess["start_utc"],
            "activity_start_utc": best["start_utc"],
            "offset_seconds": best["offset_seconds"],
        }

        out_file = MATCHES_DIR / f"{sess['recording_id']}__{best['id']}.json"
        out_file.write_text(json.dumps(match_data, indent=2), encoding="utf-8")
        written += 1
        print(f"Matched: [bold]{sess['recording_id']}[/bold] → activity {best['id']} ({best['name']}), offset {best['offset_seconds']}s")

    print(f"\nDone. {written} match(es) written, {unmatched} unmatched.")
