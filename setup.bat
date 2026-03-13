@echo off
echo === Kindle Highlights Setup ===
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Installing via winget...
    winget install Python.Python.3.12 -e
    if %errorlevel% neq 0 (
        echo Failed to install Python automatically.
        echo Please install it manually from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo Python installed. Please restart this script.
    pause
    exit /b 0
) else (
    echo Python found.
)

echo.
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Installing Playwright browser...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo Failed to install Playwright browser.
    pause
    exit /b 1
)

echo.
echo Setup complete!
echo.
set /p run="Run the script now? (y/n): "
if /i "%run%"=="y" python kindle_to_csv.py

pause
