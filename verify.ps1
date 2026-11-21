$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "No virtual environment yet. Running setup.ps1 first."
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "setup.ps1")
}

Write-Host ""
Write-Host "1. Tests"
& $python -m pytest tests -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "2. Three live cases: answer, escalation, block"
& $python -m src.demo
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "3. Full validation file, unattended"
& $python -m evaluation.harness --input "05_Datasets\validation_tickets.json" --output "evaluation\results\validation"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Open evaluation\results\validation\metrics.md"
