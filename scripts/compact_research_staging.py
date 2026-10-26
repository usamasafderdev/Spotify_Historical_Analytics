from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from spotify_historical_analytics.research_pipeline import (  # noqa: E402
    DATASETS,
    build_compact_staging_database,
    write_analysis_reports,
    write_chart_quality_reports,
    supplement_rank_rejection_samples,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a separate compact research staging database. The original database "
            "is read-only and is never replaced or deleted."
        )
    )
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--target-db", type=Path, required=True)
    parser.add_argument(
        "--dataset",
        choices=[f"{item.dataset_id}@{item.version}" for item in DATASETS],
        required=True,
    )
    parser.add_argument("--chunk-size", type=int, default=50_000)
    parser.add_argument("--minimum-free-gib", type=float, default=0)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument(
        "--refresh-existing",
        action="store_true",
        help="Supplement bounded invalid-rank samples in an existing compact DB and refresh its quality reports.",
    )
    return parser.parse_args()


def _print_progress(event: Mapping[str, Any]) -> None:
    print(json.dumps(dict(event), ensure_ascii=True), file=sys.stderr, flush=True)


def main() -> int:
    args = parse_args()
    spec = next(
        item for item in DATASETS
        if f"{item.dataset_id}@{item.version}" == args.dataset
    )
    report_dir = args.report_dir or args.target_db.with_name(
        f"{args.target_db.stem}_reports"
    )
    if args.refresh_existing:
        manifest_path = report_dir / "compact_build_manifest.json"
        if not args.target_db.is_file() or not manifest_path.is_file():
            raise FileNotFoundError(
                "Refresh mode requires an existing compact database and its build manifest."
            )
        added_samples = supplement_rank_rejection_samples(
            args.source_db,
            args.source_file,
            args.target_db,
            spec,
        )
        connection = sqlite3.connect(args.target_db)
        try:
            quality_summary = write_chart_quality_reports(
                connection,
                report_dir,
                spec.dataset_id,
                spec.version,
            )
            sample_count = connection.execute(
                """
                SELECT COUNT(*) FROM staged_rejection_samples
                WHERE dataset_id=? AND dataset_version=?
                """,
                (spec.dataset_id, spec.version),
            ).fetchone()[0]
        finally:
            connection.close()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["rejection_samples"] = sample_count
        manifest["rank_rejection_samples_added"] = (
            int(manifest.get("rank_rejection_samples_added", 0)) + added_samples
        )
        manifest["invalid_rank_sample_count"] = quality_summary[
            "invalid_rank_sample_count"
        ]
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        print(json.dumps(manifest, indent=2, ensure_ascii=True))
        return 0
    if report_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite an existing report directory: {report_dir}"
        )
    result = build_compact_staging_database(
        args.source_db,
        args.source_file,
        args.target_db,
        spec,
        chunk_size=args.chunk_size,
        minimum_free_bytes=int(args.minimum_free_gib * 1024**3),
        progress_callback=_print_progress,
    )

    report_dir.mkdir(parents=True)
    connection = sqlite3.connect(args.target_db)
    try:
        analysis_counts = write_analysis_reports(connection, report_dir)
        quality_summary = write_chart_quality_reports(
            connection,
            report_dir,
            spec.dataset_id,
            spec.version,
        )
    finally:
        connection.close()
    manifest = {
        **result,
        "analysis_report_counts": analysis_counts,
        "quality_report_file": "chart_quality_summary.json",
        "invalid_rank_sample_count": quality_summary["invalid_rank_sample_count"],
    }
    (report_dir / "compact_build_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
