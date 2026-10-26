from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import sqlite3
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from shutil import disk_usage
from threading import Event, Thread
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from spotify_historical_analytics.research_pipeline import (  # noqa: E402
    DATASETS,
    DatasetSpec,
    _initialize_staging,
    detect_columns,
    discover_dataset_files,
    file_format,
    inventory_file,
    iter_table_batches,
    process_file,
    sha256_file,
    write_analysis_reports,
    write_inventory_report,
)

DEFAULT_RESEARCH_ROOT = Path(r"D:\Spotify-Dataset-Research")
ROW_FORMATS = {"csv", "csv.gz", "parquet", "xlsx", "xlsm", "jsonl", "ndjson"}


def _lock_owner_is_running(lock_path: Path) -> bool:
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        pid = int(payload["pid"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False
    try:
        import psutil

        return psutil.pid_exists(pid)
    except ImportError:
        if os.name == "nt":
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _lock_file(path: Path) -> int | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"pid": os.getpid(), "created_at": time.time()}).encode("utf-8")

    def create_lock() -> int:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            remaining = memoryview(payload)
            while remaining:
                written = os.write(descriptor, remaining)
                if written == 0:
                    raise OSError("Failed to write the dataset lock file.")
                remaining = remaining[written:]
            os.fsync(descriptor)
        except BaseException:
            os.close(descriptor)
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            raise
        return descriptor

    try:
        return create_lock()
    except FileExistsError:
        if _lock_owner_is_running(path):
            return None
        try:
            age = time.time() - path.stat().st_mtime
        except FileNotFoundError:
            return create_lock()
        if age < 6 * 60 * 60:
            return None
        try:
            path.unlink()
        except OSError:
            return None
        try:
            return create_lock()
        except FileExistsError:
            return None


def _release_lock(path: Path, descriptor: int) -> None:
    os.close(descriptor)
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _existing_cache(root: Path, spec: DatasetSpec) -> Path | None:
    candidates = (
        root / "datasets" / spec.owner / spec.slug / "versions" / str(spec.version),
        Path.home() / ".cache" / "kagglehub" / "datasets" / spec.owner / spec.slug / "versions" / str(spec.version),
    )
    configured = os.environ.get("KAGGLEHUB_CACHE")
    if configured:
        candidates += (
            Path(configured) / "datasets" / spec.owner / spec.slug / "versions" / str(spec.version),
        )
    seen: set[str] = set()
    for candidate in candidates:
        canonical = str(candidate.resolve()).casefold()
        if canonical in seen:
            continue
        seen.add(canonical)
        archive_path = candidate.parent / f"{spec.version}.archive"
        if archive_path.exists():
            continue
        if candidate.is_dir() and any(item.is_file() for item in candidate.rglob("*")):
            return candidate
    return None


def _active_archive_paths(root: Path, spec: DatasetSpec) -> list[Path]:
    cache_roots = [root, Path.home() / ".cache" / "kagglehub"]
    configured = os.environ.get("KAGGLEHUB_CACHE")
    if configured:
        cache_roots.append(Path(configured))
    archives = {
        cache_root / "datasets" / spec.owner / spec.slug / "versions" / f"{spec.version}.archive"
        for cache_root in cache_roots
    }
    return [path for path in archives if path.exists()]


def _partial_downloads(root: Path) -> list[Path]:
    suffixes = {".part", ".partial", ".tmp", ".download", ".archive"}
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() in suffixes
    ] if root.exists() else []


def _safe_error(exc: Exception) -> str:
    message = re.sub(
        r"(?i)(kaggle_api_token|authorization|bearer)\s*[:=]\s*\S+",
        r"\1=[REDACTED]",
        str(exc),
    )
    message = re.sub(r"[\r\n]+", " ", message)
    return f"{type(exc).__name__}: {message[:500]}"


