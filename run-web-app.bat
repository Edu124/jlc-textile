@echo off
REM ── JLC Textile Manager — local web app launcher ─────────────────────────
REM Starts the backend (FastAPI on :8800) and frontend (Vite on :5173),
REM then opens the app in your browser. Close the two terminal windows to stop.
cd /d "%~dp0"

echo Starting JLC backend on http://localhost:8800 ...
start "JLC Backend" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python.exe -m uvicorn app.main:app --port 8800 --reload"

echo Starting JLC frontend on http://localhost:5173 ...
start "JLC Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev -- --port 5173"

echo Waiting for the app to come up ...
timeout /t 6 /nobreak >nul
start "" http://localhost:5173

echo.
echo JLC is running. Open http://localhost:5173 in your browser.
echo (Two terminal windows opened - close them to stop the app.)
