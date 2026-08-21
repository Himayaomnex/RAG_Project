"""
================================================================================
Central Agent Router (router.py)
================================================================================
Dispatches user requests to the 3 Production Agents:
- Manager Agent (Iyappan) -> manager_weekly_rollup
- Mentor Agent (Siddharth) -> mentor_trainee_assessment
- Team Intelligence Agent (Trainees) -> team_session_catchup
"""

import re
from typing import Dict, Any, Tuple, Optional
from agents.manager.agent import manager_agent
from agents.mentor.agent import mentor_agent
from agents.team.agent import team_agent


def detect_agent_intent(query: str) -> str:
    """
    Classifies intent into one of the three agent roles: 'manager', 'mentor', 'team'.
    """
    q_low = query.lower()

    # Mentor intent keywords
    mentor_keywords = [
        "assess", "assessment", "score", "quiz", "misconception", "learning gap",
        "taught", "pedagogical", "cognitive", "bloom", "feedback", "trainee", "mentee",
        "how did ganesh perform", "how did himaya perform", "how did dakshinya perform",
        "evaluate", "progress of", "strengths"
    ]
    if any(k in q_low for k in mentor_keywords):
        return "mentor"

    # Team catch-up intent keywords
    team_keywords = [
        "missed", "catchup", "catch up", "what did i miss", "session recap", "today's session",
        "assignment given", "what should i do", "what do i need to do", "peer", "codebase", "miss in",
        "absent", "on leave", "leave", "not present", "what happened", "missed session", "training session"
    ]
    if any(k in q_low for k in team_keywords) and not any(k in q_low for k in ["status for this week", "weekly rollup", "executive review"]):
        return "team"

    # Default to Manager Agent (Status, deliverables, rollup, executive review)
    return "manager"


def route_request(query: str, **kwargs) -> Tuple[str, str]:
    """
    Routes query to the appropriate agent based on detected intent.
    Returns: (agent_role, response_text)
    """
    agent_role = detect_agent_intent(query)
    
    if agent_role == "mentor":
        res = mentor_agent.handle_request(
            query=query,
            trainee=kwargs.get("target_member") or kwargs.get("trainee"),
            period=kwargs.get("period"),
            focus_area=kwargs.get("focus_area")
        )
        return "mentor", res
    elif agent_role == "team":
        res = team_agent.handle_request(
            query=query,
            date=kwargs.get("date"),
            trainee=kwargs.get("target_member") or kwargs.get("trainee")
        )
        return "team", res
    else:
        res = manager_agent.handle_request(
            query=query,
            period_start=kwargs.get("period_start"),
            period_end=kwargs.get("period_end"),
            trainee=kwargs.get("target_member") or kwargs.get("trainee")
        )
        return "manager", res


def route_request_with_role(query: str, user_role: Optional[str] = None, forced_role: Optional[str] = None, **kwargs) -> Tuple[str, str]:
    """
    Routes with explicit role override if provided.
    Returns: (response_text, dispatched_role)
    """
    raw_role = (forced_role or user_role or "auto").lower()

    if raw_role in ["mentor", "siddharth"]:
        res = mentor_agent.handle_request(
            query=query,
            trainee=kwargs.get("target_member") or kwargs.get("trainee"),
            period=kwargs.get("period"),
            focus_area=kwargs.get("focus_area")
        )
        return res, "mentor"
    elif raw_role in ["team", "teammate", "himaya", "ganesh", "dakshinya"]:
        res = team_agent.handle_request(
            query=query,
            date=kwargs.get("date"),
            trainee=kwargs.get("target_member") or kwargs.get("trainee")
        )
        return res, "team"
    elif raw_role in ["manager", "iyappan"]:
        res = manager_agent.handle_request(
            query=query,
            period_start=kwargs.get("period_start"),
            period_end=kwargs.get("period_end"),
            trainee=kwargs.get("target_member") or kwargs.get("trainee")
        )
        return res, "manager"

    # Default / Auto-detect intent
    role, res = route_request(query, **kwargs)
    return res, role
