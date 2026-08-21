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

    def handle_request(self, query: str, date: Optional[str] = None, trainee: Optional[str] = None) -> str:
        req = TeamCatchupRequest(
            date=date,
            trainee=trainee,
            query=query
        )
        return self.skill.execute(req)


# Global singleton instance
team_agent = TeamAgent()
