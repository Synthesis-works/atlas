$ErrorActionPreference = "Stop"

Write-Host "1. Running Setup..."
.\scripts\setup.ps1

Write-Host "`n2. Running Integration Demo..."
& .\.venv\Scripts\python.exe integration_demo.py
