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
        
        # Calculate dynamic top_k context window size
        k_val = 40 if retrieval_strategy == "exp4" else (30 if retrieval_strategy in ("exp2", "exp3") else 20)

        try:
            chunks: List[EvidenceChunk] = retrieval_client.query_evidence(
                query=search_query,
                speaker=speaker_filter,
                date=request.period or None,
                strategy=retrieval_strategy,
                use_reranker=use_reranker,
                top_k=k_val,
                agent_name="mentor",
                skill_name="trainee_assessment",
                trace_id=request.trace_id
            )
        except Exception as e:
            err_msg = str(e)
            logger.set_failure(err_msg, status="RETRIEVAL_UNAVAILABLE")
            logger.complete(err_msg, status="RETRIEVAL_UNAVAILABLE")
            raise e

        chunk_ids = [c.chunk_id for c in chunks]
        logger.record_retrieval(chunk_ids)

        # FAILURE CHECK: Missing Evidence
        if not chunks:
            clean_q = search_query
            if "<current_query>" in request.query:
                clean_match = re.search(r'<current_query>\s*(.*?)\s*</current_query>', request.query, re.DOTALL | re.IGNORECASE)
                if clean_match:
                    clean_q = clean_match.group(1).strip()
            failure_msg = f"INSUFFICIENT_EVIDENCE: No transcript evidence found for query '{clean_q}'."
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
            "   - SCORE RULE: In the Scores Table, every score column MUST be a single integer number (1-10) evaluated from their technical discussions and coding deliverables. NEVER output 'N/A' or explanatory text inside numerical score cells.\n"
            "4. NO UNRELATED ASSESSMENT SECTIONS: If the query is a specific request about what Siddharth taught, an analogy, or a curriculum topic (and NOT a request for trainee performance evaluation/breakdown), you MUST NOT output a scores table, pedagogical recommendations, or trainee-specific capability/gap/verdict sections. Output ONLY the direct focused answer to the query.\n\n"
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
            "• If user asks what Siddharth taught / curriculum (broad query):\n"
            "  ### **Topics Taught by Siddharth** (Organized by theme, core concept, direct quote with citation, and why emphasized).\n"
            "• If user asks a SPECIFIC question about a single concept, analogy, or story taught/mentioned by Siddharth:\n"
            "  Provide a focused direct response targeting ONLY that specific topic, analogy, or story, with exact quotes and citations, without listing other unrelated topics.\n"
        )

        # STAGE 8: Incorporate Live Knowledge Base Concept Gaps & Mentor Feedback
        kb_context = ""
        try:
            from ...shared.kb_client import kb_client
            concept_gaps = kb_client.get_concept_gaps(speaker_filter)
            qa_records = kb_client.get_qa_history(speaker_filter)
            feedback_records = kb_client.get_feedback_history(speaker_filter)
            
            kb_lines = ["<knowledge_base_ground_truth>"]
            if concept_gaps:
                kb_lines.append("  <verified_concept_gaps>")
                for cg in concept_gaps[:25]:
                    kb_lines.append(f"    <gap person=\"{cg.get('person')}\" concept=\"{cg.get('concept')}\" state=\"{cg.get('understanding_state')}\" date=\"{cg.get('session_date')}\">{cg.get('observation')}</gap>")
                kb_lines.append("  </verified_concept_gaps>")
            if qa_records:
                kb_lines.append("  <qa_benchmark_evaluations>")
                for q in qa_records[:20]:
                    kb_lines.append(f"    <qa answered_by=\"{q.get('answered_by')}\" topic=\"{q.get('topic')}\" quality=\"{q.get('answer_quality')}\" date=\"{q.get('session_date')}\">Q: {q.get('question_text')} | Answer: {q.get('answer_summary')}</qa>")
                kb_lines.append("  </qa_benchmark_evaluations>")
            if feedback_records:
                kb_lines.append("  <mentor_coaching_history>")
                for fb in feedback_records[:15]:
                    kb_lines.append(f"    <feedback to=\"{fb.get('to_person')}\" sentiment=\"{fb.get('sentiment')}\" topic=\"{fb.get('topic')}\" date=\"{fb.get('session_date')}\">{fb.get('verbatim_feedback')}</feedback>")
                kb_lines.append("  </mentor_coaching_history>")
            kb_lines.append("</knowledge_base_ground_truth>")
            kb_context = "\n".join(kb_lines)
        except Exception as e:
            print(f"  - [Mentor KB Injection Fail]: {e}")

        user_prompt = (
            f"Target Trainee: {trainee or 'All Teammates'}\n"
            f"Period: {request.period or 'All Sessions'}\n"
            f"Focus Area: {request.focus_area or 'General AI/ML Architecture'}\n"
            f"Query: {request.query}\n\n"
            f"{kb_context}\n\n"
            f"{xml_evidence}\n\n"
            "Generate the assessment strictly adhering to the cognitive rules and formatting directives above. Use verified concept gaps and QA ratings from <knowledge_base_ground_truth> to ground your assessment, and support every claim with verbatim citations from <transcript_evidence>."
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
