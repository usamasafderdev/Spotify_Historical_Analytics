param(
    [string]$InstallPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $InstallPath) {
    $InstallPath = Join-Path $root "dist\USMusicChartsAnalytics"
}
$exe = Join-Path $InstallPath "USMusicChartsAnalytics.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Packaged executable not found: $exe"
}

$verifyData = Join-Path $root "build\release-verification-data"
New-Item -ItemType Directory -Path $verifyData -Force | Out-Null
$env:SPOTIFY_ANALYTICS_DATA_DIR = $verifyData
$env:QT_QPA_PLATFORM = "offscreen"
$process = Start-Process -FilePath $exe -ArgumentList "--smoke-test" -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) {
    throw "Application smoke test failed with exit code $($process.ExitCode)."
}
$db = Join-Path $verifyData "database\analytics.db"
if (-not (Test-Path -LiteralPath $db)) {
    throw "Application database was not created: $db"
}
python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('create table if not exists release_persistence_check (value text not null)'); c.execute('delete from release_persistence_check'); c.execute('insert into release_persistence_check values (?)', ('preserved',)); c.commit(); print('integrity=', c.execute('pragma integrity_check').fetchone()[0]); c.close()" $db
if ($LASTEXITCODE -ne 0) {
    throw "Packaged database verification failed."
}
$restart = Start-Process -FilePath $exe -ArgumentList "--smoke-test" -WindowStyle Hidden -PassThru -Wait
if ($restart.ExitCode -ne 0) {
    throw "Packaged restart smoke test failed with exit code $($restart.ExitCode)."
}
python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); value=c.execute('select value from release_persistence_check').fetchone()[0]; print('persisted_marker=', value); c.close(); raise SystemExit(value != 'preserved')" $db
if ($LASTEXITCODE -ne 0) {
    throw "Packaged database data did not persist across restart."
}
$exportCheck = Start-Process -FilePath $exe -ArgumentList "--release-export-test" -WindowStyle Hidden -PassThru -Wait
if ($exportCheck.ExitCode -ne 0) {
    throw "Packaged CSV/XLSX export smoke test failed with exit code $($exportCheck.ExitCode)."
}
$demo = Start-Process -FilePath $exe -ArgumentList "--demo-smoke-test" -WindowStyle Hidden -PassThru -Wait
if ($demo.ExitCode -ne 0) { throw "Packaged synthetic demo smoke test failed: $($demo.ExitCode)" }
Write-Output "Packaged startup, restart persistence, six CSV/XLSX exports, and synthetic demo checks passed."
