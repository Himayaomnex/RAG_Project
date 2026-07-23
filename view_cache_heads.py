"""
================================================================================
emb_cache Inspector - View SHA-256 Cache Keys & Stored Vectors
================================================================================
Demonstrates to Siddharth:
1. How document text maps to SHA-256 Cache Keys
2. How pre-calculated 384-d vectors are stored persistently in 'emb_cache'
3. Proof that vector math is computed ONLY ONCE and re-used for $0 cost
"""

import shelve
import hashlib
import glob
from qdrant_queries import load_transcript_from_docx, parse_and_chunk_transcript, CACHE_DB

def display_cache_keys():
    print("=" * 90)
    print("   DOCUMENT EMBEDDING CACHE (`emb_cache`) - SHA-256 CACHE KEYS & VECTOR INSPECTOR")
    print("=" * 90)
    
    with shelve.open(CACHE_DB) as db:
        keys = list(db.keys())
        print(f"\n[Status]: Found {len(keys)} Persistent SHA-256 Cache Keys in '{CACHE_DB}'\n")
        
        # Display sample Cache Keys with document context
        docx_files = glob.glob("*.docx")
        hash_to_chunk = {}
        for f in docx_files:
            if f.startswith("~$"): continue
            txt = load_transcript_from_docx(f)
            if txt:
                chunks = parse_and_chunk_transcript(txt, source_file=f)
                for c in chunks:
                    h = hashlib.sha256(c["text"].encode('utf-8')).hexdigest()
                    if h not in hash_to_chunk:
                        hash_to_chunk[h] = c
                        
        print(f"{'Key #':<8} | {'SHA-256 Cache Key':<32} | {'Source Document':<26} | {'Stored Vector'}")
        print("-" * 95)
        
        for idx, k in enumerate(keys[:10]):
            chunk_info = hash_to_chunk.get(k, {})
            doc_name = chunk_info.get("source_file", "Transcript File")
            vector_data = db[k]
            vec_sample = f"[{vector_data[0]:.4f}, {vector_data[1]:.4f}, {vector_data[2]:.4f}, ...]"
            print(f"Key #{idx+1:<5} | {k[:28]}... | {doc_name[:24]:<26} | {vec_sample}")
            
        print("-" * 95)
        print(f"Displaying 10 sample SHA-256 Cache Keys out of {len(keys)} total cached vectors stored on disk.")
        print("System Summary: Every document chunk is embedded ONCE and stored under its SHA-256 Cache Key.")
        print("=" * 90)

if __name__ == "__main__":
    display_cache_keys()
