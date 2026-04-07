from __future__ import annotations

import typer
from rich import print

from ..config import auth_status_lines, load_settings
from ..paths import STRAVA_TOKENS_FILE
from ..strava_api import (
    StravaAuthError,
    StravaConfigError,
    ensure_access_token,
    exchange_code_for_token,
    get_stored_token,
    refresh_access_token,
)


app = typer.Typer(help="Strava authentication commands.")


@app.command("status")
def status() -> None:
    """Show whether Strava environment variables and token files are present."""
    settings = load_settings()
    for line in auth_status_lines(settings):
        print(f"- {line}")


@app.command("login")
def login() -> None:
    """Print the Strava OAuth URL for the manual login flow."""
    settings = load_settings()
    if not settings.strava_ready:
        raise typer.BadParameter(
            "Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env before login."
        )

    url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={settings.strava_client_id}"
        "&response_type=code"
        f"&redirect_uri={settings.strava_redirect_uri}"
        "&approval_prompt=force"
        f"&scope={settings.strava_scope}"
    )
    print("Open this URL in a browser and authorize the app:")
    print(url)
    print("")
    print("After authorization, capture the returned code and exchange it later.")


@app.command("token-path")
def token_path() -> None:
    """Show where local Strava tokens will be stored."""
    print(str(STRAVA_TOKENS_FILE))


@app.command("exchange")
def exchange(code: str) -> None:
    """Exchange a Strava authorization code for local tokens."""
    settings = load_settings()
    try:
        token_data = exchange_code_for_token(settings, code)
    except StravaConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc
    print("Stored Strava tokens locally.")
    print(f"- athlete id: {token_data.get('athlete', {}).get('id', 'unknown')}")
    print(f"- token file: {STRAVA_TOKENS_FILE}")


@app.command("refresh")
def refresh() -> None:
    """Refresh the stored Strava access token."""
    settings = load_settings()
    token_data = get_stored_token()
    refresh_token_value = token_data.get("refresh_token")
    if not refresh_token_value:
        raise typer.BadParameter("Stored token file has no refresh token.")
    refreshed = refresh_access_token(settings, str(refresh_token_value))
    print("Refreshed Strava access token.")
    print(f"- expires at: {refreshed.get('expires_at')}")


@app.command("whoami")
def whoami() -> None:
    """Verify that a usable Strava token is available."""
    settings = load_settings()
    try:
        access_token = ensure_access_token(settings)
    except (StravaConfigError, StravaAuthError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    print("Strava access token is ready.")
    print(f"- token prefix: {access_token[:8]}...")
