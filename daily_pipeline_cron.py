"""
================================================================================
Automated Daily Rollup Cron & Pipeline Runner (daily_pipeline_cron.py)
================================================================================
Automated agentic pipeline requested by mentor Siddharth:
1. Ingests new Teams meeting transcript (.docx) files from the Downloads folder.
2. Updates Dakshinya's Qdrant RAG vector collection.
3. Reads Ganesh's structured Knowledge Base (kb_readonly).
4. Generates a multi-tab Daily Rollup Excel workbook (.xlsx).
5. Saves the final report directly to Google Drive and local deliverables directory.

Usage:
    python daily_pipeline_cron.py --run-now          # Execute rollup & export immediately
    python daily_pipeline_cron.py --watch            # Continuous watcher on Downloads folder
    python daily_pipeline_cron.py --schedule 17:00   # Run daily at 5:00 PM
================================================================================
"""

import os
import sys
import time
import shutil
import argparse
import datetime
from typing import Optional, List, Dict, Any

# Ensure workspace root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.shared.kb_client import kb_client
from daily_excel_generator import generate_daily_rollup_excel


DEFAULT_DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
SOURCE_DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Source_Documents")


def find_new_transcript_files(watch_dir: str) -> List[str]:
    """Finds newly downloaded transcript .docx files in the target directory."""
    if not os.path.exists(watch_dir):
        return []
    matches = []
    for f in os.listdir(watch_dir):
        f_lower = f.lower()
        if f_lower.endswith(".docx") and ("training" in f_lower or "ai_ml" in f_lower or "meeting" in f_lower or "transcript" in f_lower):
            matches.append(os.path.join(watch_dir, f))
    return matches


