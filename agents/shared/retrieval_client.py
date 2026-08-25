"""
================================================================================
Retrieval Service Client (agents/shared/retrieval_client.py)
================================================================================
Single point of contact for all retrieval.
Wraps Dakshinya's Retrieval Service / S2 Endpoint.
Until her remote HTTP endpoint is live, connects to local Qdrant collection
and returns structured EvidenceChunk models.

Retrieval Strategies:
  auto        — Inferred dynamically from query slots at runtime (DEFAULT)
  precision   — Dense ANN semantic search + BM25 re-ranking (Hybrid)
  completeness— Full corpus scroll + date/speaker filter (no ANN)

Hybrid Ranking:
  Precision path fuses dense similarity scores and BM25 lexical scores
  using Reciprocal Rank Fusion (RRF), improving recall for both
  semantic and keyword-heavy queries.
"""

import os
import re
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from .schemas import EvidenceChunk

try:
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False
    print("  [RetrievalClient] rank_bm25 not installed — BM25 re-ranking disabled. Run: pip install rank-bm25")

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

    # ── Strategy auto-selection ────────────────────────────────────────────────

    def _auto_select_strategy(
        self,
        query: str,
        date_filter: Optional[str],
        period_start: Optional[str],
        period_end: Optional[str],
        speaker_filter: Optional[str],
    ) -> str:
        """
        Dynamically selects retrieval strategy based on the slots present.

        Rules (in priority order):
          1. Date or period present  → completeness (need all turns in window)
          2. Speaker/trainee present → precision    (semantic zoom on person)
          3. Query looks like broad status report → completeness
          4. Default                → precision    (semantic ANN + BM25)
        """
        q = query.lower()

        # Explicit date/period window → completeness for 100% coverage
        if date_filter or period_start or period_end:
            return "completeness"

        # Broad status / rollup queries → completeness
        if any(k in q for k in [
            "weekly", "rollup", "this week", "past week", "overall", "all trainees",
            "entire team", "summary of", "give me a summary", "executive"
        ]):
            return "completeness"

        # Speaker-scoped concept query → precision (ANN + BM25 hybrid)
        return "precision"

    # ── Public query_evidence ─────────────────────────────────────────────────

    def query_evidence(
        self,
        query: str,
        speaker_filter: Optional[str] = None,
        date_filter: Optional[str] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        limit: int = 40,
        strategy: str = "auto",   # auto | precision | completeness
    ) -> List[EvidenceChunk]:
        """
        Retrieves candidate evidence chunks matching the criteria.

        strategy="auto" (default) infers the best strategy from query slots.
        Pass strategy="precision" or strategy="completeness" to override.
        """
        resolved_strategy = strategy
        if strategy == "auto":
            resolved_strategy = self._auto_select_strategy(
                query=query,
                date_filter=date_filter,
                period_start=period_start,
                period_end=period_end,
                speaker_filter=speaker_filter,
            )

        print(f"  [RetrievalClient] strategy={resolved_strategy} (requested={strategy}) speaker={speaker_filter} date={date_filter}")

        return self._query_qdrant_internal(
            query=query,
            speaker_filter=speaker_filter,
            date_filter=date_filter,
            period_start=period_start,
            period_end=period_end,
            limit=limit,
            strategy=resolved_strategy
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
                # Retrieve the entire collection (max 2000 points) to prevent
                # older points from page-starving the most recent August points.
                raw_results, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=2000
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
        # PIPELINE 2 (P2): Hybrid Dense ANN + BM25 Lexical Re-ranking
        # Used for precision queries: zooms in on specific concepts & trainees
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
                print(f"  - [RetrievalClient P2 Error]: {e}. Falling back to scroll...")
                raw_results, _ = self.client.scroll(collection_name=self.collection_name, limit=fetch_limit)

        chunks = []
        for p in raw_results:
            payload = p.payload or {}
            txt = payload.get("text", "")
            spk = payload.get("speaker", "Team")
            dt = payload.get("date", "Unknown Date")

            # Apply speaker filter
            if speaker_filter and speaker_filter.lower() not in ["all", "team"]:
                sf = speaker_filter.lower()
                if sf not in spk.lower() and sf not in txt.lower():
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

        # ── Date Sorting (Latest First) ──────────────────────────────────────────
        # Ensure that if no specific date filter is applied, the most recent
        # transcript turns (August 2026) are prioritized over older ones (July).
        import datetime
        chunks.sort(
            key=lambda x: self._parse_date_obj(x.date) or datetime.date.min,
            reverse=True
        )

        # ── BM25 Hybrid Re-ranking (precision path only) ────────────────────────
        if strategy == "precision" and _BM25_AVAILABLE and chunks:
            chunks = self._bm25_rerank(query, chunks, limit)
        else:
            chunks = chunks[:limit]

        return chunks

    def _bm25_rerank(
        self,
        query: str,
        chunks: List[EvidenceChunk],
        limit: int,
        k: int = 60      # RRF constant
    ) -> List[EvidenceChunk]:
        """
        Reciprocal Rank Fusion: fuses dense ANN rank (already in chunks order)
        with BM25 lexical rank to produce a hybrid final ranking.

        RRF score = 1/(k + dense_rank) + 1/(k + bm25_rank)
        """
        if not chunks:
            return chunks

        # BM25 corpus
        corpus = [c.text.lower().split() for c in chunks]
        bm25 = BM25Okapi(corpus)
        bm25_scores = bm25.get_scores(query.lower().split())

        # BM25 rank order (descending score = rank 0 is best)
        bm25_ranks = {i: rank for rank, i in enumerate(sorted(range(len(bm25_scores)), key=lambda x: bm25_scores[x], reverse=True))}

        # RRF fusion
        rrf_scores = []
        for dense_rank, chunk in enumerate(chunks):
            bm25_rank = bm25_ranks.get(dense_rank, len(chunks))
            rrf = 1.0 / (k + dense_rank) + 1.0 / (k + bm25_rank)
            rrf_scores.append((rrf, chunk))

        rrf_scores.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in rrf_scores[:limit]]

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
