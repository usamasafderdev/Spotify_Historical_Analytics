from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("installer", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    if not options.output.name.endswith("-INTERNAL-READY.zip"):
        raise ValueError("External dataset distribution authorization is not established")
    documentation = options.bundle / "Documentation"
    files = {path.name: path for path in documentation.iterdir() if path.is_file()}
    files[options.installer.name] = options.installer
    files["THIRD_PARTY_NOTICES.md"] = options.bundle / "_internal" / "notices" / "THIRD_PARTY_NOTICES.md"
    checksums = "".join(f"{file_hash(path)}  {name}\n" for name, path in sorted(files.items()))
    with zipfile.ZipFile(options.output, "x", allowZip64=True) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, name, compress_type=zipfile.ZIP_STORED if path.suffix.lower() == ".exe" else zipfile.ZIP_DEFLATED)
        archive.writestr("SHA256SUMS.txt", checksums, compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(options.output) as archive:
        invalid = archive.testzip()
        if invalid:
            raise ValueError(f"ZIP CRC check failed: {invalid}")
    digest = file_hash(options.output)
    options.output.with_suffix(".zip.sha256").write_text(f"{digest}  {options.output.name}\n", encoding="ascii")
    print(json.dumps({"zip": str(options.output.resolve()), "bytes": options.output.stat().st_size, "sha256": digest, "entries": len(files) + 1, "crc": "PASS"}), flush=True)


if __name__ == "__main__":
    main()
