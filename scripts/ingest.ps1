# Fetch Wikivoyage extracts and rebuild the snapshot, including vectors when a model is cached.
param(
  [string]$Snapshot = "india-v1",
  [int]$Limit = 0
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "Run scripts/setup.ps1 first." }
Set-Location (Join-Path $Root "backend")
& $Py -m app.ingestion.cli fetch --limit $Limit
& $Py -m app.ingestion.cli build --snapshot $Snapshot --limit $Limit
Write-Host "Snapshot $Snapshot built. If vectors are missing, run .\scripts\prepare-knowledge.ps1."
