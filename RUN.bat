@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto failed
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Splatt2 could not start. Install Python 3.12 and check the error above.
echo To repair dependencies run UPDATE.bat. Logs: %%APPDATA%%\Splatt2
pause
exit /b 1
