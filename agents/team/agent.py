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


class TeamAgent:
    def __init__(self):
        self.name = "Team Intelligence Agent"
        self.persona = "Peer Catch-Up & Action Specialist"
        self.skill = team_session_catchup

    def handle_request(self, query: str, date: Optional[str] = None, trainee: Optional[str] = None, trace_id: Optional[str] = None) -> str:
        if trainee:
            t_low = trainee.lower()
            if "himaya" in t_low:
                trainee = "Himaya"
            elif "ganesh" in t_low:
                trainee = "Ganesh"
            elif "dakshinya" in t_low:
                trainee = "Dakshinya"
            elif t_low in ["all", "team", "everyone", "cohort"]:
                trainee = None

        req = TeamCatchupRequest(
            date=date,
            trainee=trainee,
            query=query,
            trace_id=trace_id
        )
        return self.skill.execute(req)


# Global singleton instance
team_agent = TeamAgent()
