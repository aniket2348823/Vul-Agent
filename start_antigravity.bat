@echo off
setlocal enabledelayedexpansion
title Antigravity Singularity V6 - Unified Lifecycle

chcp 65001 > nul
set PYTHONUTF8=1

echo [STATUS] Booting Antigravity IDE Framework...
echo [GSD] Restoring workflow state...
echo [RALPH] Initiating autonomous supervisor...
echo [TESTSPRITE] Activating Quality Sentinel...

:: 1. Initialize Project Memory
if not exist ".planning\STATE.md" (
    echo [PLANNING] Initializing STATE.md tracking...
    echo # Project State > .planning\STATE.md
)

:: 2. Launch Core Systems (FastAPI + Vite)
echo [SERVERS] Launching parallel processes...
start "Antigravity Backend" cmd /c "python -m backend.main"
start "Antigravity Frontend" cmd /c "npm run dev"

:: 3. Trigger Hot-Start Lifecycle
:: This signal is detected by the backend lifespan hook to resume GSD, Ralph, and TestSprite
echo AUTO_RESUME_IDE > .agents\startup_signal.tmp

echo [SUCCESS] Antigravity IDE is now ACTIVE.
echo [!] Dashboard: http://localhost:5173
echo [!] Intelligence API: http://localhost:8000
echo [!] Quality Sentinel: Headless Monitoring Active

timeout /t 5
exit
