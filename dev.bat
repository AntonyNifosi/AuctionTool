@echo off
echo Starting WoW Housing Price Tracker...

:: Start Backend in a new window
start "WoW Housing Backend" cmd /k "python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

:: Start Frontend in a new window
start "WoW Housing Frontend" cmd /k "cd frontend && npm run dev"

echo Services started!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
