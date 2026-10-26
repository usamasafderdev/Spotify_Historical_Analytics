"""Read-only, bounded release inventory; not a secret-free/security certificate."""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import types

from PyInstaller.archive.readers import CArchiveReader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=Path("dist/USMusicChartsAnalytics"))
    parser.add_argument("--output", type=Path, default=Path("build/phase10/security-inventory.json"))
    args = parser.parse_args()
    root = args.bundle
    executable = root / "USMusicChartsAnalytics.exe"
    archive = CArchiveReader(str(executable)).open_embedded_archive("PYZ.pyz")
    module_roots = sorted({name.split(".")[0] for name in archive.toc})
    distributions = metadata.packages_distributions()
    inventory = []
    for module in module_roots:
        for name in distributions.get(module, []):
            dist = metadata.distribution(name)
            inventory.append({"module": module, "distribution": dist.metadata["Name"],
                              "version": dist.version,
                              "declared_license": dist.metadata.get("License-Expression") or dist.metadata.get("License")})
    patterns = {
        "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "aws-access-id": re.compile(r"AKIA[0-9A-Z]{16}"),
        "github-token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
        "openai-token": re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
    }
    developer_path = re.compile(r"[A-Za-z]:[\\/](?:Users|Study Material)", re.I)
    source_paths, literal_paths, secret_candidates, resource_candidates = [], [], [], []

    def visit(code, module):
        if not isinstance(code, types.CodeType):
            return
        if developer_path.search(code.co_filename):
            source_paths.append(module)
        for value in code.co_consts:
            if isinstance(value, types.CodeType):
                visit(value, module)
            elif isinstance(value, str):
                if developer_path.search(value):
                    literal_paths.append(module)
                for kind, pattern in patterns.items():
                    if pattern.search(value):
                        secret_candidates.append({"module": module, "kind": kind})

    for name in archive.toc:
        if name.startswith("spotify_historical_analytics"):
            visit(archive.extract(name), name)
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".ini", ".cfg", ".txt", ".md", ".pem", ".key", ".env"} and path.stat().st_size < 2_000_000:
            content = path.read_text(encoding="utf-8", errors="ignore")
            for kind, pattern in patterns.items():
                if pattern.search(content):
                    resource_candidates.append({"file": path.relative_to(root).as_posix(), "kind": kind})
    data = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
            and (path.suffix.lower() in {".csv", ".xlsx", ".db", ".sqlite", ".sqlite3", ".parquet"} or path.name.endswith(".csv.gz"))]
    report = {
        "exe_sha256": hashlib.sha256(executable.read_bytes()).hexdigest().upper(),
        "module_roots": module_roots, "installed_distribution_mapping": inventory,
        "application_absolute_bytecode_filename_modules": sorted(set(source_paths)),
        "application_literal_developer_path_modules": sorted(set(literal_paths)),
        "application_secret_candidates": secret_candidates,
        "resource_secret_candidates": resource_candidates, "data_files": data,
        "qt_libraries": sorted(p.relative_to(root).as_posix() for p in root.rglob("Qt6*.dll")),
        "limits": ["Pattern scanning is not proof of no secrets or a complete vulnerability assessment.",
                   "Distribution mapping uses build-environment metadata; it does not establish every bundled component version or license.",
                   "Third-party binary strings are not exhaustively decoded; raw candidate values are never printed."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Release inventory saved to {args.output}")
    print(f"Application developer-path modules: {len(source_paths) + len(literal_paths)}; secret candidates: {len(secret_candidates) + len(resource_candidates)}")


if __name__ == "__main__":
    main()
