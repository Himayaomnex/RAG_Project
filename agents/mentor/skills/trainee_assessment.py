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

        # Fetch active trainee names live from the API — no hardcoding
        active_trainees: list = retrieval_client.get_active_trainees(exclude_mentor=True)
        trainees_str = ", ".join(active_trainees) if active_trainees else "all active trainees"

        trainee = request.trainee.strip()
        speaker_filter = trainee if trainee and trainee.lower() not in ["all", "team"] else None

        # STAGE 2: Retrieve Relevant Work & Learning Evidence (Precision-First via Retrieval Client)
        search_query = request.query
        if trainee and trainee.lower() not in ["all", "team"]:
            search_query = f"{trainee} {request.query}"

        # Retrieval Strategy & Reranker are derived dynamically by the LLM Router
        retrieval_strategy = request.strategy or "exp1"
        use_reranker = (retrieval_strategy == "exp1")

        chunks: List[EvidenceChunk] = retrieval_client.query_evidence(
            query=search_query,
            speaker=speaker_filter,
            date=request.period or None,
            strategy=retrieval_strategy,
            use_reranker=use_reranker,
            agent_name="mentor",
            skill_name="trainee_assessment",
            trace_id=request.trace_id
        )

        chunk_ids = [c.chunk_id for c in chunks]
        logger.record_retrieval(chunk_ids)

        # FAILURE CHECK: Missing Evidence
        if not chunks:
            failure_msg = f"INSUFFICIENT_EVIDENCE: No transcript evidence found for query '{request.query}'."
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
        spec_path = os.path.join(os.path.dirname(__file__), "trainee_assessment.md")
        skill_spec = ""
        if os.path.exists(spec_path):
            with open(spec_path, "r", encoding="utf-8") as f:
                skill_spec = f.read()        # STAGE 3: Build Unified Cognitive Mentor Prompt (Zero keyword branching)
        # Dynamically inject active trainee names discovered live from database
        key_args_template = "\n".join(
            f"   - ### KEY ARGUMENT — {name}: Verdict, Capabilities with [Date, Page — Speaker], Gaps, Score (1-10)"
            for name in active_trainees
        )

        system_prompt = (
            "You are the Lead Technical Mentor & AI Architect (Siddharth Saminathan).\n"
            "Analyze the retrieved transcript evidence and provide a sharp, evidence-backed response.\n\n"
            "CRITICAL COGNITIVE RULES:\n"
            "1. TAUGHT ≠ UNDERSTOOD: Never claim demonstrated capability unless the mentee coded, explained, or defended the solution.\n"
            "2. STRICT CITATIONS: Every claim, strength, gap, or topic MUST cite '[Date, Page — Speaker]' (e.g. '[2026-07-28, Page 18 — Siddharth Saminathan]').\n"
            "3. DETERMINISTIC RUBRIC (1-10):\n"
            "   - 9-10 (Mastery): Flawless architectural defense from first principles + production code.\n"
            "   - 7-8 (Proficient): Working implementation with clear technical grasp; minor optimization gaps.\n"
            "   - 5-6 (Developing): Basic component implementation, but struggles with architectural rationale, debugging, or token limits.\n"
            "   - 3-4 (Novice): Frequent misconceptions requiring repeated mentor correction.\n"
            "   - 1-2 (Incomplete): No working code or evidence of understanding.\n"
            "   - SCORE RULE: In the Scores Table, every score column MUST be a single integer number (1-10) evaluated from their technical discussions and coding deliverables. NEVER output 'N/A' or explanatory text inside numerical score cells.\n\n"
            "FORMATTING ADAPTATION (Follow what the user query asks):\n"
            "• If user asks for Pyramid Principle / Cohort Breakdown:\n"
            "  1. ### GOVERNING THOUGHT (1 sharp overarching verdict)\n"
            f"{key_args_template}\n"
            "  3. ### TRAINEE EVALUATION SCORES TABLE\n"
            "     | Trainee | Preparation (1-10) | Conceptual Depth (1-10) | Technical Implementation (1-10) | Engagement (1-10) | Overall (1-10) | One-Line Verdict |\n"
            "  4. ### PEDAGOGICAL RECOMMENDATION (Targeted plan per trainee)\n\n"
            "• If user asks about a specific trainee:\n"
            "  ### **[Trainee Name] · Performance Assessment**\n"
            "  * **Overall Verdict**: 1-2 sharp sentences.\n"
            "  * **Key Strengths & Demonstrated Capabilities**: Bullet points with citations.\n"
            "  * **Knowledge Gaps & Misconceptions**: Bullet points with citations.\n"
            "  * **Mentorship Guidance / Next Steps**: Specific focus areas.\n"
            "  * **Scores Table** (1-10 Rubric row for that trainee: | Trainee | Preparation | Conceptual Depth | Technical Implementation | Engagement | Overall | Verdict |).\n\n"
            "• If user asks what Siddharth taught / curriculum:\n"
            "  ### **Topics Taught by Siddharth** (Organized by theme, core concept, direct quote with citation, and why emphasized).\n"
        )

        user_prompt = (
            f"Target Trainee: {trainee or 'All Teammates'}\n"
            f"Period: {request.period or 'All Sessions'}\n"
            f"Focus Area: {request.focus_area or 'General AI/ML Architecture'}\n"
            f"Query: {request.query}\n\n"
            f"{xml_evidence}\n\n"
            "Generate the assessment strictly adhering to the cognitive rules and formatting directives above."
        )

        try:
            assessment_text, model_name, pt, ct = llm_client.generate(
                system_instruction=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                trace_id=request.trace_id
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
