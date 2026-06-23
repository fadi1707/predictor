@echo off
setlocal

echo [AI Ops Assistant v7.1] Installing for Windows...

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found in PATH.
    echo Install Python 3.11+ and enable "Add python.exe to PATH".
    exit /b 1
)

python -m venv .venv
if errorlevel 1 exit /b 1

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

if not exist workspace mkdir workspace
if not exist workspace\.rollbacks mkdir workspace\.rollbacks
if not exist data mkdir data
if not exist config mkdir config
if not exist workspace\demo.txt type nul > workspace\demo.txt

echo.
echo Installed successfully.
echo Run with: scripts\run_win.bat
endlocal
