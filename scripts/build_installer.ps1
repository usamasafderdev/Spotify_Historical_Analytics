param(
    [string]$IsccPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$searched = @("PATH: ISCC.exe")
if (-not $IsccPath) {
    $candidate = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($candidate) { $IsccPath = $candidate.Source }
    foreach ($basePath in @(${env:ProgramFiles(x86)}, $env:ProgramFiles, (Join-Path $env:LOCALAPPDATA "Programs"))) {
        foreach ($versionNumber in @(7, 6)) {
            $compilerPath = Join-Path $basePath "Inno Setup $versionNumber\ISCC.exe"
            $searched += $compilerPath
            if (-not $IsccPath -and (Test-Path -LiteralPath $compilerPath)) { $IsccPath = $compilerPath }
        }
    }
}
if (-not $IsccPath -or -not (Test-Path -LiteralPath $IsccPath)) {
    $searched | ForEach-Object { Write-Output "Searched: $_" }
    throw "Inno Setup compiler not found. Install an appropriate Inno Setup release from https://jrsoftware.org/isinfo.php after reviewing its license, or pass -IsccPath to an existing compiler. No installer was built."
}

$version = python -c 'from spotify_historical_analytics import __version__; print(__version__)'
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
