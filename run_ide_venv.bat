@echo off
REM Run Py-IDE with virtual environment
echo Starting Py-IDE with venv...

REM Activate venv and run
call .venv\Scripts\activate.bat
python run_ide.py

pause