def download_dataset(spec: DatasetSpec, research_root: Path) -> dict[str, Any]:
    dataset_root = research_root / spec.research_folder
    dataset_root.mkdir(parents=True, exist_ok=True)
    archives = _active_archive_paths(dataset_root, spec)
    if archives:
        return {
            "dataset_id": spec.dataset_id,
            "status": "SKIPPED_ACTIVE_OR_PARTIAL_DOWNLOAD",
            "path": str(archives[0].parent),
            "details": "A KaggleHub archive is present; it was not read, removed, or replaced.",
        }
    partials = _partial_downloads(dataset_root)
    if partials:
        return {
            "dataset_id": spec.dataset_id,
            "status": "SKIPPED_ACTIVE_OR_PARTIAL_DOWNLOAD",
            "path": str(dataset_root),
            "details": f"{len(partials)} partial download marker(s) found; files were not touched.",
        }
    cache_path = _existing_cache(dataset_root, spec)
    if cache_path is not None:
        return {"dataset_id": spec.dataset_id, "status": "REUSED", "path": str(cache_path)}

    lock_path = research_root / ".locks" / f"{spec.slug}.lock"
    descriptor = _lock_file(lock_path)
    if descriptor is None:
        return {
            "dataset_id": spec.dataset_id,
            "status": "SKIPPED_ACTIVE_DOWNLOAD",
            "path": str(dataset_root),
            "details": "A live or recent dataset lock exists; no files were read or modified.",
        }
    try:
        os.write(
            descriptor,
            json.dumps({"pid": os.getpid(), "created_at": time.time()}).encode("utf-8"),
        )
        os.environ["KAGGLEHUB_CACHE"] = str(dataset_root)
        try:
            version = importlib.metadata.version("kagglehub")
            from kagglehub import dataset_download
        except (importlib.metadata.PackageNotFoundError, ImportError) as exc:
            return {
                "dataset_id": spec.dataset_id,
                "status": "DEPENDENCY_MISSING",
                "path": "",
                "details": _safe_error(exc),
            }
        version_parts = tuple(int(part) for part in version.split(".") if part.isdigit())
        if version_parts < (1, 0, 3):
            return {
                "dataset_id": spec.dataset_id,
                "status": "KAGGLEHUB_TOO_OLD",
                "path": "",
                "details": f"Installed KaggleHub {version}; version 1.0.3 or newer is required.",
            }
        try:
            # Use KaggleHub's dedicated cache for this source to avoid a second extracted copy.
            returned = Path(dataset_download(spec.handle, force_download=False)).resolve()
        except Exception as exc:
            return {
                "dataset_id": spec.dataset_id,
                "status": "DOWNLOAD_FAILED",
                "path": "",
                "details": _safe_error(exc),
            }
        if not returned.exists():
            return {
                "dataset_id": spec.dataset_id,
                "status": "DOWNLOAD_PATH_MISSING",
                "path": str(returned),
                "details": "KaggleHub returned a path that does not exist.",
            }
        files = [path for path in discover_dataset_files(returned) if path.is_file()]
        if not files:
            return {
                "dataset_id": spec.dataset_id,
                "status": "NO_DATA_FILES",
                "path": str(returned),
                "details": "The returned dataset directory contains no data files.",
            }
        return {
            "dataset_id": spec.dataset_id,
            "status": "DOWNLOADED_OR_CACHE_REUSED",
            "path": str(returned),
            "file_count": len(files),
        }
    finally:
        _release_lock(lock_path, descriptor)


