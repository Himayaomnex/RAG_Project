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

    def handle_request(self, query: str, trainee: Optional[str] = None, period: Optional[str] = None, focus_area: Optional[str] = None) -> str:
        if not trainee:
            q_low = query.lower()
            if "ganesh" in q_low and "himaya" not in q_low and "dakshinya" not in q_low:
                trainee = "Ganesh"
            elif "dakshinya" in q_low and "ganesh" not in q_low and "himaya" not in q_low:
                trainee = "Dakshinya"
            elif "himaya" in q_low and "ganesh" not in q_low and "dakshinya" not in q_low:
                trainee = "Himaya"
            else:
                trainee = ""

        req = MentorAssessmentRequest(
            trainee=trainee,
            period=period,
            focus_area=focus_area,
            query=query
        )
        return self.skill.execute(req)


# Global singleton instance
mentor_agent = MentorAgent()
