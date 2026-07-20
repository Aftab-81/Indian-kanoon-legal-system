@echo off
REM filepath: d:\Backup\Jugement_fixed\find_wrong_ports.bat
REM Script to find files with incorrect API port numbers

echo Searching for incorrect API port references...
echo.

echo Files with port 5000 (should be 8000 for main backend):
findstr /s /i /m "localhost:5000" front-end\src\*.jsx front-end\src\*.js
echo.

echo Files with port 8000 in wrong context:
findstr /s /i /n "localhost:8000" front-end\src\*.jsx front-end\src\*.js
echo.

echo Expected port usage:
echo   Port 8000: Main Backend (case processing)
echo   Port 8001: Research Backend
echo   Port 8002: Legal QA
echo   Port 8003: Summary Extractor
echo.

pause