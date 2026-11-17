from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.local_integration import locked_source


def main():
    parser = argparse.ArgumentParser(description="Freeze one checked integration seed using a temporary same-drive hard link; do not write the integration database until collection finishes.")
    parser.add_argument("database", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("verification", type=Path)
    options = parser.parse_args()
    verification = json.loads(options.verification.read_text(encoding="utf-8"))
    if verification["status"] != "PASS" or verification["integrity"] != "ok":
        raise ValueError("Successful read-only verification is required")
    target = options.work / "seed" / "analytics.sqlite3"
    if target.exists():
        raise FileExistsError("A staged seed already exists; no second snapshot will be created")
    db = DatabaseManager(options.database)
    try:
        if db.connection.execute("SELECT COUNT(*) FROM integration_progress").fetchone()[0]:
            raise ValueError("An integration is incomplete")
        for row in db.connection.execute("SELECT * FROM integration_files").fetchall():
            result = json.loads(row["result_json"])
            if result.get("schema_fingerprint"):
                continue
            path = Path(row["path"])
            with locked_source(path) as (binary, stat):
                if (stat.st_size, stat.st_mtime_ns) != (row["size_bytes"], row["modified_ns"]):
                    raise ValueError(f"Previously integrated source changed: {path}")
                decoded = gzip.GzipFile(fileobj=binary) if path.name.endswith(".gz") else binary
                text = io.TextIOWrapper(decoded, encoding="utf-8-sig", newline="")
                headers = next(csv.reader(text))
                result["schema_fingerprint"] = hashlib.sha256(json.dumps(headers).encode()).hexdigest()
                result["source_path"] = str(path.resolve())
                result["schema_header_only_backfill"] = True
                text.detach()
            db.connection.execute("UPDATE integration_files SET result_json=? WHERE path=?", (json.dumps(result), str(path)))
        db.connection.commit()
        files = [dict(row) for row in db.connection.execute("SELECT * FROM integration_files ORDER BY path")]
        db.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        db.close()
    source_manifest = options.database.parent.parent / "source-manifest.json"
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    manifest["files"] = files
    manifest["database_bytes"] = options.database.stat().st_size
    source_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    os.link(options.database, target)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    report = {"seed_bytes": target.stat().st_size, "sha256": digest.hexdigest(),
              "staging_method": "temporary same-volume hard link; freeze development writes until PyInstaller collection completes",
              "distribution_authorization": "UNESTABLISHED / INTERNAL-READY only",
              "verification": str(options.verification.resolve())}
    (options.work / "seed-manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
