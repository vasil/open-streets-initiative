from __future__ import annotations

import time
from typing import Any

import httpx

from .config import Settings
from .paths import STRAVA_TOKENS_FILE
from .token_store import load_json, save_json


TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
STREAMS_URL = "https://www.strava.com/api/v3/activities/{activity_id}/streams"


class StravaConfigError(RuntimeError):
    pass


class StravaAuthError(RuntimeError):
    pass


def _require_client_config(settings: Settings) -> None:
    if not settings.strava_ready:
        raise StravaConfigError(
            "Missing STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET in environment."
        )


def exchange_code_for_token(settings: Settings, code: str) -> dict[str, Any]:
    _require_client_config(settings)
    payload = {
        "client_id": settings.strava_client_id,
        "client_secret": settings.strava_client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }
    with httpx.Client(timeout=30) as client:
        response = client.post(TOKEN_URL, data=payload)
    response.raise_for_status()
    token_data = response.json()
    save_json(STRAVA_TOKENS_FILE, token_data)
    return token_data


def refresh_access_token(settings: Settings, refresh_token: str) -> dict[str, Any]:
    _require_client_config(settings)
    payload = {
        "client_id": settings.strava_client_id,
        "client_secret": settings.strava_client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    with httpx.Client(timeout=30) as client:
        response = client.post(TOKEN_URL, data=payload)
    response.raise_for_status()
    token_data = response.json()
    save_json(STRAVA_TOKENS_FILE, token_data)
    return token_data


def get_stored_token() -> dict[str, Any]:
    token_data = load_json(STRAVA_TOKENS_FILE)
    if not token_data:
        raise StravaAuthError(
            f"No Strava token file found at {STRAVA_TOKENS_FILE}. Run `osi auth login` and `osi auth exchange --code ...` first."
        )
    return token_data


def ensure_access_token(settings: Settings) -> str:
    token_data = get_stored_token()
    expires_at = int(token_data.get("expires_at", 0))
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    if access_token and expires_at > int(time.time()) + 60:
        return str(access_token)

    if not refresh_token:
        raise StravaAuthError(
            "Stored token file has no refresh token. Re-run the Strava auth flow."
        )

    refreshed = refresh_access_token(settings, str(refresh_token))
    return str(refreshed["access_token"])


def fetch_activity_streams(
    access_token: str,
    activity_id: int,
    keys: list[str] | None = None,
) -> dict[str, Any]:
    if keys is None:
        keys = ["latlng", "time", "altitude"]
    url = STREAMS_URL.format(activity_id=activity_id)
    params = {"keys": ",".join(keys), "key_by_type": "true"}
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=30) as client:
        response = client.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def fetch_activities_page(
    access_token: str,
    page: int,
    per_page: int = 200,
    after: int | None = None,
    before: int | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "page": page,
        "per_page": per_page,
    }
    if after is not None:
        params["after"] = after
    if before is not None:
        params["before"] = before

    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=30) as client:
        response = client.get(ACTIVITIES_URL, headers=headers, params=params)
    response.raise_for_status()
    return response.json()
