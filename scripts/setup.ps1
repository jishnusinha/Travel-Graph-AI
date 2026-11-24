# TravelGraph AI — Windows setup
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> TravelGraph AI setup" -ForegroundColor Cyan

function Assert-Cmd($Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name is required but was not found on PATH."
  }
}

Assert-Cmd python
Assert-Cmd npm
python --version
npm --version

if (-not (Test-Path "$Root\.venv")) {
  Write-Host "Creating Python virtualenv..."
  python -m venv "$Root\.venv"
}

$Py = "$Root\.venv\Scripts\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install -r "$Root\backend\requirements.txt"

Write-Host "Installing frontend dependencies..."
Push-Location "$Root\frontend"
npm install
Pop-Location

New-Item -ItemType Directory -Force -Path "$Root\data" | Out-Null

if (-not (Test-Path "$Root\.env")) {
  Copy-Item "$Root\.env.example" "$Root\.env"
  Write-Host "Created .env from .env.example"
} else {
  Write-Host ".env already exists — left unchanged"
}

$env:PYTHONPATH = "$Root\backend"
Write-Host "Running migrations (create_all) + seed..."
& $Py -m app.db.migrate
& $Py -m app.seed

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Demo login: demo@travelgraph.local / TravelGraphDemo!2026"
Write-Host "Next: .\scripts\dev.ps1   or start backend + frontend separately"
