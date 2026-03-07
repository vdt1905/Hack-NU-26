@echo off
title FormatForge AI - Agent Paperpal
echo ========================================
echo   FormatForge AI - Agent Paperpal
echo   Agentic Manuscript Formatting System
echo ========================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run: python -m venv venv
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Starting Streamlit app on http://localhost:8501 ...
echo.
streamlit run app.py --server.port 8501 --server.headless true
pause
