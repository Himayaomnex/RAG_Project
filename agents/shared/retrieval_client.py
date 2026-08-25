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
import datetime
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer, util
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
        
        storage_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "qdrant_storage")
        os.makedirs(storage_path, exist_ok=True)
        
        connected = False
        if self.qdrant_url:
            try:
                self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=3)
                self.client.get_collections()
                connected = True
            except Exception:
                connected = False
                
        if not connected:
            self.client = QdrantClient(path=storage_path)
            
        self.dense_model = get_shared_dense_model()

    # ── Strategy auto-selection (P1, P2, P3, P4) ──────────────────────────────

    def _auto_select_strategy(
        self,
        query: str,
        date_filter: Optional[str],
        period_start: Optional[str],
        period_end: Optional[str],
        speaker_filter: Optional[str],
    ) -> str:
        """
        Dynamically routes queries to the teammate's 4 exact pipelines:
          • P2 (pipeline_p2_scroll_scan)   — Date/period windows or broad rollup queries (35 chunks, multi-doc balanced)
          • P1 (pipeline_p1_scroll_rerank) — Focused technical, trainee evaluation, or concept queries (top 15 + CustomMeetingReranker)
          • P3 (pipeline_p3_topk_vector)   — Single-shot fast vector search (fixed K=15)
          • P4 (pipeline_p4_map_reduce)    — Full-corpus grouped by document
        """
        q = query.lower()

        # Broad status / rollup / cohort-wide executive queries -> P4 Full-Corpus Scan
        broad_rollup_signals = [
            "weekly", "rollup", "this week", "past week", "overall", "all trainees",
            "entire team", "summary of", "give me a summary", "executive",
            "status report", "project update", "project status", "team status",
            "full breakdown", "full report", "complete report", "complete summary",
            "how is the team", "how are the trainees", "how is everyone",
            "what is the state", "what is the status", "what is the overall",
            "progress report", "all sessions", "entire cohort", "the whole team",
            "across the team", "for the team", "for all", "for everyone",
        ]
        if any(k in q for k in broad_rollup_signals):
            return "p4"

        # Explicit date/period window -> P2 Document-Balanced Scroll Scan
        if date_filter or period_start or period_end:
            return "p2"

        # Focused / Concept / Mentor assessment queries -> P1 Scroll + Custom Reranker
        return "p1"

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

    def _resolve_month_range(self, date_str: Optional[str]) -> Optional[tuple]:
        if not date_str:
            return None
        months = {
            "january": (1, 31), "february": (2, 28), "march": (3, 31), "april": (4, 30),
            "may": (5, 31), "june": (6, 30), "july": (7, 31), "august": (8, 31),
            "september": (9, 30), "october": (10, 31), "november": (11, 30), "december": (12, 31)
        }
        cleaned = re.sub(r'[^\w\s]', '', date_str).lower().strip()
        if cleaned in months:
            m_idx, max_days = months[cleaned]
            return datetime.date(2026, m_idx, 1), datetime.date(2026, m_idx, max_days)
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
            try:
                from router import _TRAINEE_ROLE_MAP
                role_map = _TRAINEE_ROLE_MAP
            except Exception:
                role_map = {}
            # Find which trainee names appear in the query — only set filter if exactly one matches
            matched = [canonical for key, canonical in role_map.items() if key in q_low]
            if len(matched) == 1:
                speaker_filter = matched[0]

        # Resolve month ranges (e.g. "July" -> July 1 to July 31)
        month_range = self._resolve_month_range(period_start or date_filter)
        if month_range and not period_end:
            period_start_obj, period_end_obj = month_range
            date_filter = None  # Handled by range filter
        else:
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
            months_pattern = "January|February|March|April|May|June|July|August|September|October|November|December"
            m = re.search(rf'(\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{months_pattern})(?:\s+\d{{2,4}})?|(?:{months_pattern})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,?\s*\d{{2,4}})?)', query, re.IGNORECASE)
            if m:
                date_filter = m.group(1).strip()

        # -------------------------------------------------------------------------
        # THE 4 NATIVE RETRIEVAL PIPELINES (Extracted from teammate's benchmark architecture)
        # -------------------------------------------------------------------------
        if strategy in ["p1", "p1_scroll_rerank"]:
            # P1: Scroll + Document-Balanced Selection + CustomMeetingReranker (Top 15)
            raw_results = self._pipeline_p1_scroll_rerank(query, top_per_doc=2, total_candidates=limit or 15)

        elif strategy in ["p2", "p2_scroll_scan"]:
            # P2: Scroll API Scan with Document-Balanced Selection (No Reranker, Top 35)
            raw_results = self._pipeline_p2_scroll_scan(query, top_per_doc=4, total_candidates=limit or 35)

        elif strategy in ["p3", "p3_topk_vector"]:
            # P3: Top-K Vector Search (Document-Balanced Top 15, No Reranker)
            raw_results = self._pipeline_p3_topk_vector(query, top_k=limit or 15)

        elif strategy in ["p4", "p4_map_reduce", "completeness"]:
            # P4: Full-Corpus Ingestion (100% of all document chunks)
            raw_results = self._pipeline_p4_map_reduce(query)

        else:
            # Default to P1
            raw_results = self._pipeline_p1_scroll_rerank(query, top_per_doc=2, total_candidates=limit or 15)

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
        # Sort chunks descending so the newest transcript turns (August 2026) take precedence
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

    # ── NATIVE PIPELINES (P1, P2, P3, P4) ────────────────────────────────────

    def _compute_batched_cosine_scores(self, query: str, chunks: List[Any]) -> List[tuple]:
        """Computes in-memory cosine similarity between query and candidates."""
        if not chunks:
            return []
        q_emb = self.dense_model.encode(query, convert_to_tensor=True)
        texts = [(c.payload or {}).get("text", "") for c in chunks]
        doc_embs = self.dense_model.encode(texts, convert_to_tensor=True)
        sims = util.cos_sim(q_emb, doc_embs)[0]
        
        return [(float(sims[i].item()), c) for i, c in enumerate(chunks)]

    def _pipeline_p1_scroll_rerank(self, query: str, top_per_doc: int = 2, total_candidates: int = 15) -> List[Any]:
        """
        P1 — Scroll + Document-Balanced Candidates + Custom Reranker
        """
        raw_results, _ = self.client.scroll(collection_name=self.collection_name, limit=2000)
        scored_pairs = self._compute_batched_cosine_scores(query, raw_results)
        
        by_doc = {}
        for score, p in scored_pairs:
            doc = (p.payload or {}).get("source_file", "unknown")
            by_doc.setdefault(doc, []).append((score, p))
            
        balanced_candidates = []
        for doc_file, plist in by_doc.items():
            plist.sort(key=lambda x: x[0], reverse=True)
            balanced_candidates.extend(plist[:top_per_doc])
            
        balanced_candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = balanced_candidates[:total_candidates]
        
        reranker = CustomMeetingReranker()
        return reranker.rerank(query, top_candidates)

    def _pipeline_p2_scroll_scan(self, query: str, top_per_doc: int = 4, total_candidates: int = 35) -> List[Any]:
        """
        P2 — Scroll API Scan with Document-Balanced Selection (No Reranker)
        """
        raw_results, _ = self.client.scroll(collection_name=self.collection_name, limit=2000)
        scored_pairs = self._compute_batched_cosine_scores(query, raw_results)
        
        by_doc = {}
        for score, p in scored_pairs:
            doc = (p.payload or {}).get("source_file", "unknown")
            by_doc.setdefault(doc, []).append((score, p))
            
        balanced_candidates = []
        for doc_file, plist in by_doc.items():
            plist.sort(key=lambda x: x[0], reverse=True)
            balanced_candidates.extend(plist[:top_per_doc])
            
        balanced_candidates.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in balanced_candidates[:total_candidates]]

    def _pipeline_p3_topk_vector(self, query: str, top_k: int = 15) -> List[Any]:
        """
        P3 — Top-K Vector Search (Document-Balanced Top 15, No Reranker)
        """
        raw_results, _ = self.client.scroll(collection_name=self.collection_name, limit=2000)
        scored_pairs = self._compute_batched_cosine_scores(query, raw_results)
        
        by_doc = {}
        for score, p in scored_pairs:
            doc = (p.payload or {}).get("source_file", "unknown")
            by_doc.setdefault(doc, []).append((score, p))
            
        balanced_candidates = []
        for doc_file, plist in by_doc.items():
            plist.sort(key=lambda x: x[0], reverse=True)
            balanced_candidates.extend(plist[:2])
            
        balanced_candidates.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in balanced_candidates[:top_k]]

    def _pipeline_p4_map_reduce(self, query: str) -> List[Any]:
        """
        P4 — Map-Reduce / Full-Corpus Scan Strategy (100% of all meeting chunks)
        """
        raw_results, _ = self.client.scroll(collection_name=self.collection_name, limit=2000)
        return raw_results

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


