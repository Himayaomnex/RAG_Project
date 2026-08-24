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
        import re
        if not trainee or trainee.lower() in ["all", "team", "everyone", "full"]:
            q_low = query.lower()
            if "ganesh" in q_low and "himaya" not in q_low and "dakshinya" not in q_low:
                trainee = "Ganesh"
            elif "dakshinya" in q_low and "ganesh" not in q_low and "himaya" not in q_low:
                trainee = "Dakshinya"
            elif "himaya" in q_low and "ganesh" not in q_low and "dakshinya" not in q_low:
                trainee = "Himaya"
            else:
                # Extract requested person name if mentioned e.g. "Assess Rahul Sharma's progress"
                m = re.search(r'assess\s+([a-zA-Z\s]+?)(?:\'s|\s+progress|\s+technical|\s+understanding|\s+on|\s+for|\s*$)', query, re.IGNORECASE)
                if m:
                    extracted = m.group(1).strip()
                    if extracted.lower() not in ["the", "this", "my", "our", "all", "team"]:
                        trainee = extracted
                if not trainee:
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
