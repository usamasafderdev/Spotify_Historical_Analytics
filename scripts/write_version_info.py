from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_PATH = ROOT / "src" / "spotify_historical_analytics" / "__init__.py"
OUTPUT_PATH = ROOT / "build" / "version_info.txt"


def main() -> None:
    source = INIT_PATH.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', source, re.MULTILINE)
    if match is None:
        raise RuntimeError(f"Could not determine the application version from {INIT_PATH}")
    version = match.group(1)
    parts = version.split(".")
    if not 2 <= len(parts) <= 4 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Windows executable version must contain 2-4 numeric parts: {version}")
    file_version = tuple(int(part) for part in (parts + ["0", "0", "0", "0"])[:4])
    version_tuple = ", ".join(str(part) for part in file_version)
    content = f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_tuple}),
    prodvers=({version_tuple}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        "040904B0",
        [
        StringStruct("CompanyName", "US Music Charts Analytics"),
        StringStruct("FileDescription", "US Music Charts Analytics"),
        StringStruct("FileVersion", "{version}"),
        StringStruct("InternalName", "USMusicChartsAnalytics"),
        StringStruct("OriginalFilename", "USMusicChartsAnalytics.exe"),
        StringStruct("ProductName", "US Music Charts Analytics"),
        StringStruct("ProductVersion", "{version}")
        ])
      ]),
    VarFileInfo([VarStruct("Translation", [1033, 1200])])
  ]
)
'''
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    (ROOT / "build" / "version.txt").write_text(version + "\n", encoding="ascii")
    print(f"Generated Windows version metadata for {version}")


if __name__ == "__main__":
    main()
