$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    throw "Virtual environment not found. Run scripts\install_win.ps1 first."
}

& ".\.venv\Scripts\Activate.ps1"

if (-not $env:APP_HOST) { $env:APP_HOST = "127.0.0.1" }
if (-not $env:APP_PORT) { $env:APP_PORT = "8080" }

python -m uvicorn app.main:app --host $env:APP_HOST --port $env:APP_PORT --reload
