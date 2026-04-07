from __future__ import annotations

import typer
from rich import print


app = typer.Typer(help="Match sensor sessions to Strava activities.")


@app.command("sessions")
def sessions() -> None:
    """Placeholder for timestamp-based matching."""
    print("Session matching is not implemented yet.")
    print("Planned behavior: align each sensor CSV recording with the most likely Strava activity by time.")
