@echo off
REM ===================================================================
REM  FormatForge AI — Start All Services
REM ===================================================================
REM  Service              Port     Description
REM  ─────────────────────────────────────────────────────────
REM  Static Format API    8000     Python FastAPI (backend/api.py + unified pipeline)
REM  MCP Editor API       8082     Python FastAPI (mcp_editor/api.py — DocBot agent)
REM  React Frontend       5173     Vite dev server (frontend/)
REM ===================================================================

echo ===================================================================
echo  FormatForge AI — Starting All Services
echo ===================================================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM 1. Start Unified Pipeline API (port 8000)
echo [1/3] Starting Unified Pipeline API on port 8000...
start "FormatForge - Python API (8000)" cmd /k "cd /d %~dp0 && .venv\Scripts\activate.bat && python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 2 /nobreak >nul

REM 2. Start MCP Editor API (port 8082)
echo [2/3] Starting MCP Editor API on port 8082...
start "FormatForge - MCP Editor (8082)" cmd /k "cd /d %~dp0 && .venv\Scripts\activate.bat && python -m uvicorn mcp_editor.api:app --host 0.0.0.0 --port 8082 --reload"
timeout /t 2 /nobreak >nul

REM 3. Start React Frontend (port 5173)
echo [3/3] Starting React Frontend on port 5173...
start "FormatForge - React Frontend (5173)" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo ===================================================================
echo  All services started!
echo.
echo  React Frontend:   http://localhost:5173
echo  Python API:       http://localhost:8000/docs
echo  MCP Editor:       http://localhost:8082/docs
echo ===================================================================
echo.
echo Press any key to close this launcher (services will keep running)...
pause >nul
