@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo Hajk Gesture Control Demo
echo Stage 0 - Camera Preview
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found in PATH.
    echo Install Python 3.10+ and make sure "Add Python to PATH" is enabled.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Creating .venv...
    python -m venv .venv

    if errorlevel 1 (
        echo.
        echo ERROR: Could not create virtual environment.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

if errorlevel 1 (
    echo.
    echo WARNING: Could not upgrade pip. Continuing anyway.
)

echo.
echo Installing requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Could not install requirements.
    echo.
    pause
    exit /b 1
)

echo.
echo Starting app...
".venv\Scripts\python.exe" python\main.py

echo.
echo App closed.
pause