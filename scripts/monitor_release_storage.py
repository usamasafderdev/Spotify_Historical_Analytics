from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    options = parser.parse_args()
    work = options.work.resolve()
    destination = work / "storage-monitor.json"
    report = {"samples": 0, "minimum_free_bytes": {}, "peak_observed_temporary_bytes": 0}
    while not (work / "stop-storage-monitor").exists():
        report["samples"] += 1
        for drive in ("C:/", "D:/"):
            available = shutil.disk_usage(drive).free
            report["minimum_free_bytes"][drive] = min(available, report["minimum_free_bytes"].get(drive, available))
        temporary = sum(path.stat().st_size for root in (work / "temp", work / "cache", work / "build" / "pyinstaller")
                        if root.exists() for path in root.rglob("*") if path.is_file())
        report["peak_observed_temporary_bytes"] = max(temporary, report["peak_observed_temporary_bytes"])
        report["current_temporary_bytes"] = temporary
        report["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        time.sleep(20)


if __name__ == "__main__":
    main()
