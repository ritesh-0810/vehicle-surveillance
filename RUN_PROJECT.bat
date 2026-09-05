@echo off
echo ========================================
echo STARTING VEHICLE SURVEILLANCE SYSTEM
echo ========================================

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

echo Starting Backend Server on http://localhost:5001...
start "Backend Server" cmd /k "cd /d "%PROJECT_ROOT%\backend" && call venv\Scripts\activate.bat && cd src && python server.py"

echo Starting Frontend Dev Server...
start "Frontend Server" cmd /k "cd /d "%PROJECT_ROOT%\frontend" && npm run dev"

timeout /t 4 /nobreak >nul
start http://localhost:3000
