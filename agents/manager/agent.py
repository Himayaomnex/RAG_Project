"""
================================================================================
Manager Agent (agents/manager/agent.py)
================================================================================
Persona: Executive Status & Decision Specialist
Skill: manager_weekly_rollup
"""

import re
from typing import Optional, Dict, Any
from .skills.weekly_rollup import manager_weekly_rollup
from ..shared.schemas import ManagerRollupRequest


class ManagerAgent:
    def __init__(self):
        self.name = "Manager Agent"
        self.persona = "Executive Status & Decision Specialist"
        self.skill = manager_weekly_rollup

    def handle_request(self, query: str, period_start: Optional[str] = None, period_end: Optional[str] = None, trainee: Optional[str] = None, trace_id: Optional[str] = None) -> str:
        req = ManagerRollupRequest(
            query=query,
            period_start=period_start,
            period_end=period_end,
            trainee=trainee if trainee else None,
            trace_id=trace_id
        )
        return self.skill.execute(req)


# Global singleton instance
manager_agent = ManagerAgent()
