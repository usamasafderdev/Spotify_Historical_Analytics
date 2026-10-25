from __future__ import annotations

from ..db import DatabaseManager


class AnalyticsService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def overview(self, start_date: str | None = None, end_date: str | None = None, chart_type: str = "daily") -> dict:
        real_summary = self.db.get_summary(start_date=start_date, end_date=end_date, include_demo=False, chart_type=chart_type)
        demo_summary = self.db.get_summary(start_date=start_date, end_date=end_date, include_demo=True, chart_type=chart_type)
        top_tracks = self.db.get_top_tracks(limit=10, start_date=start_date, end_date=end_date, include_demo=False, chart_type=chart_type)
        top_artists = self.db.get_artist_summary(start_date=start_date, end_date=end_date, include_demo=False, chart_type=chart_type)
        coverage = self.db.get_coverage(chart_type=chart_type)

        return {
            "summary": real_summary,
            "demo_summary": demo_summary,
            "top_tracks": top_tracks,
            "top_artists": top_artists,
            "coverage": coverage,
            "has_demo_data": demo_summary["total_streams"] > 0 and real_summary["total_streams"] == 0,
            "has_real_data": real_summary["total_streams"] > 0,
        }
