<#
.SYNOPSIS
    Activates the Python virtual environment for the project.
.DESCRIPTION
    This script checks if a virtual environment exists in the project directory and activates it.
    If no virtual environment is found, it will create one and install the requirements.
#>

# Get the directory where this script is located
$scriptPath = $PSScriptRoot

# Define the virtual environment directory
$venvPath = Join-Path -Path $scriptPath -ChildPath "venv"
$activateScript = Join-Path -Path $venvPath -ChildPath "Scripts\Activate.ps1"

# Check if virtual environment exists
if (-not (Test-Path -Path $activateScript)) {
    Write-Host "Virtual environment not found. Creating a new one..." -ForegroundColor Yellow
    
    # Create virtual environment
    python -m venv $venvPath
    
    if (-not $?) {
        Write-Error "Failed to create virtual environment. Please ensure Python is installed and in your PATH."
        exit 1
    }
    
    # Activate the new virtual environment
    & $activateScript
    
    # Upgrade pip and install requirements
    Write-Host "Installing requirements..." -ForegroundColor Cyan
    pip install --upgrade pip
    if (Test-Path -Path "requirements.txt") {
        pip install -r requirements.txt
    }
    
    Write-Host "Virtual environment created and activated successfully!" -ForegroundColor Green
} else {
    # Activate existing virtual environment
    & $activateScript
    Write-Host "Virtual environment activated!" -ForegroundColor Green
}

# Add any additional setup commands here
# For example, you might want to set environment variables:
# $env:FLASK_APP = "app.py"
# $env:FLASK_ENV = "development"
