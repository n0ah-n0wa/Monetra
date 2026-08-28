$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ComposeProd = "docker-compose.prod.yml"
$ComposeRestore = "docker-compose.restore-test.yml"
$RestoreDb = if ($env:POSTGRES_RESTORE_DB) { $env:POSTGRES_RESTORE_DB } else { "monetra_restore" }
$RestorePort = if ($env:POSTGRES_RESTORE_PORT) { $env:POSTGRES_RESTORE_PORT } else { "5433" }

function Write-Step([string]$Message) {
  Write-Host "[backup-restore-test] $Message"
}

function Wait-Postgres {
  param(
    [string]$ComposeFile,
    [string]$Service,
    [string]$User,
    [string]$Database,
    [int]$TimeoutSeconds = 80
  )
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    docker compose -f $ComposeFile exec -T $Service pg_isready -U $User -d $Database 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { return }
    Start-Sleep -Seconds 2
  }
  throw "PostgreSQL did not become ready ($ComposeFile/$Service)"
}

function Load-DotEnv {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return }
  Get-Content $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }
    $key = $line.Substring(0, $eq).Trim()
    $value = $line.Substring($eq + 1).Trim()
    if ($value.StartsWith('"') -and $value.EndsWith('"')) {
      $value = $value.Substring(1, $value.Length - 2)
    }
    if (-not (Test-Path "Env:$key")) {
      Set-Item -Path "Env:$key" -Value $value
    }
  }
}

function Ensure-Env {
  $envFile = Join-Path $Root ".env"
  if (-not (Test-Path $envFile)) {
    Write-Step "Creating .env from .env.production.example"
    Copy-Item (Join-Path $Root ".env.production.example") $envFile
    $content = Get-Content $envFile -Raw
    $jwt = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
    $content = $content -replace 'JWT_SECRET_KEY=.*', "JWT_SECRET_KEY=$jwt"
    $content = $content -replace 'POSTGRES_PASSWORD=.*', 'POSTGRES_PASSWORD=monetra-restore-test'
    Set-Content -Path $envFile -Value $content.TrimEnd()
  }
  Load-DotEnv $envFile
  if (-not $env:JWT_SECRET_KEY) {
    $env:JWT_SECRET_KEY = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
  }
}

function Test-StackReady {
  try {
    & curl.exe -k -sf https://localhost/ready | Out-Null
    return $true
  } catch {
    return $false
  }
}

Ensure-Env

if (-not (Test-Path (Join-Path $Root "nginx/certs/fullchain.pem"))) {
  & (Join-Path $PSScriptRoot "generate-local-tls-certs.ps1")
}

Write-Step "Resetting local production-shaped stack for a deterministic drill..."
$prevErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker compose -f $ComposeProd down -v --remove-orphans 2>&1 | Out-Null
$ErrorActionPreference = $prevErrorAction

Write-Step "Starting production-shaped stack..."
docker compose -f $ComposeProd up -d postgres
if ($LASTEXITCODE -ne 0) { throw "failed to start postgres" }
Wait-Postgres -ComposeFile $ComposeProd -Service postgres -User $env:POSTGRES_USER -Database $env:POSTGRES_DB

docker compose -f $ComposeProd run --rm --no-deps --entrypoint alembic backend upgrade head
if ($LASTEXITCODE -ne 0) { throw "migration failed" }

$env:RUN_DB_MIGRATIONS = "false"
docker compose -f $ComposeProd up -d --remove-orphans
Remove-Item Env:RUN_DB_MIGRATIONS -ErrorAction SilentlyContinue

$ready = $false
for ($i = 0; $i -lt 60; $i++) {
  if (Test-StackReady) {
    $ready = $true
    break
  }
  Start-Sleep -Seconds 3
}
if (-not $ready) { throw "/ready did not become healthy" }

Write-Step "Building backend image with restore-test scripts..."
docker compose -f $ComposeProd build backend
if ($LASTEXITCODE -ne 0) { throw "backend build failed" }

Write-Step "Seeding representative financial data..."
docker compose -f $ComposeProd run --rm --no-deps `
  --entrypoint python `
  backend -m scripts.seed_restore_test_data
if ($LASTEXITCODE -ne 0) { throw "seed failed" }

Write-Step "Creating backup..."
& (Join-Path $PSScriptRoot "backup-database.ps1")
if ($LASTEXITCODE -ne 0) { throw "backup failed" }

$backupFile = Get-ChildItem (Join-Path $Root "backups/daily") -Filter "monetra-*.dump" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
if (-not $backupFile) { throw "backup file not found" }

Write-Step "Preparing isolated restore target..."
$prevErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker compose -f $ComposeRestore down -v --remove-orphans 2>&1 | Out-Null
$ErrorActionPreference = $prevErrorAction

$env:POSTGRES_RESTORE_DB = $RestoreDb
docker compose -f $ComposeRestore up -d postgres-restore
if ($LASTEXITCODE -ne 0) { throw "failed to start restore postgres" }
Wait-Postgres -ComposeFile $ComposeRestore -Service postgres-restore -User $env:POSTGRES_USER -Database $RestoreDb

Write-Step "Restoring backup into ${RestoreDb} on port ${RestorePort}..."
cmd /c "docker compose -f docker-compose.restore-test.yml exec -T postgres-restore pg_restore -U $($env:POSTGRES_USER) -d $RestoreDb --no-owner --role=$($env:POSTGRES_USER) < `"$($backupFile.FullName)`""
if ($LASTEXITCODE -ne 0) { throw "pg_restore failed" }

$restoreDatabaseUrl = "postgresql+psycopg://$($env:POSTGRES_USER):$($env:POSTGRES_PASSWORD)@127.0.0.1:${RestorePort}/${RestoreDb}"

Write-Step "Verifying financial integrity on restored database..."
docker compose -f $ComposeProd run --rm --no-deps `
  -e "DATABASE_URL=postgresql+psycopg://$($env:POSTGRES_USER):$($env:POSTGRES_PASSWORD)@postgres-restore:5432/${RestoreDb}" `
  --entrypoint python `
  backend -m scripts.verify_restored_database
if ($LASTEXITCODE -ne 0) { throw "restore verification failed" }

Write-Step "Testing migration compatibility (alembic upgrade head)..."
docker compose -f $ComposeProd run --rm --no-deps `
  -e "DATABASE_URL=postgresql+psycopg://$($env:POSTGRES_USER):$($env:POSTGRES_PASSWORD)@postgres-restore:5432/${RestoreDb}" `
  --entrypoint alembic `
  backend upgrade head
if ($LASTEXITCODE -ne 0) { throw "alembic upgrade head failed on restored database" }

Write-Step "Re-verifying after migrations..."
docker compose -f $ComposeProd run --rm --no-deps `
  -e "DATABASE_URL=postgresql+psycopg://$($env:POSTGRES_USER):$($env:POSTGRES_PASSWORD)@postgres-restore:5432/${RestoreDb}" `
  --entrypoint python `
  backend -m scripts.verify_restored_database --require-head
if ($LASTEXITCODE -ne 0) { throw "post-migration verification failed" }

Write-Step "Cleaning up restore-test stack..."
docker compose -f $ComposeRestore down -v --remove-orphans | Out-Null

Write-Step "Backup file: $($backupFile.FullName)"
Write-Step "Backup and restore drill passed."
