from __future__ import annotations

import csv
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich import print

from ..paths import SENSORS_DIR


app = typer.Typer(help="Sensor import commands.")


@app.command("import")
def import_zip(zip_file: Path) -> None:
    """Import a phyphox sensor ZIP export into data/sensors/."""
    if not zip_file.exists():
        raise typer.BadParameter(f"File does not exist: {zip_file}")
    if not zipfile.is_zipfile(zip_file):
        raise typer.BadParameter(f"Not a valid ZIP file: {zip_file}")

    with zipfile.ZipFile(zip_file, "r") as zf:
        names = zf.namelist()

        if "Metadata.csv" not in names:
            raise typer.BadParameter("ZIP does not contain Metadata.csv — not a phyphox export.")

        # Parse Metadata.csv
        meta_rows = list(csv.DictReader(zf.open("Metadata.csv").read().decode("utf-8").splitlines()))
        if not meta_rows:
            raise typer.BadParameter("Metadata.csv is empty.")
        meta = meta_rows[0]

        recording_time = meta.get("recording time", "").strip()
        recording_id = recording_time if recording_time else zip_file.stem
        start_epoch_ms = int(meta.get("recording epoch time", 0))
        timezone_str = meta.get("recording timezone", "UTC").strip()
        device = meta.get("device name", "unknown").strip()

        # Parse sample rates — format: "50|50|50||50|50|50"
        sensors_field = meta.get("sensors", "").strip()
        sample_rates_field = meta.get("sampleRateMs", "").strip()
        sensor_names = [s.strip() for s in sensors_field.split("|") if s.strip()]
        rate_values = [r.strip() for r in sample_rates_field.split("|")]
        accel_rate_ms = 50  # default
        for i, name in enumerate(sensor_names):
            if name == "Accelerometer" and i < len(rate_values) and rate_values[i]:
                accel_rate_ms = int(rate_values[i])
                break

        start_utc = datetime.fromtimestamp(start_epoch_ms / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"

        # Extract all files to data/sensors/{recording_id}/
        out_dir = SENSORS_DIR / recording_id
        out_dir.mkdir(parents=True, exist_ok=True)
        zf.extractall(out_dir)

    # Write session.json metadata
    session = {
        "recording_id": recording_id,
        "start_epoch_ms": start_epoch_ms,
        "start_utc": start_utc,
        "timezone": timezone_str,
        "sample_rate_ms": accel_rate_ms,
        "device": device,
        "files": names,
    }
    session_file = out_dir / "session.json"
    session_file.write_text(json.dumps(session, indent=2), encoding="utf-8")

    print(f"Sensor import complete.")
    print(f"- recording ID  : {recording_id}")
    print(f"- start (UTC)   : {start_utc}")
    print(f"- device        : {device}")
    print(f"- sample rate   : {accel_rate_ms} ms")
    print(f"- files         : {len(names)}")
    print(f"- saved to      : {out_dir}")
