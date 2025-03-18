# -------------------------------------------------------------------------------
# run_smoke_tests.ps1
# -------------------------------------------------------------------------------
# 
# Smoke test execution script
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File tests\scripts\run_smoke_tests.ps1
# -------------------------------------------------------------------------------

Write-Host "Running smoke tests..." -ForegroundColor Cyan

# Get current directory
$current_dir = Get-Location
Write-Host "Current working directory: $current_dir" -ForegroundColor Gray

# Move to project root if needed
if (-not (Test-Path ".\tests")) {
    try {
        Set-Location C:\Users\nyham\work\sampletest
        Write-Host "Moved to project root: $(Get-Location)" -ForegroundColor Gray
    } catch {
        Write-Host "Failed to move to project root." -ForegroundColor Red
        exit 1
    }
}

# Set error action preference
$ErrorActionPreference = "Stop"

try {
    # Activate virtual environment
    if (Test-Path "venv") {
        & .\venv\Scripts\Activate.ps1
        Write-Host "Virtual environment activated" -ForegroundColor Gray
    } else {
        Write-Error "Virtual environment not found in venv/ directory."
        exit 1
    }

    # Record start time
    $start_time = Get-Date

    # Run smoke tests
    Write-Host "`nRunning smoke tests..." -ForegroundColor Yellow
    Write-Host "--------------------------------------------------" -ForegroundColor Yellow

    # Execute smoke tests
    $env:PYTHONPATH = "."
    & pytest tests/smoke_tests/test_api_endpoints.py -v --tb=short -m "smoke"
    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed."
    }

    # Record end time and calculate duration
    $end_time = Get-Date
    $execution_time = ($end_time - $start_time).TotalSeconds

    Write-Host "`n--------------------------------------------------" -ForegroundColor Yellow
    Write-Host "Smoke tests completed" -ForegroundColor Green
    Write-Host "Execution time: $($execution_time) seconds" -ForegroundColor Cyan

} catch {
    Write-Host "Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    # Deactivate virtual environment
    if (Get-Command deactivate -ErrorAction SilentlyContinue) {
        deactivate
        Write-Host "Virtual environment deactivated" -ForegroundColor Gray
    }

    # Return to original directory
    if ($current_dir -ne (Get-Location)) {
        Set-Location $current_dir
        Write-Host "Returned to original directory: $(Get-Location)" -ForegroundColor Gray
    }
} 