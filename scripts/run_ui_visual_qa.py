"""Render a resolution/scaling matrix without changing Windows display settings."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / "build" / "import-visual-qa" / "matrix"
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "windows"
    environment.pop("QT_SCREEN_SCALE_FACTORS", None)
    environment.pop("QT_SCALE_FACTOR", None)
    baseline = float(subprocess.check_output([
        sys.executable, "-c",
        "from PySide6.QtWidgets import QApplication; a=QApplication([]); print(a.primaryScreen().devicePixelRatio())",
    ], env=environment, text=True).strip())
    results = []
    for width, height in [(1366, 768), (1600, 900), (1920, 1080)]:
        for scale in [1, 1.25, 1.5]:
            environment["QT_SCALE_FACTOR"] = str(scale / baseline)
            target = output / f"{width}x{height}-{int(scale * 100)}"
            # Reserve physical space for the title bar, taskbar, and window margins.
            logical_width = min(960, int(width / scale) - 48)
            logical_height = min(680, int(height / scale) - 80)
            subprocess.run([
                sys.executable, "-m", "spotify_historical_analytics", "--import-visual-qa",
                str(target), str(logical_width), str(logical_height),
            ], cwd=ROOT, env=environment, check=True, timeout=90)
            result = json.loads((target / "results.json").read_text())
            assert abs(result["scale"] - scale) < 0.02, result
            result["simulated_resolution"] = [width, height]
            results.append(result)
            print(f"Rendered {width}x{height} at simulated {scale * 100:g}%", flush=True)
    (output / "matrix.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
