"""
================================================================================
Automatic Download Folder Watcher Daemon (`auto_folder_watcher.py`)
================================================================================
Monitors your Windows 'Downloads' folder. Whenever you download a new Teams 
transcript (.docx) from Teams, this script automatically moves it to your 
RAG DEMO project directory and triggers instant incremental indexing!

Includes STRICT Transcript Content Verification to ignore random Word files.
"""

import os
import shutil
import time
import glob
import re
from pathlib import Path
from qdrant_queries import main as run_rag_indexing, load_transcript_from_docx

DOWNLOADS_DIR = str(Path.home() / "Downloads")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def is_valid_teams_transcript(file_path: str) -> bool:
    """
    STRICT VERIFICATION: Checks if a Word file is actually a Teams Transcript.
    Ignores non-transcript Word files (e.g., resumes, forms, reports).
    """
    try:
        txt = load_transcript_from_docx(file_path)
        if not txt or len(txt.strip()) < 30:
            return False
            
        # Check for Teams speaker dialogue patterns (e.g., timestamp HH:MM or known speaker turn markers)
        has_timestamps = bool(re.search(r"\b\d{1,2}:\d{2}\b", txt))
        has_known_speakers = any(name in txt for name in ["Siddharth", "Himaya", "Dakshinya", "Ganesh", "Speaker"])
        
        # Valid if it contains Teams timestamps or speaker dialogue turns
        return has_timestamps or has_known_speakers
    except Exception:
        return False

def watch_downloads_folder():
    print("=" * 80)
    print(" 📂 AUTOMATIC TEAMS TRANSCRIPT DOWNLOAD WATCHER DAEMON")
    print("=" * 80)
    print(f"[Monitoring]: Windows Downloads folder -> '{DOWNLOADS_DIR}'")
    print(f"[Destination]: RAG DEMO Project folder  -> '{PROJECT_DIR}'")
    print(f"[Filter]: Strict Teams Transcript Content Verification (Ignores non-transcript Word docs)")
    print("\n[Status]: Active & Listening. Download a transcript from Teams now...")
    print("Press Ctrl+C to stop.\n" + "-" * 80)
    
    known_downloads = set(glob.glob(os.path.join(DOWNLOADS_DIR, "*.docx")))
    
    try:
        while True:
            current_downloads = set(glob.glob(os.path.join(DOWNLOADS_DIR, "*.docx")))
            new_files = current_downloads - known_downloads
            
            for file_path in new_files:
                filename = os.path.basename(file_path)
                if filename.startswith("~$"):
                    continue
                    
                # Strict Transcript Verification
                if not is_valid_teams_transcript(file_path):
                    print(f"   [IGNORED NON-TRANSCRIPT WORD FILE]: '{filename}' (Not a Teams Transcript)")
                    continue
                    
                dest_path = os.path.join(PROJECT_DIR, filename)
                print(f"\n[NEW TEAMS TRANSCRIPT VERIFIED & DETECTED]: '{filename}'")
                time.sleep(1) # Ensure download finishes
                
                shutil.move(file_path, dest_path)
                print(f"   [+] Automatically moved to project folder: '{dest_path}'")
                print("   [+] Triggering Automatic Incremental RAG Indexing...")
                
                # Run indexer for new file
                run_rag_indexing()
                print("   [+] Incremental Indexing Complete! New transcript is live!")
                
            known_downloads = current_downloads
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n[Watcher Stopped].")

if __name__ == "__main__":
    watch_downloads_folder()
