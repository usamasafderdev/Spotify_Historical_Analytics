from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import time

from spotify_historical_analytics.db import DatabaseManager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    db = DatabaseManager(options.database, read_only=True)
    report = {"database_bytes": options.database.stat().st_size, "checks": {}}
    try:
        report["integrity"] = db.connection.execute("PRAGMA quick_check").fetchone()[0]
        assert report["integrity"] == "ok"
        report["tables"] = {table: db.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                            for table in ["chart_records", "album_chart_records", "artist_chart_records", "artist_listener_records", "tracks", "artists", "albums", "track_artists", "track_albums", "album_artists", "entity_references", "integration_conflicts", "integration_slot_conflicts"]}
        report["song_sources"] = [dict(row) for row in db.connection.execute("SELECT chart_type,batch_id,COUNT(*) AS records,MIN(chart_date) AS earliest,MAX(chart_date) AS latest,SUM(streams) AS streams FROM chart_records GROUP BY chart_type,batch_id")]
        report["song_coverage"] = {}
        for cadence in ["daily", "weekly", "weekly_derived"]:
            started = time.perf_counter()
            rows = db.connection.execute(f"SELECT COUNT(*) AS records,COUNT(DISTINCT track_id) AS tracks,COUNT(DISTINCT chart_date) AS dates,MIN(chart_date) AS earliest,MAX(chart_date) AS latest,SUM(streams) AS streams FROM {db.analytics_table(cadence)} WHERE country='US' AND chart_type=?", (cadence,)).fetchone()
            report["song_coverage"][cadence] = dict(rows)
            report["song_coverage"][cadence]["seconds"] = round(time.perf_counter() - started, 3)
            print(cadence, report["song_coverage"][cadence], flush=True)
        assert report["song_coverage"]["weekly"]["records"] == 12599
        assert report["song_coverage"]["weekly"]["streams"] == 42913401825
        assert report["song_coverage"]["daily"]["streams"] == report["song_coverage"]["weekly_derived"]["streams"]
        assert report["tables"]["album_chart_records"] == 61588
        assert report["tables"]["artist_listener_records"] == 3262204
        report["daily_by_year"] = [dict(row) for row in db.connection.execute("SELECT substr(chart_date,1,4) AS year,COUNT(*) AS records,COUNT(DISTINCT chart_date) AS dates,SUM(streams) AS streams FROM chart_records WHERE country='US' AND chart_type='daily' GROUP BY year")]
        dates = {row[0] for row in db.connection.execute("SELECT DISTINCT chart_date FROM chart_records WHERE country='US' AND chart_type='daily'")}
        first, last = date.fromisoformat(min(dates)), date.fromisoformat(max(dates))
        report["missing_daily_reporting_dates"] = [(first + timedelta(days=offset)).isoformat() for offset in range((last - first).days + 1) if (first + timedelta(days=offset)).isoformat() not in dates]
        report["daily_short_dates"] = [dict(row) for row in db.connection.execute("SELECT chart_date,COUNT(*) AS observations FROM chart_records WHERE country='US' AND chart_type='daily' GROUP BY chart_date HAVING COUNT(*)<200")]
        report["daily_overfull_dates"] = [dict(row) for row in db.connection.execute("SELECT chart_date,COUNT(*) AS observations FROM chart_records WHERE country='US' AND chart_type='daily' GROUP BY chart_date HAVING COUNT(*)>200")]
        report["duplicate_song_identities"] = db.connection.execute("SELECT COUNT(*) FROM (SELECT 1 FROM chart_records WHERE source<>'DEMO / SYNTHETIC' GROUP BY country,chart_type,chart_date,track_id HAVING COUNT(*)>1)").fetchone()[0]
        assert report["duplicate_song_identities"] == 0
        report["metric_coverage"] = {}
        for table, field, identity in [("album_chart_records", "chart_date", "album_id"), ("artist_chart_records", "chart_date", "artist_id"), ("artist_listener_records", "metric_date", "artist_id")]:
            report["metric_coverage"][table] = dict(db.connection.execute(f"SELECT COUNT(*) AS records,COUNT(DISTINCT {identity}) AS entities,COUNT(DISTINCT {field}) AS dates,MIN({field}) AS earliest,MAX({field}) AS latest FROM {table}").fetchone())
        report["files"] = [{**dict(row), "result_json": json.loads(row["result_json"])} for row in db.connection.execute("SELECT * FROM integration_files")]
        report["conflict_types"] = dict(db.connection.execute("SELECT 'streams_differ',COUNT(*) FROM integration_conflicts WHERE established_streams<>incoming_streams UNION ALL SELECT 'position_differs',COUNT(*) FROM integration_conflicts WHERE established_position IS NOT incoming_position UNION ALL SELECT 'labels_differ',COUNT(*) FROM integration_conflicts WHERE established_title<>incoming_title OR established_credits<>incoming_credits"))
        report["status"] = "PASS"
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    finally:
        db.close()


if __name__ == "__main__":
    main()
