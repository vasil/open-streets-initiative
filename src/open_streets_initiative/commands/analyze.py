from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich import print

from ..paths import ACTIVITIES_DIR, DERIVED_DIR, MATCHES_DIR, SENSORS_DIR, STREAMS_DIR


app = typer.Typer(help="Road-burden and accessibility analysis commands.")


def _parse_utc(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def _interpolate(gps_epochs: list[float], latlngs: list[list[float]], t: float) -> tuple[float, float] | None:
    """Linear interpolation of lat/lng at epoch t."""
    if t < gps_epochs[0] or t > gps_epochs[-1]:
        return None

    lo, hi = 0, len(gps_epochs) - 1
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if gps_epochs[mid] <= t:
            lo = mid
        else:
            hi = mid

    if gps_epochs[hi] == gps_epochs[lo]:
        return latlngs[lo][0], latlngs[lo][1]

    fraction = (t - gps_epochs[lo]) / (gps_epochs[hi] - gps_epochs[lo])
    lat = latlngs[lo][0] + fraction * (latlngs[hi][0] - latlngs[lo][0])
    lng = latlngs[lo][1] + fraction * (latlngs[hi][1] - latlngs[lo][1])
    return lat, lng


def _interp_scalar(epochs: list[float], values: list[float], t: float) -> float | None:
    """Linear interpolation of a scalar value at epoch t."""
    if not epochs or t < epochs[0] or t > epochs[-1]:
        return None

    lo, hi = 0, len(epochs) - 1
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if epochs[mid] <= t:
            lo = mid
        else:
            hi = mid

    if epochs[hi] == epochs[lo]:
        return values[lo]

    fraction = (t - epochs[lo]) / (epochs[hi] - epochs[lo])
    return values[lo] + fraction * (values[hi] - values[lo])


@app.command("run")
def run() -> None:
    """Merge GPS streams with accelerometer data for each matched session."""
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)

    match_files = list(MATCHES_DIR.glob("*.json"))
    if not match_files:
        print("No match files found. Run `osi match sessions` first.")
        raise typer.Exit()

    for match_file in sorted(match_files):
        match = json.loads(match_file.read_text(encoding="utf-8"))
        recording_id = match["recording_id"]
        activity_id = match["activity_id"]

        # Load GPS stream
        stream_file = STREAMS_DIR / f"{activity_id}.json"
        if not stream_file.exists():
            print(f"[yellow]No stream file for activity {activity_id}. Run `osi activities streams --activity-id {activity_id}` first.[/yellow]")
            continue

        streams = json.loads(stream_file.read_text(encoding="utf-8"))
        latlngs = streams.get("latlng", {}).get("data", [])
        time_offsets = streams.get("time", {}).get("data", [])

        if not latlngs or not time_offsets:
            print(f"[yellow]Stream for {activity_id} has no latlng or time data.[/yellow]")
            continue

        # Build GPS epoch timeline
        activity_file = ACTIVITIES_DIR / f"{activity_id}.json"
        activity = json.loads(activity_file.read_text(encoding="utf-8"))
        activity_start_epoch = _parse_utc(activity["start_date"])
        gps_epochs = [activity_start_epoch + t for t in time_offsets]

        # Load accelerometer CSV
        accel_file = SENSORS_DIR / recording_id / "Accelerometer.csv"
        if not accel_file.exists():
            print(f"[yellow]Accelerometer.csv missing for {recording_id}.[/yellow]")
            continue

        # Load gyroscope CSV (optional)
        gyro_epochs: list[float] = []
        gyro_x_vals: list[float] = []
        gyro_y_vals: list[float] = []
        gyro_z_vals: list[float] = []
        gyro_file = SENSORS_DIR / recording_id / "Gyroscope.csv"
        if gyro_file.exists():
            with open(gyro_file, encoding="utf-8") as gf:
                for grow in csv.DictReader(gf):
                    gyro_epochs.append(int(grow["time"]) / 1_000_000_000)
                    gyro_x_vals.append(float(grow["x"]))
                    gyro_y_vals.append(float(grow["y"]))
                    gyro_z_vals.append(float(grow["z"]))
        has_gyro = bool(gyro_epochs)

        # Write merged output
        out_file = DERIVED_DIR / f"{recording_id}__{activity_id}.csv"
        rows_written = 0
        rows_skipped = 0

        header = ["timestamp_utc", "lat", "lng", "accel_x", "accel_y", "accel_z", "magnitude",
                  "gyro_x", "gyro_y", "gyro_z", "gyro_magnitude"]

        with open(accel_file, encoding="utf-8") as af, open(out_file, "w", newline="", encoding="utf-8") as of:
            reader = csv.DictReader(af)
            writer = csv.writer(of)
            writer.writerow(header)

            for row in reader:
                sensor_epoch = int(row["time"]) / 1_000_000_000
                pos = _interpolate(gps_epochs, latlngs, sensor_epoch)

                if pos is None:
                    rows_skipped += 1
                    continue

                lat, lng = pos
                x = float(row["x"])
                y = float(row["y"])
                z = float(row["z"])
                magnitude = math.sqrt(x**2 + y**2 + z**2)
                ts_utc = datetime.fromtimestamp(sensor_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

                if has_gyro:
                    gx = _interp_scalar(gyro_epochs, gyro_x_vals, sensor_epoch)
                    gy = _interp_scalar(gyro_epochs, gyro_y_vals, sensor_epoch)
                    gz = _interp_scalar(gyro_epochs, gyro_z_vals, sensor_epoch)
                    if gx is not None and gy is not None and gz is not None:
                        gyro_mag = math.sqrt(gx**2 + gy**2 + gz**2)
                        gyro_cols = [round(gx, 6), round(gy, 6), round(gz, 6), round(gyro_mag, 6)]
                    else:
                        gyro_cols = ["", "", "", ""]
                else:
                    gyro_cols = ["", "", "", ""]

                writer.writerow([ts_utc, round(lat, 7), round(lng, 7), round(x, 6), round(y, 6), round(z, 6), round(magnitude, 6)] + gyro_cols)
                rows_written += 1

        print(f"Analyzed: [bold]{recording_id}[/bold] → activity {activity_id}")
        print(f"  - rows written  : {rows_written}")
        print(f"  - rows skipped  : {rows_skipped} (outside GPS window)")
        print(f"  - output        : {out_file}")

    print("\nAnalysis complete.")
