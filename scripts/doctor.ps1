# Report whether this machine can run the offline Terra demo.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$issues = @()

Write-Host "==> Terra / TravelGraph doctor" -ForegroundColor Cyan

function Ok($msg) { Write-Host "  OK  $msg" -ForegroundColor Green }
function Bad($msg) { Write-Host "  !!  $msg" -ForegroundColor Yellow; $script:issues += $msg }

if (Get-Command python -ErrorAction SilentlyContinue) { Ok "python on PATH" } else { Bad "python missing from PATH" }
if (Get-Command npm -ErrorAction SilentlyContinue) { Ok "npm on PATH" } else { Bad "npm missing from PATH" }
if (Test-Path $Py) { Ok "venv python at $Py" } else { Bad "venv missing — run scripts/setup.ps1" }
if (Test-Path (Join-Path $Root ".env")) { Ok ".env present" } else { Bad ".env missing — copy .env.example" }
if (Test-Path (Join-Path $Root "frontend\node_modules")) { Ok "frontend node_modules installed" } else { Bad "frontend deps missing — run npm install in frontend/" }

$knowledge = Join-Path $Root "data\knowledge"
$modelManifest = Join-Path $knowledge "models\terra-model-manifest.json"
$vectors = Join-Path $knowledge "indexes\india-v1\vectors.npz"
$wikiCache = Join-Path $knowledge "raw\wikivoyage"
$assets = Join-Path $knowledge "assets"

if (Test-Path $modelManifest) { Ok "model manifest present" } else { Bad "models not prepared — run scripts/prepare-knowledge.ps1" }
if (Test-Path $vectors) { Ok "india-v1 dense vectors present" } else { Bad "india-v1 vectors missing — run prepare-knowledge or build" }
if (Test-Path $wikiCache) {
  $n = (Get-ChildItem $wikiCache -Filter *.json -ErrorAction SilentlyContinue | Measure-Object).Count
  Ok "wikivoyage cache files: $n"
} else {
  Bad "wikivoyage cache directory missing"
}
if (Test-Path $assets) {
  $imgs = (Get-ChildItem $assets -Recurse -Include *.jpg,*.jpeg,*.png -ErrorAction SilentlyContinue | Measure-Object).Count
  Ok "local commons assets: $imgs"
} else {
  Bad "knowledge assets folder missing"
}

$db = Join-Path $Root "data\travelgraph.sqlite"
if (Test-Path $db) { Ok "SQLite database present" } else { Bad "database missing — run setup/migrate/seed" }

if (Test-Path $Py) {
  $env:PYTHONPATH = Join-Path $Root "backend"
  Push-Location (Join-Path $Root "backend")
  try {
    & $Py -c @"
from app.rag.store import corpus_stats
s = corpus_stats()
print(s.get('status'), s.get('snapshot_id'), 'docs', s.get('documents'), 'chunks', s.get('chunks'), 'images', s.get('images'), 'embed', s.get('embedding_kind'))
"@
    if ($LASTEXITCODE -eq 0) { Ok "corpus_stats readable" } else { Bad "corpus_stats failed" }
  } catch {
    Bad "could not import app.rag.store — check PYTHONPATH and deps"
  }
  Pop-Location
}

$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
$port5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($port8000) { Ok "API listening on :8000" } else { Write-Host "  --  API not listening on :8000 (start with scripts/start-backend.ps1)" -ForegroundColor DarkGray }
if ($port5173) { Ok "Vite listening on :5173" } else { Write-Host "  --  frontend not listening on :5173 (start with scripts/start-frontend.ps1)" -ForegroundColor DarkGray }

Write-Host ""
if ($issues.Count -eq 0) {
  Write-Host "Doctor found no blocking issues for the offline demo." -ForegroundColor Green
  exit 0
}
Write-Host "Doctor found $($issues.Count) issue(s):" -ForegroundColor Yellow
$issues | ForEach-Object { Write-Host " - $_" }
exit 1
