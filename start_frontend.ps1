$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendRoot = Join-Path $projectRoot "frontend-hotel-main"
$pythonPath = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$port = 5500

if (-not (Test-Path $pythonPath)) {
    throw "No se encontro Python en: $pythonPath"
}

if (-not (Test-Path $frontendRoot)) {
    throw "No se encontro la carpeta del frontend en: $frontendRoot"
}

Set-Location $frontendRoot

Write-Host "Sirviendo frontend de Hotel Aurora..." -ForegroundColor Cyan
Write-Host "URL: http://127.0.0.1:$port/index.html" -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detenerlo." -ForegroundColor Yellow

& $pythonPath -m http.server $port --bind 127.0.0.1
