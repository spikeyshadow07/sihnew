@echo off
setlocal
cd /d "%~dp0"
echo NearGuard - installing Python dependencies
echo Internet is needed for this first setup. Python 3.12 is recommended.
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>&1
if errorlevel 1 goto use_python
py -3 -m venv .venv
if errorlevel 1 goto failed
goto install
:use_python
where python >nul 2>&1
if errorlevel 1 goto missing_python
python -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Setup complete. Double-click START_WINDOWS.bat.
pause
exit /b 0
:missing_python
echo Install Python 3.12 from python.org and enable Add Python to PATH.
echo Then run this installer again.
pause
exit /b 1
:failed
echo.
echo Setup did not finish. Read the error above; do not close this window yet.
pause
exit /b 1
