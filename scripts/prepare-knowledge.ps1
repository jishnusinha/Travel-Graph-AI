# Download local models and rebuild the travel snapshot from the cached sources.
param(
  [string]$Snapshot = "india-v1"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  throw "Run scripts/setup.ps1 first so the virtualenv exists."
}

& $Py -m pip install -r (Join-Path $Root "backend\requirements.txt")
$env:PYTHONPATH = Join-Path $Root "backend"
Set-Location (Join-Path $Root "backend")

Write-Host "Preparing local embedding and cross-encoder models..."
& $Py -m app.ingestion.cli prepare-models
if ($LASTEXITCODE -ne 0) { throw "Model preparation failed." }

Write-Host "Reading cached Wikivoyage pages (network is used only for titles that are not cached)..."
& $Py -m app.ingestion.cli fetch --limit 0
if ($LASTEXITCODE -ne 0) { throw "Source fetch failed." }

Write-Host "Rebuilding snapshot $Snapshot with dense vectors..."
& $Py -m app.ingestion.cli build --snapshot $Snapshot --limit 0
if ($LASTEXITCODE -ne 0) { throw "Snapshot build failed." }

Write-Host "Verifying keyword, dense, hybrid and reranked retrieval..."
& $Py -m app.ingestion.cli verify-retrieval
if ($LASTEXITCODE -ne 0) { throw "Retrieval verification failed." }

Write-Host "Knowledge snapshot is ready for offline hybrid retrieval." -ForegroundColor Green
