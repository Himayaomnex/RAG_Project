"""
================================================================================
Copy RAG_Training Qdrant Database to RAG_COMBINED (copy_rag_training_qdrant.py)
================================================================================
Creates an exact, independent local file copy of RAG_Training's Qdrant database
(`storage.sqlite` & `meta.json`) inside `RAG_COMBINED/qdrant_storage/`.
"""

import os
import sys
import shutil
from qdrant_client import QdrantClient

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def copy_rag_training_qdrant():
    print("=" * 80)
    print("📋 COPYING EXACT QDRANT DATABASE FROM RAG_Training TO RAG_COMBINED")
    print("=" * 80)

    rag_combined_dir = os.path.dirname(os.path.abspath(__file__))
    rag_training_dir = os.path.join(os.path.dirname(rag_combined_dir), "RAG_Training")

    target_qdrant_dir = os.path.join(rag_combined_dir, "qdrant_storage")
    target_collection_dir = os.path.join(target_qdrant_dir, "collection", "teams_dense_collection")

    os.makedirs(target_collection_dir, exist_ok=True)

    src_meta = os.path.join(rag_training_dir, "meta.json")
    src_sqlite = os.path.join(rag_training_dir, "storage.sqlite")

    dest_meta = os.path.join(target_qdrant_dir, "meta.json")
    dest_sqlite = os.path.join(target_collection_dir, "storage.sqlite")

    print(f"\n[1] Source RAG_Training path: {rag_training_dir}")
    print(f"[2] Target RAG_COMBINED Qdrant path: {target_qdrant_dir}")

    if os.path.exists(src_meta) and os.path.exists(src_sqlite):
        shutil.copy2(src_meta, dest_meta)
        shutil.copy2(src_sqlite, dest_sqlite)
        print("✅ Copied meta.json & storage.sqlite directly from RAG_Training.")
    else:
        print("⚠️ Source files not found at root, checking subdirectories...")
        for root, dirs, files in os.walk(rag_training_dir):
            for f in files:
                if f == "meta.json":
                    shutil.copy2(os.path.join(root, f), dest_meta)
                elif f == "storage.sqlite":
                    shutil.copy2(os.path.join(root, f), dest_sqlite)

    print("\n[3] Verifying copied Qdrant database in RAG_COMBINED...")
    client = QdrantClient(path=target_qdrant_dir)
    collection_name = "teams_dense_collection"

    if client.collection_exists(collection_name):
        col_info = client.get_collection(collection_name)
        print("\n" + "=" * 80)
        print("🎉 SUCCESS! SEPARATE COPY OF RAG_Training QDRANT DATABASE CREATED:")
        print(f"   Storage Location: {target_qdrant_dir}")
        print(f"   Collection Name:  {collection_name}")
        print(f"   Total Vectors:    {col_info.points_count}")
        print("=" * 80)
    else:
        print(f"❌ Collection '{collection_name}' not found after copy.")

    client.close()

if __name__ == "__main__":
    copy_rag_training_qdrant()
