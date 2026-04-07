from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print

from ..config import load_settings
from ..paths import ACTIVITIES_DIR
from ..strava_api import (
    StravaAuthError,
    StravaConfigError,
    ensure_access_token,
    fetch_activities_page,
)


app = typer.Typer(help="Strava activity download commands.")


@app.command("fetch")
def fetch(
    per_page: int = typer.Option(200, min=1, max=200),
    after: int | None = typer.Option(None, help="Epoch timestamp filter."),
    before: int | None = typer.Option(None, help="Epoch timestamp filter."),
    max_pages: int | None = typer.Option(
        None, min=1, help="Limit page count for testing."
    ),
    overwrite: bool = typer.Option(False, help="Overwrite existing JSON files."),
) -> None:
    """Download Strava activities into one local JSON file per activity."""
    settings = load_settings()
    try:
        access_token = ensure_access_token(settings)
    except (StravaConfigError, StravaAuthError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    page = 1
    written = 0
    skipped = 0
    total_seen = 0

    while True:
        if max_pages is not None and page > max_pages:
            break

        activities = fetch_activities_page(
            access_token=access_token,
            page=page,
            per_page=per_page,
            after=after,
            before=before,
        )
        if not activities:
            break

        for activity in activities:
            activity_id = activity.get("id")
            if activity_id is None:
                continue
            total_seen += 1
            output_file = ACTIVITIES_DIR / f"{activity_id}.json"
            if output_file.exists() and not overwrite:
                skipped += 1
                continue
            _write_activity(output_file, activity)
            written += 1

        print(f"Fetched page {page} with {len(activities)} activities.")
        page += 1

    print("")
    print("Activity download complete.")
    print(f"- output dir: {ACTIVITIES_DIR}")
    print(f"- activities seen: {total_seen}")
    print(f"- files written: {written}")
    print(f"- files skipped: {skipped}")


def _write_activity(path: Path, activity: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(activity, indent=2, sort_keys=True), encoding="utf-8")
