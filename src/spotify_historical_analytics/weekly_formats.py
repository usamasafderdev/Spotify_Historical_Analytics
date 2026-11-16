from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import re


def spotify_weekly_context(path: Path, headers: list[str]) -> dict[str, str]:
    normalized = {re.sub(r"[^a-z0-9]", "", header.lower()) for header in headers}
    legacy = {"position", "trackname", "artist", "streams", "url"}
    current = {"rank", "uri", "artistnames", "trackname", "streams"}
    if not (legacy.issubset(normalized) or current.issubset(normalized)):
        return {}
    match = re.fullmatch(
        r"regional-([a-z]{2}|global)-weekly-(\d{4}-\d{2}-\d{2})(?:--(\d{4}-\d{2}-\d{2}))?\.(?:csv(?:\.gz)?|xlsx)",
        path.name, re.IGNORECASE,
    )
    if not match:
        return {}
    first = date.fromisoformat(match[2])
    if match[3]:
        boundary = date.fromisoformat(match[3])
        span = (boundary - first).days
        if span == 7 and first.weekday() == 3:
            start, end = first + timedelta(days=1), boundary
        elif first.weekday() == 4 and span in {6, 7}:
            start = first
            end = boundary - timedelta(days=1) if span == 7 else boundary
        else:
            raise ValueError("Ambiguous Spotify reporting week; provide explicit week boundaries.")
    else:
        if first.weekday() != 3:
            raise ValueError("Spotify weekly filenames must identify a Thursday week end or an unambiguous seven-day reporting range.")
        end = first
        start = end - timedelta(days=6)
    return {
        "_spotify_date": end.isoformat(), "_spotify_country": match[1].upper(),
        "_spotify_chart_type": "weekly", "_spotify_week_start": start.isoformat(),
        "_spotify_week_end": end.isoformat(),
    }
