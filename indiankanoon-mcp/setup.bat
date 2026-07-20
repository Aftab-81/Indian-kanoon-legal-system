@echo off
title Indian Kanoon Downloader - Setup
color 0B

echo.
echo  ====================================================
echo    Indian Kanoon Judgement Downloader - Setup
echo  ====================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo  [OK] Python found:
python --version

echo.
echo  Installing Python packages...
echo  ------------------------------------------------
pip install fastmcp requests beautifulsoup4 pdfkit lxml flask flask-cors

echo.
echo  ------------------------------------------------
echo  Checking for wkhtmltopdf (needed for PDF output)...

where wkhtmltopdf >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] wkhtmltopdf is already installed!
) else (
    echo.
    echo  [WARNING] wkhtmltopdf NOT found.
    echo.
    echo  Without it, judgements will be saved as HTML instead of PDF.
    echo  To enable PDF output, download and install it from:
    echo.
    echo    https://wkhtmltopdf.org/downloads.html
    echo.
    echo  After installing, re-run this setup.bat
)

echo.
echo  Creating downloads folder...
if not exist "D:\indiankanoon-mcp\downloads" mkdir "D:\indiankanoon-mcp\downloads"
echo  [OK] Downloads folder ready at D:\indiankanoon-mcp\downloads

echo.
echo  ====================================================
echo    Setup complete! Run  run.bat  to start the app.
echo  ====================================================
echo.
pause
