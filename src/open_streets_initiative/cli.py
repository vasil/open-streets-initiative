import typer

from .commands.activities import app as activities_app
from .commands.analyze import app as analyze_app
from .commands.auth import app as auth_app
from .commands.match import app as match_app
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


@app.callback()
def main() -> None:
    """Prepare local folders before running any command."""
    ensure_project_dirs()
