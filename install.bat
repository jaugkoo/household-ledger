@echo off
REM Receipt Automation - Installation Script
REM This script sets up auto-start on Windows

echo ========================================
echo Receipt Automation - Auto-Start Setup
echo ========================================
echo.

cd /d "%~dp0"

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo     Dependencies installed successfully!
echo.

REM Run setup wizard if .env doesn't exist
if not exist ".env" (
    echo [2/4] Running initial setup wizard...
    python setup_wizard.py
    if errorlevel 1 (
        echo ERROR: Setup wizard failed or cancelled
        pause
        exit /b 1
    )
    echo     Configuration saved!
    echo.
) else (
    echo [2/4] Configuration file found, skipping setup wizard
    echo.
)

echo [3/4] Setting up auto-start...

REM Get startup folder path
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

REM Create VBS script for silent startup
set "VBS_FILE=%STARTUP_FOLDER%\ReceiptAutomation.vbs"
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.Run """%~dp0start.bat""", 0, False
) > "%VBS_FILE%"

if exist "%VBS_FILE%" (
    echo     Auto-start configured successfully!
    echo     Location: %VBS_FILE%
) else (
    echo     WARNING: Could not create auto-start file
)
echo.

echo [4/4] Testing configuration...
python -c "from notion_validator import NotionValidator; print('Import test passed')" 2>nul
if errorlevel 1 (
    echo     WARNING: Module import test failed
) else (
    echo     Configuration test passed!
)
echo.

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo The program will now start automatically when Windows starts.
echo.
echo To start now, run: start.bat
echo To stop, use Task Manager to end the Python process.
echo.
pause
