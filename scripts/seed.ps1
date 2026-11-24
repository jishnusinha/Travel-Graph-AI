$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$Root\backend"
& "$Root\.venv\Scripts\python.exe" -m app.seed @args
