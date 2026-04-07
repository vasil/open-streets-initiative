from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from ..paths import SENSORS_DIR


app = typer.Typer(help="Sensor import commands.")


@app.command("import")
def import_csv(csv_file: Path) -> None:
    """Placeholder for importing a raw sensor CSV file."""
    if not csv_file.exists():
        raise typer.BadParameter(f"File does not exist: {csv_file}")
    print(f"Sensor import is not implemented yet.")
    print(f"Input file: {csv_file}")
    print(f"Target sensor directory: {SENSORS_DIR}")
