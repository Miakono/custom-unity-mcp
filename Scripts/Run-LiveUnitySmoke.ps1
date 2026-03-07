param(
    [string]$UnityInstance,
    [string]$HttpUrl = "http://127.0.0.1:8080",
    [string]$PytestFilter = "live_unity_http_smoke_matrix_opt_in"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$serverRoot = Join-Path $repoRoot "Server"
$pythonExe = Join-Path $serverRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at '$pythonExe'. Create the server venv first."
}

Push-Location $serverRoot
try {
    $env:UNITY_MCP_RUN_LIVE_SMOKE = "1"
    $env:UNITY_MCP_HTTP_URL = $HttpUrl

    if (-not [string]::IsNullOrWhiteSpace($UnityInstance)) {
        $env:UNITY_MCP_LIVE_INSTANCE = $UnityInstance
    }
    elseif (Test-Path Env:UNITY_MCP_LIVE_INSTANCE) {
        Remove-Item Env:UNITY_MCP_LIVE_INSTANCE
    }

    Write-Host "Running live Unity smoke test via $HttpUrl" -ForegroundColor Cyan
    if (-not [string]::IsNullOrWhiteSpace($UnityInstance)) {
        Write-Host "Target instance: $UnityInstance" -ForegroundColor DarkGray
    }

    & $pythonExe -m pytest tests/integration/test_live_unity_smoke_runner.py -q -k $PytestFilter
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "Live Unity smoke test failed with exit code $exitCode."
    }
}
finally {
    Pop-Location
}