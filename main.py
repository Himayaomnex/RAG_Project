"""
================================================================================
Master 1-Click Launcher (main.py)
================================================================================
Starts the entire system in ONE command:
1. Auto-detects & starts Dakshinya's Retrieval Service (Port 8000) in background if not running
2. Starts the 5:00 PM Google Drive Cron Daemon in background
3. Launches the Interactive Multi-Agent CLI for immediate chat
================================================================================
"""

import os
import sys
import time
import socket
import subprocess
import threading

WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
DAKSHINYA_PATH = r"C:\dev\dakshinya-service"


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def ensure_retrieval_service():
    """Checks if Dakshinya's retrieval service is running on port 8000, starts it if not."""
    if is_port_in_use(8000):
        print("  [1/3] Dakshinya's Retrieval Service: Running on Port 8000 (Active)")
        return None

    if os.path.exists(DAKSHINYA_PATH):
        print("  [1/3] Starting Dakshinya's Retrieval Service on Port 8000...")
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "rag_platform.api.app:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=DAKSHINYA_PATH,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        # Wait up to 5 seconds for service to bind port
        for _ in range(10):
            time.sleep(0.5)
            if is_port_in_use(8000):
                print("        Dakshinya's Service successfully started.")
                return proc
    else:
        print("  [1/3] Note: Dakshinya service folder not found at C:\\dev\\dakshinya-service. Using direct KB & fallback.")
    return None


def start_background_daemon():
    """Starts the 5:00 PM Google Drive cron daemon in a background daemon thread."""
    from daily_pipeline_cron import start_agentic_daemon
    t = threading.Thread(
        target=start_agentic_daemon,
        kwargs={"check_interval_seconds": 15},
        daemon=True
    )
    t.start()
    print("  [2/3] Automated 5:00 PM Cron Daemon: Active & Watching Downloads folder")


def main():
    print("\n" + "=" * 75)
    print(" 🚀 STARTING UNIFIED MULTI-AGENT & RAG SYSTEM (HIMAYA)")
    print("=" * 75)

    # 1. Start Retrieval Microservice
    ensure_retrieval_service()

    # 2. Start 5:00 PM Background Cron Daemon
    start_background_daemon()

    print("  [3/3] Launching Interactive Multi-Agent CLI...")
    print("=" * 75 + "\n")

    # 3. Launch CLI
    from cli import main as run_cli
    run_cli()


if __name__ == "__main__":
    main()
