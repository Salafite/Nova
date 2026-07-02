param(
    [string]$Port = "8070"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Nova ERP Server Restart ===" -ForegroundColor Cyan

# 1. Kill existing Python processes on the port
Write-Host "[1/4] Stopping existing server..." -ForegroundColor Yellow
$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
if ($existing) {
    $procId = $existing.OwningProcess
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "  Stopped process $procId" -ForegroundColor Green
} else {
    Write-Host "  No existing server found on port $Port" -ForegroundColor Gray
}

# 2. Activate virtual environment (if it exists)
Write-Host "[2/4] Activating environment..." -ForegroundColor Yellow
$venvPath = Join-Path $PSScriptRoot "..\venv\Scripts\Activate.ps1"
$venvPath2 = Join-Path $PSScriptRoot "..\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
    Write-Host "  venv activated" -ForegroundColor Green
} elseif (Test-Path $venvPath2) {
    & $venvPath2
    Write-Host "  .venv activated" -ForegroundColor Green
} else {
    Write-Host "  No venv found, using system Python" -ForegroundColor Gray
}

# 3. Start server in background
Write-Host "[3/4] Starting server..." -ForegroundColor Yellow
$apiDir = Join-Path $PSScriptRoot "..\apps\api"
$logFile = Join-Path $PSScriptRoot "..\server.log"

$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = "python"
$startInfo.Arguments = "main.py"
$startInfo.WorkingDirectory = (Resolve-Path $apiDir).Path
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
$startInfo.UseShellExecute = $false

$proc = [System.Diagnostics.Process]::Start($startInfo)
Start-Sleep -Seconds 3

# 4. Verify
Write-Host "[4/4] Verifying..." -ForegroundColor Yellow
try {
    $res = Invoke-WebRequest -Uri "http://localhost:$Port/api/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "  Server is running! Status: $($res.Content)" -ForegroundColor Green
} catch {
    Write-Host "  Server may still be starting up. Check server.log" -ForegroundColor Yellow
}

Write-Host "=== Done ===" -ForegroundColor Cyan
