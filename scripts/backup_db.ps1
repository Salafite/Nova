param(
    [string]$OutDir = (Join-Path (Split-Path $PSScriptRoot -Parent) "backups"),
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Stop"

$required = @("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
$missing = $required | Where-Object { -not (Get-Item "env:$_" -ErrorAction SilentlyContinue) }
if ($missing) {
    Write-Error "Missing required env vars: $($missing -join ', ')"
    exit 1
}

if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
    Write-Error "pg_dump not found. Install PostgreSQL client tools and add to PATH."
    exit 1
}

if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$filename = "nova_erp_$timestamp.sql.gz"
$filepath = Join-Path $OutDir $filename

$env:PGPASSWORD = $env:DB_PASSWORD
$dumpArgs = @(
    "-h", $env:DB_HOST,
    "-p", $env:DB_PORT,
    "-U", $env:DB_USER,
    "-d", $env:DB_NAME,
    "-F", "c",
    "-Z", "9",
    "-f", $filepath,
    "--no-owner",
    "--no-privileges"
)

Write-Host "Starting backup of $($env:DB_NAME) to $filepath ..."
$result = Start-Process -FilePath pg_dump -ArgumentList $dumpArgs -Wait -NoNewWindow -PassThru
Remove-Item env:PGPASSWORD

if ($result.ExitCode -ne 0) {
    Write-Error "Backup failed (exit code $($result.ExitCode))."
    exit $result.ExitCode
}

$size = (Get-Item $filepath).Length
Write-Host "Backup completed: $([math]::Round($size / 1MB, 2)) MB"

$old = Get-ChildItem $OutDir -Filter "nova_erp_*.sql.gz" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays)
}
foreach ($f in $old) {
    Remove-Item $f.FullName -Force
    Write-Host "Removed old backup: $($f.Name)"
}

Write-Host "Done. $($old.Count) old backup(s) cleaned."
exit 0
