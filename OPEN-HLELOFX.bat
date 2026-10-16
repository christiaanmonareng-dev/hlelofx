@echo off
setlocal
cd /d "%~dp0"
title HleloFX Website and Owner Portal
echo ==========================================
echo       HLELOFX WEBSITE + OWNER PORTAL
echo ==========================================
echo.
echo Checking Python...
where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=py"
  goto python_found
)
where python >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=python"
  goto python_found
)
echo Python was not found. Install it from https://www.python.org/downloads/windows/
echo Then run this file again.
pause
exit /b 1

:python_found
if not exist ".venv\Scripts\python.exe" (
  echo Creating website environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto failed
)
echo Installing/checking website package (first run may take a minute)...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Opening HleloFX in your browser...
start "" "http://127.0.0.1:8000/"
echo.
echo The server will now run. Keep this window open.
echo Main website:  http://127.0.0.1:8000/
echo Owner portal:  http://127.0.0.1:8000/owner
echo Owner email:   hlelomabuza@icloud.com
echo Default pass:  change-me-now
echo.
".venv\Scripts\python.exe" server.py
echo.
echo HleloFX server stopped. If there was an error above, take a screenshot.
pause
exit /b 0

:failed
echo.
echo Setup failed. Check your internet connection and screenshot this window.
pause
exit /b 1
