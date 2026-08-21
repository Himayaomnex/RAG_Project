"""
================================================================================
Retrieval Service Client (agents/shared/retrieval_client.py)
================================================================================
Single point of contact for all retrieval.
Wraps Dakshinya's Retrieval Service / S2 Endpoint.
Until her remote HTTP endpoint is live, connects to local Qdrant collection
and returns structured EvidenceChunk models.
"""

import os
import sys
import re
from typing import List, Optional, Dict, Any
from .schemas import EvidenceChunk

parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from pipeline import get_vector_db, ensure_pipeline_initialized
from qdrant_client.http.models import Filter, FieldCondition, MatchText, MatchValue


class RetrievalClient:
    """
    Dedicated Client for Dakshinya's S2 Retrieval Service.
    Only this class is allowed to communicate with the vector database / retrieval API.
    """
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.getenv("RETRIEVAL_API_URL")
        self.db = None

    def _get_local_db(self):
        if self.db is None:
            self.db = ensure_pipeline_initialized()
        return self.db

    def query_evidence(
        self,
        query: str,
        speaker_filter: Optional[str] = None,
        date_filter: Optional[str] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        limit: int = 40,
        strategy: str = "precision"  # precision vs completeness
    ) -> List[EvidenceChunk]:
        """
        Retrieves candidate evidence chunks matching the criteria.
        """
        # If external S2 endpoint is configured, call via HTTP
        if self.endpoint_url:
            return self._call_remote_api(query, speaker_filter, date_filter, limit)

        # Otherwise, query Qdrant collection directly
        return self._query_qdrant_internal(query, speaker_filter, date_filter, limit, strategy)

    def _query_qdrant_internal(
        self,
        query: str,
        speaker_filter: Optional[str],
        date_filter: Optional[str],
        limit: int,
        strategy: str
    ) -> List[EvidenceChunk]:
        db = self._get_local_db()
        must_conditions = []
        if speaker_filter and speaker_filter.lower() not in ["all", "everyone", "team"]:
            must_conditions.append(FieldCondition(key="speaker", match=MatchText(text=speaker_filter)))
        if date_filter:
            must_conditions.append(FieldCondition(key="date", match=MatchValue(value=date_filter)))

        query_filter = Filter(must=must_conditions) if must_conditions else None

        if strategy == "completeness":
            # Broad scroll across the collection
            pts, _ = db.client.scroll(collection_name=db.collection_name, limit=max(limit, 500))
            chunks = []
            for p in pts:
                payload = p.payload or {}
                txt = payload.get("text", "")
                spk = payload.get("speaker", "Team")
                dt = payload.get("date", "Unknown Date")
                
                # Apply filter in memory if scrolling
                if speaker_filter and speaker_filter.lower() not in ["all", "team"] and speaker_filter.lower() not in spk.lower():
                    continue
                if date_filter and date_filter.lower() not in dt.lower():
                    continue

                chunk_id = f"chk-{p.id}" if hasattr(p, 'id') else f"chk-{len(chunks)}"
                chunks.append(EvidenceChunk(
                    chunk_id=chunk_id,
                    text=txt,
                    speaker=spk,
                    date=dt,
                    page=str(payload.get("page", "1")),
                    source_file=payload.get("source_file", "transcript.docx"),
                    score=1.0
                ))
            return chunks[:limit]
        else:
            # Semantic Vector Search
            dense_vec = db.dense_model.encode(query)
            if hasattr(dense_vec, 'tolist'):
                dense_vec = dense_vec.tolist()
            try:
                results = db.client.query_points(
                    collection_name=db.collection_name,
                    query=dense_vec,
                    query_filter=query_filter,
                    using="dense",
                    limit=limit
                ).points
            except Exception as e:
                print(f"  - [RetrievalClient Error]: {e}")
                results = []

            chunks = []
            for p in results:
                payload = p.payload or {}
                chunk_id = f"chk-{p.id}" if hasattr(p, 'id') else f"chk-{len(chunks)}"
                chunks.append(EvidenceChunk(
                    chunk_id=chunk_id,
                    text=payload.get("text", ""),
                    speaker=payload.get("speaker", "Team"),
                    date=payload.get("date", "Unknown Date"),
                    page=str(payload.get("page", "1")),
                    source_file=payload.get("source_file", "transcript.docx"),
                    score=float(p.score) if hasattr(p, 'score') else 1.0
                ))
            return chunks

    def _call_remote_api(self, query: str, speaker_filter: Optional[str], date_filter: Optional[str], limit: int) -> List[EvidenceChunk]:
        import urllib.request
        import json
        payload = {"query": query, "speaker": speaker_filter, "date": date_filter, "limit": limit}
        req = urllib.request.Request(
            f"{self.endpoint_url}/retrieve",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [EvidenceChunk(**item) for item in data.get("chunks", [])]


# Global singleton client
retrieval_client = RetrievalClient()
