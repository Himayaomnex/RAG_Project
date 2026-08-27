"""
================================================================================
Team Intelligence Agent (agents/team/agent.py)
================================================================================
Persona: Peer Catch-Up & Action Specialist
Skill: team_session_catchup
"""

from typing import Optional, Dict, Any
from .skills.session_catchup import team_session_catchup
from ..shared.schemas import TeamCatchupRequest


def _resolve_trainee_name(raw_name: str) -> Optional[str]:
    if not raw_name or raw_name.lower() in ["all", "team", "everyone", "cohort"]:
        return None
    raw_lower = raw_name.lower().strip()
    try:
        from router import get_dynamic_trainees
        for t in get_dynamic_trainees():
            if raw_lower in t.lower() or t.lower() in raw_lower:
                return t
    except Exception:
        pass
    return raw_name


class TeamAgent:
    def __init__(self):
        self.name = "Team Intelligence Agent"
        self.persona = "Peer Catch-Up & Action Specialist"
        self.skill = team_session_catchup

    def handle_request(self, query: str, date: Optional[str] = None, trainee: Optional[str] = None, strategy: Optional[str] = None, trace_id: Optional[str] = None) -> str:
        if trainee:
            trainee = _resolve_trainee_name(trainee)

        req = TeamCatchupRequest(
            date=date,
            trainee=trainee,
            query=query,
            strategy=strategy,
            trace_id=trace_id
        )
        return self.skill.execute(req)


# Global singleton instance
team_agent = TeamAgent()
