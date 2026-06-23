@echo off
setlocal

if not exist .venv\Scripts\activate.bat (
    echo ERROR: Virtual environment not found.
    echo Run scripts\install_win.bat first.
    exit /b 1
)

call .venv\Scripts\activate.bat

set APP_HOST=127.0.0.1
if "%APP_PORT%"=="" set APP_PORT=8080

python -m uvicorn app.main:app --host %APP_HOST% --port %APP_PORT% --reload

endlocal
