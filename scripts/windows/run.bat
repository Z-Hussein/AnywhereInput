@echo off
setlocal EnableDelayedExpansion

title AnywhereInput - Universal Launcher

print_banner() {
    echo -e "${CYAN}"
    echo "░█▀█░█▀█░█░█░█ ░ █░█░█░█▀▀░█▀▄░█▀▀░▀█▀░█▀█░█▀█░█░█░▀█▀"
    echo "░█▀█░█░█░░█░░█▄▀▄█░█▀█░█▀▀░█▀▄░█▀▀░░█░░█░█░█▀▀░█░█░░█░"
    echo "░▀░▀░▀░▀░░▀░░▀░ ░▀ ▀░▀░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░░▀░.com"
    echo "  AnywhereInput v1.0.0 — Remote Control Your PC"
    echo -e "${NC}"
}

call :print_banner

:: ── Activate venv ─────────────────────────────────────────────────────────
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found. Running setup first...
    call scripts\windows\setup.bat
    call .venv\Scripts\activate.bat
)

:menu
call :print_banner
echo  Select tunnel provider for remote access:
echo.
echo   [1] Cloudflare Tunnel  (Recommended - FREE, no account)
echo   [2] Tailscale          (FREE, requires Tailscale account)
echo   [3] Pinggy.io         (FREE, uses SSH, no install)
echo   [4] Zrok2             (FREE, open source, 5GB/day)
echo   [5] ngrok             (Free tier, requires account)
echo   [6] Local only        (Same WiFi, no tunnel)
echo.
echo   [S] Setup / Repair
echo   [Q] Quit
echo.
set /p choice="Enter choice (1-6, S, Q): "

if "%choice%"=="1" goto cloudflare
if "%choice%"=="2" goto tailscale
if "%choice%"=="3" goto pinggy
if "%choice%"=="4" goto zrok2
if "%choice%"=="5" goto ngrok
if "%choice%"=="6" goto local
if /I "%choice%"=="S" goto setup
if /I "%choice%"=="Q" goto quit
goto menu

:cloudflare
echo.
echo [Cloudflare] Starting tunnel...
python -m anywhereinput.server --tunnel cloudflare
goto end

:tailscale
echo.
echo [Tailscale] Starting tailnet tunnel...
python -m anywhereinput.server --tunnel tailscale
goto end

:pinggy
echo.
echo [Pinggy] Starting SSH tunnel...
python -m anywhereinput.server --tunnel pinggy
goto end

:zrok2
echo.
echo [Zrok2] Starting tunnel...
python -m anywhereinput.server --tunnel zrok2
goto end

:ngrok
echo.
echo [ngrok] Starting tunnel...
python -m anywhereinput.server --tunnel ngrok
goto end

:local
echo.
echo [Local] Starting server (no tunnel)...
python -m anywhereinput.server
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
