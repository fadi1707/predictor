@echo off
setlocal

if not exist .venv\Scripts\activate.bat (
    echo ERROR: Virtual environment not found.
    echo Run scripts\install_win.bat first.
    exit /b 1
)

call .venv\Scripts\activate.bat

if "%WORKER_NAME%"=="" set WORKER_NAME=worker-win

python -m app.worker

endlocal
