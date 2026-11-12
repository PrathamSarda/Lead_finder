@echo off
title Company Lead Finder - Setup & Installer
color 0B
echo =======================================================================
echo          COMPANY LEAD FINDER - ONE-CLICK CLIENT INSTALLER
echo =======================================================================
echo.

:: 1. Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is NOT installed on this machine!
    echo.
    echo Please download and install Python 3.11 from:
    echo https://www.python.org/downloads/release/python-3117/
    echo.
    echo IMPORTANT: Make sure to check the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/4] Detected Python installation:
python --version
echo.

:: 2. Create Virtual Environment
echo [2/4] Setting up Python virtual environment (venv)...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)
echo.

:: 3. Upgrade pip and Install dependencies
echo [3/4] Installing Python requirements from requirements.txt...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.

:: 4. Verify Playwright browsers
echo [4/4] Setting up browser dependencies...
playwright install chromium
echo.

echo =======================================================================
echo           INSTALLATION COMPLETED SUCCESSFULLY!
echo =======================================================================
echo You can now double-click 'start_app.bat' to launch the application.
echo.
pause

