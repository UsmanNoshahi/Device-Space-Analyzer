@echo off
echo ================================================
echo   Disk Space Scanner Pro - Modern UI Edition
echo ================================================
echo.
echo Starting application with modern interface...
echo.
python space_scanner_modern.py
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
