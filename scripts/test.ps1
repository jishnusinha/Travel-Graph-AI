$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$failed = $false

Write-Host "==> Backend tests" -ForegroundColor Cyan
$env:PYTHONPATH = "$Root\backend"
Push-Location "$Root\backend"
try {
  & "$Root\.venv\Scripts\python.exe" -m pytest -q --tb=short
  if ($LASTEXITCODE -ne 0) { $failed = $true }
} finally {
  Pop-Location
}

Write-Host "==> Frontend unit tests" -ForegroundColor Cyan
Push-Location "$Root\frontend"
try {
  npx vitest run
  if ($LASTEXITCODE -ne 0) { $failed = $true }
  Write-Host "==> Frontend typecheck + build" -ForegroundColor Cyan
  npm run build
  if ($LASTEXITCODE -ne 0) { $failed = $true }
} finally {
  Pop-Location
}

if ($failed) {
  Write-Host "Tests FAILED" -ForegroundColor Red
  exit 1
}
Write-Host "All local checks passed." -ForegroundColor Green
