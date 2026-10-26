from __future__ import annotations

import threading

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ..db import DatabaseManager
from ..exports import export_rankings
from ..importer import import_csv_file, import_xlsx_file
from ..metadata_importer import import_metadata_file
from ..runtime import LOGGER
from ..services.analytics import AnalyticsService


class ImportWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

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
            self.progress.emit("Opening the local database…")
            db = DatabaseManager(Path(self.db_path))
            if self.kind == "metadata":
                result = import_metadata_file(
                    db,
                    self.file_path,
                    self.source_name,
                    self.source_license,
                    self.column_mapping,
                    self.progress.emit,
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
                    progress_callback=self.progress.emit,
                )
            self.completed.emit(result)
        except Exception as exc:
            LOGGER.exception("Background import failed.")
            self.failed.emit(str(exc))
        finally:
            if db is not None:
                db.close()


class DetailQueryWorker(QObject):
    completed = Signal(object)
    failed = Signal(object)

    def __init__(
        self,
        db_path: str,
        generation: int,
        kind: str,
        key: str,
        start_date: str | None,
        end_date: str | None,
        chart_type: str,
        dashboard_generation: int,
        include_demo: bool = False,
    ) -> None:
        super().__init__()
        self.db_path = db_path
        self.generation = generation
        self.kind = kind
        self.key = key
        self.start_date = start_date
        self.end_date = end_date
        self.chart_type = chart_type
        self.dashboard_generation = dashboard_generation
        self.include_demo = include_demo

    @Slot()
    def run(self) -> None:
        db = None
        try:
            db = DatabaseManager(Path(self.db_path))
            if self.kind == "songs":
                detail = db.get_song_detail(
                    "", "", self.start_date, self.end_date,
                    include_demo=self.include_demo,
                    chart_type=self.chart_type, track_key=self.key,
                )
                result = {
                    "detail": detail,
                    "streams": db.get_streams_over_time(
                        self.start_date, self.end_date, self.chart_type, self.key,
                        self.include_demo,
                    ),
                }
            elif self.kind == "artists":
                detail = db.get_artist_detail(
                    self.key, self.start_date, self.end_date, self.chart_type,
                    self.include_demo,
                )
                result = {
                    "detail": detail,
                    "streams": db.get_artist_streams_over_time(
                        self.key, self.start_date, self.end_date, self.chart_type,
                        self.include_demo,
                    ),
                }
            elif self.kind == "albums":
                detail = db.get_album_detail(
                    self.key, self.start_date, self.end_date, self.chart_type,
                    self.include_demo,
                )
                result = {
                    "detail": detail,
                    "tracks": db.get_album_tracks(
                        self.key, self.start_date, self.end_date, self.chart_type,
                        self.include_demo,
                    ),
                    "streams": db.get_album_streams_over_time(
                        self.key, self.start_date, self.end_date, self.chart_type,
                        self.include_demo,
                    ),
                }
            else:
                raise ValueError(f"Unsupported detail category: {self.kind}")
            self.completed.emit(
                {
                    "generation": self.generation,
                    "dashboard_generation": self.dashboard_generation,
                    "kind": self.kind,
                    "key": self.key,
                    **result,
                }
            )
        except Exception as exc:
            LOGGER.exception("Background detail query failed.")
            self.failed.emit(
                (self.generation, self.dashboard_generation, str(exc))
            )
        finally:
            if db is not None:
                db.close()


class ExportWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(
        self,
        db_path: str,
        category: str,
        destination: str,
        start_date: str | None,
        end_date: str | None,
        chart_type: str,
        limit: int,
        search: str | None,
        include_demo: bool = False,
    ) -> None:
        super().__init__()
        self.db_path = db_path
        self.category = category
        self.destination = destination
        self.start_date = start_date
        self.end_date = end_date
        self.chart_type = chart_type
        self.limit = limit
        self.search = search
        self.include_demo = include_demo

    @Slot()
    def run(self) -> None:
        db = None
        try:
            self.progress.emit("Preparing filtered rankings and coverage…")
            db = DatabaseManager(Path(self.db_path))
            row_count = export_rankings(
                db,
                self.category,
                self.destination,
                self.start_date,
                self.end_date,
                self.chart_type,
                self.limit,
                self.search,
                include_demo=self.include_demo,
            )
            self.completed.emit(
                {"destination": self.destination, "row_count": row_count}
            )
        except Exception as exc:
            LOGGER.exception("Background export failed.")
            self.failed.emit(str(exc))
        finally:
            if db is not None:
                db.close()


class DashboardQueryWorker(QObject):
    completed = Signal(object)
    failed = Signal(object)
    cancelled = Signal()

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
        include_demo: bool = False,
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
        self.include_demo = include_demo
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    @Slot()
    def run(self) -> None:
        db = None
        try:
            db = DatabaseManager(Path(self.db_path))
            db.connection.set_progress_handler(lambda: int(self.cancel_event.is_set()), 1000)
            if self.cancel_event.is_set():
                self.cancelled.emit()
                return
            analytics = AnalyticsService(db)
            all_songs = db.get_top_tracks(
                limit=max(10, self.song_limit),
                start_date=self.filters["start_date"],
                end_date=self.filters["end_date"],
                include_demo=self.include_demo,
                chart_type=self.filters["chart_type"],
            )
            songs = all_songs
            if self.song_search:
                songs = db.get_top_tracks(
                    limit=self.song_limit,
                    start_date=self.filters["start_date"],
                    end_date=self.filters["end_date"],
                    include_demo=self.include_demo,
                    chart_type=self.filters["chart_type"],
                    search=self.song_search,
                )
            inventory = db.get_data_inventory(include_demo=self.include_demo)
            active_summary = db.get_summary(
                start_date=self.filters["start_date"],
                end_date=self.filters["end_date"],
                include_demo=self.include_demo,
                chart_type=self.filters["chart_type"],
            )
            real_rows = int(inventory["summary"]["real_rows"] or 0)
            demo_rows = int(inventory["summary"]["demo_rows"] or 0)
            overview = {
                "summary": active_summary,
                "demo_summary": active_summary if self.include_demo else None,
                "top_tracks": all_songs[:10],
                "has_demo_data": demo_rows > 0 and real_rows == 0,
                "has_real_data": real_rows > 0 and not self.include_demo,
            }
            result = {
                "generation": self.generation,
                "overview": overview,
                "inventory": inventory,
                "streams": analytics.streams_over_time(
                    **self.filters, include_demo=self.include_demo
                ),
                "songs": songs,
                "artists": analytics.artist_rankings(
                    start_date=self.filters["start_date"],
                    end_date=self.filters["end_date"],
                    chart_type=self.filters["chart_type"],
                    limit=self.artist_limit,
                    search=self.artist_search or None,
                    include_demo=self.include_demo,
                ),
                "albums": analytics.album_rankings(
                    start_date=self.filters["start_date"],
                    end_date=self.filters["end_date"],
                    chart_type=self.filters["chart_type"],
                    limit=self.album_limit,
                    search=self.album_search or None,
                    include_demo=self.include_demo,
                ),
                "coverage": db.get_coverage(
                    self.filters["chart_type"], include_demo=self.include_demo
                ),
                "mapping_summary": db.get_metadata_mapping_summary(),
            }
            if self.cancel_event.is_set():
                self.cancelled.emit()
            else:
                self.completed.emit(result)
        except Exception as exc:
            if self.cancel_event.is_set():
                self.cancelled.emit()
            else:
                LOGGER.exception("Background dashboard query failed.")
                self.failed.emit((self.generation, str(exc)))
        finally:
            if db is not None:
                db.close()
