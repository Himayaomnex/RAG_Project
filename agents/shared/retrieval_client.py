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
import re
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from .schemas import EvidenceChunk

load_dotenv()

_GLOBAL_DENSE_MODEL = None

def get_shared_dense_model():
    global _GLOBAL_DENSE_MODEL
    if _GLOBAL_DENSE_MODEL is None:
        _GLOBAL_DENSE_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _GLOBAL_DENSE_MODEL


class RetrievalClient:
    """
    Dedicated Client for Dakshinya's S2 Retrieval Service.
    Only this class is allowed to communicate with the vector database / retrieval API.
    """
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.getenv("RETRIEVAL_API_URL")
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "teams_dense_collection")
        
        if self.qdrant_url:
            self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
        else:
            self.client = QdrantClient(location=":memory:")
            
        self.dense_model = get_shared_dense_model()

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
        return self._query_qdrant_internal(
            query=query,
            speaker_filter=speaker_filter,
            date_filter=date_filter,
            period_start=period_start,
            period_end=period_end,
            limit=limit,
            strategy=strategy
        )

    def _parse_date_obj(self, date_str: str):
        if not date_str:
            return None
        import datetime
        # Strip punctuation like '?', '.', ','
        date_clean = re.sub(r'[^\w\s]', '', date_str)
        # Only replace ordinal suffixes following a digit (e.g. '21st' -> '21', NOT 'August' -> 'Augus')
        date_clean = re.sub(r'(?<=\d)(st|nd|rd|th)\b', '', date_clean, flags=re.IGNORECASE).strip()
        
        # Append default year 2026 if no year present
        if not re.search(r'\b20\d{2}\b', date_clean):
            date_clean += ' 2026'

        for fmt in ["%d %B %Y", "%B %d %Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                return datetime.datetime.strptime(date_clean, fmt).date()
            except Exception:
                continue

        # Fallback: extract day and month
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        for idx, m in enumerate(months, start=1):
            if m in date_clean.lower():
                d_match = re.search(r'\b\d{1,2}\b', date_clean)
                if d_match:
                    try:
                        return datetime.date(2026, idx, int(d_match.group(0)))
                    except Exception:
                        pass
        return None

    def _query_qdrant_internal(
        self,
        query: str,
        speaker_filter: Optional[str],
        date_filter: Optional[str],
        period_start: Optional[str],
        period_end: Optional[str],
        limit: int,
        strategy: str
    ) -> List[EvidenceChunk]:
        # Auto-detect speaker filter from query if not explicitly provided
        q_low = query.lower()
        if not speaker_filter or speaker_filter.lower() in ["all", "everyone", "team"]:
            if "ganesh" in q_low and "himaya" not in q_low and "dakshinya" not in q_low:
                speaker_filter = "Ganesh"
            elif "himaya" in q_low and "ganesh" not in q_low and "dakshinya" not in q_low:
                speaker_filter = "Himaya"
            elif "dakshinya" in q_low and "ganesh" not in q_low and "himaya" not in q_low:
                speaker_filter = "Dakshinya"

        # Check for date range in query like "between July 27 and August 4" or "from July 27 to August 4"
        range_match = re.search(r'(?:between|from)\s+([a-zA-Z0-9\s]+?)\s+(?:and|to)\s+([a-zA-Z0-9\s\?]+)', query, re.IGNORECASE)
        if range_match and not period_start and not period_end:
            p_s = self._parse_date_obj(range_match.group(1))
            p_e = self._parse_date_obj(range_match.group(2))
            if p_s and p_e:
                period_start_obj = min(p_s, p_e)
                period_end_obj = max(p_s, p_e)
            else:
                period_start_obj = self._parse_date_obj(period_start)
                period_end_obj = self._parse_date_obj(period_end)
        else:
            period_start_obj = self._parse_date_obj(period_start)
            period_end_obj = self._parse_date_obj(period_end)

        # Auto-detect single date filter only if no period range was detected
        if not date_filter and not period_start_obj and not period_end_obj:
            months = "January|February|March|April|May|June|July|August|September|October|November|December"
            m = re.search(rf'(\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{months})(?:\s+\d{{2,4}})?|(?:{months})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,?\s*\d{{2,4}})?)', query, re.IGNORECASE)
            if m:
                date_filter = m.group(1).strip()

        # -------------------------------------------------------------------------
        # PIPELINE 4 (P4): Broad Full-Corpus Completeness Ingestion
        # Used by Manager Weekly Rollup & Single-Session Catch-Up for 100% coverage
        # -------------------------------------------------------------------------
        if strategy == "completeness":
            try:
                fetch_limit = min(max(limit * 3, 300), 1000)
                raw_results, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=fetch_limit
                )
            except Exception as e:
                print(f"  - [RetrievalClient P4 Error]: {e}. Falling back to query_points...")
                dense_vec = self.dense_model.encode(query).tolist()
                raw_results = self.client.query_points(
                    collection_name=self.collection_name,
                    query=dense_vec,
                    using="dense",
                    limit=limit * 2
                ).points

        # -------------------------------------------------------------------------
        # PIPELINES 1 & 2 (P1/P2): Dense Semantic Vector Search + Precision Ranking
        # Used by Mentor Trainee Assessment to zoom in on specific concepts & code
        # -------------------------------------------------------------------------
        else:
            dense_vec = self.dense_model.encode(query)
            if hasattr(dense_vec, 'tolist'):
                dense_vec = dense_vec.tolist()
            try:
                fetch_limit = min(max(limit * 2, 100), 300)
                raw_results = self.client.query_points(
                    collection_name=self.collection_name,
                    query=dense_vec,
                    using="dense",
                    limit=fetch_limit
                ).points
            except Exception as e:
                print(f"  - [RetrievalClient P1/P2 Error]: {e}. Falling back to scroll...")
                raw_results, _ = self.client.scroll(collection_name=self.collection_name, limit=fetch_limit)

        chunks = []
        for p in raw_results:
            payload = p.payload or {}
            txt = payload.get("text", "")
            spk = payload.get("speaker", "Team")
            dt = payload.get("date", "Unknown Date")

            # Apply speaker filter
            if speaker_filter and speaker_filter.lower() not in ["all", "team"]:
                if speaker_filter.lower() not in spk.lower() and "siddharth" not in spk.lower():
                    continue

            # Apply Date Range filter if present
            chunk_dt_obj = self._parse_date_obj(dt)
            if period_start_obj and period_end_obj:
                if not chunk_dt_obj or not (period_start_obj <= chunk_dt_obj <= period_end_obj):
                    continue
            elif period_start_obj:
                if not chunk_dt_obj or chunk_dt_obj < period_start_obj:
                    continue
            elif period_end_obj:
                if not chunk_dt_obj or chunk_dt_obj > period_end_obj:
                    continue
            elif date_filter:
                df_tokens = re.findall(r'[a-zA-Z0-9]+', date_filter.lower())
                dt_low = dt.lower()
                if not all(tok in dt_low for tok in df_tokens if tok not in ["session", "meeting", "the", "training"]):
                    continue

            chunk_id = f"chk-{p.id}" if hasattr(p, 'id') else f"chk-{len(chunks)}"
            chunks.append(EvidenceChunk(
                chunk_id=chunk_id,
                text=txt,
                speaker=spk,
                date=dt,
                page=str(payload.get("page", "1")),
                source_file=payload.get("source_file", "transcript.docx"),
                score=float(p.score) if hasattr(p, 'score') else 1.0
            ))

            if len(chunks) >= limit:
                break

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
