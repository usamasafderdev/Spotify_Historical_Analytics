from __future__ import annotations

from ..db import DatabaseManager


class AnalyticsService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def validate_date_range(self, start_date: str | None, end_date: str | None) -> None:
        self.db.validate_date_range(start_date, end_date)

    def overview(self, start_date: str | None = None, end_date: str | None = None, chart_type: str = "daily") -> dict:
        self.validate_date_range(start_date, end_date)
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

    def song_detail(self, track_name: str, artist_names: str, start_date: str | None = None, end_date: str | None = None, chart_type: str = "daily") -> dict | None:
        return self.db.get_song_detail(
            track_name=track_name,
            artist_names=artist_names,
            start_date=start_date,
            end_date=end_date,
            include_demo=False,
            chart_type=chart_type,
        )

    def streams_over_time(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        track_key: str | None = None,
        include_demo: bool = False,
    ) -> list[dict]:
        return self.db.get_streams_over_time(
            start_date, end_date, chart_type, track_key, include_demo
        )

    def song_detail_by_key(
        self,
        track_key: str,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
    ) -> dict | None:
        return self.db.get_song_detail(
            track_name="",
            artist_names="",
            start_date=start_date,
            end_date=end_date,
            include_demo=False,
            chart_type=chart_type,
            track_key=track_key,
        )

    def data_inventory(self, include_demo: bool = False) -> dict:
        return self.db.get_data_inventory(include_demo=include_demo)

    def available_date_bounds(
        self, chart_type: str = "daily", include_demo: bool = False
    ) -> dict:
        return self.db.get_available_date_bounds(
            include_demo=include_demo, chart_type=chart_type
        )

    def available_chart_types(self) -> list[str]:
        return self.db.get_chart_type_availability(include_demo=False)

    def artist_rankings(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        limit: int = 50,
        search: str | None = None,
        include_demo: bool = False,
    ) -> list[dict]:
        return self.db.get_artist_summary(
            start_date=start_date,
            end_date=end_date,
            include_demo=include_demo,
            chart_type=chart_type,
            limit=limit,
            search=search,
        )

    def artist_streams_over_time(
        self,
        artist_key: str,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        include_demo: bool = False,
    ) -> list[dict]:
        return self.db.get_artist_streams_over_time(
            artist_key, start_date, end_date, chart_type, include_demo
        )

    def album_rankings(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        limit: int = 50,
        search: str | None = None,
        include_demo: bool = False,
    ) -> list[dict]:
        return self.db.get_album_rankings(
            start_date, end_date, chart_type, limit, search, include_demo
        )

    def album_detail(
        self,
        album_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        include_demo: bool = False,
    ) -> dict | None:
        return self.db.get_album_detail(
            album_id, start_date, end_date, chart_type, include_demo
        )
