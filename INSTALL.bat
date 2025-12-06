@echo off
echo ============================================
echo  Disk Space Scanner - Installation Script
echo ============================================
echo.

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo.
echo Installing required packages...
echo.

pip install --upgrade pip

echo.
echo Installing optional dependencies...
echo (These enhance functionality but are not required)
echo.

pip install send2trash
pip install matplotlib
pip install reportlab

echo.
echo ============================================
echo  Installation Complete!
echo ============================================
echo.
echo To run the basic version:
echo    python space_scanner.py
echo.
echo To run the enhanced version:
echo    python space_scanner_enhanced.py
echo.
echo Press any key to exit...
pause > nul
