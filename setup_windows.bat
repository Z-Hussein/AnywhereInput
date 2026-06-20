@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

REM Try to find Python
set "PYCMD=python"
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        REM Python not found, try to install it
        echo.
        echo Python is not installed. Attempting to install...
        echo.
        
        REM Try using winget (Windows Package Manager)
        winget --version >nul 2>&1
        if errorlevel 1 (
            echo ERROR: Could not find Python or install automatically.
            echo.
            echo Please install Python 3.11+ manually:
            echo   1. Download from https://www.python.org/downloads/
            echo   2. Run the installer
            echo   3. CHECK "Add Python to PATH"
            echo   4. Run this script again
            echo.
            pause
            exit /b 1
        ) else (
            echo Using Windows Package Manager to install Python...
            winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
            if errorlevel 1 (
                echo.
                echo Installation failed. Please install Python manually:
                echo   1. Download from https://www.python.org/downloads/
                echo   2. Run the installer
                echo   3. CHECK "Add Python to PATH"
                echo   4. Run this script again
                echo.
                pause
                exit /b 1
            )
            echo Python installed successfully!
            set "PYCMD=python"
        )
    ) else (
        set "PYCMD=py"
    )
)

echo.
echo Creating Python virtual environment...
if not exist ".venv" (
    %PYCMD% -m venv .venv
)

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing required packages...
%PYCMD% -m pip install --upgrade pip >nul 2>&1
%PYCMD% -m pip install -r requirements.txt >nul 2>&1

echo.
echo ================================================================
echo Setup complete!
echo ================================================================
echo.
echo To start the server, run one of these commands:
echo.
echo   For local network use:
echo     python secure_server.py
echo.
echo   For remote access (requires ngrok):
echo     python launch_with_ngrok.py
echo.
echo ================================================================
echo.
pause
