@echo off
echo ========================================
echo Starting Advanced Vehicle Surveillance System - Backend
echo ========================================

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

echo.
echo [1/4] Checking virtual environment...
cd /d "%PROJECT_ROOT%\backend"
if not exist "venv\Scripts\activate.bat" (
    echo WARNING: Virtual environment not found in backend\venv!
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Checking environment file...
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Creating template .env file...
    echo MONGODB_URI=mongodb://localhost:27017/vehicle_surveillance > .env
    echo TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe >> .env
    echo PORT=5001 >> .env
    echo.
)

echo [4/4] Starting backend server...
cd src
echo.
echo Backend server starting on http://localhost:5001
echo Press Ctrl+C to stop the server
echo.
python server.py

pause
