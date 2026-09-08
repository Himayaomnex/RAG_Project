"""Skills module registering composite recipe tools into the ToolRegistry."""

import re
from typing import List, Optional
from harness.evidence_store import EvidenceItem
from harness.tool_registry import register_tool, ToolError
from harness.tools.kb import (
    get_concepts,
    get_qa_events,
    get_feedback,
    get_assignments,
    get_session_digest,
    get_decisions
)
from harness.tools.retrieval import search_transcripts
from agents.shared.retrieval_client import _normalize_date


@register_tool(
    "assess_person",
    "Gather everything needed to assess one person's progress: concepts, QA events, feedback, assignments."
)
def assess_person(person: str, period: Optional[str] = None) -> List[EvidenceItem]:
    """Composite skill recipe for assessing a person's demonstrated progress."""
    items: List[EvidenceItem] = []

    # 1. Concepts
    try:
        concepts = get_concepts(person=person)
        items.extend([c for c in concepts if "empty" not in c.id])
    except Exception:
        pass

    # 2. QA Events
    try:
        qa = get_qa_events(person=person, period=period)
        items.extend([q for q in qa if "empty" not in q.id])
    except Exception:
        pass

    # 3. Feedback
    try:
        fb = get_feedback(person=person)
        items.extend([f for f in fb if "empty" not in f.id])
    except Exception:
        pass

    # 4. Assignments
    try:
        assigns = get_assignments(person=person)
        items.extend([a for a in assigns if "empty" not in a.id])
    except Exception:
        pass

    if not items:
        return [EvidenceItem(
            id=f"skill-assess-{person}-empty",
            source="kb",
            origin={"person": person, "found_nothing": True},
            content=f"No concepts, QA, feedback, or assignments recorded for {person} in the KB.",
            relevance=1.0
        )]

    # 5. Targeted transcript search for context/language if specific date/concept observed
    target_date = None
    for it in items:
        if it.origin.get("date"):
            target_date = it.origin["date"]
            break

    try:
        transcripts = search_transcripts(
            query=f"{person} progress work",
            speaker=person,
            date=target_date,
            k=3
        )
        items.extend(transcripts)
    except Exception:
        pass

    return items


@register_tool(
    "catch_up",
    "Gather everything needed to brief someone who missed one session date."
)
def catch_up(date: str, person: Optional[str] = None) -> List[EvidenceItem]:
    """Composite skill recipe for catching up on a single session."""
    norm_date = _normalize_date(date) or date
    items: List[EvidenceItem] = []

    # 1. Session digest for the date
    digest_found = False
    try:
        digests = get_session_digest(date=norm_date)
        valid_digests = [d for d in digests if "empty" not in d.id]
        if valid_digests:
            items.extend(valid_digests)
            digest_found = True
    except Exception:
        pass

    # 2. Assignments & Decisions for the specific date
    try:
        assigns = get_assignments(person=person)
        # Filter assignments relevant to this date
        date_assigns = [
            a for a in assigns
            if "empty" not in a.id and (a.origin.get("date") == norm_date or norm_date in a.content)
        ]
        items.extend(date_assigns)
    except Exception:
        pass

    try:
        decs = get_decisions(period=norm_date)
        date_decs = [
            d for d in decs
            if "empty" not in d.id and (d.origin.get("date") == norm_date or norm_date in d.content)
        ]
        items.extend(date_decs)
    except Exception:
        pass

    # 3. Only if digest is missing or thin, do targeted transcript search
    if not digest_found or len(items) <= 1:
        try:
            transcripts = search_transcripts(
                query=f"meeting discussion {norm_date}",
                date=norm_date,
                strategy="exp1",
                k=3
            )
            items.extend(transcripts)
        except Exception:
            pass

    if not items:
        return [EvidenceItem(
            id=f"skill-catchup-{norm_date}-empty",
            source="kb",
            origin={"date": norm_date, "found_nothing": True, "reason": "no session on that date"},
            content=f"No recorded session found for date {norm_date}.",
            relevance=1.0
        )]

    return items


@register_tool(
    "summarize_period",
    "Gather everything needed for a state-of-work report over a window."
)
def summarize_period(period_start: str, period_end: str, person: Optional[str] = None) -> List[EvidenceItem]:
    """Composite skill recipe for period summary / weekly rollup."""
    items: List[EvidenceItem] = []

    candidate_sessions = [
        "2026-07-21", "2026-07-22", "2026-07-23", "2026-07-28",
        "2026-07-29", "2026-08-01", "2026-08-05", "2026-08-12"
    ]
    sessions_in_window = [s for s in candidate_sessions if period_start <= s <= period_end]

    if not sessions_in_window and len(period_start) == 7:
        sessions_in_window = [s for s in candidate_sessions if s.startswith(period_start)]

    if not sessions_in_window:
        return [EvidenceItem(
            id=f"skill-summary-{period_start}-empty",
            source="kb",
            origin={"period_start": period_start, "period_end": period_end, "found_nothing": True, "reason": "no sessions in window"},
            content=f"No recorded sessions found in window {period_start} to {period_end}.",
            relevance=1.0
        )]

    # Get session digests for each session in window
    for s_date in sessions_in_window:
        try:
            digests = get_session_digest(date=s_date)
            items.extend([d for d in digests if "empty" not in d.id])
        except Exception:
            pass

    # Assignments in period
    try:
        assigns = get_assignments(person=person)
        items.extend([a for a in assigns if "empty" not in a.id])
    except Exception:
        pass

    # Decisions in period
    try:
        decs = get_decisions(period=period_start)
        items.extend([d for d in decs if "empty" not in d.id])
    except Exception:
        pass

    return items
