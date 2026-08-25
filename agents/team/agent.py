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


# Canonical trainee name map — single source of truth imported from router
def _get_trainee_role_map():
    try:
        from router import _TRAINEE_ROLE_MAP
        return _TRAINEE_ROLE_MAP
    except Exception:
        return {}


class TeamAgent:
    def __init__(self):
        self.name = "Team Intelligence Agent"
        self.persona = "Peer Catch-Up & Action Specialist"
        self.skill = team_session_catchup

    def handle_request(self, query: str, date: Optional[str] = None, trainee: Optional[str] = None, trace_id: Optional[str] = None) -> str:
        if trainee:
            t_low = trainee.lower()
            # Dynamically resolve canonical name from the router's trainee map
            role_map = _get_trainee_role_map()
            resolved = role_map.get(t_low)
            if resolved:
                trainee = resolved
            elif t_low in ["all", "team", "everyone", "cohort"]:
                trainee = None
            else:
                # Partial-match fallback: check if any canonical name is a substring
                for key, canonical in role_map.items():
                    if key in t_low or t_low in key:
                        trainee = canonical
                        break

        req = TeamCatchupRequest(
            date=date,
            trainee=trainee,
            query=query,
            trace_id=trace_id
        )
        return self.skill.execute(req)


# Global singleton instance
team_agent = TeamAgent()