def download_dataset_latest(
    spec: DatasetSpec,
    research_root: Path,
    *,
    latest_version: int,
    listed_size_bytes: int,
    expansion_factor: int = 3,
    reserve_bytes: int = 2 * 1024**3,
) -> dict[str, Any]:
    if latest_version <= 0 or listed_size_bytes <= 0:
        raise ValueError("Latest version and listed size must be positive.")
    if expansion_factor < 1 or reserve_bytes < 0:
        raise ValueError("The expansion factor must be at least 1 and reserve cannot be negative.")
    latest_spec = replace(spec, version=latest_version)
    dataset_root = research_root / spec.research_folder
    dataset_root.mkdir(parents=True, exist_ok=True)
    cache_path = _existing_cache(dataset_root, latest_spec)
    if cache_path is not None:
        return {
            "dataset_id": spec.dataset_id,
            "status": "REUSED_LATEST_CACHE",
            "version": latest_version,
            "path": str(cache_path),
            "unversioned_request": "not_called",
        }
    archives = _active_archive_paths(dataset_root, latest_spec)
    if archives:
        return {
            "dataset_id": spec.dataset_id,
            "status": "SKIPPED_ACTIVE_OR_PARTIAL_DOWNLOAD",
            "version": latest_version,
            "path": str(archives[0].parent),
            "unversioned_request": "not_called",
        }
    partials = _partial_downloads(dataset_root)
    if partials:
        return {
            "dataset_id": spec.dataset_id,
            "status": "SKIPPED_ACTIVE_OR_PARTIAL_DOWNLOAD",
            "version": latest_version,
            "path": str(dataset_root),
            "details": f"{len(partials)} partial marker(s) found; files were not touched.",
            "unversioned_request": "not_called",
        }

    required_free_bytes = listed_size_bytes * expansion_factor + reserve_bytes
    free_bytes = disk_usage(dataset_root).free
    if free_bytes < required_free_bytes:
        return {
            "dataset_id": spec.dataset_id,
            "status": "SKIPPED_INSUFFICIENT_SPACE",
            "version": latest_version,
            "path": str(dataset_root),
            "listed_size_bytes": listed_size_bytes,
            "expansion_factor": expansion_factor,
            "reserve_bytes": reserve_bytes,
            "required_free_bytes": required_free_bytes,
            "free_bytes": free_bytes,
            "unversioned_request": "not_called",
            "details": (
                "Conservative storage preflight failed; no KaggleHub download call was made."
            ),
        }

    lock_path = research_root / ".locks" / f"{spec.slug}.latest.lock"
    descriptor = _lock_file(lock_path)
    if descriptor is None:
        return {
            "dataset_id": spec.dataset_id,
            "status": "SKIPPED_ACTIVE_DOWNLOAD",
            "version": latest_version,
            "path": str(dataset_root),
            "unversioned_request": "not_called",
        }
    try:
        os.environ["KAGGLEHUB_CACHE"] = str(dataset_root)
        try:
            version = importlib.metadata.version("kagglehub")
            from kagglehub import dataset_download
        except (importlib.metadata.PackageNotFoundError, ImportError) as exc:
            return {
                "dataset_id": spec.dataset_id,
                "status": "DEPENDENCY_MISSING",
                "version": latest_version,
                "path": "",
                "details": _safe_error(exc),
                "unversioned_request": "not_called",
            }
        version_parts = tuple(int(part) for part in version.split(".") if part.isdigit())
        if version_parts < (1, 0, 3):
            return {
                "dataset_id": spec.dataset_id,
                "status": "KAGGLEHUB_TOO_OLD",
                "version": latest_version,
                "path": "",
                "details": f"Installed KaggleHub {version}; version 1.0.3 or newer is required.",
                "unversioned_request": "not_called",
            }
        try:
            returned = Path(
                dataset_download(spec.dataset_id, force_download=False)
            ).resolve()
        except Exception as exc:
            return {
                "dataset_id": spec.dataset_id,
                "status": "DOWNLOAD_FAILED",
                "version": latest_version,
                "path": "",
                "details": _safe_error(exc),
                "unversioned_request": "attempted",
            }
        actual_version = returned.name if returned.parent.name == "versions" else ""
        if not returned.exists():
            return {
                "dataset_id": spec.dataset_id,
                "status": "DOWNLOAD_PATH_MISSING",
                "version": actual_version,
                "path": str(returned),
                "unversioned_request": "attempted",
            }
        if actual_version != str(latest_version):
            return {
                "dataset_id": spec.dataset_id,
                "status": "LISTING_VERSION_CHANGED",
                "version": actual_version,
                "path": str(returned),
                "details": (
                    f"The unversioned request returned {actual_version or 'an unversioned path'}, "
                    f"but listing metadata reported {latest_version}; no audit was started."
                ),
                "unversioned_request": "attempted",
            }
        files = [path for path in discover_dataset_files(returned) if path.is_file()]
        if not files:
            return {
                "dataset_id": spec.dataset_id,
                "status": "NO_DATA_FILES",
                "version": actual_version,
                "path": str(returned),
                "unversioned_request": "attempted",
            }
        return {
            "dataset_id": spec.dataset_id,
            "status": "DOWNLOADED_OR_CACHE_REUSED",
            "version": actual_version,
            "path": str(returned),
            "file_count": len(files),
            "unversioned_request": "attempted",
            "required_free_bytes": required_free_bytes,
            "free_bytes_at_preflight": free_bytes,
        }
    finally:
        _release_lock(lock_path, descriptor)


