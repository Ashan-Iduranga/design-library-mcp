# Start the Design Library gallery and open it in your browser.
# Usage: in PowerShell run  .\start.ps1   (or double-click start.cmd, which needs no PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "First run: creating .venv and installing dependencies..."
    python -m uv sync
}

& $python -m designlib serve --open
