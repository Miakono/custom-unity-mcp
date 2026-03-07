param(
    [string]$UnityInstance,
    [string]$HttpUrl = "http://127.0.0.1:8080",
    [switch]$SkipServer,
    [switch]$SkipLive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$serverRoot = Join-Path $repoRoot "Server"
$pythonExe = Join-Path $serverRoot ".venv\Scripts\python.exe"
$liveScript = Join-Path $PSScriptRoot "Run-LiveUnitySmoke.ps1"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at '$pythonExe'. Create the server venv first."
}

$serverTests = @(
    "tests/test_v2_ping.py",
    "tests/test_v2_manage_windows.py",
    "tests/test_v2_manage_selection.py",
    "tests/test_v2_project_config.py",
    "tests/test_v2_spatial.py",
    "tests/test_v3_navigation.py",
    "tests/test_v3_transactions.py",
    "tests/test_v3_waiters_events.py",
    "tests/integration/test_live_unity_smoke_runner.py"
)

Push-Location $serverRoot
try {
    if (-not $SkipServer) {
        Write-Host "Running targeted server validation suite" -ForegroundColor Cyan
        & $pythonExe -m pytest @serverTests -q
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw "Server validation suite failed with exit code $exitCode."
        }
    }

    if (-not $SkipLive) {
        Write-Host "Running live Unity validation suite" -ForegroundColor Cyan
        & $liveScript -UnityInstance $UnityInstance -HttpUrl $HttpUrl
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw "Live validation suite failed with exit code $exitCode."
        }
    }
}
finally {
    Pop-Location
}