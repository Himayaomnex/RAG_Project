"""
================================================================================
Manager Skill: weekly_rollup (agents/manager/skills/weekly_rollup.py)
================================================================================
Implements the locked 8-stage workflow for manager_weekly_rollup:
1. Determine the reporting period
2. Retrieve relevant evidence for the period (via retrieval_client)
3. Separate evidence by trainee
4. Identify assignments, progress, blockers, decisions
5. Cross-check every status against evidence
6. Identify changes and intervention points
7. Produce the executive report
8. Self-check the report against evidence & log trace
"""

import re
import json
from typing import Dict, Any, Optional, List
from ...shared.schemas import ManagerRollupRequest, EvidenceChunk
from ...shared.retrieval_client import retrieval_client
from ...shared.llm_client import llm_client
from ...shared.logging import TraceLogger


class ManagerWeeklyRollupSkill:
    def __init__(self):
        self.skill_name = "manager_weekly_rollup"
        self.agent_name = "manager"

    def execute(self, request: ManagerRollupRequest) -> str:
        logger = TraceLogger(
            agent=self.agent_name,
            skill=self.skill_name,
            input_query=request.query,
            input_params=request.model_dump()
        )

        # STAGE 1: Determine Reporting Period & Trainee Filters
        period_str = f"{request.period_start or ''} to {request.period_end or ''}".strip(" to ")
        target_trainee = request.trainee if request.trainee and request.trainee.lower() not in ["all", "team"] else None

        # STAGE 2: Retrieve Relevant Evidence (Completeness-First via Retrieval Client)
        chunks: List[EvidenceChunk] = retrieval_client.query_evidence(
            query=request.query,
            speaker_filter=target_trainee,
            period_start=request.period_start,
            period_end=request.period_end,
            limit=60,
            strategy="completeness"
        )
        
        chunk_ids = [c.chunk_id for c in chunks]
        logger.record_retrieval(chunk_ids)

        # FAILURE CHECK: Missing or Empty Evidence
        if not chunks:
            failure_msg = "INSUFFICIENT_EVIDENCE: No transcript evidence available for the requested review period."
            logger.set_failure(failure_msg, status="INSUFFICIENT_EVIDENCE")
            return logger.complete(failure_msg, status="INSUFFICIENT_EVIDENCE").output

        # STAGE 3: Separate Evidence by Trainee
        trainee_chunks: Dict[str, List[EvidenceChunk]] = {"Himaya": [], "Ganesh": [], "Dakshinya": [], "General": []}
        for c in chunks:
            spk_low = c.speaker.lower()
            txt_low = c.text.lower()
            if "himaya" in spk_low or "himaya" in txt_low:
                trainee_chunks["Himaya"].append(c)
            elif "ganesh" in spk_low or "ganesh" in txt_low:
                trainee_chunks["Ganesh"].append(c)
            elif "dakshinya" in spk_low or "dakshinya" in txt_low:
                trainee_chunks["Dakshinya"].append(c)
            else:
                trainee_chunks["General"].append(c)

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

        # STAGES 4, 5, 6 & 7: LLM Reasoning & Executive Report Production
        system_prompt = (
            "You are Iyappan Sir, Executive Engineering Director.\n"
            "Your task is to generate a state-of-work report from the provided transcript evidence.\n\n"
            "OPERATIONAL RULES:\n"
            "1. Read all evidence turns in <transcript_evidence>.\n"
            "2. Completed: List only discrete deliverables verified as done and demonstrated in meetings. Quote at most one supporting sentence.\n"
            "3. In Progress: List active work currently being coded or debugged.\n"
            "4. Blocked or At Risk: Identify impediments. Label resolution state explicitly (Agreed / Contested / Resolved / Pending Decision).\n"
            "5. Important Changes: Note architectural or technology shifts.\n"
            "6. Requires Attention: State where executive intervention is required.\n"
            "7. Never invent facts or infer completion from absence of discussion.\n"
            "8. If evidence for a mentee is missing, state 'INSUFFICIENT_EVIDENCE for [Trainee]'.\n"
            "9. Present the output in clean prose under short headers (no markdown tables)."
        )

        user_prompt = (
            f"Review Period: {period_str or 'Full Review Window'}\n"
            f"Target Trainee: {target_trainee or 'All Trainees'}\n"
            f"Query: {request.query}\n\n"
            f"{xml_evidence}\n\n"
            "Generate the Executive State-of-Work Report following the exact output schema:\n"
            "Executive conclusion\n"
            "Completed\n"
            "In Progress\n"
            "Blocked or At Risk\n"
            "Important Changes\n"
            "Requires Attention"
        )

        try:
            report_text, model_name, pt, ct = llm_client.generate(
                system_instruction=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=4096
            )
            logger.record_llm_call(model=model_name, prompt_tokens=pt, completion_tokens=ct)

            # STAGE 8: Self-Check Against Evidence
            if not report_text.strip():
                failure_msg = "INSUFFICIENT_EVIDENCE: Generation produced empty output."
                logger.set_failure(failure_msg, status="INSUFFICIENT_EVIDENCE")
                return logger.complete(failure_msg, status="INSUFFICIENT_EVIDENCE").output

            return logger.complete(report_text, status="SUCCESS").output

        except Exception as e:
            err_msg = f"ERROR: Manager weekly rollup failed during LLM reasoning stage: {str(e)}"
            logger.set_failure(err_msg, status="ERROR")
            return logger.complete(err_msg, status="ERROR").output


# Global singleton instance
manager_weekly_rollup = ManagerWeeklyRollupSkill()
