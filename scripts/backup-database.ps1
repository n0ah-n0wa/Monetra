# Logical PostgreSQL backup for Monetra (Windows PowerShell).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ComposeFile = if ($env:COMPOSE_FILE) { $env:COMPOSE_FILE } else { "docker-compose.prod.yml" }
$BackupDir = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { Join-Path $Root "backups" }
$DailyDir = Join-Path $BackupDir "daily"
$WeeklyDir = Join-Path $BackupDir "weekly"
$MonthlyDir = Join-Path $BackupDir "monthly"
$DailyRetention = if ($env:BACKUP_DAILY_RETENTION_DAYS) { [int]$env:BACKUP_DAILY_RETENTION_DAYS } else { 7 }
$WeeklyRetention = if ($env:BACKUP_WEEKLY_RETENTION_DAYS) { [int]$env:BACKUP_WEEKLY_RETENTION_DAYS } else { 28 }
$MonthlyRetention = if ($env:BACKUP_MONTHLY_RETENTION_DAYS) { [int]$env:BACKUP_MONTHLY_RETENTION_DAYS } else { 365 }
$Timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd'T'HHmmss'Z'")
$Filename = "monetra-$Timestamp.dump"

function Load-DotEnv([string]$Path) {
  if (-not (Test-Path $Path)) { return }
  Get-Content $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }
    $key = $line.Substring(0, $eq).Trim()
    $value = $line.Substring($eq + 1).Trim()
    if (-not (Test-Path "Env:$key")) { Set-Item -Path "Env:$key" -Value $value }
  }
}

New-Item -ItemType Directory -Force -Path $DailyDir, $WeeklyDir, $MonthlyDir | Out-Null
if (-not (Test-Path (Join-Path $Root ".env"))) {
  throw "[backup] .env not found"
}
Load-DotEnv (Join-Path $Root ".env")
if (-not $env:POSTGRES_USER) { throw "[backup] POSTGRES_USER is required" }
if (-not $env:POSTGRES_DB) { throw "[backup] POSTGRES_DB is required" }

$output = Join-Path $DailyDir $Filename
Write-Host "[backup] Creating logical backup for database $($env:POSTGRES_DB)..."
cmd /c "docker compose -f $ComposeFile exec -T postgres pg_dump -U $($env:POSTGRES_USER) -d $($env:POSTGRES_DB) -Fc > `"$output`""
if ($LASTEXITCODE -ne 0) { throw "[backup] pg_dump failed" }
if (-not (Test-Path $output) -or (Get-Item $output).Length -eq 0) {
  throw "[backup] backup file is empty: $output"
}

$hash = Get-FileHash -Algorithm SHA256 $output
"$($hash.Hash.ToLower())  $Filename" | Set-Content -Path "$output.sha256" -Encoding ascii

$utcNow = (Get-Date).ToUniversalTime()
if ($utcNow.DayOfWeek -eq "Sunday") {
  Copy-Item $output (Join-Path $WeeklyDir $Filename)
  Copy-Item "$output.sha256" (Join-Path $WeeklyDir "$Filename.sha256")
  Write-Host "[backup] Copied to weekly retention ($WeeklyDir)"
}
if ($utcNow.Day -eq 1) {
  Copy-Item $output (Join-Path $MonthlyDir $Filename)
  Copy-Item "$output.sha256" (Join-Path $MonthlyDir "$Filename.sha256")
  Write-Host "[backup] Copied to monthly retention ($MonthlyDir)"
}

Get-ChildItem $DailyDir -Filter "monetra-*.dump" |
  Where-Object { $_.LastWriteTimeUtc -lt (Get-Date).ToUniversalTime().AddDays(-$DailyRetention) } |
  Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem $WeeklyDir -Filter "monetra-*.dump" |
  Where-Object { $_.LastWriteTimeUtc -lt (Get-Date).ToUniversalTime().AddDays(-$WeeklyRetention) } |
  Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem $MonthlyDir -Filter "monetra-*.dump" |
  Where-Object { $_.LastWriteTimeUtc -lt (Get-Date).ToUniversalTime().AddDays(-$MonthlyRetention) } |
  Remove-Item -Force -ErrorAction SilentlyContinue

if ($env:MONETRA_BACKUP_S3_URI) {
  if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "[backup] MONETRA_BACKUP_S3_URI is set but aws CLI is not installed"
  }
  $sse = if ($env:MONETRA_BACKUP_S3_SSE) { $env:MONETRA_BACKUP_S3_SSE } else { "AES256" }
  $s3Dest = "$($env:MONETRA_BACKUP_S3_URI.TrimEnd('/'))/$Filename"
  aws s3 cp $output $s3Dest --sse $sse
  aws s3 cp "$output.sha256" "$s3Dest.sha256" --sse $sse
}

$bytes = (Get-Item $output).Length
Write-Host "[backup] Wrote $output ($bytes bytes)"
