from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import pefile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("seed_manifest", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    expected_seed = json.loads(options.seed_manifest.read_text(encoding="utf-8"))
    report = {"native_files": [], "excluded_microsoft_files_present": [], "unresolved_imports": [], "files": []}
    files = [path for path in options.bundle.rglob("*") if path.is_file()]
    available = {path.name.lower() for path in files} | {path.name.lower() for path in Path("C:/Windows/System32").glob("*.dll")}
    for path in files:
        relative = path.relative_to(options.bundle).as_posix()
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        report["files"].append({"path": relative, "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
        if relative == "_internal/seed/analytics.sqlite3":
            assert digest.hexdigest() == expected_seed["sha256"], "Collected seed differs from the frozen seed"
            report["seed_sha256"] = digest.hexdigest()
        if path.suffix.lower() not in {".pyd", ".dll", ".exe"}:
            continue
        image = pefile.PE(str(path), fast_load=True)
        image.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"], pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
        strings = {}
        for group in getattr(image, "FileInfo", []):
            for item in group:
                for table in getattr(item, "StringTable", []):
                    strings.update({key.decode(errors="replace"): value.decode(errors="replace") for key, value in table.entries.items()})
        imports = [entry.dll.decode("ascii") for entry in getattr(image, "DIRECTORY_ENTRY_IMPORT", [])]
        if "microsoft" in strings.get("CompanyName", "").lower() or path.name.lower().startswith(("msvcp", "vcruntime", "api-ms-win-", "ucrtbase")):
            report["excluded_microsoft_files_present"].append(relative)
        for imported in imports:
            if imported.lower() not in available and not imported.lower().startswith(("api-ms-win-", "ext-ms-win-")):
                report["unresolved_imports"].append({"file": relative, "import": imported})
            if re.fullmatch(r"(?i)(msvcp\d+(?:_\d+)?|vcruntime\d+(?:_\d+)?)-[0-9a-f]+\.dll", imported):
                raise ValueError(f"Unnormalized private Microsoft runtime dependency: {relative}: {imported}")
        report["native_files"].append({"path": relative, "company": strings.get("CompanyName"), "version": strings.get("FileVersion"), "imports": imports})
        image.close()
    report["bundle_bytes"] = sum(item["bytes"] for item in report["files"])
    report["status"] = "PASS" if report.get("seed_sha256") and not report["excluded_microsoft_files_present"] and not report["unresolved_imports"] else "FAIL"
    options.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] != "PASS":
        raise ValueError({key: report[key] for key in ["excluded_microsoft_files_present", "unresolved_imports"]})
    print(json.dumps({"status": report["status"], "bundle_bytes": report["bundle_bytes"], "native_files": len(report["native_files"]), "seed_sha256": report["seed_sha256"]}), flush=True)


if __name__ == "__main__":
    main()
