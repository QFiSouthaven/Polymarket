@echo off
REM PolyAgent MCP Server — Persistent Memory for Dev Lifecycle & Polymarket App
REM This script creates a virtual environment, installs dependencies, and launches the server.
REM Run this from: F:\PolyMarket\mcp-server\

setlocal enabledelayedexpansion

echo ========================================
echo   PolyAgent MCP Server Launcher
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Please install Python 3.11+ first.
    pause
    exit /b 1
)

echo [INFO] Python version:
python --version
echo.

REM Check if venv exists; create if needed
if exist ".venv\Scripts\activate.bat" (
    echo [OK] Virtual environment already exists at .venv/
) else (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created at .venv/
)

echo.
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

echo [OK] Virtual environment activated: !PYTHON!
echo.

REM Install dependencies directly (no editable install — avoids setuptools requirement)
echo [INFO] Installing dependencies...
pip install --quiet mcp pydantic sqlite-utils rich requests PyYAML
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. Check your network connection.
    pause
    exit /b 1
)

echo [OK] Dependencies installed successfully.
echo.

REM Change to src directory and launch the MCP server
cd /d "%~dp0src"
echo [INFO] Launching MCP server (python -m mcp_server.server)...
echo [INFO] Press Ctrl+C to stop the server.
echo.

python -m mcp_server.server
