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

        # Detect query intent: Curriculum Summary vs Trainee Assessment
        is_curriculum_query = any(w in request.query.lower() for w in [
            "teach", "taught", "explain", "explained", "cover", "covered",
            "introduce", "introduced", "what did siddharth", "what did the mentor",
            "what was covered", "what topics", "curriculum", "lesson"
        ])

        # Cohort-wide or exhaustive queries need full corpus (p4), single-trainee needs precision (p1)
        is_cohort_query = not speaker_filter or any(w in request.query.lower() for w in [
            "all", "trainees", "team", "everyone", "cohort", "entire",
            "breakdown", "performance", "exhaustive", "pyramid", "2000 token"
        ])
        # Mentor uses precision-first retrieval even for cohort queries.
        # exp4 sends 689 chunks (~345k tokens) and causes Gemini 503 timeouts.
        retrieval_strategy = "exp1"
        use_reranker = True

        chunks: List[EvidenceChunk] = retrieval_client.query_evidence(
            query=search_query,
            speaker="Siddharth Saminathan" if is_curriculum_query else speaker_filter,
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
                skill_spec = f.read()

        if is_curriculum_query:
            system_prompt = (
                "You are summarising what the Lead Technical Mentor (Siddharth Saminathan) taught the trainees.\n"
                "Based strictly on the transcript evidence provided, answer the user's curriculum question.\n\n"
                "OUTPUT FORMAT:\n"
                "### **Topics Taught by Siddharth**\n"
                "Organise the answer by topic/theme — NOT by date. For each topic:\n"
                "  - State the core concept taught\n"
                "  - Include a direct quote or paraphrase with citation [Date, Page — Siddharth Saminathan]\n"
                "  - Note WHY Siddharth emphasised this concept if stated in the evidence\n\n"
                "RULES:\n"
                "1. Only report concepts Siddharth himself explained or directed — not trainee work.\n"
                "2. CITATION FORMAT: [Date, Page — Siddharth Saminathan] on every point.\n"
                "3. Do not invent or assume topics not present in the evidence.\n"
            )
        else:
            # Detect if user explicitly asked for Pyramid Principle structure
            is_pyramid_query = any(w in request.query.lower() for w in [
                "pyramid principle", "pyramid", "exhaustive", "2000 token", "breakdown"
            ])

            # Build numbered KEY ARGUMENT sections dynamically from live trainee list
            key_args_text = ""
            for i, name in enumerate(active_trainees, start=2):
                key_args_text += (
                    f"{i}. ### KEY ARGUMENT {i - 1} — {name}\n"
                    f"   - One sharp verdict sentence\n"
                    f"   - Demonstrated capabilities with citations [Date, Page — Speaker]\n"
                    f"   - Knowledge gaps with citations\n"
                    f"   - Score: Overall X/10\n\n"
                )

            if is_pyramid_query:
                system_prompt = (
                    "You are the Lead Technical Mentor & AI Architect (Siddharth Saminathan).\n"
                    "The user has asked for a PYRAMID PRINCIPLE breakdown. Follow this structure EXACTLY:\n\n"
                    "=== PYRAMID PRINCIPLE STRUCTURE (MANDATORY) ===\n"
                    "The Pyramid Principle requires: STATE THE CONCLUSION FIRST, then support it with evidence below.\n\n"
                    "OUTPUT MUST FOLLOW THIS EXACT ORDER:\n"
                    "1. ### GOVERNING THOUGHT (1 sharp sentence)\n"
                    "   - The single most important conclusion about the cohort's performance.\n"
                    "   - Example: 'The cohort builds functional systems but cannot defend design choices from first principles.'\n\n"
                    f"{key_args_text}"
                    f"{len(active_trainees) + 2}. ### TRAINEE EVALUATION SCORES TABLE\n"
                    "   | Trainee | Preparation (1-10) | Conceptual Depth (1-10) | Code Quality (1-10) | Engagement (1-10) | Overall (1-10) | One-Line Verdict |\n\n"
                    f"{len(active_trainees) + 3}. ### PEDAGOGICAL RECOMMENDATION\n"
                    "   - What the mentor must teach next, specific per trainee\n\n"
                    "DETERMINISTIC RUBRIC SCORING SCALE (1-10):\n"
                    "- 9-10 (Mastery): Flawless architectural defense from first principles + production-grade implementation.\n"
                    "- 7-8 (Proficient): Working implementation with clear technical grasp; minor gaps in optimization.\n"
                    "- 5-6 (Developing): Basic component implementation, but struggles with architectural rationale, debugging, or token limits.\n"
                    "- 3-4 (Novice): Frequent misconceptions requiring repeated mentor intervention; unable to articulate system mechanics.\n"
                    "- 1-2 (Incomplete): No working code or evidence of understanding.\n\n"
                    "STRICT RULES:\n"
                    "- Lead with the CONCLUSION — never start with background context.\n"
                    "- Taught ≠ Understood: Only claim demonstrated capability when the mentee coded or defended it.\n"
                    "- EVERY claim must have [Date, Page — Speaker] citation.\n"
                    "- Do not invent facts not present in the evidence.\n"
                )
            else:
                system_prompt = (
                    "You are the Lead Technical Mentor & AI Architect (Siddharth Saminathan).\n"
                    "Your task is to provide a sharp, evidence-backed evaluation of the trainee based strictly on transcript records.\n\n"
                    "CRITICAL COGNITIVE & FORMATTING RULES:\n"
                    "0. QUERY ALIGNMENT (HIGHEST PRIORITY):\n"
                    "   - Directly and specifically address what the user asked. Do NOT dump unnecessary boilerplate sections.\n"
                    "   - Organize the evaluation cleanly:\n"
                    "     ### **[Trainee Name] · Performance Assessment**\n"
                    "     * **Overall Verdict**: 1-2 sharp sentences on practical execution vs conceptual grasp.\n"
                    "     * **Key Strengths & Demonstrated Capabilities**: Bullet points with concrete evidence.\n"
                    "     * **Knowledge Gaps & Misconceptions**: Bullet points with concrete evidence.\n"
                    "     * **Mentorship Guidance / Next Steps**: Specific focus areas for improvement.\n"
                    "   - If evaluating all trainees, repeat the structure cleanly for each active trainee: {trainees_str}.\n"
                    "1. TAUGHT ≠ UNDERSTOOD:\n"
                    "   - Never claim demonstrated capability unless the mentee explained, coded, or defended the solution.\n"
                    "   - If unproven, state 'Not demonstrated from available evidence'.\n"
                    "2. DETERMINISTIC RUBRIC SCORING SCALE (1-10):\n"
                    "   - 9-10 (Mastery): Flawless architectural defense from first principles + production-grade implementation.\n"
                    "   - 7-8 (Proficient): Working implementation with clear technical grasp; minor gaps in optimization.\n"
                    "   - 5-6 (Developing): Basic component implementation, but struggles with architectural rationale, debugging, or token limits.\n"
                    "   - 3-4 (Novice): Frequent misconceptions requiring repeated mentor intervention; unable to articulate system mechanics.\n"
                    "   - 1-2 (Incomplete): No working code or evidence of understanding.\n"
                    "3. EXACT CITATION FORMAT: Every single claim and evaluation must be backed by '[Date, Page — Speaker]' (e.g. '[28 July 2026, Page 18 — Siddharth Saminathan]').\n"
                    "4. QUOTE QUALITY: Select clear, technically meaningful statements without conversational filler.\n"
                    "5. SCORES TABLE (Include at the end):\n"
                    "   | Trainee | Preparation (1-10) | Conceptual Depth (1-10) | Code Quality (1-10) | Engagement (1-10) | Overall (1-10) | One-Line Verdict |\n"
                )



        # STAGE 8: Incorporate GitHub MCP Live Repo Context
        github_context = ""
        try:
            from github_mcp_client import github_mcp
            github_context = github_mcp.format_github_context_for_llm()
        except Exception as e:
            print(f"  - [GitHub MCP Injection Fail]: {e}")

        trainee_display = trainee if trainee else "Teammates"

        # Detect if the user has requested a custom output format
        # If yes, honour their format instead of enforcing the rigid schema headers
        raw_query_lower = request.query.lower()
        custom_format_signals = [
            "pyramid principle", "pyramid", "2000 token", "1000 token", "exhaustive",
            "detailed breakdown", "long report", "long form", "in depth", "in-depth",
            "comprehensive", "bullet point", "table format", "brief summary",
            "short summary", "one liner", "one line", "tldr", "tl;dr"
        ]
        has_custom_format = any(sig in raw_query_lower for sig in custom_format_signals)

        if has_custom_format:
            schema_instruction = (
                f"Generate the Mentor Trainee Assessment for: {trainee_display}.\n"
                "IMPORTANT FORMAT DIRECTIVE: The user has requested a specific output format in their query. "
                "You MUST honour this format request exactly — adapt the structure, length, depth, and layout "
                "to match what the user asked for (e.g., Pyramid Principle, exhaustive 2000-token breakdown, "
                "bullet points, brief summary). Ground every claim strictly in the transcript evidence provided. "
                "Always cite as '[Date, Page — Speaker]'. Do NOT default to the standard assessment schema."
            )
        else:
            schema_instruction = (
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

        user_prompt = (
            f"Target Trainee: {trainee or 'All Teammates'}\n"
            f"Period: {request.period or 'All Sessions'}\n"
            f"Focus Area: {request.focus_area or 'General AI/ML Architecture'}\n"
            f"Query: {request.query}\n\n"
            f"{github_context}\n\n"
            f"{xml_evidence}\n\n"
            f"{schema_instruction}"
        )

        try:
            assessment_text, model_name, pt, ct = llm_client.generate(
                system_instruction=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,
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
