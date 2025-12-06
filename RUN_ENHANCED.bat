@echo off
echo Starting Advanced Disk Space Scanner...
python space_scanner_enhanced.py
if errorlevel 1 (
    echo.
    echo ERROR: Failed to run the application
    echo Make sure Python is installed and dependencies are met
    echo Run INSTALL.bat first if you haven't
    pause
)
