# Rebuild the active snapshot index from the Wikivoyage cache without refetching.
param([string]$Snapshot = "india-v1", [int]$Limit = 0)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
Set-Location (Join-Path $Root "backend")
& $Py -m app.ingestion.cli build --snapshot $Snapshot --limit $Limit