class MemorySampler:
    def __init__(self, interval: float = 0.2) -> None:
        self.interval = interval
        self.peak_rss_bytes: int | None = None
        self._stop = Event()
        self._thread: Thread | None = None

    def __enter__(self) -> "MemorySampler":
        try:
            import psutil
        except ImportError:
            return self
        process = psutil.Process()

        def sample() -> None:
            while not self._stop.is_set():
                try:
                    rss = process.memory_info().rss
                    self.peak_rss_bytes = max(self.peak_rss_bytes or 0, rss)
                except (psutil.Error, OSError):
                    return
                self._stop.wait(self.interval)

        self._thread = Thread(target=sample, name="dataset-memory-sampler", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)


def _has_chart_schema(path: Path) -> bool:
    if file_format(path) not in ROW_FORMATS:
        return False
    try:
        headers, _ = next(iter_table_batches(path, 1))
    except (StopIteration, OSError, ValueError, ImportError):
        return False
    columns = detect_columns(headers)
    return all(field in columns for field in ("chart_date", "country", "position"))


def run_audit(research_root: Path, chunk_size: int) -> None:
    staging_dir = research_root / "staging"
    report_dir = research_root / "reports"
    audit_dir = research_root / "audit"
    staging_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    stage_db = staging_dir / "research_staging.sqlite"
    stage = sqlite3.connect(stage_db)
    stage.row_factory = sqlite3.Row
    _initialize_staging(stage)

    roots: dict[str, Path] = {}
    file_stats: list[dict[str, Any]] = []
    try:
        for spec in DATASETS:
            dataset_root = research_root / spec.research_folder
            actual_root = _existing_cache(dataset_root, spec) or dataset_root
            roots[spec.dataset_id] = actual_root
            partials = _partial_downloads(dataset_root)
            partials.extend(_active_archive_paths(dataset_root, spec))
            if partials:
                file_stats.append(
                    {
                        "dataset_id": spec.dataset_id,
                        "source_url": spec.url,
                        "dataset_version": spec.version,
                        "filename": "",
                        "path": str(actual_root),
                        "format": "",
                        "size_bytes": "",
                        "sha256": "",
                        "row_count": "",
                        "column_names_json": "[]",
                        "detected_fields_json": "{}",
                        "category": "",
                        "listed_license": spec.listed_license,
                        "permission_status": "UNVERIFIED",
                        "processing_status": "SKIPPED_ACTIVE_OR_PARTIAL_DOWNLOAD",
                        "accepted_rows": "",
                        "rejected_rows": "",
                        "processing_seconds": 0,
                        "sampled_peak_rss_bytes": "",
                        "processing_details": (
                            f"{len(partials)} active/partial Kaggle cache artifact(s) detected; "
                            "the source directory was not inspected."
                        ),
                    }
                )
                continue
            for path in discover_dataset_files(actual_root):
                if path.name.casefold().endswith((".part", ".partial", ".tmp", ".download")):
                    continue
                started = time.perf_counter()
                row_count = ""
                digest = sha256_file(path)
                result: dict[str, Any] = {"status": "INVENTORIED"}
                memory_peak: int | None = None
                if _has_chart_schema(path):
                    try:
                        with MemorySampler() as sampler:
                            result = process_file(
                                stage,
                                spec,
                                path,
                                chunk_size=chunk_size,
                                file_sha256=digest,
                            )
                        memory_peak = sampler.peak_rss_bytes
                        row_count = result["rows_seen"]
                    except Exception as exc:
                        result = {"status": "PROCESSING_FAILED", "details": _safe_error(exc)}
                inventory = inventory_file(
                    path,
                    spec.dataset_id,
                    spec.version,
                    spec.url,
                    spec.listed_license,
                    digest=digest,
                    known_row_count=int(row_count) if row_count != "" else None,
                )
                if row_count != "":
                    inventory["row_count"] = row_count
                file_stats.append(
                    {
                        **inventory,
                        "processing_status": result.get("status", ""),
                        "accepted_rows": result.get("rows_accepted", ""),
                        "rejected_rows": result.get("rows_rejected", ""),
                        "processing_seconds": round(time.perf_counter() - started, 3),
                        "sampled_peak_rss_bytes": memory_peak if memory_peak is not None else "",
                        "processing_details": result.get("details", ""),
                    }
                )
        report_dir.mkdir(parents=True, exist_ok=True)
        if file_stats:
            fields = list(dict.fromkeys(key for row in file_stats for key in row))
            with (report_dir / "dataset_inventory.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as stream:
                import csv

                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(file_stats)
            manifest = {
                "research_root": str(research_root),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "datasets": [
                    {
                        "dataset_id": spec.dataset_id,
                        "version": spec.version,
                        "url": spec.url,
                        "publisher": spec.publisher,
                        "listed_license": spec.listed_license,
                        "rights_status": "UNVERIFIED",
                        "path": str(roots[spec.dataset_id]),
                        "files": sum(row["dataset_id"] == spec.dataset_id for row in file_stats),
                    }
                    for spec in DATASETS
                ],
            }
            (audit_dir / "dataset_registry.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8"
            )
        else:
            write_inventory_report(research_root, roots, report_dir)
        write_analysis_reports(stage, report_dir)
    finally:
        stage.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and audit pinned Kaggle source versions into isolated research staging."
    )
    parser.add_argument("--research-root", type=Path, default=DEFAULT_RESEARCH_ROOT)
    parser.add_argument("--download", action="store_true", help="Attempt one supported KaggleHub download per dataset.")
    parser.add_argument(
        "--probe-gonzalo-latest",
        action="store_true",
        help="Check cache and disk space, then use KaggleHub's unversioned latest call only if safe.",
    )
    parser.add_argument("--latest-version", type=int)
    parser.add_argument("--latest-size-bytes", type=int)
    parser.add_argument("--audit-only", action="store_true", help="Skip downloads and inspect files already present.")
    parser.add_argument("--chunk-size", type=int, default=50_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size must be a positive integer.")
    root = args.research_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if getattr(args, "probe_gonzalo_latest", False):
        if args.latest_version is None or args.latest_size_bytes is None:
            raise SystemExit(
                "--probe-gonzalo-latest requires --latest-version and --latest-size-bytes "
                "from a current listing check."
            )
        report_dir = root / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "kaggle_latest_download_preflight.json"
        if report_path.exists():
            raise FileExistsError(
                f"Refusing to overwrite latest-download report: {report_path}"
            )
        result = download_dataset_latest(
            DATASETS[0],
            root,
            latest_version=args.latest_version,
            listed_size_bytes=args.latest_size_bytes,
        )
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "listing_version": args.latest_version,
            "listing_size_bytes": args.latest_size_bytes,
            "result": result,
        }
        report_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    statuses: list[dict[str, Any]] = []
    if args.download and not args.audit_only:
        seen: set[str] = set()
        for spec in DATASETS:
            if spec.dataset_id in seen:
                continue
            seen.add(spec.dataset_id)
            statuses.append(download_dataset(spec, root))
            print(f"{spec.dataset_id}: {statuses[-1]['status']}")
    status_path = root / "reports" / "dataset_download_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    if (args.download and not args.audit_only) or not status_path.exists():
        status_path.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "kagglehub_version": _installed_kagglehub_version(),
                    "download_attempted": bool(args.download and not args.audit_only),
                    "datasets": statuses,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    run_audit(root, args.chunk_size)
    for entry in statuses:
        print(f"  local_path={entry.get('path') or '(not downloaded)'}")
        if entry.get("details"):
            print(f"  details={entry['details']}")
    print(f"Research staging DB: {root / 'staging' / 'research_staging.sqlite'}")
    print(f"Audit reports: {root / 'reports'}")
    return 0 if not any(entry["status"] == "DOWNLOAD_FAILED" for entry in statuses) else 2


def _installed_kagglehub_version() -> str | None:
    try:
        return importlib.metadata.version("kagglehub")
    except importlib.metadata.PackageNotFoundError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
