$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    throw "Virtual environment not found. Run scripts\install_win.ps1 first."
}

& ".\.venv\Scripts\Activate.ps1"

if (-not $env:WORKER_NAME) { $env:WORKER_NAME = "worker-win" }

python -m app.worker
