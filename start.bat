@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] virtual environment not found.
    echo Run the following commands first:
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
".venv\Scripts\python.exe" run.py
pause
