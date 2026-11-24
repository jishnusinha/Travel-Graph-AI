$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Write-Host "This will DELETE local SQLite demo databases under .\data and reseed." -ForegroundColor Yellow
$confirm = Read-Host "Type RESET to continue"
if ($confirm -ne "RESET") {
  Write-Host "Aborted."
  exit 1
}
New-Item -ItemType Directory -Force -Path "$Root\data" | Out-Null
Remove-Item -Force -ErrorAction SilentlyContinue "$Root\data\travelgraph.sqlite", "$Root\data\checkpoints.sqlite", "$Root\data\dev_reset_inbox.jsonl"
$env:PYTHONPATH = "$Root\backend"
& "$Root\.venv\Scripts\python.exe" -m app.db.migrate
& "$Root\.venv\Scripts\python.exe" -m app.seed --reset
Write-Host "Demo database reset and reseeded." -ForegroundColor Green
