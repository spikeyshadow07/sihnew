@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
if not exist "models\nearguard_starter.pt" goto missing
echo Starting the EXPERIMENTAL small-data model. Stop the old server first.
echo This model is not validated for near-miss accuracy.
set "NEARGUARD_MODEL_PATH=%~dp0models\nearguard_starter.pt"
".venv\Scripts\python.exe" run.py
if errorlevel 1 pause
exit /b
:missing
echo Extract the complete release and run INSTALL_WINDOWS.bat and INSTALL_AI_WINDOWS.bat.
pause
exit /b 1
