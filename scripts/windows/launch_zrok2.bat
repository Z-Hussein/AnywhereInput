@echo off
title AnywhereInput - Zrok2


REM Change to project root (two levels up from scripts\windows)
cd /d "%~dp0..\.."

echo.
echo ░█▀█░█▀█░█░█░█ ░ █░█░█░█▀▀░█▀▄░█▀▀░▀█▀░█▀█░█▀█░█░█░▀█▀
echo ░█▀█░█░█░░█░░█▄▀▄█░█▀█░█▀▀░█▀▄░█▀▀░░█░░█░█░█▀▀░█░█░░█░
echo ░▀░▀░▀░▀░░▀░░▀░ ░▀ ▀░▀░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░░▀░.com
echo   AnywhereInput v1.2.7 - Remote Control Your PC
echo.

if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat
python -m anywhereinput.server --tunnel zrok2
pause
