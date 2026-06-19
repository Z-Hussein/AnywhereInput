@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

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
    REM Check common install locations across drives C..Z (covers D:, E:, etc.)
    for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
        for %%P in (
            "%%D:\\Program Files\\Python39\\python.exe"
            "%%D:\\Program Files\\Python310\\python.exe"
            "%%D:\\Program Files\\Python311\\python.exe"
            "%%D:\\Python39\\python.exe"
            "%%D:\\Python310\\python.exe"
            "%%D:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Python\\Python39\\python.exe"
            "%%D:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Python\\Python310\\python.exe"
            "%%D:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Python\\Python311\\python.exe"
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
    echo   Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo Activating virtual environment...
if not exist ".venv" (
    echo Creating virtual environment...
    %PYCMD% -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing required packages...
%PYCMD% -m pip install -q -r requirements.txt >nul 2>&1

echo.
echo Searching for ngrok executable across drives and PATH...
set "NGROK_PATH="

REM Prefer bundled copy in repository
if exist "%~dp0ngrok.exe" (
    set "NGROK_PATH=%~dp0ngrok.exe"
)

if not defined NGROK_PATH (
    REM Search common locations across drives C..Z
    for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
        for %%P in (
            "%%D:\\Program Files\\ngrok\\ngrok.exe"
            "%%D:\\Program Files (x86)\\ngrok\\ngrok.exe"
            "%%D:\\Users\\%USERNAME%\\AppData\\Local\\ngrok\\ngrok.exe"
            "%%D:\\Downloads\\ngrok.exe"
            "%%D:\\ngrok.exe"
        ) do (
            if exist %%~P (
                set "NGROK_PATH=%%~P"
                goto :found_ngrok
            )
        )
    )
)

REM Try system PATH using where
if not defined NGROK_PATH (
    for /f "delims=" %%i in ('where ngrok 2^>nul') do (
        set "NGROK_PATH=%%i"
        goto :found_ngrok
    )
)

:found_ngrok
if defined NGROK_PATH (
    echo Found ngrok: %NGROK_PATH%
) else (
    echo WARNING: ngrok not found. The launcher will prompt for instructions.
)

echo Starting ngrok launcher...
if defined NGROK_PATH (
    %PYCMD% "%~dp0launch_with_ngrok.py" --ngrok-path "%NGROK_PATH%" %*
) else (
    %PYCMD% "%~dp0launch_with_ngrok.py" %*
)

pause


