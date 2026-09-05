#!/usr/bin/env bash
cd "$(dirname "$0")"

echo "========================================"
echo "STARTING VEHICLE SURVEILLANCE SYSTEM"
echo "========================================"

# Stop any running instances on ports 5001, 3000, 3001, 5173
lsof -t -i :5001 -i :3000 -i :3001 -i :5173 2>/dev/null | xargs kill -9 2>/dev/null || true

# Start backend server
echo "[1/2] Launching Backend Server (Python Flask)..."
cd backend
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi
cd src
python3 server.py &
BACKEND_PID=$!

# Start frontend dev server
echo "[2/2] Launching Frontend Server (React / Vite)..."
cd ../../frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!

sleep 3

echo ""
echo "========================================"
echo "PROJECT STARTED SUCCESSFULLY!"
echo "Backend API:  http://localhost:5001"
echo "Frontend App: http://localhost:3000 or http://localhost:5173"
echo "========================================"
echo "Opening browser..."

open "http://localhost:3000" 2>/dev/null || open "http://localhost:3001" 2>/dev/null || open "http://localhost:5173" 2>/dev/null || true

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
wait
