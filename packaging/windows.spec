from pathlib import Path
import sys
import os

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent
WORK = Path(os.environ.get("SPOTIFY_RELEASE_WORK", ROOT / "build"))
sys.path.insert(0, str(ROOT / "src"))

datas = [(str(ROOT / "assets"), "assets"), (str(WORK / "release-notices"), "notices")]
if os.environ.get("SPOTIFY_RELEASE_SEED"):
    datas.append((os.environ["SPOTIFY_RELEASE_SEED"], "seed"))
if os.environ.get("SPOTIFY_COMPLIANCE"):
    datas.append((os.environ["SPOTIFY_COMPLIANCE"], "compliance"))
binaries = []
hiddenimports = [
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
]
datas += collect_data_files(
    "pyqtgraph", excludes=["examples", "examples/**", "tests", "tests/**"]
)
hiddenimports += [
    "pyqtgraph.graphicsItems.AxisItem",
    "pyqtgraph.graphicsItems.BarGraphItem",
    "pyqtgraph.graphicsItems.PlotDataItem",
    "pyqtgraph.graphicsItems.PlotItem",
    "pyqtgraph.graphicsItems.TextItem",
    "pyqtgraph.graphicsItems.ViewBox",
    "openpyxl.cell._writer",
]

analysis = Analysis(
    [str(ROOT / "scripts" / "windows_entry.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "tests",
        "IPython",
        "jupyter",
        "scipy",
        "torch",
        "torchvision",
        "matplotlib",
        "zmq",
        "sqlalchemy",
        "tkinter",
        "PIL",
        "pyarrow",
        "lxml",
        "pandas.tests",
        "PySide6.QtTest",
        "pyqtgraph.opengl",
        "pyqtgraph.jupyter",
        "pyqtgraph.examples",
    ],
    noarchive=False,
)
# Qt's automatic plugin collection includes an unused virtual keyboard whose
# open-source terms are GPLv3 rather than LGPL. This desktop app uses Windows'
# standard input context; omit that optional plugin and its DLL/resources.
analysis.binaries = [entry for entry in analysis.binaries if "virtualkeyboard" not in entry[0].lower()]
analysis.datas = [entry for entry in analysis.datas if "virtualkeyboard" not in entry[0].lower()]
if os.environ.get("SPOTIFY_COMPLIANCE"):
    sys.path.insert(0, str(ROOT / "scripts"))
    from package_runtime import prepare_binaries
    analysis.binaries = prepare_binaries(analysis.binaries, Path(os.environ["SPOTIFY_COMPLIANCE"]), WORK)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="USMusicChartsAnalytics",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
    icon=str(ROOT / "assets" / "app_icon.ico"),
    version=str(WORK / "version_info.txt"),
)
collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="USMusicChartsAnalytics",
)
