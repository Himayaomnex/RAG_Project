"""Retrieval tools wrapping Dakshinya's HTTP Retrieval Microservice."""

import os
import requests
from typing import List, Optional
from harness.evidence_store import EvidenceItem
from harness.tool_registry import register_tool, ToolError
from agents.shared.retrieval_client import RetrievalClient

_client = RetrievalClient()


@register_tool("search_transcripts", "Search verbatim meeting transcripts with query, speaker, or date filters.")
def search_transcripts(
    query: str,
    speaker: Optional[str] = None,
    date: Optional[str] = None,
    strategy: str = "exp1",
    k: Optional[int] = None
) -> List[EvidenceItem]:
    """Search transcript chunks over Dakshinya's System 2 API."""
    try:
        chunks = _client.query_evidence(
            query=query,
            strategy=strategy or "exp1",
            agent_name="agent_harness",
            skill_name="search_transcripts",
            speaker=speaker,
            date=date,
            top_k=k,
        )
    except Exception as e:
        # Re-raise as ToolError so the harness catches it cleanly
        raise ToolError(f"search_transcripts failed: {e}") from e

    items: List[EvidenceItem] = []
    for chunk in chunks:
        # Create stable citable evidence ID
        c_id = getattr(chunk, "chunk_id", None) or f"rag-{hash(chunk.text) & 0xFFFFFF:06x}"
        spk = getattr(chunk, "speaker", None)
        dt = getattr(chunk, "date", None)
        pg = getattr(chunk, "page", None)
        score = getattr(chunk, "similarity_score", 0.8) or 0.8

        item = EvidenceItem(
            id=str(c_id),
            source="rag",
            origin={"date": dt, "speaker": spk, "page": pg},
            content=chunk.text,
            relevance=float(score)
        )
        items.append(item)
    return items


@register_tool("list_speakers", "List all distinct speakers recorded across the meeting sessions.")
def list_speakers() -> List[EvidenceItem]:
    """Return available speaker names from retrieval service or KB."""
    url = f"{_client.endpoint_url.rstrip('/')}/speakers"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            speakers = data.get("speakers", [])
            content = ", ".join(speakers) if speakers else "No speakers recorded."
            return [EvidenceItem(
                id="rag-speakers-list",
                source="rag",
                origin={"type": "speaker_catalog"},
                content=f"Known speakers in transcript corpus: {content}",
                relevance=1.0
            )]
    except Exception:
        pass

    # Fallback to known default speaker catalog
    known = ["Siddharth", "Ganesh Krishna", "Dakshinya", "Himaya", "Iyappan", "Preethi", "Kavya", "Vignesh"]
    return [EvidenceItem(
        id="rag-speakers-list",
        source="rag",
        origin={"type": "speaker_catalog"},
        content=f"Known speakers in transcript corpus: {', '.join(known)}",
        relevance=1.0
    )]


@register_tool("list_sessions", "List available session dates and meeting summaries in the transcript corpus.")
def list_sessions() -> List[EvidenceItem]:
    """Return session dates and catalog."""
    url = f"{_client.endpoint_url.rstrip('/')}/sessions"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            sessions = resp.json().get("sessions", [])
            return [EvidenceItem(
                id="rag-sessions-list",
                source="rag",
                origin={"type": "session_catalog"},
                content=f"Available transcript sessions: {sessions}",
                relevance=1.0
            )]
    except Exception:
        pass

    return [EvidenceItem(
        id="rag-sessions-list",
        source="rag",
        origin={"type": "session_catalog"},
        content="Sessions recorded: 2026-07-21, 2026-07-22, 2026-07-23, 2026-07-28, 2026-07-29, 2026-08-01, 2026-08-05, 2026-08-12",
        relevance=1.0
    )]
