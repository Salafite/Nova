param(
    [ValidateSet("frontend","backend","all")]
    [string]$Target = "all",
    [switch]$SkipBuild,
    [switch]$SkipRestart
)

$ErrorActionPreference = "Stop"
$ROOT = Resolve-Path (Join-Path $PSScriptRoot "..")
$API_DIR = Join-Path $ROOT "apps\api"
$VUE_DIR = Join-Path $ROOT "apps\web-vue"

Write-Host "=== Nova ERP Deploy ===" -ForegroundColor Cyan
Write-Host "Target: $Target"

# --- Frontend Build ---
if ($Target -in @("frontend","all") -and !$SkipBuild) {
    Write-Host "[Frontend] Building..." -ForegroundColor Yellow
    Push-Location $VUE_DIR
    try {
        npm install --silent
        npm run build
        Write-Host "  Frontend built OK" -ForegroundColor Green
    } finally {
        Pop-Location
    }
}

# --- Backend Prep ---
if ($Target -in @("backend","all") -and !$SkipBuild) {
    Write-Host "[Backend] Installing dependencies..." -ForegroundColor Yellow
    Push-Location $API_DIR
    try {
        if (Test-Path "requirements.txt") {
            pip install -r requirements.txt --quiet
            Write-Host "  Dependencies installed" -ForegroundColor Green
        }
        # Run pending migrations
        $migScript = Join-Path $ROOT "scripts\run_migration.py"
        if (Test-Path $migScript) {
            python $migScript
            Write-Host "  Migrations applied" -ForegroundColor Green
        }
    } finally {
        Pop-Location
    }
}

# --- Restart Server ---
if (!$SkipRestart) {
    Write-Host "[Server] Restarting..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "restart_server.ps1")
}

Write-Host "=== Deploy Complete ===" -ForegroundColor Cyan
