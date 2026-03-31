@echo off
setlocal enabledelayedexpansion

title Vul Agent Singularity V6 - Unified Lifecycle
cls

echo ============================================================
echo [STATUS] Booting Vul Agent Penetration Testing System...
echo ============================================================

:: 1. Environment & Dependencies
set "PROMPT_ID=VulAgent_V6"
echo [CORE] Priming OS-Level Daemon (GSD/Ralph/TestSprite)...

:: 2. Launch TRIPLE-PILLAR Ecosystem
:: Pillar A: Backend Orchestrator (Ollama / OpenRouter Proxy)
echo [CORE] Initiating Backend Orchestrator...
start "Vul Agent Backend" cmd /c "python -m backend.main"

:: Pillar B: Frontend Dashboard (Vite React)
echo [CORE] Initiating Performance Dashboard...
start "Vul Agent Frontend" cmd /c "npm run dev"

:: Pillar C: Headless Quality Guardian (TestSprite)
echo [CORE] Starting TestSprite Quality Sentry...

echo.
echo [SUCCESS] Vul Agent Penetration Testing System is now ACTIVE.
echo [INFO] Dashboard: http://localhost:5173
echo [INFO] Backend: http://localhost:8000
echo.
pause
