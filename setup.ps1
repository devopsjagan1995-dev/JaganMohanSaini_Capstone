$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

function Test-ProjectPython {
    if (-not (Test-Path $python)) {
        return $false
    }
    & $python -c "import fastapi, pytest, fpdf" 2>$null
    return ($LASTEXITCODE -eq 0)
}

if (-not (Test-ProjectPython)) {
    Write-Host "Creating .venv in this folder..."
    if (Test-Path (Join-Path $PSScriptRoot ".venv")) {
        Remove-Item -Recurse -Force (Join-Path $PSScriptRoot ".venv")
    }
    py -3 -m venv (Join-Path $PSScriptRoot ".venv")
    & $python -m pip install --upgrade pip
    & $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
}

Write-Host "Ready: $python"
& $python -c "import sys; print(sys.version)"
