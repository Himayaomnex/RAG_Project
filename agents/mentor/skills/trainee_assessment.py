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

import os
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
            input_params=request.model_dump(),
            trace_id=request.trace_id
        )

        trainee = request.trainee.strip()
        speaker_filter = trainee if trainee and trainee.lower() not in ["all", "team"] else None

        # STAGE 2: Retrieve Relevant Work & Learning Evidence
        chunks: List[EvidenceChunk] = retrieval_client.query_evidence(
            query=f"{trainee or 'trainee'} technical implementation code review {request.focus_area or ''}",
            speaker_filter=speaker_filter,
            date_filter=request.period or None,
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
                f'  <turn date="{c.date}" page="{c.page}" speaker="{c.speaker}" doc="{c.source_file}">\n'
                f'    {c.text.strip()}\n'
                f'  </turn>'
            )
        xml_evidence_lines.append("</transcript_evidence>")
        xml_evidence = "\n".join(xml_evidence_lines)

        # STAGES 3 TO 9: Pedagogical Reasoning & Assessment Production
        # Dynamically load the skill specification markdown file
        spec_path = os.path.join(os.path.dirname(__file__), "trainee_assessment.md")
        skill_spec = ""
        if os.path.exists(spec_path):
            with open(spec_path, "r", encoding="utf-8") as f:
                skill_spec = f.read()

        system_prompt = (
            "You are the Lead Technical Mentor & AI Architect.\n"
            "Your task is to produce a strict, evidence-backed evaluation for the specified trainee.\n\n"
            f"=== OFFICIAL SKILL SPECIFICATION ===\n{skill_spec}\n\n"
            "CRITICAL COGNITIVE & CITATION RULES:\n"
            "1. Read all evidence turns in <transcript_evidence>.\n"
            "2. Enforce the ladder: Taught != Understood. Never claim demonstrated capability unless the mentee explained or built it.\n"
            "3. If understanding is unproven, state 'Not demonstrated from available evidence'.\n"
            "4. CITATION RULE: Always cite as '[Date, Page — Speaker]' (e.g. '[28 July 2026, Page 18 — Siddharth Saminathan]'). NEVER use chunk IDs, hex numbers, or UUIDs in citations.\n"
            "5. QUOTE QUALITY RULE: When referencing or quoting transcript turns, select clear, technically meaningful statements. Avoid selecting or focusing on conversational stutters, filler words ('uh', 'ah', 'oh', 'ok'), or mic checks.\n"
            "6. DYNAMIC OVERALL ASSESSMENT: Read the current query inside <current_query> carefully. Adapt the style, depth, length, and layout of the '### **Trainee · Overall assessment**' section ONLY to satisfy the formatting instructions requested in the <current_query> (e.g., 'pyramid principle breakdown', 'exhaustive', 'short summary'). Do NOT carry over style instructions, word counts, or formatting requests from the <conversation_history> block. If the <current_query> does not ask for a specific format or length, you MUST default to a clean, standard 1-2 sentence verdict.\n"
            "7. Present output in clean prose under short headers without markdown tables."
        )

        # STAGE 8: Incorporate GitHub MCP Live Repo Context
        github_context = ""
        try:
            from github_mcp_client import github_mcp
            github_context = github_mcp.format_github_context_for_llm()
        except Exception as e:
            print(f"  - [GitHub MCP Injection Fail]: {e}")

        trainee_display = trainee if trainee else "Teammates"

        user_prompt = (
            f"Target Trainee: {trainee or 'All Teammates'}\n"
            f"Period: {request.period or 'All Sessions'}\n"
            f"Focus Area: {request.focus_area or 'General AI/ML Architecture'}\n"
            f"Query: {request.query}\n\n"
            f"{github_context}\n\n"
            f"{xml_evidence}\n\n"
            "Generate the Mentor Trainee Assessment following the exact output schema:\n"
            f"### **{trainee_display} · Overall assessment**\n"
            "### **Current work**\n"
            "### **Demonstrated capabilities**\n"
            "### **Learning progress**\n"
            "### **Knowledge gaps**\n"
            "### **Recurring misconceptions**\n"
            "### **Feedback signals**\n"
            "### **Change from previous period**\n"
            "### **Evidence-backed conclusion**"
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
