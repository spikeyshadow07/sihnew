@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run INSTALL_WINDOWS.bat, then run this file again.
  pause
  exit /b 1
)
echo Installing the AI detector. Internet and several hundred MB are required.
".venv\Scripts\python.exe" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements-ai.txt
if errorlevel 1 goto failed
echo Done. Run START_WINDOWS.bat and select YOLO in Video studio.
echo To try the small experimental fine-tune, run START_EXPERIMENTAL_AI_WINDOWS.bat.
pause
exit /b 0
:failed
echo AI installation did not finish. Keep this error visible.
pause
exit /b 1
