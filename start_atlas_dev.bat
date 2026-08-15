@echo off
echo ========================================================
echo  Starting Atlas Canonical Development Environment
echo ========================================================
echo.
set "WORKTREE_DIR=C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter"
cd /d "%WORKTREE_DIR%"

echo [1/2] Checking & Starting Backend API (127.0.0.1:8000)...
node scripts/check-backend-port.js
start /b uv run python -m uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000 > NUL 2>&1

echo [2/2] Checking & Starting Frontend Server (0.0.0.0:5173)...
start /b npm --prefix apps/landing run dev > NUL 2>&1

echo.
echo ========================================================
echo  Atlas is running!
echo  Frontend: http://localhost:5173/dashboard/evaluations/new
echo  Backend:  http://127.0.0.1:8000
echo ========================================================
