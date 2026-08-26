"""
================================================================================
Pure API Retrieval Service Client (agents/shared/retrieval_client.py)
================================================================================
Dedicated HTTP Client for Dakshinya's S2 Retrieval & S3 Evaluation Service.
Communicates directly with the FastAPI endpoints on http://127.0.0.1:8000:
  • POST /query/retrieve-only  — Primary retrieval & reranking endpoint (P1-P4)
  • GET  /filters/metadata     — Live speaker, date, and source file discovery
  • GET  /health               — System and Qdrant Cloud cluster health check
  • POST /evaluate/query       — System 3 automated LLM Judge evaluation
  • POST /ingest/upload        — Single-document transcript parser & indexer
"""

import os
import requests
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from .schemas import EvidenceChunk

load_dotenv()


class RetrievalClient:
    """
    Dedicated API Client for Dakshinya's S2 Retrieval Service.
    All agent retrieval requests are delegated directly over HTTP to the backend server.
    """
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.getenv("RETRIEVAL_API_URL", "http://127.0.0.1:8000")

    # ── Strategy Mapping (Section 11 Skill Parameter Spec -> S2 API) ──────────

    def _resolve_strategy(
        self,
        strategy: str,
        query: str,
        date_filter: Optional[str] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> tuple[str, bool]:
        """
        Maps skill-specific retrieval character to Dakshinya's S2 API strategies:
          • "p1" / "mentor"  → "exp1": Precision-first (Scroll + Custom Meeting Reranker, Top 15)
          • "p2" / "team"    → "exp2": Date-scoped scan (Document-Balanced Scroll, Top 35)
          • "p4" / "manager" → "exp4": Completeness-first (Single-Pass Full Corpus Ingestion)

        Returns: (strategy_name: str, use_reranker: bool)
        """
        strat_norm = strategy.lower().strip()

        if strat_norm in ["exp1", "p1", "mentor", "precision"]:
            return "exp1", True
        if strat_norm in ["exp2", "p2", "team", "date_range"]:
            return "exp2", False
        if strat_norm in ["exp4", "p4", "manager", "completeness"]:
            return "exp4", False
        if strat_norm in ["exp3", "p3", "fast"]:
            return "exp3", False

        # Default fallback
        if date_filter or period_start or period_end:
            return "exp2", False
        return "exp1", True



    # ── Primary Retrieval Method ──────────────────────────────────────────────

    def query_evidence(
        self,
        query: str,
        speaker_filter: Optional[str] = None,
        date_filter: Optional[str] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        limit: int = 40,
        strategy: str = "auto",
    ) -> List[EvidenceChunk]:
        """
        Calls Dakshinya's POST /query/retrieve-only endpoint over HTTP.
        Returns parsed, validated EvidenceChunk models.
        """
        api_strategy, use_reranker = self._resolve_strategy(
            strategy=strategy,
            query=query,
            date_filter=date_filter,
            period_start=period_start,
            period_end=period_end,
        )

        # Merge period date range into date string if needed
        effective_date = date_filter
        if not effective_date and (period_start or period_end):
            effective_date = f"{period_start or ''} to {period_end or ''}".strip(" to ")

        # Sanitize date filter: Only pass to API if it contains actual calendar markers (months or digits)
        # Relative terms like "this week", "last week", "today", "recent" should NOT filter out all Qdrant documents
        if effective_date:
            cal_months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
            has_calendar_token = any(m in effective_date.lower() for m in cal_months) or any(char.isdigit() for char in effective_date)
            if not has_calendar_token or effective_date.lower() in ["this week", "last week", "current week", "today", "yesterday", "recent", "all"]:
                effective_date = None

        # Sanitize speaker filter
        effective_speaker = speaker_filter
        if effective_speaker and effective_speaker.lower() in ["all", "team", "everyone"]:
            effective_speaker = None

        url = f"{self.endpoint_url.rstrip('/')}/query/retrieve-only"
        payload = {
            "query": query,
            "strategy": api_strategy,
            "use_reranker": use_reranker,
            "speaker": effective_speaker,
            "date": effective_date,
            "source_file": None,
            "top_k": limit or (15 if api_strategy in ["exp1", "exp3"] else 35)
        }

        print(f"  [RetrievalClient -> S2 API] POST {url} | strategy={api_strategy} (rerank={use_reranker}) speaker={effective_speaker} date={effective_date}")

        try:
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"[RetrievalClient Error] Could not connect to Dakshinya's Retrieval Service at {self.endpoint_url}.\n"
                f"Please ensure her FastAPI server is started: uvicorn main:app --port 8000 (or python api_server.py)"
            )
        except Exception as e:
            raise RuntimeError(f"[RetrievalClient Error] S2 API request failed: {e}")

        raw_chunks = data.get("evidence_chunks", [])
        chunks: List[EvidenceChunk] = []

        for idx, c in enumerate(raw_chunks):
            chunks.append(EvidenceChunk(
                chunk_id=str(c.get("point_id") or f"chk-remote-{idx+1}"),
                text=c.get("text", ""),
                speaker=c.get("speaker", "Unknown"),
                date=c.get("date", "Unknown Date"),
                page=str(c.get("page", "1")),
                source_file=c.get("file") or c.get("source_file", "transcript.docx"),
                score=float(c.get("score", 1.0))
            ))

        print(f"  [RetrievalClient <- S2 API] Received {len(chunks)} evidence chunks successfully.")
        return chunks

    # ── System 2 Discovery & Metadata Endpoints ───────────────────────────────

    def check_health(self) -> Dict[str, Any]:
        """Calls GET /health to verify API server and Qdrant Cloud cluster connectivity."""
        url = f"{self.endpoint_url.rstrip('/')}/health"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def fetch_collections(self) -> Dict[str, Any]:
        """Calls GET /collections to list all available vector collections in Qdrant Cloud."""
        url = f"{self.endpoint_url.rstrip('/')}/collections"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def fetch_metadata(self) -> Dict[str, Any]:
        """Calls GET /filters/metadata to retrieve available speakers, dates, and source files."""
        url = f"{self.endpoint_url.rstrip('/')}/filters/metadata"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json().get("metadata", {})

    def get_active_trainees(self, exclude_mentor: bool = True) -> List[str]:
        """
        Returns the list of active trainee full names discovered live from the API metadata.
        Excludes the mentor speaker by default (anyone whose first name is 'Siddharth').
        Also removes noise entries like 'Unknown' or names ending with '...'.
        Falls back to an empty list — never falls back to hardcoded names.
        """
        try:
            meta = self.fetch_metadata()
            speakers: List[str] = meta.get("available_speakers", [])
            # Filter noise: remove Unknown, trailing ellipsis variants, and mentor
            speakers = [
                s for s in speakers
                if s
                and not s.lower().startswith("unknown")
                and s.lower() not in ["speaker", "none", "n/a", "general", "all", "system", "teammates", "trainees"]
                and not s.endswith("...")
                and (not exclude_mentor or not s.lower().startswith("siddharth"))
            ]
            # Deduplicate and sort
            return sorted(set(speakers))
        except Exception:
            return []


    # ── System 3 Unified Evaluation Endpoint ──────────────────────────────────

    def evaluate_query(
        self,
        question: str,
        answer: str,
        context: str,
        expected_facts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calls POST /evaluate/query to evaluate answer quality with DeepSeek LLM Judge:
        Returns Faithfulness (1-10), Relevancy (1-10), Context Recall (1-10), and Composite Overall Score %.
        """
        url = f"{self.endpoint_url.rstrip('/')}/evaluate/query"
        payload = {
            "question": question,
            "answer": answer,
            "context": context,
            "expected_facts": expected_facts or []
        }
        resp = requests.post(url, json=payload, timeout=25)
        resp.raise_for_status()
        return resp.json()

    # ── System 1 Ingestion Endpoint ───────────────────────────────────────────

    def ingest_file(self, file_path: str, collection: str = "teams_dense_collection") -> Dict[str, Any]:
        """Calls POST /ingest/upload (or POST /upload) to chunk and index a single transcript file."""
        url = f"{self.endpoint_url.rstrip('/')}/ingest/upload"
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {"collection": collection, "skip_if_exists": "true"}
            resp = requests.post(url, files=files, data=data, timeout=60)
            resp.raise_for_status()
            return resp.json()


# Global Singleton Instance for downstream Agent Skills
retrieval_client = RetrievalClient()
