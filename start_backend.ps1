$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"

if (-not (Test-Path $pythonPath)) {
    throw "No se encontro Python en: $pythonPath"
}

Set-Location $projectRoot
$env:DATABASE_URL = "sqlite:///hotel_aurora.db"

Write-Host "Iniciando backend con SQLite local..." -ForegroundColor Cyan
Write-Host "URL: http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detenerlo." -ForegroundColor Yellow

& $pythonPath run_server.py
