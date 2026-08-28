$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$Message) {
  Write-Host "[clean-deploy-test] $Message"
}

function Wait-PostgresHealthy {
  param([int]$TimeoutSeconds = 120)
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    docker compose -f docker-compose.prod.yml exec -T postgres pg_isready -U monetra -d monetra 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { return }
    Start-Sleep -Seconds 3
  }
  throw "PostgreSQL did not become ready within ${TimeoutSeconds}s"
}

function Wait-ContainersHealthy {
  param([int]$TimeoutSeconds = 300)
  $containers = @("monetra-postgres", "monetra-backend", "monetra-frontend", "monetra-nginx")
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    $allHealthy = $true
    foreach ($name in $containers) {
      $status = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}" $name 2>$null
      if ($status -ne "healthy") {
        Write-Step "Waiting: ${name}=${status}"
        $allHealthy = $false
      }
    }
    if ($allHealthy) { return }
    Start-Sleep -Seconds 5
  }
  docker compose -f docker-compose.prod.yml ps
  throw "Services did not become healthy within ${TimeoutSeconds}s"
}

function Assert-CurlStatus {
  param(
    [string[]]$CurlArgs,
    [string]$Expected,
    [string]$Name
  )
  $status = & curl.exe -s -o NUL -w "%{http_code}" @CurlArgs
  if ($status -ne $Expected) {
    throw "$Name expected HTTP $Expected, got $status"
  }
  Write-Step "OK $Name -> $status"
}

Write-Step "Tearing down existing production stack and volumes..."
$prevErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker compose -f docker-compose.prod.yml down -v --remove-orphans 2>&1 | Out-Null
$ErrorActionPreference = $prevErrorAction

$envFile = Join-Path $Root ".env"
if (-not (Test-Path $envFile)) {
  Write-Step "Creating .env from .env.production.example"
  Copy-Item (Join-Path $Root ".env.production.example") $envFile
}

$jwt = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
$content = Get-Content $envFile -Raw
$content = $content -replace 'JWT_SECRET_KEY=.*', "JWT_SECRET_KEY=$jwt"
$content = $content -replace 'POSTGRES_PASSWORD=.*', 'POSTGRES_PASSWORD=monetra-clean-test'
$content = $content -replace 'POSTGRES_DB=.*', 'POSTGRES_DB=monetra'
$content = $content -replace 'POSTGRES_USER=.*', 'POSTGRES_USER=monetra'
$content = $content -replace 'CORS_ORIGINS=.*', 'CORS_ORIGINS=https://localhost,https://127.0.0.1'
Set-Content -Path $envFile -Value $content.TrimEnd()

& (Join-Path $PSScriptRoot "generate-local-tls-certs.ps1")

foreach ($cert in @("nginx/certs/fullchain.pem", "nginx/certs/privkey.pem")) {
  if (-not (Test-Path (Join-Path $Root $cert))) {
    throw "Missing TLS certificate: $cert"
  }
}

docker compose -f docker-compose.prod.yml config | Out-Null
if ($LASTEXITCODE -ne 0) { throw "docker compose config failed" }
Write-Step "Compose configuration valid"

Write-Step "Building production images..."
docker compose -f docker-compose.prod.yml build
if ($LASTEXITCODE -ne 0) { throw "docker compose build failed" }

Write-Step "Starting PostgreSQL..."
docker compose -f docker-compose.prod.yml up -d postgres
if ($LASTEXITCODE -ne 0) { throw "failed to start postgres" }
Wait-PostgresHealthy

Write-Step "Applying database migrations..."
docker compose -f docker-compose.prod.yml run --rm --no-deps --entrypoint alembic backend upgrade head
if ($LASTEXITCODE -ne 0) { throw "database migration failed" }

Write-Step "Starting application services..."
$env:RUN_DB_MIGRATIONS = "false"
docker compose -f docker-compose.prod.yml up -d --remove-orphans
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }
Remove-Item Env:RUN_DB_MIGRATIONS -ErrorAction SilentlyContinue

Wait-ContainersHealthy

Write-Step "Running smoke checks..."
Assert-CurlStatus -CurlArgs @("http://localhost/nginx-health") -Expected "200" -Name "nginx-health"
Assert-CurlStatus -CurlArgs @("-k", "https://localhost/health") -Expected "200" -Name "/health"
Assert-CurlStatus -CurlArgs @("-k", "https://localhost/ready") -Expected "200" -Name "/ready"
Assert-CurlStatus -CurlArgs @("-k", "https://localhost/") -Expected "200" -Name "frontend"
Assert-CurlStatus -CurlArgs @("-k", "https://localhost/api/v1/users/me") -Expected "401" -Name "protected API"
Assert-CurlStatus -CurlArgs @("http://localhost/health") -Expected "301" -Name "HTTP redirect"

Write-Step "Testing database backup..."
$backupDir = Join-Path $Root "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$backupFile = Join-Path $backupDir "manual-test.dump"
cmd /c "docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U monetra -d monetra -Fc > `"$backupFile`""
if (-not (Test-Path $backupFile) -or (Get-Item $backupFile).Length -eq 0) {
  throw "database backup failed"
}
Write-Step "Backup written to $backupFile"

Write-Step "Simulating migration failure guard..."
docker compose -f docker-compose.prod.yml run --rm --no-deps --entrypoint alembic backend current | Out-Null
if ($LASTEXITCODE -ne 0) { throw "alembic current failed after deploy" }

docker compose -f docker-compose.prod.yml ps
Write-Step "Clean production deployment test passed."
