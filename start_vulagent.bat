@echo off
setlocal enabledelayedexpansion

title Vulagent Scanner Singularity V6 - Unified Lifecycle
cls

echo ============================================================
echo [STATUS] Booting Vulagent Scanner Penetration Testing System...
echo ============================================================

:: 1. Environment & Dependencies
set "PROMPT_ID=VulagentScanner_V6"
echo [CORE] Priming OS-Level Daemon (GSD/Ralph/TestSprite)...

:: 2. Launch TRIPLE-PILLAR Ecosystem
:: Pillar A: Backend Orchestrator (Ollama / OpenRouter Proxy)
echo [CORE] Initiating Backend Orchestrator...
start "Vulagent Scanner Backend" cmd /c "python -m backend.main"

:: Pillar B: Frontend Dashboard (Vite React)
echo [CORE] Initiating Performance Dashboard...
start "Vulagent Scanner Frontend" cmd /c "npm run dev"

:: Pillar C: Headless Quality Guardian (TestSprite)
echo [CORE] Starting TestSprite Quality Sentry...

echo.
echo [SUCCESS] Vulagent Scanner Penetration Testing System is now ACTIVE.
echo [INFO] Dashboard: http://localhost:5173
echo [INFO] Backend: http://localhost:8000
echo.
pause
