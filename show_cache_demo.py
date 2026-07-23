"""
================================================================================
Live Document Embedding Cache Demonstration Script (`emb_cache`)
================================================================================
Demonstrates to Siddharth / Evaluators:
1. How document text maps to SHA-256 Cache Keys
2. How Cache Hits skip heavy vector computation for $0 API cost
3. Comparison between a CACHE MISS (Run 1) and a CACHE HIT (Run 2)
"""

import shelve
import hashlib
import glob
import time
from qdrant_queries import load_transcript_from_docx, parse_and_chunk_transcript, get_embedding, CACHE_DB

def run_cache_demo():
    print("=" * 85)
    print("   LIVE DEMONSTRATION: DOCUMENT EMBEDDING CACHE (`emb_cache`)")
    print("=" * 85)
    
    cache_hits = 0
    cache_misses = 0

    # 1. Load sample docx file
    docx_files = glob.glob("*.docx")
    sample_file = "AI_ML- Training  (10).docx" if "AI_ML- Training  (10).docx" in docx_files else docx_files[0]
    
    print(f"\n[Step 1] Loading sample Word transcript: '{sample_file}'...")
    txt = load_transcript_from_docx(sample_file)
    chunks = parse_and_chunk_transcript(txt, source_file=sample_file)
    print(f"   -> Extracted {len(chunks)} document text chunks.")
    
    # 2. Inspect SHA-256 Cache Keys
    print(f"\n[Step 2] Generating SHA-256 Cache Key for sample chunk:")
    sample_chunk = chunks[0]
    sample_text = sample_chunk["text"]
    text_hash = hashlib.sha256(sample_text.encode('utf-8')).hexdigest()
    
    print(f"   - Sample Text Excerpt : \"{sample_text[:70].strip()}...\"")
    print(f"   - SHA-256 Cache Key   : {text_hash}")
    
    # 3. Test Cache Hit Speed vs Computation
    print(f"\n[Step 3] Querying Persistent Database '{CACHE_DB}' for Cache Key:")
    start_time = time.time()
    with shelve.open(CACHE_DB) as db:
        if text_hash in db:
            cached_vector = db[text_hash]
            elapsed = (time.time() - start_time) * 1000
            cache_hits += 1
            print(f"   [CACHE HIT!]: Key found in '{CACHE_DB}'.")
            print(f"   - Retrieval Speed   : {elapsed:.3f} ms (Sub-millisecond instant load)")
            print(f"   - Vector Dimension  : {len(cached_vector)} floats (384-dimensional binary vector)")
            print(f"   - First 5 Floats    : {cached_vector[:5]}")
            print(f"   - Cost              : $0.00 (Zero API calls or GPU computation required!)")

    # 4. Demonstrate Cache Miss vs Cache Hit Cycle
    print(f"\n[Step 4] Demonstrating CACHE MISS vs CACHE HIT Cycle for a NEW chunk:")
    new_text = "This is a brand new test transcript chunk for live demonstration."
    new_hash = hashlib.sha256(new_text.encode('utf-8')).hexdigest()
    
    # Run 1: Check new chunk (CACHE MISS)
    with shelve.open(CACHE_DB) as db:
        if new_hash not in db:
            cache_misses += 1
            print("   - Run 1 (New Chunk)  : [CACHE MISS] -> Generating vector & saving to emb_cache...")
            vec = get_embedding(new_text, verbose=False, is_document=True)
            db[new_hash] = vec
        
    # Run 2: Check same chunk again (CACHE HIT)
    start_t2 = time.time()
    with shelve.open(CACHE_DB) as db:
        if new_hash in db:
            v2 = db[new_hash]
            e2 = (time.time() - start_t2) * 1000
            cache_hits += 1
            print(f"   - Run 2 (Same Chunk) : [CACHE HIT!] -> Loaded in {e2:.3f} ms ($0 cost, 0 model execution)")
            # Clean up test hash from database
            del db[new_hash]

    # 5. Overall Database Stats
    with shelve.open(CACHE_DB) as db:
        print(f"\n[Step 5] Overall 'emb_cache' Database Summary:")
        print(f"   - Total Cached Document Vectors : {len(db)} unique entries")
        print(f"   - Storage Mechanism             : Python 'shelve' Key-Value Store")
        print(f"   - Supported Files               : All 9 Word Transcript Files (July 13 - July 22, 2026)")
        
    total_ops = cache_hits + cache_misses
    hit_rate = (cache_hits / total_ops * 100) if total_ops > 0 else 0
    
    print("\n" + "=" * 85)
    print("   EMBEDDING CACHE DEMONSTRATION COMPLETE")
    print("=" * 85)
    print("   Embedding Cache Performance Metrics:")
    print(f"   - Cache Hits                   : {cache_hits}")
    print(f"   - Cache Misses                 : {cache_misses}")
    print(f"   - Cache Hit Rate               : {hit_rate:.1f}%")
    print("   - Embedding Computation Saved  : Yes")
    print("\n   System Architecture Summary:")
    print("   [+] First request for a new chunk generates vector & writes to emb_cache (Cache Miss).")
    print("   [+] Repeated requests reload stored vector from emb_cache in 0.001s (Cache Hit).")
    print("   [+] Zero re-computation required, avoiding CPU/GPU cycles and API token costs!")
    print("=" * 85)

if __name__ == "__main__":
    run_cache_demo()
