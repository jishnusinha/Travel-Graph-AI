# Measure reviewed retrieval cases against the active snapshot.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Write-Host "Retrieval measurement runs inside the app as POST /api/v1/evaluations/retrieval."
Write-Host "Cases whose expected destination is missing are skipped and are not scored as hits."
Write-Host "See docs/TERRA.md. Case file: data/knowledge/manifests/eval_cases.json"
