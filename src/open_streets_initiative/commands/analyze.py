from __future__ import annotations

import typer
from rich import print


app = typer.Typer(help="Road-burden and accessibility analysis commands.")


@app.command("run")
def run() -> None:
    """Placeholder for route burden analysis."""
    print("Analysis is not implemented yet.")
    print("Planned metrics: vibration, shocks, instability, and later Relative Fatigue Cost.")
