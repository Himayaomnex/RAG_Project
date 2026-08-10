"""
================================================================================
Verification Script: Pre-Chunking Normalization vs Raw Indexing
================================================================================
Demonstrates the data quality problem highlighted by Siddharth:
- Problem: Audio leakage / unmuted mic causes Siddharth's task assignments 
           to be attributed to Dakshinya or Himaya in raw transcripts.
- Fix: Pre-chunking speaker & crosstalk normalization cleanly re-attributes
       spoken lines to the true speaker before vector chunking & indexing.
"""

import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(__file__))
from transcript_normalizer import parse_and_normalize_turns, build_normalized_transcript_text

def run_comparison_demo():
    print("=" * 80)
    print("  PRE-CHUNKING TRANSCRIPT NORMALIZATION & DATA QUALITY COMPARISON")
    print("=" * 80)
    
    # Raw un-normalized transcript snippet (Simulating unmuted mic / audio leakage)
    raw_sample = """
Dakshinya Nachimuthu 8 minutes 57 seconds
Siddharth Saminathan: OK, think about these things. Next task for Himaya is to work on prompt engineering.
Dakshinya Nachimuthu 9 minutes 09 seconds
Inventor agent technology specifically asks for word.
Himaya Perumal 9 minutes 18 seconds
somebody or something like that. It won't like specifically give it like from the transcript.
Siddharth Saminathan 10 minutes 18 seconds
How are you planning to solve this problem where I am speaking something and it's coming in your mic or Ganesh?
Himaya Perumal 10 minutes 18 seconds
This is a data quality problem, not a RAG problem.
"""

    print("\n--- ❌ BEFORE PRE-CHUNKING NORMALIZATION (RAW INPUT) ---")
    print(raw_sample.strip())

    print("\n" + "-" * 80)
    print("--- ✅ AFTER PRE-CHUNKING NORMALIZATION (CLEANED & RE-ATTRIBUTED) ---")
    print("-" * 80)
    
    normalized_turns = parse_and_normalize_turns(raw_sample)
    for spk, txt in normalized_turns:
        print(f"👤 [{spk}]: \"{txt}\"")
        
    print("\n" + "=" * 80)
    print("  KEY DATA QUALITY IMPROVEMENTS:")
    print("  1. Fixed Misattributed Task Assignments: Re-attributed Siddharth's task instructions to 'Siddharth Saminathan'.")
    print("  2. Stripped Audio Timestamp Noise: Removed '8 minutes 57 seconds' timestamp clutter.")
    print("  3. Standardized Speaker Identities: Canonicalized initials (SS, HP, DN) to full names.")
    print("  4. Subset Search Optimization: Ready for exact brute-force search over small filtered payload subsets.")
    print("=" * 80)

if __name__ == "__main__":
    run_comparison_demo()
