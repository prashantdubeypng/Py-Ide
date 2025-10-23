# Run Py-IDE with virtual environment
# PowerShell version

Write-Host "Starting Py-IDE with venv..." -ForegroundColor Green

# Activate venv
& .\.venv\Scripts\Activate.ps1

# Run IDE
python run_ide.py
