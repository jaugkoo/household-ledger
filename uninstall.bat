@echo off
REM Receipt Automation - Uninstall Script
REM This script removes auto-start configuration

echo ========================================
echo Receipt Automation - Uninstall
echo ========================================
echo.

REM Remove from startup folder
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS_FILE=%STARTUP_FOLDER%\ReceiptAutomation.vbs"

if exist "%VBS_FILE%" (
    del "%VBS_FILE%"
    echo Auto-start removed successfully!
) else (
    echo Auto-start file not found.
)

echo.
echo Note: Configuration file (.env) and program files are NOT deleted.
echo To completely remove, manually delete the receipt-automation folder.
echo.
pause
