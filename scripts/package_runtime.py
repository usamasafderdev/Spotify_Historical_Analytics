from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import pefile


def prepare_binaries(entries, compliance: Path, work: Path):
    exclusions = {name.removeprefix("_internal/").replace("\\", "/").lower()
                  for name in json.loads((compliance / "excluded-files.json").read_text())}
    inventory = json.loads((compliance / "microsoft-runtime-inventory.json").read_text())
    excluded_names = {Path(item["file"]).name.lower() for item in inventory["excluded_microsoft_files"]}
    result, changes = [], []
    for target, source, kind in entries:
        basename = Path(target).name.lower()
        if (target.replace("\\", "/").lower() in exclusions or basename in excluded_names
                or basename.startswith(("msvcp", "vcruntime", "api-ms-win-", "ucrtbase"))):
            continue
        if Path(source).suffix.lower() in {".pyd", ".dll"}:
            image = pefile.PE(source, fast_load=True)
            image.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
            patches = []
            for descriptor in getattr(image, "DIRECTORY_ENTRY_IMPORT", []):
                imported = descriptor.dll.decode("ascii")
                match = re.fullmatch(r"(?i)(msvcp\d+(?:_\d+)?|vcruntime\d+(?:_\d+)?)-[0-9a-f]+\.dll", imported)
                if match:
                    patches.append((image.get_offset_from_rva(descriptor.struct.Name), imported, match[1] + ".dll"))
            image.close()
            if patches:
                content = bytearray(Path(source).read_bytes())
                original_hash = hashlib.sha256(content).hexdigest()
                for offset, original, replacement in patches:
                    if len(replacement) > len(original):
                        raise ValueError("Runtime import normalization would change PE layout")
                    content[offset:offset + len(original)] = replacement.encode().ljust(len(original), b"\0")
                destination = work / "runtime-patches" / target
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
                patched = pefile.PE(str(destination))
                patched.OPTIONAL_HEADER.CheckSum = patched.generate_checksum()
                patched.write(filename=str(destination))
                patched.close()
                changes.append({"file": target, "original_sha256": original_hash,
                                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "imports": patches})
                source = str(destination)
        result.append((target, source, kind))
    (work / "runtime-normalization.json").write_text(json.dumps(changes, indent=2))
    return result
