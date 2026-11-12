@echo off
title Company Lead Finder - Production Server
color 0A
echo =======================================================================
echo               LAUNCHING COMPANY LEAD FINDER APPLICATION
echo =======================================================================
echo.

:: Activate Python virtual environment if it exists, otherwise use system Python
if exist "venv\Scripts\activate.bat" (
    echo Activating Python virtual environment...
    call venv\Scripts\activate.bat
)

echo Starting backend server on http://127.0.0.1:8000 ...
start "Company Lead Finder Backend" python run_backend.py

:: Give backend 2 seconds to boot
timeout /t 2 /nobreak >nul

:: Open browser automatically
echo Opening dashboard in your default browser...
start http://localhost:5173

echo.
echo Application is running!
echo Keep this window open while using the platform.
echo Press any key to stop the server when done.
pause >nul

:: Terminate running server on exit
taskkill /F /IM python.exe /T >nul 2>&1

