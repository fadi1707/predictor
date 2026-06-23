@echo off
setlocal
call .venv\Scripts\activate.bat
python -m compileall app
python -c "from app.db import init_db; init_db(); print('DB initialized OK')"
echo Smoke test complete.
endlocal
