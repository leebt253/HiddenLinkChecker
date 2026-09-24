@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv. Create it with: python -m venv .venv
    exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 exit /b 1

python scripts\initialize_database.py
if errorlevel 1 (
    echo Database initialization failed. API was not started.
    exit /b 1
)

python -m uvicorn hidden_link_checker_api.main:app --host "127.0.0.1" --port "8000"
