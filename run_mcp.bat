@echo off
echo Starting Enterprise FastMCP RAG Server...
cd /d "%~dp0"
python mcp_server.py --server
pause
