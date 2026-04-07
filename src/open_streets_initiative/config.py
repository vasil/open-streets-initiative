from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .paths import STRAVA_TOKENS_FILE


@dataclass(slots=True)
class Settings:
    strava_client_id: str | None
    strava_client_secret: str | None
    strava_redirect_uri: str
    strava_scope: str

    @property
    def strava_ready(self) -> bool:
        return bool(self.strava_client_id and self.strava_client_secret)


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        strava_client_id=os.getenv("STRAVA_CLIENT_ID"),
        strava_client_secret=os.getenv("STRAVA_CLIENT_SECRET"),
        strava_redirect_uri=os.getenv(
            "STRAVA_REDIRECT_URI",
            "http://localhost:8080/exchange_token",
        ),
        strava_scope=os.getenv("STRAVA_SCOPE", "activity:read_all"),
    )


def auth_status_lines(settings: Settings) -> list[str]:
    lines = []
    lines.append(
        "Strava environment variables: "
        + ("configured" if settings.strava_ready else "missing client id/secret")
    )
    lines.append(
        f"Stored token file: {'present' if STRAVA_TOKENS_FILE.exists() else 'missing'}"
    )
    return lines
