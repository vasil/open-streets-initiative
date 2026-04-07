from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
STRAVA_DIR = DATA_DIR / "strava"
ACTIVITIES_DIR = STRAVA_DIR / "activities"
SENSORS_DIR = DATA_DIR / "sensors"
DERIVED_DIR = DATA_DIR / "derived"
TOKENS_DIR = PROJECT_ROOT / "tokens"
CACHE_DIR = PROJECT_ROOT / "cache"
STRAVA_TOKENS_FILE = TOKENS_DIR / "strava_tokens.json"


def ensure_project_dirs() -> None:
    for path in (
        DATA_DIR,
        STRAVA_DIR,
        ACTIVITIES_DIR,
        SENSORS_DIR,
        DERIVED_DIR,
        TOKENS_DIR,
        CACHE_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
