@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo  Atlas Canonical Development Environment Startup
echo ========================================================
echo.

set "WORKTREE_DIR=C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter"
cd /d "%WORKTREE_DIR%"

echo [GUARD] Verifying canonical worktree...
if not exist "%WORKTREE_DIR%\apps\backend\main.py" (
    echo [ERROR] Canonical backend not found in %WORKTREE_DIR%
    echo [ERROR] Do NOT run Atlas from a different worktree.
    exit /b 1
)
echo [OK] Canonical worktree confirmed: %WORKTREE_DIR%
echo.

echo [1/3] Running backend port 8000 security guard...
node scripts\check-backend-port.js
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Backend port guard failed. Aborting startup.
    exit /b 1
)

echo [2/3] Running frontend port 5173 security guard...
node apps\landing\scripts\check-port.js
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Frontend port guard failed. Aborting startup.
    exit /b 1
)

echo.
echo [3/3] Starting Atlas services...

REM Set canonical environment variables with absolute paths.
set "DATABASE_URL=sqlite:///%WORKTREE_DIR:\=/%/atlas_dev.db"
set "PYTHONPATH=%WORKTREE_DIR%\packages\database;%WORKTREE_DIR%\packages;%WORKTREE_DIR%\services;%WORKTREE_DIR%"
set "CELERY_TASK_ALWAYS_EAGER=true"

echo   DATABASE_URL = %DATABASE_URL%
echo   PYTHONPATH   = %PYTHONPATH:~0,80%...
echo.

echo   Starting Backend API (0.0.0.0:8000)...
start /b uv run python -m uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000 > NUL 2>&1

echo   Starting Frontend Server (0.0.0.0:5173)...
start /b npm --prefix apps/landing run dev > NUL 2>&1

echo.
echo   Starting Execution Worker...
start /b uv run python -m apps.backend.worker.execution_runner > NUL 2>&1

echo.
echo [WAIT] Waiting for backend to become healthy...
set "BACKEND_READY=0"
for /L %%i in (1,1,20) do (
    if "!BACKEND_READY!" == "0" (
        timeout /t 1 /nobreak > NUL
        powershell -Command "try { $r = Invoke-RestMethod 'http://localhost:8000/health' -TimeoutSec 1; Write-Host '[OK] Backend healthy (attempt %%i)'; exit 0 } catch { exit 1 }" 2>NUL
        if !ERRORLEVEL! EQU 0 set "BACKEND_READY=1"
    )
)

if "!BACKEND_READY!" == "0" (
    echo [WARNING] Backend did not respond within 20 seconds.
    echo [WARNING] Check the backend startup logs for errors.
    echo [WARNING] Common cause: PYTHONPATH or DATABASE_URL misconfiguration.
) else (
    echo.
    echo ========================================================
    echo  Atlas is running!
    echo  Frontend:    http://localhost:5173
    echo  Evaluations: http://localhost:5173/dashboard/evaluations/new
    echo  Backend API: http://localhost:8000
    echo  Database:    %WORKTREE_DIR%\atlas_dev.db
    echo ========================================================
    echo.
    echo  Run regression test:
    echo    node apps/landing/scripts/auth-e2e-dispatch.js
    echo ========================================================
)
