"""
================================================================================
Manager Agent (agents/manager/agent.py)
================================================================================
Persona: Iyappan Sir (Executive Status & Decision Specialist)
Skill: manager_weekly_rollup
"""

import re
from typing import Optional, Dict, Any
from .skills.weekly_rollup import manager_weekly_rollup
from ..shared.schemas import ManagerRollupRequest


class ManagerAgent:
    def __init__(self):
        self.name = "Manager Agent"
        self.persona = "Iyappan Sir (Executive Status & Decision Specialist)"
        self.skill = manager_weekly_rollup

    def handle_request(self, query: str, period_start: Optional[str] = None, period_end: Optional[str] = None, trainee: Optional[str] = None) -> str:
        # Extract trainee filter from query if not explicitly passed
        if not trainee:
            q_low = query.lower()
            if "ganesh" in q_low and "himaya" not in q_low and "dakshinya" not in q_low:
                trainee = "Ganesh"
            elif "himaya" in q_low and "ganesh" not in q_low and "dakshinya" not in q_low:
                trainee = "Himaya"
            elif "dakshinya" in q_low and "ganesh" not in q_low and "himaya" not in q_low:
                trainee = "Dakshinya"

        req = ManagerRollupRequest(
            query=query,
            period_start=period_start,
            period_end=period_end,
            trainee=trainee
        )
        return self.skill.execute(req)


# Global singleton instance
manager_agent = ManagerAgent()
