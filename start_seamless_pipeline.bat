@echo off
echo ========================================
echo STARTING SEAMLESS VEHICLE SURVEILLANCE PIPELINE
echo ========================================

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

echo.
echo [1/5] Checking system requirements...
echo - Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

echo - Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found! Please install Node.js 16+
    pause
    exit /b 1
)

echo.
echo [2/5] Setting up backend environment...
cd /d "%PROJECT_ROOT%\backend"

echo - Checking virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo WARNING: Virtual environment not found in backend\venv!
    echo Attempting to create virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo - Installing backend dependencies...
    call venv\Scripts\activate.bat
    if exist "requirements.txt" pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo - Checking environment file...
if not exist ".env" (
    echo WARNING: .env file not found! Creating default...
    echo MONGODB_URI=mongodb://localhost:27017/vehicle_surveillance > .env
    echo TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe >> .env
    echo PORT=5001 >> .env
    echo.
    echo Please edit backend\.env file with your MongoDB connection string if needed.
)

echo.
echo [3/5] Starting backend server...
echo [INFO] Backend server starting on http://localhost:5001

REM Create temporary batch file for backend
echo @echo off > "%PROJECT_ROOT%\temp_backend.bat"
echo cd /d "%PROJECT_ROOT%\backend" >> "%PROJECT_ROOT%\temp_backend.bat"
echo call venv\Scripts\activate.bat >> "%PROJECT_ROOT%\temp_backend.bat"
echo cd src >> "%PROJECT_ROOT%\temp_backend.bat"
echo python server.py >> "%PROJECT_ROOT%\temp_backend.bat"
echo pause >> "%PROJECT_ROOT%\temp_backend.bat"

start "Backend Server (Port 5001)" cmd /k "%PROJECT_ROOT%\temp_backend.bat"

echo.
echo [4/5] Starting frontend server...
cd /d "%PROJECT_ROOT%\frontend"

echo - Installing frontend dependencies (if needed)...
if not exist "node_modules" (
    echo Installing frontend dependencies...
    npm install
    if errorlevel 1 (
        echo ERROR: Failed to install frontend dependencies!
        pause
        exit /b 1
    )
)

echo - Starting frontend development server (Vite)...
echo [INFO] Frontend dev server starting...

REM Create temporary batch file for frontend dev server
echo @echo off > "%PROJECT_ROOT%\temp_frontend_dev.bat"
echo cd /d "%PROJECT_ROOT%\frontend" >> "%PROJECT_ROOT%\temp_frontend_dev.bat"
echo npm run dev >> "%PROJECT_ROOT%\temp_frontend_dev.bat"
echo pause >> "%PROJECT_ROOT%\temp_frontend_dev.bat"

start "Frontend Dev Server" cmd /k "%PROJECT_ROOT%\temp_frontend_dev.bat"

echo.
echo ========================================
echo PIPELINE STARTED SUCCESSFULLY!
echo ========================================
echo.
echo Backend API Server:  http://localhost:5001
echo Frontend Dev Server: http://localhost:5173 (or 3000/3001)
echo.
echo The pipeline is now running:
echo 1. Upload videos through the web interface
echo 2. Automatic license plate detection and extraction
echo 3. Real-time progress tracking
echo 4. Results stored in MongoDB database
echo.
echo Both servers are running in separate console windows.
echo Close those windows to stop the servers.
echo.
echo Cleaning up temporary launcher files...
timeout /t 5 /nobreak >nul
del "%PROJECT_ROOT%\temp_backend.bat" 2>nul
del "%PROJECT_ROOT%\temp_frontend_dev.bat" 2>nul
echo.
pause