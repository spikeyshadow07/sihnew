@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing_setup
".venv\Scripts\python.exe" run.py
if errorlevel 1 pause
exit /b
:missing_setup
echo Run INSTALL_WINDOWS.bat once before starting NearGuard.
pause
exit /b 1
