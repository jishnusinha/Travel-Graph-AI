# Measure reviewed retrieval cases against the active snapshot.
param(
  [string[]]$Strategy = @("keyword", "dense", "hybrid", "hybrid_rerank", "graph_hybrid")
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  throw "Run scripts/setup.ps1 first so the virtualenv exists."
}

$env:PYTHONPATH = Join-Path $Root "backend"
Set-Location (Join-Path $Root "backend")

$argsList = @("-m", "app.ingestion.cli", "evaluate")
foreach ($item in $Strategy) {
  $argsList += @("--strategy", $item)
}
Write-Host "Evaluating $($Strategy -join ', ') against data/knowledge/manifests/eval_cases.json"
& $Py @argsList
if ($LASTEXITCODE -ne 0) { throw "evaluate failed" }
