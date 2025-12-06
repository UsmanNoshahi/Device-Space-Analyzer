@echo off
echo Starting Ultra Disk Space Scanner (v3.0)...
python space_scanner_ultra.py
if errorlevel 1 (
    echo.
    echo ERROR: Failed to run the application
    echo Make sure Python is installed and dependencies are met
    echo Run INSTALL.bat first if you haven't
    pause
)
