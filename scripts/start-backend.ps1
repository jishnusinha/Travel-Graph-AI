$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$Root\backend"
Set-Location "$Root\backend"
$Py = "$Root\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "Virtualenv missing. Run .\scripts\setup.ps1 first." }
Write-Host "Starting TravelGraph API on http://127.0.0.1:8000 (docs: /docs)" -ForegroundColor Cyan
& $Py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
