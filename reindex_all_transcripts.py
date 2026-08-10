"""
================================================================================
Qdrant Storage Re-Indexing & Crosstalk Re-Attribution Script
================================================================================
Updates all existing vector payload metadata in qdrant_storage/local_vector_db.json:
- Fixes misattributed speaker turns (e.g. Siddharth's tasks spoken into Dakshinya's mic).
- Canonicalizes all speaker names to standardized canonical forms.
"""

import os
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(__file__))
from transcript_normalizer import reattribute_crosstalk_turn, normalize_speaker_name

def reindex_vector_db():
    db_file = os.path.join(os.path.dirname(__file__), "qdrant_storage", "local_vector_db.json")
    if not os.path.exists(db_file):
        print(f"❌ DB file '{db_file}' not found.")
        return
        
    with open(db_file, "r", encoding="utf-8") as f:
        db_data = json.load(f)
        
    updated_count = 0
    total_count = 0
    
    for collection, c_data in db_data.items():
        points = c_data.get("points", [])
        total_count += len(points)
        for p in points:
            payload = p.get("payload", {})
            orig_spk = payload.get("speaker", "")
            txt = payload.get("text", "")
            
            new_spk, new_txt = reattribute_crosstalk_turn(orig_spk, txt)
            if new_spk != orig_spk:
                payload["speaker"] = new_spk
                payload["text"] = new_txt
                updated_count += 1
            else:
                payload["speaker"] = normalize_speaker_name(orig_spk)
                
    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2)
        
    print(f"✅ RE-INDEXING COMPLETE!")
    print(f"   Total Vectors Processed: {total_count}")
    print(f"   Speaker Crosstalk Re-attributions Fixed: {updated_count}")

if __name__ == "__main__":
    reindex_vector_db()
