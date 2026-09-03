@echo off
title Daily Rollup Agentic Daemon
echo ======================================================================
echo  Starting Daily Rollup Agentic Daemon & Cron (4:00 PM / 5:00 PM)
echo ======================================================================
cd /d "%~dp0"
python daily_pipeline_cron.py --daemon --schedule 17:00
pause
