from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ..db import DatabaseManager
from ..importer import import_csv_file, import_xlsx_file
from ..metadata_importer import import_metadata_file
from ..services.analytics import AnalyticsService


class ImportWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        db_path: str,
        kind: str,
        file_path: str,
        source_name: str,
        source_license: str,
        chart_type: str = "daily",
        column_mapping: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.db_path = db_path
        self.kind = kind
        self.file_path = file_path
        self.source_name = source_name
        self.source_license = source_license
        self.chart_type = chart_type
        self.column_mapping = column_mapping

    @Slot()
    def run(self) -> None:
        db = None
        try:
            db = DatabaseManager(Path(self.db_path))
            if self.kind == "metadata":
                result = import_metadata_file(
                    db,
                    self.file_path,
                    self.source_name,
                    self.source_license,
                    self.column_mapping,
                )
            else:
                path = Path(self.file_path)
                importer = import_xlsx_file if path.suffix.lower() == ".xlsx" else import_csv_file
                kwargs = {"xlsx_path": path} if path.suffix.lower() == ".xlsx" else {"csv_path": path}
                result = importer(
                    db=db,
                    **kwargs,
                    source_name=self.source_name,
                    source_license=self.source_license,
                    chart_type=self.chart_type,
                    country="US",
                )
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if db is not None:
                db.close()


class DashboardQueryWorker(QObject):
    completed = Signal(object)
    failed = Signal(object)

    def __init__(
        self,
        db_path: str,
        generation: int,
        start_date: str | None,
        end_date: str | None,
        chart_type: str,
        song_search: str,
        artist_search: str,
        album_search: str,
        song_limit: int,
        artist_limit: int,
        album_limit: int,
    ) -> None:
        super().__init__()
        self.db_path = db_path
        self.generation = generation
        self.filters = {
            "start_date": start_date,
            "end_date": end_date,
            "chart_type": chart_type,
        }
        self.song_search = song_search
        self.artist_search = artist_search
        self.album_search = album_search
        self.song_limit = song_limit
        self.artist_limit = artist_limit
        self.album_limit = album_limit

    @Slot()
    def run(self) -> None:
        db = None
        try:
            db = DatabaseManager(Path(self.db_path))
            analytics = AnalyticsService(db)
            all_songs = db.get_top_tracks(
                limit=max(10, self.song_limit),
                start_date=self.filters["start_date"],
                end_date=self.filters["end_date"],
                chart_type=self.filters["chart_type"],
            )
            songs = all_songs
            if self.song_search:
                songs = db.get_top_tracks(
                    limit=self.song_limit,
                    start_date=self.filters["start_date"],
                    end_date=self.filters["end_date"],
                    chart_type=self.filters["chart_type"],
                    search=self.song_search,
                )
            real_summary = db.get_summary(
                start_date=self.filters["start_date"],
                end_date=self.filters["end_date"],
                chart_type=self.filters["chart_type"],
            )
            demo_summary = db.get_summary(
                start_date=self.filters["start_date"],
                end_date=self.filters["end_date"],
                chart_type=self.filters["chart_type"],
                include_demo=True,
            )
            has_real_data = real_summary["total_streams"] > 0
            overview = {
                "summary": real_summary,
                "demo_summary": demo_summary,
                "top_tracks": all_songs[:10],
                "has_demo_data": demo_summary["total_streams"] > 0 and not has_real_data,
                "has_real_data": has_real_data,
            }
            result = {
                "generation": self.generation,
                "overview": overview,
                "inventory": analytics.data_inventory(),
                "streams": analytics.streams_over_time(**self.filters),
                "songs": songs,
                "artists": analytics.artist_rankings(
                    start_date=self.filters["start_date"],
                    end_date=self.filters["end_date"],
                    chart_type=self.filters["chart_type"],
                    limit=self.artist_limit,
                    search=self.artist_search or None,
                ),
                "albums": analytics.album_rankings(
                    start_date=self.filters["start_date"],
                    end_date=self.filters["end_date"],
                    chart_type=self.filters["chart_type"],
                    limit=self.album_limit,
                    search=self.album_search or None,
                ),
                "coverage": db.get_coverage(self.filters["chart_type"]),
                "mapping_summary": db.get_metadata_mapping_summary(),
            }
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit((self.generation, str(exc)))
        finally:
            if db is not None:
                db.close()
