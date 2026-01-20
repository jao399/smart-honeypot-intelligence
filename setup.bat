@echo off
REM Smart Honeypot Intelligence - Setup Script
REM Automated setup for distribution package

echo.
echo =====================================
echo Smart Honeypot Intelligence Setup
echo =====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)
echo ✓ Dependencies installed successfully

echo.
echo [2/3] Verifying data files...
if not exist "data\" (
    echo Warning: data folder not found
)
if not exist "snapshots\" (
    echo Warning: snapshots folder not found
)
echo ✓ File verification complete

echo.
echo [3/3] Starting application...
echo.
echo =====================================
echo The app will open at: http://localhost:8501
echo Press Ctrl+C to stop the application
echo =====================================
echo.

streamlit run app.py
pause
