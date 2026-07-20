@echo off
title Indian Kanoon Judgement Downloader
color 0B

echo.
echo  ====================================================
echo    Indian Kanoon Judgement Downloader
echo    Open your browser at: http://localhost:5000
echo  ====================================================
echo.

:: Check if setup has been run
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Dependencies not installed. Please run setup.bat first!
    pause
    exit /b 1
)

:: Start the Flask UI server
cd /d "%~dp0ui"
python app.py
