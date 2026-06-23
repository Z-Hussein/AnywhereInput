@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
setlocal enabledelayedexpansion
cd /d %~dp0

echo.
echo ================================================================
echo  AnywhereInput - Zrok2 Launcher - Creator: Z-Hussein
echo ================================================================
echo.

REM Try to find Python
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
    echo ERROR: Python 3.9+ was not found.
    echo Please install Python and ensure it's on your PATH.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [*] Python found: %PYCMD%
echo.

REM Create venv if needed
if not exist ".venv" (
    echo [*] Creating virtual environment...
    %PYCMD% -m venv .venv
)
call .venv\Scripts\activate.bat

REM Install dependencies
echo [*] Installing dependencies...
%PYCMD% -m pip install -q -r requirements.txt >nul 2>&1

echo.
echo [*] Launching with Zrok2...
echo.
echo    If this is your first time:
echo    1. Get your token from https://zrok.io ^(Dashboard ^> Environments^)
echo    2. Run: zrok2 enable ^<YOUR_TOKEN^>
echo    3. Then run this launcher again.
echo.
%PYCMD% "%~dp0launch_with_tunnel.py" --provider zrok2 %*

pause
