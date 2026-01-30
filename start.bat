@echo off
REM Receipt Automation - Windows Startup Script
REM This script runs the receipt automation in the background

cd /d "%~dp0"

REM Check if .env file exists
if not exist ".env" (
    echo First time setup required...
    echo Starting setup wizard...
    python setup_wizard.py
    if errorlevel 1 (
        echo Setup failed or cancelled.
        pause
        exit /b 1
    )
)

REM Start the main program in background (hidden window)
echo Starting Receipt Automation...
start /B pythonw main.py

echo Receipt Automation is now running in the background.
echo Check the log file for details.
timeout /t 3 /nobreak >nul
