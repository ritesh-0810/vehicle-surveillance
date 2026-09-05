@echo off
echo ========================================
echo Starting Frontend Development Server
echo ========================================

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

echo.
echo [1/3] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo [2/3] Checking dependencies...
cd /d "%PROJECT_ROOT%\frontend"
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo [3/3] Starting frontend server...
echo.
echo Frontend server starting on http://localhost:5173
echo Press Ctrl+C to stop the server
echo.
npm run dev

pause
