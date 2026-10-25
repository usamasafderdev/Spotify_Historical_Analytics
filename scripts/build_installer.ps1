param(
    [string]$IsccPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $IsccPath) {
    $candidate = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($candidate) {
        $IsccPath = $candidate.Source
    } else {
        $standardPath = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
        if (Test-Path -LiteralPath $standardPath) {
            $IsccPath = $standardPath
        }
    }
}
if (-not $IsccPath -or -not (Test-Path -LiteralPath $IsccPath)) {
    throw "Inno Setup 6 is not installed. Install it from https://jrsoftware.org/isinfo.php, then rerun scripts/build_installer.ps1."
}

$version = python -c "import re; from pathlib import Path; s=Path('src/spotify_historical_analytics/__init__.py').read_text(); print(re.search(r'__version__\s*=\s*\"([^\"]+)\"', s).group(1))"
if ($LASTEXITCODE -ne 0 -or -not $version) {
    throw "Could not read the application version."
}
if (-not (Test-Path -LiteralPath "dist\USMusicChartsAnalytics\USMusicChartsAnalytics.exe")) {
    throw "Build the standalone application first by running scripts/build_windows.ps1."
}

& $IsccPath "/DAppVersion=$version" "packaging\installer.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compiler failed with exit code $LASTEXITCODE."
}
$installer = Join-Path $root "dist\installer\US-Music-Charts-Analytics-Setup.exe"
if (-not (Test-Path -LiteralPath $installer)) {
    throw "Inno Setup returned success but did not produce $installer."
}
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash
Set-Content -LiteralPath "$installer.sha256" -Value "$hash  US-Music-Charts-Analytics-Setup.exe" -Encoding ascii
Write-Output "Installer: $installer"
Write-Output "SHA256: $hash"
