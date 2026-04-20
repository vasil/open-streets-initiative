import typer
from rich.console import Console
from rich.table import Table

from .commands.activities import app as activities_app
from .commands.analyze import app as analyze_app
from .commands.auth import app as auth_app
from .commands.match import app as match_app
from .commands.report import app as report_app
from .commands.sensors import app as sensors_app
from .paths import ensure_project_dirs


app = typer.Typer(
    help="Open Streets Initiative CLI for Strava, sensors, and road-burden analysis."
)

app.add_typer(auth_app, name="auth")
app.add_typer(activities_app, name="activities")
app.add_typer(sensors_app, name="sensors")
app.add_typer(match_app, name="match")
app.add_typer(analyze_app, name="analyze")
app.add_typer(report_app, name="report")


@app.callback()
def main() -> None:
    """Prepare local folders before running any command."""
    ensure_project_dirs()


@app.command("help")
def help_command() -> None:
    """Show a summary of all available commands."""
    console = Console()

    console.print("\n[bold]Open Streets Initiative (osi)[/bold] — wheelchair mobility & road-burden CLI\n")

    commands = [
        ("auth status",       "Show whether Strava credentials and token files are present."),
        ("auth login",        "Print the Strava OAuth URL for the manual login flow."),
        ("auth exchange CODE","Exchange a Strava authorization code for local tokens."),
        ("auth refresh",      "Refresh the stored Strava access token."),
        ("auth whoami",       "Verify that a usable Strava token is available."),
        ("auth token-path",   "Show where local Strava tokens are stored."),
        ("activities fetch",  "Download all Strava activities locally (one JSON file each)."),
        ("sensors import FILE","Import a raw sensor CSV recording."),
        ("match sessions",    "Match sensor CSV recordings to Strava activities by timestamp."),
        ("analyze run",       "Run road-burden and accessibility analysis."),
        ("report generate",   "Generate advocacy evidence report as HTML."),
    ]

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("Command", style="green")
    table.add_column("Description")

    for cmd, desc in commands:
        table.add_row(f"osi {cmd}", desc)

    console.print(table)
    console.print("\nRun [green]osi <command> --help[/green] for details on any command.\n")
