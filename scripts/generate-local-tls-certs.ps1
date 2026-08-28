$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$CertDir = Join-Path $Root "nginx\certs"
New-Item -ItemType Directory -Force -Path $CertDir | Out-Null

$fullchain = Join-Path $CertDir "fullchain.pem"
$privkey = Join-Path $CertDir "privkey.pem"

if ((Test-Path $fullchain) -and (Test-Path $privkey)) {
    Write-Host "TLS certificates already exist in nginx/certs"
    exit 0
}

if (Get-Command openssl -ErrorAction SilentlyContinue) {
    openssl req -x509 -nodes -newkey rsa:4096 `
        -keyout $privkey `
        -out $fullchain `
        -days 365 `
        -subj "/CN=localhost/O=Monetra Local Production/C=US"
    Write-Host "Generated self-signed TLS certificates in nginx/certs (openssl)"
    exit 0
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Neither openssl nor docker is available to generate local TLS certificates."
}

docker run --rm `
    -v "${CertDir}:/certs" `
    alpine/openssl req -x509 -nodes -newkey rsa:4096 `
    -keyout /certs/privkey.pem `
    -out /certs/fullchain.pem `
    -days 365 `
    -subj "/CN=localhost/O=Monetra Local Production/C=US"

Write-Host "Generated self-signed TLS certificates in nginx/certs (docker openssl)"
