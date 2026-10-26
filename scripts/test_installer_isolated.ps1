param([string]$IsccPath = "")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not $IsccPath) { $IsccPath = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path -LiteralPath $IsccPath)) { throw "Pass the installed Inno Setup compiler path with -IsccPath." }
$qaRoot = [IO.Path]::GetFullPath((Join-Path $root "build\phase9\installer-qa"))
$workspace = [IO.Path]::GetFullPath($root) + [IO.Path]::DirectorySeparatorChar
if (-not $qaRoot.StartsWith($workspace, [StringComparison]::OrdinalIgnoreCase)) { throw "QA path escapes workspace." }
$installPath = Join-Path $qaRoot "installed"
$dataPath = Join-Path $qaRoot "userdata"
New-Item -ItemType Directory -Force -Path $qaRoot,$dataPath | Out-Null
$qaName = "US Music Charts Analytics Phase 9 QA"
$qaId = "{{EB7C2FA5-B93B-4AF7-833D-DA907E77A019}"
function Compile-QA {
    param([string]$PackageVersion)
    & $IsccPath "/DAppName=$qaName" "/DAppIdentifier=$qaId" "/DAppVersion=$PackageVersion" "/DOutputName=US-Music-Charts-Analytics-Phase9-QA-Setup" "packaging\installer.iss" *> (Join-Path $qaRoot "compile-$PackageVersion.log")
    if ($LASTEXITCODE -ne 0) { throw "QA installer compilation failed." }
}
Compile-QA "0.1.0"
$setup = Join-Path $root "dist\installer\US-Music-Charts-Analytics-Phase9-QA-Setup.exe"
$env:SPOTIFY_ANALYTICS_DATA_DIR = $dataPath
$env:QT_QPA_PLATFORM = "offscreen"
function Invoke-QAProcess {
    param([string]$File, [string[]]$Arguments)
    $logFile = Join-Path $dataPath "logs\application.log"
    $previousLog = if (Test-Path -LiteralPath $logFile) { [IO.File]::ReadAllText($logFile) } else { "" }
    $process = Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "$File failed: $($process.ExitCode)" }
    if ((Split-Path -Leaf $File) -eq "USMusicChartsAnalytics.exe" -and (Test-Path -LiteralPath $logFile)) {
        $currentLog = [IO.File]::ReadAllText($logFile)
        $newLog = if ($currentLog.StartsWith($previousLog)) { $currentLog.Substring($previousLog.Length) } else { $currentLog }
        if ($newLog -match '\s(ERROR|CRITICAL)\s') { throw "Installed application logged an error: $newLog" }
    }
}
function Install-QA {
    Invoke-QAProcess $setup @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/DIR=`"$installPath`"", "/GROUP=`"$qaName`"", "/TASKS=desktopicon", "/LOG=`"$(Join-Path $qaRoot 'install.log')`"")
}
Install-QA
$exe = Join-Path $installPath "USMusicChartsAnalytics.exe"
if ((Get-FileHash -LiteralPath $exe).Hash -ne (Get-FileHash -LiteralPath (Join-Path $root "dist\USMusicChartsAnalytics\USMusicChartsAnalytics.exe")).Hash) { throw "Installed executable does not match the tested bundle." }
$programs = [Environment]::GetFolderPath("Programs")
$desktop = [Environment]::GetFolderPath("DesktopDirectory")
$shortcuts = @((Join-Path $programs "$qaName.lnk"), (Join-Path $programs "$qaName\$qaName.lnk"))
$startMenu = $shortcuts | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$desktopLink = Join-Path $desktop "$qaName.lnk"
if (-not $startMenu -or -not (Test-Path -LiteralPath $desktopLink)) { throw "Expected QA shortcuts were not created." }
$shell = New-Object -ComObject WScript.Shell
foreach ($link in @($startMenu,$desktopLink)) {
    if ($shell.CreateShortcut($link).TargetPath -ne $exe) { throw "Shortcut target mismatch: $link" }
}
# Only the test executable runs with PATH stripped; Python is used separately for assertions.
$savedPath = $env:PATH
$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
try { Invoke-QAProcess $exe @("--smoke-test") } finally { $env:PATH = $savedPath }
$database = Join-Path $dataPath "database\analytics.db"
python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('create table if not exists phase9_upgrade_marker(value text)'); c.execute('delete from phase9_upgrade_marker'); c.execute('insert into phase9_upgrade_marker values (?)',('preserved',)); c.commit(); c.close()" $database
if ($LASTEXITCODE -ne 0) { throw "Could not create QA persistence marker." }
Compile-QA "0.1.0.1"
Install-QA
Invoke-QAProcess $exe @("--smoke-test")
Invoke-QAProcess $exe @("--release-export-test")
Invoke-QAProcess $exe @("--demo-smoke-test")
python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); assert c.execute('select value from phase9_upgrade_marker').fetchone()[0]=='preserved'; assert c.execute('pragma integrity_check').fetchone()[0]=='ok'; c.close()" $database
if ($LASTEXITCODE -ne 0) { throw "Upgrade did not preserve QA data." }
$uninstaller = Join-Path $installPath "unins000.exe"
if (-not ([IO.Path]::GetFullPath($uninstaller)).StartsWith($qaRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Unsafe uninstaller path." }
Invoke-QAProcess $uninstaller @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=`"$(Join-Path $qaRoot 'uninstall.log')`"")
if (Test-Path -LiteralPath $exe) { throw "QA executable remains after uninstall." }
if ((Test-Path -LiteralPath $startMenu) -or (Test-Path -LiteralPath $desktopLink)) { throw "QA shortcuts remain after uninstall." }
if (-not (Test-Path -LiteralPath $database)) { throw "Uninstall deleted separate QA user data." }
@{ install=$true; start_menu=$true; desktop_shortcut=$true; path_without_python=$true; upgrade_preserved=$true; exports=$true; demo=$true; uninstall=$true; user_data_retained=$true; clean_vm=$false; qa_app_id=$qaId; package_upgrade="0.1.0 to 0.1.0.1 (same application payload)"; qa_root=$qaRoot } | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $qaRoot "results.json")
Write-Output "Isolated installer install, shortcut, launch, upgrade, persistence, export, demo and uninstall checks passed."
