"""Collect exact installed core dependency notices; no licensing clearance implied."""
from importlib import metadata
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "build" / "release-notices"
PACKAGES = ["PySide6", "PySide6-Essentials", "PySide6-Addons", "shiboken6", "pyqtgraph",
            "pandas", "numpy", "openpyxl", "et-xmlfile", "python-dateutil", "pytz", "tzdata", "six", "packaging", "PyInstaller"]


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    inventory = []
    for name in PACKAGES:
        distribution = metadata.distribution(name)
        copied = []
        for file in distribution.files or ():
            if not any(part.lower().startswith(("license", "licence", "copying", "notice")) for part in file.parts):
                continue
            source = Path(distribution.locate_file(file))
            if source.is_file():
                destination = DESTINATION / "licenses" / name / str(file).replace("..", "_")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                copied.append(str(destination.relative_to(DESTINATION)))
        inventory.append({"name": name, "version": distribution.version,
                          "license_expression": distribution.metadata.get("License-Expression"),
                          "license": distribution.metadata.get("License"), "notice_files": copied})
    runtime_license = Path(sys.base_prefix) / "LICENSE.txt"
    if runtime_license.is_file():
        shutil.copyfile(runtime_license, DESTINATION / "PYTHON_LICENSE.txt")
    (DESTINATION / "dependency-inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    (DESTINATION / "THIRD_PARTY_NOTICES.md").write_text(
        "# Third-party notices\n\nThis directory retains license/notice files from the exact build environment. "
        "The JSON inventory records dependency versions and declared license metadata. "
        "PyInstaller is a build dependency; its notices cover the packaged bootloader. "
        "This inventory does not certify distribution compliance or identify every Qt module's terms. "
        "Review all shipped DLLs/plugins and the applicable Qt license obligations before release.\n\n"
        + "\n".join(f"- {item['name']} {item['version']}: {len(item['notice_files'])} notice files" for item in inventory)
        + "\n", encoding="utf-8")
    print(f"Collected core dependency notices: {DESTINATION}")


if __name__ == "__main__":
    main()
