"""
================================================================================
emb_cache Inspector - View Document Cache Metadata & File Origins
================================================================================
"""

import shelve
import glob
import hashlib
from qdrant_queries import load_transcript_from_docx, parse_and_chunk_transcript, CACHE_DB

def inspect_emb_cache():
    print("=" * 80)
    print("   DOCUMENT EMBEDDING CACHE (`emb_cache`) - FILE ORIGIN INSPECTOR")
    print("=" * 80)
    
    docx_files = glob.glob("*.docx")
    hash_to_meta = {}
    
    # Build text hash to file mapping across all 9 Word transcripts
    for file_path in docx_files:
        if file_path.startswith("~$"):
            continue
        txt = load_transcript_from_docx(file_path)
        if txt:
            chunks = parse_and_chunk_transcript(txt, source_file=file_path)
            for c in chunks:
                h = hashlib.sha256(c["text"].encode('utf-8')).hexdigest()
                if h not in hash_to_meta:
                    hash_to_meta[h] = {
                        "file": file_path,
                        "date": c["date"],
                        "speaker": c["speaker"],
                        "page": c["page"],
                        "excerpt": c["text"][:60].replace("\n", " ") + "..."
                    }

    with shelve.open(CACHE_DB) as db:
        keys = list(db.keys())
        print(f"\nTotal Key-Value Pairs stored in '{CACHE_DB}': {len(keys)}\n")
        print(f"{'SHA-256 Key (First 16 chars)':<30} | {'Source Document File':<30} | {'Date':<15} | {'Vector Size'}")
        print("-" * 90)
        
        for k in keys[:15]: # Display first 15 sample entries
            meta = hash_to_meta.get(k, {"file": "Unknown File", "date": "Unknown", "excerpt": ""})
            val = db[k]
            vec_len = len(val["vector"]) if isinstance(val, dict) else len(val)
            print(f"{k[:26]}... | {meta['file'][:28]:<30} | {meta['date']:<15} | 384-d ({vec_len} floats)")
            
        print("-" * 90)
        print(f"Showing first 15 entries out of {len(keys)} total cached vectors.")

if __name__ == "__main__":
    inspect_emb_cache()
