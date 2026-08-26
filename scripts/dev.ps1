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
    "verify"
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
  .\scripts\dev.ps1 verify        Full quality gate
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
      docker build -t monetra-frontend:local ./frontend --target production
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
}
