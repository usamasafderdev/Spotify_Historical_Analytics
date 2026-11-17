from __future__ import annotations

import argparse
import json
from pathlib import Path

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.local_integration import initialize


def main():
    parser = argparse.ArgumentParser(description="Quarantine cross-source rank-slot collisions from one isolated integration batch; retain earlier observations and exact incoming values.")
    parser.add_argument("database", type=Path)
    parser.add_argument("source", type=Path)
    options = parser.parse_args()
    db = DatabaseManager(options.database)
    try:
        initialize(db)
        source = str(options.source.resolve())
        manifest = db.connection.execute("SELECT * FROM integration_files WHERE path=? AND category='chart_csv_daily' AND status='complete'", (source,)).fetchone()
        if manifest is None:
            raise ValueError("A completed isolated legacy daily integration manifest is required")
        result = json.loads(manifest["result_json"])
        batch = result["batch_id"]
        with db.transaction():
            db.connection.execute("""INSERT OR IGNORE INTO integration_slot_conflicts
                SELECT ?,incoming.chart_type,incoming.chart_date,incoming.position,
                    existing.track_id,incoming.track_id,existing.streams,incoming.streams,
                    existing.track_name,incoming.track_name,existing.artist_names,incoming.artist_names
                FROM chart_records incoming CROSS JOIN chart_records existing INDEXED BY idx_chart_records_slot
                WHERE incoming.batch_id=? AND incoming.country='US' AND incoming.chart_type='daily'
                  AND existing.country=incoming.country AND existing.chart_type=incoming.chart_type
                  AND existing.chart_date=incoming.chart_date AND existing.position=incoming.position
                  AND existing.id<incoming.id AND existing.batch_id<>incoming.batch_id
                  AND existing.source<>'DEMO / SYNTHETIC' AND existing.track_id<>incoming.track_id""", (source, batch))
            removed = db.connection.execute("""DELETE FROM chart_records
                WHERE batch_id=? AND EXISTS (SELECT 1 FROM integration_slot_conflicts conflict
                    WHERE conflict.source_path=? AND conflict.chart_type=chart_records.chart_type
                      AND conflict.chart_date=chart_records.chart_date AND conflict.position=chart_records.position
                      AND conflict.incoming_track_id=chart_records.track_id)""", (batch, source)).rowcount
            if removed > result["imported_rows"]:
                raise ValueError("Quarantine exceeds the source's documented imported observations")
            result["imported_rows"] -= removed
            result["conflicts"] += removed
            result["slot_conflicts"] = result.get("slot_conflicts", 0) + removed
            result["quarantined_previous_task_rows"] = result.get("quarantined_previous_task_rows", 0) + removed
            db.connection.execute("UPDATE integration_files SET result_json=? WHERE path=?", (json.dumps(result), source))
        for index in ["idx_chart_records_identity", "idx_chart_records_slot", "idx_chart_records_real_analytics", "idx_chart_records_market_type_date", "idx_chart_records_artist", "idx_chart_records_filter_source"]:
            db.connection.execute(f"ANALYZE {index}")
        db.connection.commit()
        db.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        target = options.database.parent.parent / "source-manifest.json"
        report = json.loads(target.read_text(encoding="utf-8"))
        report["files"] = [dict(row) for row in db.connection.execute("SELECT * FROM integration_files ORDER BY path")]
        report["database_bytes"] = options.database.stat().st_size
        report["slot_quarantine_note"] = "Different track IDs occupying an earlier source's chart date/rank are retained in integration_slot_conflicts, not added to totals. No entity aliases or memberships are inferred."
        target.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"quarantined": removed, "source_result": result}), flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
