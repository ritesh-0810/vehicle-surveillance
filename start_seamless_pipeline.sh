#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "========================================"
echo "STARTING SEAMLESS VEHICLE SURVEILLANCE PIPELINE"
echo "========================================"

echo ""
echo "[1/4] Checking Python & Node.js environment..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 could not be found."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "ERROR: node could not be found."
    exit 1
fi

echo ""
echo "[2/4] Setting up backend environment..."
cd "$SCRIPT_DIR/backend"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found. Creating default..."
    echo "MONGODB_URI=mongodb://localhost:27017/vehicle_surveillance" > .env
    echo "PORT=5001" >> .env
fi

echo ""
echo "[3/4] Starting backend server..."
cd "$SCRIPT_DIR/backend/src"
python3 server.py &
BACKEND_PID=$!
echo "Backend server started (PID: $BACKEND_PID) on http://localhost:5001"

echo ""
echo "[4/4] Starting frontend dev server..."
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!
echo "Frontend server started (PID: $FRONTEND_PID)"

echo ""
echo "========================================"
echo "PIPELINE RUNNING SUCCESSFULLY!"
echo "========================================"
echo "Backend API:  http://localhost:5001"
echo "Frontend App: http://localhost:3001 or http://localhost:5173"
echo "Press Ctrl+C to terminate both servers."
echo "========================================"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
wait
