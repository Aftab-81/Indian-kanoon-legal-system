@echo off
REM Start ONLY the Evaluation API (port 8005)
REM Run this after start_all.bat if eval service is not running

echo ========================================
echo  Starting Evaluation API on port 8005
echo ========================================
echo.

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

if not exist "%ROOT_DIR%venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

echo Starting Evaluation API...
start "Evaluation API (8005)" cmd /k "cd /d "%ROOT_DIR%" && call "%ROOT_DIR%venv\Scripts\activate" && python -m uvicorn evaluation.api:app --port 8005 --reload"

echo.
echo Evaluation API started at http://localhost:8005
echo Eval Dashboard: http://localhost:5173/evaluation
echo.
echo To build datasets and run eval manually:
echo   venv\Scripts\python.exe evaluation\build_datasets.py --module all
echo   venv\Scripts\python.exe evaluation\run_eval.py --module all
echo.
pause >nul
