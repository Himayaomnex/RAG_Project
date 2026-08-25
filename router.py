"""
================================================================================
Central Agent Router (router.py)
================================================================================
Dispatches user requests to the 3 Production Agents:
- Manager Agent (Iyappan) → manager_weekly_rollup
- Mentor Agent (Siddharth) → mentor_trainee_assessment
- Team Intelligence Agent → team_session_catchup

Router uses LLM-based semantic intent classification.
Hardcoded keyword lists are REMOVED.
Trainee identity (himaya/ganesh/dakshinya) scopes the entity — it does NOT force
a specific agent. Intent is always derived from the query semantics.
"""

import json
import re
from typing import Tuple, Optional
from agents.manager.agent import manager_agent
from agents.mentor.agent import mentor_agent
from agents.team.agent import team_agent
from agents.shared.llm_client import llm_client


# ── Trainee identity map ───────────────────────────────────────────────────────
# Maps user_role header values → canonical trainee names used by agents
_TRAINEE_ROLE_MAP = {
    "himaya":    "Himaya",
    "ganesh":    "Ganesh",
    "dakshinya": "Dakshinya",
}

# Roles that explicitly pin a specific agent (bypass intent classification)
_PINNED_MANAGER_ROLES  = {"manager", "iyappan"}
_PINNED_MENTOR_ROLES   = {"mentor", "siddharth"}
_PINNED_TEAM_ROLES     = {"team", "teammate"}


def classify_intent(query: str, trainee_hint: Optional[str] = None) -> dict:
    """
    LLM-based semantic intent classifier.

    Returns a dict:
    {
        "agent":   "manager" | "mentor" | "team",
        "trainee": str | null,   # canonical name extracted from query or hint
        "date":    str | null,   # session date if catch-up query
        "period":  str | null,   # reporting period if rollup query
        "focus_area": str | null # technical topic/focus area mentioned (e.g. 'RAG', 'Qdrant') or null
    }

    Falls back to rule-based heuristic if LLM call fails.
    """
    system_prompt = (
        "You are a routing classifier for a multi-agent training RAG system.\n"
        "There are exactly three agents:\n"
        "  • manager  — Executive status, deliverables, blockers, decisions, weekly rollup\n"
        "  • mentor   — Trainee evaluation, knowledge gaps, misconceptions, progress, assessment, quiz\n"
        "  • team     — Session catch-up for a trainee who missed a session; assignments, what happened\n\n"
        "Given a user query, output a JSON object with exactly these keys:\n"
        "  agent:      one of 'manager', 'mentor', 'team'\n"
        "  trainee:    canonical trainee name ('Himaya', 'Ganesh', 'Dakshinya') or null\n"
        "  date:       session date string if agent=team and a concrete date is mentioned (e.g. 'July 31', 'August 18') or null. Do NOT extract relative terms like 'yesterday', 'today', 'last session', 'previous meeting' — return null for these.\n"
        "  period:     date range string or month name if agent=manager or agent=mentor (e.g. 'July 21 to July 28', 'July', 'August') or null\n"
        "  focus_area: specific technical topic mentioned in the query if user is asking about a particular subject (e.g., 'RAG', 'Qdrant', 'LangGraph', 'BM25', 'API design') or null.\n\n"
        "RULES:\n"
        "- agent=mentor  when query is about evaluating, assessing, scoring, diagnosing a trainee's technical understanding, performance, technical capability, misconceptions, knowledge gaps, strengths, how they are performing, or feedback given by the mentor.\n"
        "- agent=team    when query is about catching up on a missed session, what happened in a session, what assignments were given, what decisions were made in a specific session.\n"
        "- agent=manager for everything else: executive project milestones, deliverables, blockers, risks, what tasks are completed/in-progress across the project.\n"
        "- Extract the trainee name from the query if mentioned. If a trainee_hint is provided and no name is in the query, use the hint.\n"
        "- BROAD REPORT RULE: If the query asks for a general rollup, status, blocker report, or refers to 'all trainees', 'entire team', or the training program as a whole, the trainee scope MUST be null (representing the entire cohort), even if the conversation history previously focused on a specific trainee.\n"
        "- Output ONLY valid compact JSON. No explanation, no markdown, no extra text."
    )

    hint_clause = f"\nTrainee hint (authenticated user): {trainee_hint}" if trainee_hint else ""
    user_prompt = f"Query: {query}{hint_clause}"

    try:
        raw, _, _, _ = llm_client.generate(
            system_instruction=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=128,
            json_mode=True
        )
        # Strip markdown fences if any
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        result = json.loads(raw)
        # Validate and normalise
        agent = result.get("agent", "manager").lower()
        if agent not in ("manager", "mentor", "team"):
            agent = "manager"
        return {
            "agent":      agent,
            "trainee":    result.get("trainee") or trainee_hint or None,
            "date":       result.get("date") or None,
            "period":     result.get("period") or None,
            "focus_area": result.get("focus_area") or None,
        }
    except Exception as e:
        print(f"  - [Router] LLM classifier failed ({e}). Using rule-based fallback.")
        return _rule_fallback(query, trainee_hint)


