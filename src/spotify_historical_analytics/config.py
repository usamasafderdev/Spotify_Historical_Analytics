from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Spotify Historical Analytics"
APP_ROOT = Path(os.environ.get("SPOTIFY_ANALYTICS_DATA_DIR", Path.home() / "AppData" / "Local" / "SpotifyHistoricalAnalytics"))
if not APP_ROOT.exists():
    APP_ROOT = Path.home() / ".spotify_historical_analytics"
APP_ROOT.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_ROOT / "spotify_historical_analytics.db"
LOG_PATH = APP_ROOT / "spotify_historical_analytics.log"
