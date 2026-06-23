@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
setlocal enabledelayedexpansion
cd /d %~dp0

REM ================================================================
REM AnywhereInput - Universal Tunnel Launcher - Creator: Z-Hussein
REM ================================================================
REM Supports: Cloudflare Tunnel, Pinggy, Zrok2, ngrok
REM ================================================================

echo.
echo ================================================================
echo  AnywhereInput - Remote Access Launcher - Creator: Z-Hussein
echo ================================================================
echo.

REM Try to find Python: prefer local venv, then py launcher, then common install paths
set "PYCMD="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYCMD=%~dp0.venv\Scripts\python.exe"
)
if not defined PYCMD (
    py --version >nul 2>&1
    if not errorlevel 1 set "PYCMD=py"
)
if not defined PYCMD (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYCMD=python"
)

if not defined PYCMD (
    REM Check common install locations across drives C..Z
    for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
        for %%P in (
            "%%D:\Program Files\Python39\python.exe"
            "%%D:\Program Files\Python310\python.exe"
            "%%D:\Program Files\Python311\python.exe"
            "%%D:\Program Files\Python312\python.exe"
            "%%D:\Python39\python.exe"
            "%%D:\Python310\python.exe"
            "%%D:\Python311\python.exe"
            "%%D:\Python312\python.exe"
            "%%D:\Users\%USERNAME%\AppData\Local\Programs\Python\Python39\python.exe"
            "%%D:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe"
            "%%D:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe"
            "%%D:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"
        ) do (
            if exist %%~P (
                set "PYCMD=%%~P"
                goto :found_python
            )
        )
    )
)
:found_python

if not defined PYCMD (
    echo.
    echo ERROR: Python 3.9+ was not found on this system.
    echo Please install Python and ensure it's on your PATH, or place a copy in the repository.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [*] Python found: %PYCMD%
echo.

REM Create venv if needed
echo [*] Setting up virtual environment...
if not exist ".venv" (
    echo [*] Creating virtual environment...
    %PYCMD% -m venv .venv
)
call .venv\Scripts\activate.bat

REM Install dependencies
echo [*] Installing dependencies...
%PYCMD% -m pip install -q -r requirements.txt >nul 2>&1

REM ================================================================
REM Provider Selection Menu
REM ================================================================

:menu
echo.
echo ================================================================
echo  Choose your tunnel provider:
echo ================================================================
echo.
echo  [1] Cloudflare Tunnel  - FREE, no account, fastest globally
echo  [2] Pinggy.io          - FREE, uses SSH, no install needed
echo  [3] Zrok2              - FREE, open source, zero-trust
echo  [4] ngrok              - Free tier, requires account
echo.
echo  [Q] Quit
echo.
echo ================================================================
echo.

set /p choice="Enter choice (1-4, or Q): "

if /i "%choice%"=="Q" exit /b 0
if "%choice%"=="1" goto :cloudflare
if "%choice%"=="2" goto :pinggy
if "%choice%"=="3" goto :zrok2
if "%choice%"=="4" goto :ngrok

echo [!] Invalid choice. Please try again.
goto :menu

:cloudflare
echo.
echo [*] Launching with Cloudflare Tunnel...
%PYCMD% "%~dp0launch_with_tunnel.py" --provider cloudflare %*
goto :end

:pinggy
echo.
echo [*] Launching with Pinggy...
%PYCMD% "%~dp0launch_with_tunnel.py" --provider pinggy %*
goto :end

:zrok2
echo.
echo [*] Launching with Zrok2...
%PYCMD% "%~dp0launch_with_tunnel.py" --provider zrok2 %*
goto :end

:ngrok
echo.
echo [*] Launching with ngrok...
%PYCMD% "%~dp0launch_with_tunnel.py" --provider ngrok %*
goto :end

:end
pause
