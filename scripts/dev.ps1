#Requires -Version 5.1
<#
.SYNOPSIS
  Monetra development helper scripts for Windows PowerShell.
#>

param(
  [Parameter(Position = 0)]
  [ValidateSet(
    "help",
    "install",
    "up",
    "down",
    "lint",
    "typecheck",
    "test",
    "build",
    "docker-build",
    "prod-build",
    "prod-up",
    "prod-down",
    "prod-verify",
    "verify",
    "loadtest"
  )]
  [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Invoke-InDirectory {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [Parameter(Mandatory = $true)]
    [scriptblock]$Action
  )
  Push-Location $Path
  try {
    & $Action
    if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
      throw "Command failed with exit code $LASTEXITCODE"
    }
  } finally {
    Pop-Location
  }
}

switch ($Command) {
  "help" {
    Write-Host @"
Monetra development commands
  .\scripts\dev.ps1 install       Install dependencies
  .\scripts\dev.ps1 up            Start Docker Compose
  .\scripts\dev.ps1 down          Stop Docker Compose
  .\scripts\dev.ps1 lint          Lint backend and frontend
  .\scripts\dev.ps1 typecheck     Type-check backend and frontend
  .\scripts\dev.ps1 test          Run unit tests
  .\scripts\dev.ps1 build         Build frontend
  .\scripts\dev.ps1 docker-build  Build Docker images
  .\scripts\dev.ps1 prod-build    Build production Docker images
  .\scripts\dev.ps1 prod-up       Start production Compose stack
  .\scripts\dev.ps1 prod-down     Stop production Compose stack
  .\scripts\dev.ps1 prod-verify   Build and smoke-test production stack
  .\scripts\dev.ps1 verify        Full quality gate
  .\scripts\dev.ps1 loadtest      Run API load tests (local stack)
"@
  }
  "install" {
    Invoke-InDirectory (Join-Path $Root "backend") {
      python -m pip install -e ".[dev]"
    }
    Invoke-InDirectory (Join-Path $Root "frontend") {
      npm install
    }
  }
  "up" {
    Invoke-InDirectory $Root { docker compose up --build -d }
  }
  "down" {
    Invoke-InDirectory $Root { docker compose down }
  }
  "lint" {
    Invoke-InDirectory (Join-Path $Root "backend") {
      ruff check app tests
      ruff format --check app tests
    }
    Invoke-InDirectory (Join-Path $Root "frontend") {
      npm run lint
      npm run format:check
    }
  }
  "typecheck" {
    Invoke-InDirectory (Join-Path $Root "backend") { mypy app }
    Invoke-InDirectory (Join-Path $Root "frontend") { npm run typecheck }
  }
  "test" {
    Invoke-InDirectory (Join-Path $Root "backend") { pytest }
    Invoke-InDirectory (Join-Path $Root "frontend") { npm run test }
  }
  "build" {
    Invoke-InDirectory (Join-Path $Root "frontend") { npm run build }
  }
  "docker-build" {
    Invoke-InDirectory $Root {
      docker compose build
      docker compose -f docker-compose.prod.yml build
    }
  }
  "prod-build" {
    Invoke-InDirectory $Root {
      docker compose -f docker-compose.prod.yml build
    }
  }
  "prod-up" {
    & (Join-Path $PSScriptRoot "generate-local-tls-certs.ps1")
    Invoke-InDirectory $Root {
      docker compose -f docker-compose.prod.yml up --build -d
    }
  }
  "prod-down" {
    Invoke-InDirectory $Root {
      docker compose -f docker-compose.prod.yml down
    }
  }
  "prod-verify" {
    & (Join-Path $PSScriptRoot "generate-local-tls-certs.ps1")
    Invoke-InDirectory $Root {
      if (-not $env:JWT_SECRET_KEY) {
        $env:JWT_SECRET_KEY = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
      }
      if (-not $env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD = "monetra" }
      if (-not $env:POSTGRES_DB) { $env:POSTGRES_DB = "monetra" }
      if (-not $env:POSTGRES_USER) { $env:POSTGRES_USER = "monetra" }
      $prevErrorAction = $ErrorActionPreference
      $ErrorActionPreference = "Continue"
      try {
        docker compose down 2>&1 | Out-Null
        docker compose -f docker-compose.prod.yml down 2>&1 | Out-Null
      } finally {
        $ErrorActionPreference = $prevErrorAction
      }
      if ($LASTEXITCODE -ne 0) {
        throw "docker compose down failed with exit code $LASTEXITCODE"
      }
      docker compose -f docker-compose.prod.yml up --build -d
      $deadline = (Get-Date).AddMinutes(5)
      do {
        Start-Sleep -Seconds 5
        $ps = docker compose -f docker-compose.prod.yml ps --format json | ConvertFrom-Json
        $healthy = @($ps | Where-Object { $_.Health -eq "healthy" }).Count
        $total = @($ps | Where-Object { $_.Health }).Count
        if ($healthy -ge 4 -and $total -ge 4) { break }
      } while ((Get-Date) -lt $deadline)
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
      }

      Assert-CurlStatus -CurlArgs @("http://localhost/nginx-health") -Expected "200" -Name "nginx-health"
      Assert-CurlStatus -CurlArgs @("-k", "https://localhost/health") -Expected "200" -Name "/health"
      Assert-CurlStatus -CurlArgs @("-k", "https://localhost/ready") -Expected "200" -Name "/ready"
      Assert-CurlStatus -CurlArgs @("-k", "https://localhost/") -Expected "200" -Name "frontend"
      Assert-CurlStatus -CurlArgs @("-k", "https://localhost/api/v1/users/me") -Expected "401" -Name "protected API"
      Assert-CurlStatus -CurlArgs @("http://localhost/health") -Expected "301" -Name "HTTP to HTTPS redirect"

      Write-Host "Production stack smoke checks passed."
    }
  }
  "verify" {
    & $PSCommandPath lint
    & $PSCommandPath typecheck
    & $PSCommandPath test
    & $PSCommandPath build
    & $PSCommandPath docker-build
    Write-Host "Verification complete."
  }
  "loadtest" {
    Invoke-InDirectory (Join-Path $Root "backend") {
      python -m loadtest --quick-seed @args
    }
  }
}
