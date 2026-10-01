@echo off
REM filepath: d:\Backup\Jugement_fixed\start_all.bat
REM Batch script to start all backend and frontend services

echo ========================================
echo Starting Legal Case Analysis System
echo ========================================
echo.

REM Set the root directory
set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

REM Check if virtual environment exists
if not exist "%ROOT_DIR%venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create a virtual environment first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Start Main Backend (Port 8000)
echo [1/7] Starting Main Backend on port 8000...
start "Main Backend (8000)" cmd /k "cd /d "%ROOT_DIR%backend" && call "%ROOT_DIR%venv\Scripts\activate" && python api.py"
timeout /t 2 /nobreak >nul

REM Start Research Backend (Port 8001)
echo [2/7] Starting Research Backend on port 8001...
start "Research Backend (8001)" cmd /k "cd /d "%ROOT_DIR%rbackend" && call "%ROOT_DIR%venv\Scripts\activate" && python backend.py"
timeout /t 2 /nobreak >nul

REM Start Legal QA Backend (Port 8002)
echo [3/7] Starting Legal QA Backend on port 8002...
start "Legal QA Backend (8002)" cmd /k "cd /d "%ROOT_DIR%Legal_QA\legal-qa-system\backend" && call "%ROOT_DIR%venv\Scripts\activate" && python app.py"
timeout /t 2 /nobreak >nul

REM Start Summary Backend (Port 8003)
echo [4/7] Starting Summary Backend on port 8003...
start "Summary Backend (8003)" cmd /k "cd /d "%ROOT_DIR%Legal_Summary\backend" && call "%ROOT_DIR%venv\Scripts\activate" && python app.py"
timeout /t 5 /nobreak >nul

REM Start Document Retrieval Backend (Port 8004)
echo [5/7] Starting Document Retrieval Backend on port 8004...
start "Document Retrieval Backend (8004)" cmd /k "cd /d "%ROOT_DIR%indiankanoon-mcp\ui" && call "%ROOT_DIR%venv\Scripts\activate" && python app.py"
timeout /t 2 /nobreak >nul

REM Start Evaluation API (Port 8005)
echo [6/7] Starting Evaluation API on port 8005...
start "Evaluation API (8005)" cmd /k "cd /d "%ROOT_DIR%" && call "%ROOT_DIR%venv\Scripts\activate" && python -m uvicorn evaluation.api:app --port 8005 --reload"
timeout /t 2 /nobreak >nul

REM Start Frontend (Port 5173)
echo [7/7] Starting Frontend on port 5173...
start "Frontend (5173)" cmd /k "cd /d "%ROOT_DIR%front-end" && npm run dev"

echo.
echo ========================================
echo All services started successfully!
echo ========================================
echo.
echo Services running:
echo   Main Backend:      http://localhost:8000
echo   Research Backend:  http://localhost:8001
echo   Legal QA Backend:  http://localhost:8002
echo   Summary Backend:   http://localhost:8003
echo   Doc Retrieval:     http://localhost:8004
echo   Evaluation API:    http://localhost:8005
echo   Frontend:          http://localhost:5173
echo   Eval Dashboard:    http://localhost:5173/evaluation
echo.
echo Press any key to exit this window...
echo (Services will continue running in their own windows)
pause >nul