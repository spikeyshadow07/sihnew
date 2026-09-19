@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
if exist "datasets\coco128_road_starter\data.yaml" goto train
".venv\Scripts\python.exe" -m training.prepare_starter
if errorlevel 1 goto failed
:train
echo Training a new experimental detector. Results do not replace the app's model.
".venv\Scripts\python.exe" -m training.train_detector --name starter_local
if errorlevel 1 goto failed
echo Completed. See training_runs\starter_local\report.json and nearguard_starter.pt.
pause
exit /b 0
:missing
echo Run INSTALL_WINDOWS.bat and INSTALL_AI_WINDOWS.bat first.
pause
exit /b 1
:failed
echo Training did not finish. Read the error above.
echo If the run folder already exists, use a new --name with the command in TRAINING_GUIDE.md.
pause
exit /b 1
