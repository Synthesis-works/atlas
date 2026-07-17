$ErrorActionPreference = "Stop"

Write-Host "Setting up Project Atlas..."

# Check if python is available
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "Python is required but not found. Please install Python 3.10+."
    exit 1
}

Write-Host "Creating Virtual Environment..."
python -m venv .venv

Write-Host "Activating Virtual Environment and Installing Dependencies..."
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Atlas Setup Complete!"
