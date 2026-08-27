"""
================================================================================
Thin HTTP Retrieval Service Client (agents/shared/retrieval_client.py)
================================================================================
Dedicated HTTP Client calling Dakshinya's System 2 Retrieval Service.
Points strictly to: {RETRIEVAL_API_URL}/retrieve
Target Collection : teams_dense_collection_normalized

Zero local retrieval algorithms. Zero local database code.
If Dakshinya's server is offline, this client raises RETRIEVAL_UNAVAILABLE.
================================================================================
"""

import os
import time
import requests
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from .schemas import EvidenceChunk

load_dotenv()


def _normalize_date(raw_date: Optional[str]) -> Optional[str]:
    """Normalizes natural date strings like 'July 21' or '21 July 2026' into ISO '2026-07-21'."""
    if not raw_date:
        return None
    raw = raw_date.strip().lower()
    import re
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
        return raw
    months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
        "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
    }
    day_match = re.search(r'\b(\d{1,2})\b', raw)
    month_match = next((num for k, num in months.items() if k in raw), None)
    if day_match and month_match:
        return f"2026-{month_match}-{int(day_match.group(1)):02d}"
    return raw_date


class RetrievalClient:
    """
    Thin HTTP client communicating with Dakshinya's System 2 FastAPI Retrieval Microservice.
    """
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.getenv("RETRIEVAL_API_URL", "http://127.0.0.1:8000")
        self.target_collection = "teams_dense_collection_normalized"

    def query_evidence(
        self,
        query: str,
        speaker: Optional[str] = None,
        date: Optional[str] = None,
        strategy: str = "exp1",
        use_reranker: bool = True,
        agent_name: str = "mentor",
        skill_name: str = "trainee_assessment",
        trace_id: Optional[str] = None,
    ) -> List[EvidenceChunk]:
        """
        Calls Dakshinya's POST /retrieve endpoint over HTTP.
        Logs routing decisions BEFORE execution and raises RETRIEVAL_UNAVAILABLE on failure.
        """
        tid = trace_id or "trc-live"
        norm_date = _normalize_date(date)
        spk_str = f'"{speaker}"' if speaker else "None"
        dt_str = f'"{norm_date}"' if norm_date else "None"

        # ── Non-Negotiable Log Line 1: Pre-execution Route Decision ───────────
        print(f"[{tid}] ROUTE agent={agent_name} skill={skill_name} strategy={strategy} collection={self.target_collection} speaker={spk_str} date={dt_str}", flush=True)

        url = f"{self.endpoint_url.rstrip('/')}/retrieve"
        payload = {
            "query": query,
            "collection": self.target_collection,
            "strategy": strategy,
            "use_reranker": use_reranker,
            "top_k": None,
            "speaker": speaker,
            "date": norm_date,
        }

        t0 = time.time()
        try:
            resp = requests.post(url, json=payload, timeout=20)
            latency_ms = round((time.time() - t0) * 1000, 1)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"[{tid}] HTTP POST /retrieve -> ERROR: Server unreachable at {self.endpoint_url}", flush=True)
            raise RuntimeError(
                f"RETRIEVAL_UNAVAILABLE: Dakshinya's Retrieval Service is offline at {self.endpoint_url}.\n"
                f"Please start her service in C:\\dev\\dakshinya-service:\n"
                f"python -m uvicorn rag_platform.api.app:app --host 127.0.0.1 --port 8000"
            ) from e
        except Exception as e:
            raise RuntimeError(f"RETRIEVAL_UNAVAILABLE: S2 API call failed: {e}") from e

        if resp.status_code != 200:
            print(f"[{tid}] HTTP POST /retrieve -> {resp.status_code} Error: {resp.text}", flush=True)
            raise RuntimeError(f"RETRIEVAL_UNAVAILABLE: Server returned status {resp.status_code}: {resp.text}")

        data = resp.json()
        raw_chunks = data.get("chunks", []) or data.get("evidence_chunks", [])
        server_latency = data.get("latency_ms", latency_ms)

        # ── Non-Negotiable Log Line 2: HTTP Retrieval Success ─────────────────
        print(f"[{tid}] HTTP POST /retrieve -> 200 chunks={len(raw_chunks)} latency_ms={server_latency}", flush=True)

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

        return chunks

    def fetch_metadata(self) -> Dict[str, Any]:
        """Calls GET /filters/metadata to retrieve available speakers, dates, and source files."""
        url = f"{self.endpoint_url.rstrip('/')}/filters/metadata"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            return resp.json().get("metadata", {})
        except Exception as e:
            print(f"  - [Metadata Fetch Error]: {e}")
            return {}

    def get_active_trainees(self, exclude_mentor: bool = True) -> List[str]:
        """
        Returns active individual trainee full names discovered live from the API metadata.
        Splits any comma-separated composite speaker strings.
        """
        try:
            meta = self.fetch_metadata()
            raw_speakers: List[str] = meta.get("available_speakers", [])
            trainees = set()
            for s in raw_speakers:
                for sub in s.split(","):
                    c = sub.strip()
                    if (
                        c
                        and not c.lower().startswith("unknown")
                        and not c.lower().startswith("speaker")
                        and c.lower() not in ["none", "n/a", "general", "all", "system", "teammates", "trainees"]
                        and not c.endswith("...")
                        and (not exclude_mentor or not c.lower().startswith("siddharth"))
                    ):
                        trainees.add(c)
            return sorted(list(trainees))
        except Exception:
            return []

    def check_health(self) -> Dict[str, Any]:
        """Calls GET /health to verify API server connectivity."""
        url = f"{self.endpoint_url.rstrip('/')}/health"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def fetch_collections(self) -> Dict[str, Any]:
        """Calls GET /collections to list available vector collections."""
        url = f"{self.endpoint_url.rstrip('/')}/collections"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()


# Global Singleton Instance for downstream Agent Skills
retrieval_client = RetrievalClient()
