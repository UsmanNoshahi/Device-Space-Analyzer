@echo off
echo ================================================
echo   Disk Space Scanner Pro - Fluent Design
echo ================================================
echo.
echo Starting application with Microsoft Fluent UI...
echo.
python space_scanner_fluent.py
if errorlevel 1 (
    echo.
    echo ERROR: Failed to run the application
    echo.
    echo Make sure:
    echo - Python 3.6+ is installed
    echo - Run INSTALL.bat to install dependencies
    echo.
    pause
)
