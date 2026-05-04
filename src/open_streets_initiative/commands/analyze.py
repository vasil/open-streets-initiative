from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import typer
from rich import print
from rich.table import Table

from ..paths import ACTIVITIES_DIR, DERIVED_DIR, MATCHES_DIR, SENSORS_DIR, STREAMS_DIR

_LOCAL_TZ = ZoneInfo("Europe/Skopje")


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


def _parse_waytrace_filename(path: Path) -> datetime:
    """Parse sensors_YYYYMMDD_HHMMSS.csv → local datetime (Europe/Skopje)."""
    stem = path.stem  # sensors_20260504_184737
    parts = stem.split("_")
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        raise ValueError(f"Cannot parse WayTrace filename: {path.name}. Expected sensors_YYYYMMDD_HHMMSS.csv")
    date_str, time_str = parts[1], parts[2]
    local_dt = datetime(
        int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]),
        int(time_str[:2]), int(time_str[2:4]), int(time_str[4:6]),
        tzinfo=_LOCAL_TZ,
    )
    return local_dt


def _find_matching_activity(csv_start_epoch: float, csv_end_epoch: float) -> Optional[dict]:
    """Find the Strava activity whose time window overlaps the CSV recording window."""
    best = None
    best_overlap = 0.0
    for f in sorted(ACTIVITIES_DIR.glob("*.json")):
        act = json.loads(f.read_text(encoding="utf-8"))
        act_start = _parse_utc(act.get("start_date", ""))
        act_end = act_start + act.get("moving_time", 0)
        overlap = max(0.0, min(csv_end_epoch, act_end) - max(csv_start_epoch, act_start))
        if overlap > best_overlap:
            best_overlap = overlap
            best = act
    return best


