@echo off
chcp 65001 >nul
title PolyAgent - Autonomous Polymarket Trading Agent

echo.
echo ========================================
echo    🤖 PolyAgent - Starting Up...
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python from https://python.org
    echo         Then run this file again.
    pause
    exit /b 1
)

echo [1/3] Installing Python dependencies...
cd agent
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your internet connection.
    pause
    exit /b 1
)
echo       ✓ Dependencies installed

REM Go back to root
cd ..

echo.
echo [2/3] Installing app dependencies...
call npm install >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found! Install Node.js from https://nodejs.org
    pause
    exit /b 1
)
echo       ✓ App installed

echo.
echo [3/3] Starting PolyAgent...
echo.
echo ========================================
echo    Open the app and follow these steps:
echo    1. Click "Settings" in left sidebar
echo    2. Enter your Polymarket credentials
echo    3. Set your budget sliders
echo    4. Click "Enable Agent" (Options menu)
echo    5. Type "scan NFL" in the chat!
echo ========================================
echo.

REM Start the app
call npm start

pause
