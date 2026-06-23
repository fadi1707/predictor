$ErrorActionPreference = "Stop"

Write-Host "[AI Ops Assistant v7.1] Installing for Windows..."

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python was not found in PATH. Install Python 3.11+ and enable Add python.exe to PATH."
}

python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"

python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

New-Item -ItemType Directory -Force -Path workspace | Out-Null
New-Item -ItemType Directory -Force -Path workspace\.rollbacks | Out-Null
New-Item -ItemType Directory -Force -Path data | Out-Null
New-Item -ItemType Directory -Force -Path config | Out-Null

if (-not (Test-Path "workspace\demo.txt")) {
    New-Item -ItemType File -Path "workspace\demo.txt" | Out-Null
}

Write-Host "Installed successfully."
Write-Host "Run with: powershell -ExecutionPolicy Bypass -File scripts\run_win.ps1"