def _rule_fallback(query: str, trainee_hint: Optional[str] = None) -> dict:
    """
    Minimal rule-based fallback used ONLY when the LLM classifier fails entirely.
    Kept intentionally minimal — not the primary routing path.
    Defaults to manager (safest), only overrides for the most unambiguous signals.
    """
    q = query.lower()

    # Extract trainee name dynamically from the query
    trainee = trainee_hint
    for key, canonical in _TRAINEE_ROLE_MAP.items():
        if key in q:
            trainee = canonical
            break

    # Only the most unambiguous catch-up phrase triggers team agent
    if "i missed" in q or re.search(r"\bi was absent\b", q) or re.search(r"\bcatch.?up\b", q):
        # Extract date for team catch-up
        date = None
        months = (
            "January|February|March|April|May|June|July|August|"
            "September|October|November|December"
        )
        m = re.search(
            rf"(\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{months})|(?:{months})\s+\d{{1,2}}(?:st|nd|rd|th)?)",
            query, re.IGNORECASE
        )
        if m:
            date = m.group(1).strip()
        return {"agent": "team", "trainee": trainee, "date": date, "period": None, "focus_area": None}

    # Default → manager (safe fallback for all other queries)
    return {"agent": "manager", "trainee": trainee, "date": None, "period": None, "focus_area": None}


# ── Public API ─────────────────────────────────────────────────────────────────

def route_request_with_role(
    query: str,
    user_role: Optional[str] = None,
    forced_role: Optional[str] = None,
    **kwargs
) -> Tuple[str, str]:
    """
    Primary routing entry point called by api_server.py and cli.py.

    Returns: (response_text, dispatched_agent_role)

    Logic:
    1. If forced_role or user_role pins an agent role → dispatch directly.
    2. If user_role is a trainee identity (himaya/ganesh/dakshinya) →
       extract trainee name as a hint but still run intent classification
       on the query — do NOT force Team agent.
    3. Otherwise run full LLM intent classification.
    """
    raw_role = (forced_role or user_role or "auto").lower()

    # Extract target_member from kwargs (from request body)
    target_member = kwargs.get("target_member") or kwargs.get("trainee") or ""

    # ── Step 1: Pinned agent roles ─────────────────────────────────────────────
    if raw_role in _PINNED_MANAGER_ROLES:
        res = manager_agent.handle_request(
            query=query,
            period_start=kwargs.get("period_start"),
            period_end=kwargs.get("period_end"),
            trainee=target_member or None,
            trace_id=kwargs.get("trace_id")
        )
        return res, "manager"

    if raw_role in _PINNED_MENTOR_ROLES:
        res = mentor_agent.handle_request(
            query=query,
            trainee=target_member or None,
            period=kwargs.get("period"),
            focus_area=kwargs.get("focus_area"),
            trace_id=kwargs.get("trace_id")
        )
        return res, "mentor"

    if raw_role in _PINNED_TEAM_ROLES:
        res = team_agent.handle_request(
            query=query,
            date=kwargs.get("date"),
            trainee=target_member or None,
            trace_id=kwargs.get("trace_id")
        )
        return res, "team"

    # ── Step 2: Trainee identity — scope entity, classify intent from query ────
    trainee_hint = _TRAINEE_ROLE_MAP.get(raw_role)  # "himaya" → "Himaya" or None
    # If target_member was explicitly passed in the request body, prefer that
    effective_trainee = target_member or trainee_hint or None

    # ── Step 3: LLM-based intent classification ────────────────────────────────
    intent = classify_intent(query, trainee_hint=effective_trainee)
    agent  = intent["agent"]
    # Entity slots from classifier override only if not already set by caller
    resolved_trainee = effective_trainee or intent.get("trainee")
    resolved_date    = kwargs.get("date")    or intent.get("date")
    resolved_period  = kwargs.get("period")  or intent.get("period")

    if agent == "mentor":
        res = mentor_agent.handle_request(
            query=query,
            trainee=resolved_trainee,
            period=resolved_period,
            focus_area=kwargs.get("focus_area"),
            trace_id=kwargs.get("trace_id")
        )
        return res, "mentor"

    if agent == "team":
        res = team_agent.handle_request(
            query=query,
            date=resolved_date,
            trainee=resolved_trainee,
            trace_id=kwargs.get("trace_id")
        )
        return res, "team"

    # Default → manager
    res = manager_agent.handle_request(
        query=query,
        period_start=kwargs.get("period_start"),
        period_end=kwargs.get("period_end"),
        trainee=resolved_trainee,
        trace_id=kwargs.get("trace_id")
    )
    return res, "manager"


def route_request(query: str, **kwargs) -> Tuple[str, str]:
    """
    Convenience wrapper for callers that don't pass a role.
    Returns: (agent_role, response_text)
    """
    res, role = route_request_with_role(query, user_role="auto", **kwargs)
    return role, res


def detect_agent_intent(query: str) -> str:
    """
    Legacy compatibility shim.
    Returns agent role string for callers that only need the classification
    without dispatching (e.g. script.js detectIntentRole equivalent).
    """
    return classify_intent(query).get("agent", "manager")
