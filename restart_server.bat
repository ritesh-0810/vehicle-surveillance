@echo off
echo ========================================
echo Restarting Server with Optimized Settings
echo ========================================

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

echo.
echo [1/3] Stopping any running server processes...
taskkill /f /im python.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2/3] Activating virtual environment...
cd /d "%PROJECT_ROOT%\backend"
call venv\Scripts\activate.bat

echo [3/3] Starting server...
cd src
echo.
echo Server starting on http://localhost:5001...
echo.
python server.py

pause
