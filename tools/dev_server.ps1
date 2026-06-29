param(
    [int]$Port = 5000,
    [string]$HostAddress = "127.0.0.1",
    [switch]$Reload,
    [switch]$NoMigrate,
    [switch]$StopOnly,
    [string]$DatabaseUrl = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

Write-Host "Checking for existing servers on port $Port..."
$Listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
$ProcessIds = @($Listeners | Select-Object -ExpandProperty OwningProcess -Unique)

foreach ($ProcessId in $ProcessIds) {
    if ($ProcessId -and $ProcessId -ne 0) {
        Write-Host "Stopping process $ProcessId on port $Port"
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}

if ($ProcessIds.Count -gt 0) {
    Start-Sleep -Seconds 1
}

if ($StopOnly) {
    Write-Host "Server stop complete."
    exit 0
}

if ($DatabaseUrl) {
    $env:DATABASE_URL = $DatabaseUrl
    Write-Host "Using DATABASE_URL from -DatabaseUrl argument."
} else {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Write-Host "Cleared inherited DATABASE_URL so backend/.env is authoritative."
}

$env:PYTHONPATH = "."

if (-not $NoMigrate) {
    Write-Host "Applying migrations..."
    & uv --cache-dir .uv-cache run alembic upgrade head
}

Write-Host "Effective database URL:"
& uv --cache-dir .uv-cache run python -c "from backend.config import settings; print(settings.database_url)"

$UvicornArgs = @(
    "--cache-dir", ".uv-cache",
    "run", "uvicorn", "backend.app:app",
    "--host", $HostAddress,
    "--port", "$Port"
)

if ($Reload) {
    $UvicornArgs += "--reload"
}

Write-Host "Starting server at http://${HostAddress}:$Port"
& uv @UvicornArgs