@app.command("waytrace")
def waytrace(
    csv_path: Path = typer.Option(..., "--csv", help="Path to WayTrace sensors_YYYYMMDD_HHMMSS.csv"),
    activity_id: Optional[int] = typer.Option(None, "--activity-id", help="Strava activity ID (auto-detected if omitted)"),
    out_dir: Optional[Path] = typer.Option(None, "--out", help="Output directory (default: data/derived/)"),
) -> None:
    """Map WayTrace sensor events (bumps, tilts, wheelies) to GPS coordinates."""
    if not csv_path.exists():
        print(f"[red]File not found: {csv_path}[/red]")
        raise typer.Exit(1)

    output_dir = out_dir or DERIVED_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- 1. Parse CSV filename for wall-clock start time ---
    try:
        csv_start_local = _parse_waytrace_filename(csv_path)
    except ValueError as e:
        print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    csv_start_epoch = csv_start_local.timestamp()

    # --- 2. Load CSV rows ---
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("[red]CSV file is empty.[/red]")
        raise typer.Exit(1)

    first_ts_ms = int(rows[0]["timestamp_ms"])
    last_ts_ms  = int(rows[-1]["timestamp_ms"])
    csv_duration_s = (last_ts_ms - first_ts_ms) / 1000
    csv_end_epoch = csv_start_epoch + csv_duration_s

    accel_rows = [r for r in rows if r["sensor"] == "accel"]
    event_rows = [r for r in accel_rows if r.get("event", "").strip()]

    print(f"CSV          : {csv_path.name}")
    print(f"Start (local): {csv_start_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Duration     : {csv_duration_s:.1f}s")
    print(f"Total rows   : {len(rows)} ({len(accel_rows)} accel)")
    print(f"Events found : {len(event_rows)}")

    if not event_rows:
        print("[yellow]No events (bump/fall/wheelie/tilt) in CSV. Nothing to map.[/yellow]")
        raise typer.Exit()

    # --- 3. Find or load Strava activity ---
    if activity_id is not None:
        act_file = ACTIVITIES_DIR / f"{activity_id}.json"
        if not act_file.exists():
            print(f"[red]Activity file not found: {act_file}[/red]")
            raise typer.Exit(1)
        activity = json.loads(act_file.read_text(encoding="utf-8"))
    else:
        activity = _find_matching_activity(csv_start_epoch, csv_end_epoch)
        if activity is None:
            print("[red]No matching Strava activity found. Use --activity-id to specify one.[/red]")
            raise typer.Exit(1)
        activity_id = activity["id"]
        print(f"Auto-matched : activity {activity_id} — {activity.get('name', '?')}")

    activity_start_epoch = _parse_utc(activity["start_date"])

    # --- 4. Load GPS stream ---
    stream_file = STREAMS_DIR / f"{activity_id}.json"
    if not stream_file.exists():
        print(f"[red]No GPS stream for activity {activity_id}. Run:[/red]")
        print(f"  osi activities streams --activity-id {activity_id}")
        raise typer.Exit(1)

    streams = json.loads(stream_file.read_text(encoding="utf-8"))
    latlngs      = streams.get("latlng",    {}).get("data", [])
    time_offsets = streams.get("time",      {}).get("data", [])
    altitudes    = streams.get("altitude",  {}).get("data", [])

    if not latlngs or not time_offsets:
        print("[red]GPS stream has no latlng/time data.[/red]")
        raise typer.Exit(1)

    gps_epochs = [activity_start_epoch + t for t in time_offsets]
    has_alt    = len(altitudes) == len(gps_epochs)

    # --- 5. Map each event to GPS ---
    features     = []
    event_counts: dict[str, int] = {}
    skipped      = 0

    for row in event_rows:
        event_type = row["event"].strip()
        row_ts_ms  = int(row["timestamp_ms"])
        event_epoch = csv_start_epoch + (row_ts_ms - first_ts_ms) / 1000

        pos = _interpolate(gps_epochs, latlngs, event_epoch)
        if pos is None:
            skipped += 1
            continue

        lat, lng = pos
        alt = _interp_scalar(gps_epochs, altitudes, event_epoch) if has_alt else None

        x = float(row["x"])
        y = float(row["y"])
        z = float(row["z"])
        magnitude = math.sqrt(x**2 + y**2 + z**2)
        ts_utc = datetime.fromtimestamp(event_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        features.append({
            "ts_utc": ts_utc,
            "lat": round(lat, 7),
            "lng": round(lng, 7),
            "alt": round(alt, 1) if alt is not None else "",
            "event": event_type,
            "magnitude": round(magnitude, 2),
            "x": round(x, 4),
            "y": round(y, 4),
            "z": round(z, 4),
        })
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    # --- 6. Write GeoJSON ---
    stem = csv_path.stem.replace("sensors_", "waytrace_events_")
    geojson_path = output_dir / f"{stem}.geojson"
    csv_out_path = output_dir / f"{stem}.csv"

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [f["lng"], f["lat"]]},
                "properties": {
                    "event":     f["event"],
                    "magnitude": f["magnitude"],
                    "timestamp_utc": f["ts_utc"],
                    "altitude":  f["alt"],
                    "x": f["x"], "y": f["y"], "z": f["z"],
                },
            }
            for f in features
        ],
    }
    geojson_path.write_text(json.dumps(geojson, indent=2), encoding="utf-8")

    # --- 7. Write CSV ---
    with open(csv_out_path, "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=["timestamp_utc","lat","lng","altitude","event","magnitude","x","y","z"])
        writer.writeheader()
        for f in features:
            writer.writerow(f)

    # --- 8. Summary ---
    print()
    table = Table(title="Events mapped to GPS")
    table.add_column("Event", style="cyan")
    table.add_column("Count", justify="right")
    for ev, cnt in sorted(event_counts.items()):
        table.add_row(ev, str(cnt))
    if skipped:
        table.add_row("[yellow]skipped (outside GPS window)[/yellow]", str(skipped))
    print(table)
    print(f"\nGeoJSON → {geojson_path}")
    print(f"CSV     → {csv_out_path}")
    print("\n[green]Load the GeoJSON in JOSM or https://geojson.io to see bump locations on the map.[/green]")
