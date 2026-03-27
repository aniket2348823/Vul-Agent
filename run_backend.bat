@echo off
rem Fix character encoding for emojis in Windows
chcp 65001 > nul
set PYTHONUTF8=1

echo Starting Antigravity V3 Backend...
python -m backend.main
pause
