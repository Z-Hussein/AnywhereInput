@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo  Zrok2 Diagnostic ^& Repair Tool
echo ================================================================
echo.

REM Find zrok2
set "ZROK="
for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    for %%P in (
        "%%D:\Users\%USERNAME%\bin\zrok2.exe"
        "%%D:\Users\%USERNAME%\bin\zrok.exe"
        "%%D:\zrok2.exe"
        "%%D:\zrok.exe"
    ) do (
        if exist %%~P (
            set "ZROK=%%~P"
            goto :found
        )
    )
)
for %%P in (zrok2 zrok) do (
    where %%P >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%i in ('where %%P') do (
            set "ZROK=%%i"
            goto :found
        )
    )
)
:found

if not defined ZROK (
    echo [!] zrok/zrok2 not found in PATH or common locations.
    echo [*] Please download from: https://github.com/openziti/zrok/releases
    pause
    exit /b 1
)

echo [+] Found: %ZROK%
echo.

REM Step 1: Check status
echo [*] Step 1: Checking zrok status...
"%ZROK%" status 2>&1
echo.

REM Step 2: Disable old environment
echo [*] Step 2: Disabling old environment (safe to ignore errors)...
"%ZROK%" disable 2>nul
timeout /t 2 /nobreak >nul
echo.

REM Step 3: Prompt for new token
echo [*] Step 3: Re-authentication required.
echo.
echo    Get your token from: https://zrok.io
echo    Dashboard ^> Environments ^> Enable Environment
echo    Or run: zrok2 invite  (if you need a new account)
echo.
set /p TOKEN="Paste your zrok2 enable token here: "

if "!TOKEN!"=="" (
    echo [!] No token provided. Exiting.
    pause
    exit /b 1
)

echo.
echo [*] Enabling zrok2 with new token...
"%ZROK%" enable !TOKEN!
if %errorlevel% neq 0 (
    echo.
    echo [!] Enable failed. Possible causes:
    echo     - Invalid or expired token
    echo     - Network connectivity issues
    echo     - zrok service outage
echo.
    echo [*] Try generating a new token at https://zrok.io
echo [*] Or check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo [+] SUCCESS! zrok2 environment re-enabled.
echo.
echo [*] You can now run: launch_with_zrok2.bat
echo.
pause
