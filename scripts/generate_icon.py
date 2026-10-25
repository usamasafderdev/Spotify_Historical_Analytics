from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QByteArray, QSize
from PySide6.QtGui import QImage
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "assets" / "app_icon.svg"
PNG_PATH = ROOT / "build" / "app_icon.png"
ICO_PATH = ROOT / "assets" / "app_icon.ico"


def main() -> None:
    PNG_PATH.parent.mkdir(parents=True, exist_ok=True)
    renderer = QSvgRenderer(QByteArray(SVG_PATH.read_bytes()))
    if not renderer.isValid():
        raise RuntimeError(f"Could not load original application icon: {SVG_PATH}")
    image = QImage(QSize(256, 256), QImage.Format.Format_ARGB32)
    image.fill(0)
    from PySide6.QtGui import QPainter

    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    if not image.save(str(PNG_PATH), "PNG"):
        raise RuntimeError(f"Could not render application icon: {PNG_PATH}")
    with Image.open(io.BytesIO(PNG_PATH.read_bytes())) as rendered:
        rendered.save(ICO_PATH, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Created {ICO_PATH}")


if __name__ == "__main__":
    main()
