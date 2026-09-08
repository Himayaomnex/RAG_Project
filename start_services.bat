@echo off
title Omnex Multi-Agent Production Platform
cd /d "%~dp0"

echo ======================================================================
echo   OMNEX AI MULTI-AGENT SYSTEM - TURNKEY AUTONOMOUS LAUNCHER
echo ======================================================================
echo.

:: 1. Launch Background Daily Rollup & Transcript Watcher Daemon
echo [*] Starting Autonomous Cron & Folder Watcher Daemon in background...
start "Omnex-Daemon" /min python daily_pipeline_cron.py --daemon

:: 2. Launch FastAPI Web & API Server
echo [*] Starting Production API Server & Web UI on http://127.0.0.1:8080 ...
start "Omnex-API-Server" python api_server.py

:: 3. Wait a moment for server initialization and pop open the browser
timeout /t 3 /nobreak >nul
echo [*] Opening Browser Dashboard...
start http://127.0.0.1:8080

echo.
echo ======================================================================
echo   ALL SYSTEMS ONLINE AND RUNNING AUTONOMOUSLY!
echo   • Web Dashboard: http://127.0.0.1:8080
echo   • Daily Cron:    Active (Runs daily at 17:00 & on transcript drops)
echo   • Excel Reports: Auto-synced to Google Drive
echo ======================================================================
echo.
echo You can minimize this window. Press any key to stop all services...
pause >nul

:: Stop background services on exit
taskkill /fi "WINDOWTITLE eq Omnex-Daemon*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Omnex-API-Server*" /f >nul 2>&1
