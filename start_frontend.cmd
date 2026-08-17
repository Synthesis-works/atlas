@echo off
echo Starting Atlas Frontend (Landing App)...
cd apps\landing

echo Checking for package installations...
call npm install

echo Starting Vite development server and opening browser...
call npm run dev -- --open
pause
