@echo off
setlocal EnableDelayedExpansion

title AnywhereInput - Windows Setup
color 0A

echo ============================================
echo    AnywhereInput - Windows Setup
echo ============================================
echo.

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.9+ from python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=*" %%a in ('python --version') do echo [OK] Found: %%a

:: Create virtual environment
if not exist ".venv" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/4] Virtual environment already exists
)

:: Activate and install
echo [2/4] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [3/4] Upgrading pip...
python -m pip install --upgrade pip

echo [4/4] Installing dependencies...
pip install -e .

if errorlevel 1 (
    echo [ERROR] Installation failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo    Setup Complete!
echo ============================================
echo.
echo Run 'scripts\windows\run.bat' to start the server.
echo.
pause
