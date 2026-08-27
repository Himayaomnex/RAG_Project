"""
================================================================================
Mentor Agent (agents/mentor/agent.py)
================================================================================
Persona: Technical Evaluation & Learning Specialist
Skill: mentor_trainee_assessment
"""

from typing import Optional, Dict, Any
from .skills.trainee_assessment import mentor_trainee_assessment
from ..shared.schemas import MentorAssessmentRequest


class MentorAgent:
    def __init__(self):
        self.name = "Mentor Agent"
        self.persona = "Technical Evaluation & Learning Specialist"
        self.skill = mentor_trainee_assessment

    def handle_request(self, query: str, trainee: Optional[str] = None, period: Optional[str] = None, focus_area: Optional[str] = None, strategy: Optional[str] = None, trace_id: Optional[str] = None) -> str:
        req = MentorAssessmentRequest(
            trainee=trainee if trainee else "",
            period=period,
            focus_area=focus_area,
            query=query,
            strategy=strategy,
            trace_id=trace_id
        )
        return self.skill.execute(req)


# Global singleton instance
mentor_agent = MentorAgent()
