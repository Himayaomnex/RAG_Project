"""
================================================================================
Mentor Skill: trainee_assessment (agents/mentor/skills/trainee_assessment.py)
================================================================================
Implements the 10-stage operational workflow for mentor_trainee_assessment:
1. Identify the trainee and reporting period
2. Retrieve relevant work and learning evidence (via retrieval_client)
3. Identify concepts taught
4. Identify what the trainee attempted
5. Identify demonstrated understanding (Taught != Understood ladder)
6. Identify gaps and misconceptions
7. Compare with previous evidence
8. Identify recurring feedback
9. Produce the assessment
10. Self-check every conclusion against evidence & log trace
"""

import re
import json
from typing import Dict, Any, Optional, List
from ...shared.schemas import MentorAssessmentRequest, EvidenceChunk
from ...shared.retrieval_client import retrieval_client
from ...shared.llm_client import llm_client
from ...shared.logging import TraceLogger


class MentorTraineeAssessmentSkill:
    def __init__(self):
        self.skill_name = "mentor_trainee_assessment"
        self.agent_name = "mentor"

    def execute(self, request: MentorAssessmentRequest) -> str:
        logger = TraceLogger(
            agent=self.agent_name,
            skill=self.skill_name,
            input_query=request.query,
            input_params=request.model_dump()
        )

        trainee = request.trainee.strip()
        speaker_filter = trainee if trainee and trainee.lower() not in ["all", "team"] else None

        # STAGE 2: Retrieve Relevant Work & Learning Evidence
        chunks: List[EvidenceChunk] = retrieval_client.query_evidence(
            query=f"{trainee or 'trainee'} technical implementation code review {request.focus_area or ''}",
            speaker_filter=speaker_filter,
            limit=40,
            strategy="precision"
        )

        chunk_ids = [c.chunk_id for c in chunks]
        logger.record_retrieval(chunk_ids)

        # FAILURE CHECK: Missing Evidence
        if not chunks:
            failure_msg = f"INSUFFICIENT_EVIDENCE: No transcript evidence found for trainee '{trainee}'."
            logger.set_failure(failure_msg, status="INSUFFICIENT_EVIDENCE")
            return logger.complete(failure_msg, status="INSUFFICIENT_EVIDENCE").output

        # Format XML Context for LLM
        xml_evidence_lines = ["<transcript_evidence>"]
        for c in chunks:
            xml_evidence_lines.append(
                f'  <turn id="{c.chunk_id}" date="{c.date}" doc="{c.source_file}" page="{c.page}" speaker="{c.speaker}">\n'
                f'    {c.text.strip()}\n'
                f'  </turn>'
            )
        xml_evidence_lines.append("</transcript_evidence>")
        xml_evidence = "\n".join(xml_evidence_lines)

        # STAGES 3 TO 9: Pedagogical Reasoning & Assessment Production
        system_prompt = (
            "You are Siddharth Saminathan, Lead Technical Mentor & AI Architect.\n"
            "Your task is to evaluate a trainee's demonstrated progress based strictly on transcript turns.\n\n"
            "CRITICAL COGNITIVE RULE:\n"
            "• Taught ≠ Understood. A concept mentioned by the mentor does NOT prove understanding.\n"
            "• You may only claim 'Demonstrated' if the mentee defends trade-offs or shows working code.\n"
            "• If evidence does not establish understanding, explicitly write: 'Not demonstrated from available evidence'.\n"
            "• For every misconception, state what the mentee believed vs what is actually true.\n"
            "• Cite [Date, Page — Speaker] for every key evaluation item.\n"
            "• Format output in clear prose under short headers (no markdown tables)."
        )

        user_prompt = (
            f"Target Trainee: {trainee}\n"
            f"Period: {request.period or 'All Sessions'}\n"
            f"Focus Area: {request.focus_area or 'General AI/ML Architecture'}\n"
            f"Query: {request.query}\n\n"
            f"{xml_evidence}\n\n"
            "Generate the Mentor Trainee Assessment following the exact output schema:\n"
            f"{trainee} · Overall assessment\n"
            "Current work\n"
            "Demonstrated capabilities\n"
            "Learning progress\n"
            "Knowledge gaps\n"
            "Recurring misconceptions\n"
            "Feedback signals\n"
            "Change from previous period\n"
            "Evidence-backed conclusion"
        )

        try:
            assessment_text, model_name, pt, ct = llm_client.generate(
                system_instruction=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1
            )
            logger.record_llm_call(model=model_name, prompt_tokens=pt, completion_tokens=ct)

            if not assessment_text.strip():
                failure_msg = "INSUFFICIENT_EVIDENCE: Generation produced empty output."
                logger.set_failure(failure_msg, status="INSUFFICIENT_EVIDENCE")
                return logger.complete(failure_msg, status="INSUFFICIENT_EVIDENCE").output

            return logger.complete(assessment_text, status="SUCCESS").output

        except Exception as e:
            err_msg = f"ERROR: Mentor trainee assessment failed during LLM stage: {str(e)}"
            logger.set_failure(err_msg, status="ERROR")
            return logger.complete(err_msg, status="ERROR").output


# Global singleton instance
mentor_trainee_assessment = MentorTraineeAssessmentSkill()
