@echo off
setlocal EnableDelayedExpansion

title AnywhereInput - Universal Launcher

REM Change to project root (two levels up from scripts\windows)
cd /d "%~dp0..\.." || (
    echo [ERROR] Failed to change to project root.
    pause
    exit /b 1
)

goto :main

REM ── Print banner function ──────────────────────────────────────────────────
:print_banner
cls
echo.
echo ░█▀█░█▀█░█░█░█ ░ █░█░█░█▀▀░█▀▄░█▀▀░▀█▀░█▀█░█▀█░█░█░▀█▀
echo ░█▀█░█░█░░█░░█▄▀▄█░█▀█░█▀▀░█▀▄░█▀▀░░█░░█░█░█▀▀░█░█░░█░
echo ░▀░▀░▀░▀░░▀░░▀░ ░▀ ▀░▀░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░░▀░.com
echo   AnywhereInput v1.2.7 - Remote Control Your PC
echo         by AnywhereInput.com Github: @Z-Hussein
echo.
goto :eof

REM ── Main Program ───────────────────────────────────────────────────────────
:main

:: ── Check Python ─────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.9+ from python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%a in ('python --version') do echo [OK] %%a

:: ── Activate venv ─────────────────────────────────────────────────────────
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found. Running setup first...
    call scripts\windows\setup.bat
    if errorlevel 1 (
        echo [ERROR] Setup failed!
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
)

:: ── Verify anywhereinput is available ──────────────────────────────────────
python -c "import anywhereinput" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Package not found. Installing...
    pip install -e .
    if errorlevel 1 (
        echo [ERROR] Failed to install package!
        pause
        exit /b 1
    )
)

:menu
call :print_banner
echo Select tunnel provider for remote access:
echo.
echo [1] Cloudflare Tunnel (Recommended - FREE, no account)
echo [2] Tailscale (FREE, requires Tailscale account)
echo [3] Pinggy.io (FREE, uses SSH, no install)
echo [4] Zrok2 (FREE, open source, 5GB/day)
echo [5] Local only (Same WiFi, no tunnel)
echo.
echo [S] Setup / Repair
echo [Q] Quit
echo.
set /p choice="Enter choice (1-5, S, Q): "

if "%choice%"=="1" goto cloudflare
if "%choice%"=="2" goto tailscale
if "%choice%"=="3" goto pinggy
if "%choice%"=="4" goto zrok2
if "%choice%"=="5" goto local
if /I "%choice%"=="S" goto setup
if /I "%choice%"=="Q" goto quit
goto menu

:cloudflare
echo.
echo [Cloudflare] Starting tunnel...
python -m anywhereinput.server --tunnel cloudflare
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server failed to start (exit code: %errorlevel%)
    echo.
)
goto end

:tailscale
echo.
echo [Tailscale] Starting tailnet tunnel...
python -m anywhereinput.server --tunnel tailscale
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server failed to start (exit code: %errorlevel%)
    echo.
)
goto end

:pinggy
echo.
echo [Pinggy] Starting SSH tunnel...
python -m anywhereinput.server --tunnel pinggy
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server failed to start (exit code: %errorlevel%)
    echo.
)
goto end

:zrok2
echo.
echo [Zrok2] Starting tunnel...
python -m anywhereinput.server --tunnel zrok2
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server failed to start (exit code: %errorlevel%)
    echo.
)
goto end

:local
echo.
echo [Local] Starting server (no tunnel)...
python -m anywhereinput.server
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server failed to start (exit code: %errorlevel%)
    echo.
)
goto end

:setup
call scripts\windows\setup.bat
goto menu

:quit
exit /b 0

:end
echo.
echo Server stopped.
pause
goto menu