def run_daily_pipeline(
    transcript_file: Optional[str] = None,
    gdrive_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the full end-of-day agentic pipeline:
    1. Ingests/syncs new transcript if present
    2. Reads live Knowledge Base facts
    3. Exports Excel rollup to Google Drive
    """
    t0 = time.time()
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    print(f"\n{'='*70}")
    print(f" [Daily Pipeline] Running Daily Rollup for {today_str}")
    print(f"{'='*70}")

    # Step 1: Check/Ingest Transcript
    if transcript_file and os.path.exists(transcript_file):
        print(f"  [1/3] New transcript detected: {os.path.basename(transcript_file)}")
        os.makedirs(SOURCE_DOCS_DIR, exist_ok=True)
        dest = os.path.join(SOURCE_DOCS_DIR, os.path.basename(transcript_file))
        shutil.copy2(transcript_file, dest)
        print(f"        Copied to local Source_Documents: {dest}")
        # Note: Ingestion into Qdrant is triggered via retrieval service / auto_folder_watcher
    else:
        print(f"  [1/3] Using latest indexed transcripts in Qdrant & Knowledge Base.")

    # Step 2: Read Knowledge Base Status
    print(f"  [2/3] Reading structured state from Ganesh's Knowledge Base (Supabase)...")
    person_states = kb_client.get_person_state()
    active_trainees = [p for p in person_states if p.get("person") != "Siddharth Saminathan"]
    for t in active_trainees:
        print(f"        • {t.get('person')}: Open={t.get('assignments_open')}, Delivered={t.get('assignments_delivered')}, Gaps={(t.get('concepts_confused') or 0) + (t.get('concepts_partial') or 0)}")

    # Step 3: Generate Multi-Tab Excel in Google Drive
    print(f"  [3/3] Generating formatted Excel report and syncing to Google Drive...")
    excel_path = generate_daily_rollup_excel(target_date=today_str, gdrive_dir=gdrive_dir)

    latency = round(time.time() - t0, 2)
    print(f"\n{'='*70}")
    print(f" [Daily Pipeline] SUCCESS in {latency}s")
    print(f" Rollup Workbook: {excel_path}")
    print(f"{'='*70}\n")

    return {
        "status": "success",
        "date": today_str,
        "excel_path": excel_path,
        "latency_seconds": latency,
        "trainees_audited": len(active_trainees)
    }


def start_watcher(watch_dir: str, check_interval_seconds: int = 15):
    """Monitors the Downloads folder for new transcript drops."""
    print(f"[Watcher Daemon] Monitoring '{watch_dir}' for new Teams .docx transcripts (interval: {check_interval_seconds}s)...")
    seen_files = set(find_new_transcript_files(watch_dir))

    while True:
        try:
            current_files = set(find_new_transcript_files(watch_dir))
            new_files = current_files - seen_files

            if new_files:
                for nf in new_files:
                    print(f"\n[Watcher Alert] New transcript file discovered: {nf}")
                    run_daily_pipeline(transcript_file=nf)
                seen_files = current_files

            time.sleep(check_interval_seconds)
        except KeyboardInterrupt:
            print("\n[Watcher Daemon] Stopped by user.")
            break
        except Exception as e:
            print(f"[Watcher Error] {e}")
            time.sleep(check_interval_seconds)


def start_agentic_daemon(
    watch_dir: str = DEFAULT_DOWNLOADS,
    target_time_str: Optional[str] = None,
    gdrive_dir: Optional[str] = None,
    check_interval_seconds: int = 15
):
    """
    Unified Agentic Daemon:
    1. Watches Downloads folder for new Teams transcripts continuously.
    2. Automatically executes the daily rollup at the scheduled time (e.g., 5:00 PM or 4:00 PM).
    """
    sched_time = target_time_str or os.getenv("CRON_SCHEDULE_TIME", "17:00")
    print("=" * 70)
    print(" 🤖 AGENTIC DAILY ROLLUP DAEMON & CRON")
    print("=" * 70)
    print(f"  [Folder Watcher] Monitoring: '{watch_dir}'")
    print(f"  [Daily Schedule] Automated trigger at: {sched_time} daily")
    print(f"  [Google Drive]   Sync destination: {gdrive_dir or os.getenv('GOOGLE_DRIVE_FOLDER', 'deliverables/daily_rollups/')}")
    print(f"  [Status]         Active & Listening. Press Ctrl+C to stop.")
    print("=" * 70 + "\n")

    seen_files = set(find_new_transcript_files(watch_dir))
    executed_today = False

    while True:
        try:
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")

            # 1. Scheduled Time Check (e.g., 4:00 PM / 5:00 PM)
            if current_time == sched_time and not executed_today:
                print(f"\n[Cron Trigger] Daily scheduled time reached ({sched_time}). Generating daily rollup...")
                run_daily_pipeline(gdrive_dir=gdrive_dir)
                executed_today = True

            if current_time != sched_time:
                executed_today = False

            # 2. File-drop Check (Immediate trigger on new transcript in Downloads)
            current_files = set(find_new_transcript_files(watch_dir))
            new_files = current_files - seen_files

            if new_files:
                for nf in new_files:
                    print(f"\n[Watcher Trigger] New transcript detected: {os.path.basename(nf)}")
                    run_daily_pipeline(transcript_file=nf, gdrive_dir=gdrive_dir)
                seen_files = current_files

            time.sleep(check_interval_seconds)
        except KeyboardInterrupt:
            print("\n[Agentic Daemon] Stopped by user.")
            break
        except Exception as e:
            print(f"[Daemon Error] {e}")
            time.sleep(check_interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Daily Rollup Pipeline")
    parser.add_argument("--run-now", action="store_true", help="Execute daily rollup immediately")
    parser.add_argument("--daemon", action="store_true", help="Start continuous unified daemon (Watcher + 5:00 PM Cron)")
    parser.add_argument("--watch", action="store_true", help="Start continuous folder watcher only")
    parser.add_argument("--schedule", type=str, default=None, help="Schedule daily execution time (e.g. 16:00 or 17:00)")
    parser.add_argument("--watch-dir", type=str, default=DEFAULT_DOWNLOADS, help="Directory to watch for transcripts")
    parser.add_argument("--gdrive", type=str, default=None, help="Google Drive folder path to save Excel copy")

    args = parser.parse_args()

    if args.daemon:
        start_agentic_daemon(watch_dir=args.watch_dir, target_time_str=args.schedule, gdrive_dir=args.gdrive)
    elif args.watch:
        start_watcher(args.watch_dir)
    elif args.schedule:
        start_agentic_daemon(watch_dir=args.watch_dir, target_time_str=args.schedule, gdrive_dir=args.gdrive)
    else:
        # Default / --run-now: execute run-now
        run_daily_pipeline(gdrive_dir=args.gdrive)

