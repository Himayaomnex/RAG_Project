import re
import json
import datetime
from typing import List, Optional, Dict, Any
from harness.evidence_store import EvidenceItem
from harness.tool_registry import register_tool, ToolError
from agents.shared.kb_client import kb_client, KBUnavailableError


def _normalize_iso_date(val: Optional[str]) -> Optional[str]:
    """Safely converts natural language periods ('this week', 'recent', 'July 24') or dates to ISO YYYY-MM-DD."""
    if not val or not isinstance(val, str):
        return None
    val_clean = val.strip().lower()
    
    # Check if already ISO format YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", val_clean):
        return val_clean

    today = datetime.date.today()
    if val_clean in ("this week", "past week", "last 7 days", "recent", "current"):
        return (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    if val_clean in ("today", "current day"):
        return today.strftime("%Y-%m-%d")
    if val_clean in ("yesterday",):
        return (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if val_clean in ("this month", "past 30 days"):
        return (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        
    # Try parsing Month Day (e.g. 'july 24' or 'july 24, 2026')
    for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%B %d", "%b %d", "%d %B %Y", "%d %b %Y"):
        try:
            dt = datetime.datetime.strptime(val_clean, fmt)
            year = dt.year if dt.year != 1900 else today.year
            return datetime.date(year, dt.month, dt.day).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # If unparseable, return None so SQL does not fail on invalid cast
    return None


def _rows_to_evidence(table: str, rows: List[Dict[str, Any]], id_prefix: str, id_key: Optional[str] = None) -> List[EvidenceItem]:
    items: List[EvidenceItem] = []
    for idx, r in enumerate(rows):
        cid = r.get(id_key) if id_key and r.get(id_key) else f"{id_prefix}-{idx+1}"
        person = r.get("person") or r.get("answered_by") or r.get("to_person") or r.get("owner")
        date = r.get("session_date") or r.get("due_date") or r.get("delivered_date")

        # Format content cleanly
        parts = []
        for k, v in r.items():
            if v is not None:
                parts.append(f"{k}: {v}")
        content = " | ".join(parts)

        item = EvidenceItem(
            id=str(cid),
            source="kb",
            origin={"table": table, "person": person, "date": date},
            content=content,
            relevance=1.0
        )
        items.append(item)
    return items


@register_tool("get_person_state", "Fetch rolled-up performance metrics and state for a person or all trainees.")
def get_person_state(person: Optional[str] = None) -> List[EvidenceItem]:
    try:
        rows = kb_client.get_person_state(person=person)
        if not rows:
            return [EvidenceItem(
                id=f"kb-state-{person or 'all'}",
                source="kb",
                origin={"table": "v_person_state", "person": person},
                content=f"No rolled-up person state found for {person or 'everyone'}.",
                relevance=1.0
            )]
        return _rows_to_evidence("v_person_state", rows, f"kb-state-{person or 'all'}")
    except KBUnavailableError as e:
        raise ToolError(f"KB_UNAVAILABLE: {e}") from e
    except Exception as e:
        raise ToolError(f"KB tool get_person_state failed: {e}") from e


@register_tool("get_assignments", "Fetch current and historical assignments filtered by person or status.")
def get_assignments(person: Optional[str] = None, status: Optional[str] = None) -> List[EvidenceItem]:
    try:
        rows = kb_client.get_current_assignments(person=person, status=status)
        if not rows:
            return [EvidenceItem(
                id=f"kb-assignments-empty",
                source="kb",
                origin={"table": "v_assignments_current", "person": person},
                content=f"No assignments found matching person={person}, status={status}.",
                relevance=1.0
            )]
        return _rows_to_evidence("v_assignments_current", rows, "kb-assignment")
    except KBUnavailableError as e:
        raise ToolError(f"KB_UNAVAILABLE: {e}") from e
    except Exception as e:
        raise ToolError(f"KB tool get_assignments failed: {e}") from e


@register_tool("get_concepts", "Fetch observed concept gaps, confusions, and understandings.")
def get_concepts(person: Optional[str] = None) -> List[EvidenceItem]:
    try:
        rows = kb_client.get_concept_gaps(person=person)
        if not rows:
            return [EvidenceItem(
                id=f"kb-concepts-empty",
                source="kb",
                origin={"table": "v_concepts", "person": person},
                content=f"No concept gaps recorded for {person or 'anyone'}.",
                relevance=1.0
            )]
        return _rows_to_evidence("v_concepts", rows, "kb-concept")
    except KBUnavailableError as e:
        raise ToolError(f"KB_UNAVAILABLE: {e}") from e
    except Exception as e:
        raise ToolError(f"KB tool get_concepts failed: {e}") from e


@register_tool("get_qa_events", "Fetch technical Q&A exchanges and answer quality records.")
def get_qa_events(person: Optional[str] = None, period: Optional[str] = None) -> List[EvidenceItem]:
    try:
        rows = kb_client.get_qa_history(person=person)
        if not rows:
            return [EvidenceItem(
                id="kb-qa-empty",
                source="kb",
                origin={"table": "v_qa", "person": person},
                content=f"No QA events recorded for {person or 'anyone'}.",
                relevance=1.0
            )]
        return _rows_to_evidence("v_qa", rows, "kb-qa")
    except KBUnavailableError as e:
        raise ToolError(f"KB_UNAVAILABLE: {e}") from e
    except Exception as e:
        raise ToolError(f"KB tool get_qa_events failed: {e}") from e


@register_tool("get_feedback", "Fetch verbatim mentor and peer feedback signals.")
def get_feedback(person: Optional[str] = None, from_person: Optional[str] = None) -> List[EvidenceItem]:
    try:
        rows = kb_client.get_feedback_history(person=person, from_person=from_person)
        if not rows:
            return [EvidenceItem(
                id="kb-feedback-empty",
                source="kb",
                origin={"table": "v_feedback", "person": person},
                content=f"No feedback records found for {person or 'anyone'}.",
                relevance=1.0
            )]
        return _rows_to_evidence("v_feedback", rows, "kb-feedback")
    except KBUnavailableError as e:
        raise ToolError(f"KB_UNAVAILABLE: {e}") from e
    except Exception as e:
        raise ToolError(f"KB tool get_feedback failed: {e}") from e


@register_tool("get_decisions", "Fetch agreed architectural and technical decisions.")
def get_decisions(period: Optional[str] = None, owner: Optional[str] = None) -> List[EvidenceItem]:
    try:
        iso_start = _normalize_iso_date(period) if period else None
        rows = kb_client.get_decisions(start_date=iso_start, owner=owner)
        if not rows:
            return [EvidenceItem(
                id="kb-decisions-empty",
                source="kb",
                origin={"table": "v_decisions"},
                content="No decisions recorded for the specified criteria.",
                relevance=1.0
            )]
        return _rows_to_evidence("v_decisions", rows, "kb-decision")
    except KBUnavailableError as e:
        raise ToolError(f"KB_UNAVAILABLE: {e}") from e
    except Exception as e:
        raise ToolError(f"KB tool get_decisions failed: {e}") from e


@register_tool("get_session_digest", "Fetch structured digest and key topics for a session date.")
def get_session_digest(date: Optional[str] = None) -> List[EvidenceItem]:
    try:
        iso_date = _normalize_iso_date(date) if date else None
        rows = kb_client.get_session_digest(session_date=iso_date)
        if not rows:
            return [EvidenceItem(
                id=f"kb-digest-{date or 'latest'}-empty",
                source="kb",
                origin={"table": "v_digests", "date": date},
                content=f"No digest found for session date {date or 'all'}.",
                relevance=1.0
            )]
        return _rows_to_evidence("v_digests", rows, f"kb-digest-{date or 'session'}")
    except KBUnavailableError as e:
        raise ToolError(f"KB_UNAVAILABLE: {e}") from e
    except Exception as e:
        raise ToolError(f"KB tool get_session_digest failed: {e}") from e


@register_tool("list_people", "List all canonical persons, trainees, and mentors in the KB.")
def list_people() -> List[EvidenceItem]:
    try:
        persons = kb_client.get_all_persons()
        content = ", ".join(persons) if persons else "No persons found in KB."
        return [EvidenceItem(
            id="kb-people-list",
            source="kb",
            origin={"table": "person"},
            content=f"Canonical persons: {content}",
            relevance=1.0
        )]
    except KBUnavailableError as e:
        raise ToolError(f"KB_UNAVAILABLE: {e}") from e
    except Exception as e:
        raise ToolError(f"KB tool list_people failed: {e}") from e
