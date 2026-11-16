$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousDataDirectory = $env:SPOTIFY_ANALYTICS_DATA_DIR
$previousPythonPath = $env:PYTHONPATH
$integrationDirectory = Join-Path $projectRoot 'local-data\v018-integration'
if (-not (Test-Path -LiteralPath (Join-Path $integrationDirectory 'database\analytics.db'))) {
    throw 'The isolated integration database has not been created.'
}
Push-Location $projectRoot
try {
    $env:SPOTIFY_ANALYTICS_DATA_DIR = $integrationDirectory
    $env:PYTHONPATH = Join-Path $projectRoot 'src'
    python -m spotify_historical_analytics
} finally {
    Pop-Location
    $env:SPOTIFY_ANALYTICS_DATA_DIR = $previousDataDirectory
    $env:PYTHONPATH = $previousPythonPath
}
