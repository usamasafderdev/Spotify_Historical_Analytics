param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed with exit code $LASTEXITCODE"
    }
}

$architecture = python -c "import struct; print(struct.calcsize('P') * 8)"
if ($LASTEXITCODE -ne 0 -or $architecture -ne "64") {
    throw "A 64-bit Python interpreter is required to build the Windows x64 release."
}

python -c "import PyInstaller, PySide6, pyqtgraph, pandas, openpyxl, PIL"
if ($LASTEXITCODE -ne 0) {
    throw "Install the project and Windows build dependencies before building."
}

$env:PYTHONPYCACHEPREFIX = Join-Path $root "build\pycache"
if (-not $SkipTests) {
    Invoke-Checked "python" @("-m", "pytest", "-q")
}
Invoke-Checked "python" @("-m", "compileall", "-q", "src", "tests")
Invoke-Checked "python" @("scripts/generate_icon.py")
Invoke-Checked "python" @("scripts/write_version_info.py")
Invoke-Checked "python" @("scripts/write_release_notices.py")
Invoke-Checked "python" @("-m", "PyInstaller", "--clean", "--noconfirm", "packaging/windows.spec", "--distpath", "dist", "--workpath", "build/pyinstaller")

$smokeData = Join-Path $root "build\smoke-data"
New-Item -ItemType Directory -Path $smokeData -Force | Out-Null
$env:SPOTIFY_ANALYTICS_DATA_DIR = $smokeData
$env:QT_QPA_PLATFORM = "offscreen"
$exe = Join-Path $root "dist\USMusicChartsAnalytics\USMusicChartsAnalytics.exe"
$process = Start-Process -FilePath $exe -ArgumentList "--smoke-test" -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) {
    throw "Packaged application smoke test failed with exit code $($process.ExitCode). See $smokeData\logs."
}
$exportCheck = Start-Process -FilePath $exe -ArgumentList "--release-export-test" -WindowStyle Hidden -PassThru -Wait
if ($exportCheck.ExitCode -ne 0) {
    throw "Packaged CSV/XLSX export smoke test failed with exit code $($exportCheck.ExitCode)."
}
$database = Join-Path $smokeData "database\analytics.db"
if (-not (Test-Path -LiteralPath $database)) {
    throw "Packaged application exited without creating its user database at $database."
}

$packageRoot = Join-Path $root "dist\USMusicChartsAnalytics"
$manifest = Join-Path $packageRoot "SHA256SUMS.txt"
$hashLines = Get-ChildItem -LiteralPath $packageRoot -File -Recurse |
    Where-Object { $_.FullName -ne $manifest } |
    ForEach-Object {
        $relativePath = $_.FullName.Substring($packageRoot.Length + 1).Replace("\", "/")
        $fileHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash
        "$fileHash  $relativePath"
    }
Set-Content -LiteralPath $manifest -Value $hashLines -Encoding ascii
$executableHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash
Write-Output "Windows x64 build and offscreen launch smoke test succeeded."
Write-Output "Executable: $exe"
Write-Output "User data smoke-test database: $database"
Write-Output "Executable SHA256: $executableHash"
Write-Output "Bundle SHA256 manifest: $manifest"