class CustomMeetingReranker:
    """Heuristic scoring reranker: Speaker match (+0.5), Date match (+0.5), Topic density (+0.05/keyword)."""
    def rerank(self, query: str, candidates: List[Any]) -> List[Any]:
        query_lower = query.lower()
        stop_words = {"what", "is", "the", "difference", "between", "an", "and", "according", "to", "did", "say", "about", "how", "are", "you"}
        keywords = [w for w in re.findall(r'\b\w+\b', query_lower) if w not in stop_words and len(w) > 3]
        
        reranked = []
        for item in candidates:
            if isinstance(item, tuple):
                score, res = item
            else:
                score = getattr(item, 'score', 1.0)
                res = item
                
            payload = getattr(res, 'payload', {}) or {}
            chunk_speaker = payload.get("speaker", "").lower()
            try:
                from router import _TRAINEE_ROLE_MAP, _PINNED_MENTOR_ROLES
                known_speakers = [k.lower() for k in _TRAINEE_ROLE_MAP.keys()] + list(_PINNED_MENTOR_ROLES)
            except Exception:
                known_speakers = ["siddharth"]
            if any(s in query_lower and s in chunk_speaker for s in known_speakers):
                score += 0.5
                
            chunk_date = payload.get("date", "").lower()
            if chunk_date and chunk_date != "unknown date" and chunk_date in query_lower:
                score += 0.5
                
            chunk_text = payload.get("text", "").lower()
            keyword_matches = sum(1 for k in keywords if k in chunk_text)
            score += (keyword_matches * 0.05)
            
            reranked.append((score, res))
            
        reranked.sort(key=lambda x: x[0], reverse=True)
        return [res for _, res in reranked]


# Global singleton client
retrieval_client = RetrievalClient()
