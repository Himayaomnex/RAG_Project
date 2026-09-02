"""
================================================================================
Team Intelligence Skill: session_catchup (agents/team/skills/session_catchup.py)
================================================================================
Implements the 9-stage operational workflow for team_session_catchup:
1. Identify the requested session
2. Retrieve the session's evidence (via retrieval_client)
3. Identify major technical discussions
4. Identify assignments given
5. Identify decisions made
6. Identify changes and blockers
7. Filter for the requesting trainee
8. Produce the actionable catch-up
9. Self-check against evidence & log trace
"""

import os
import re
import json
from typing import Dict, Any, Optional, List
from ...shared.schemas import TeamCatchupRequest, EvidenceChunk
from ...shared.retrieval_client import retrieval_client
from ...shared.llm_client import llm_client
from ...shared.logging import TraceLogger


class TeamSessionCatchupSkill:
    def __init__(self):
        self.skill_name = "team_session_catchup"
        self.agent_name = "team"

    def execute(self, request: TeamCatchupRequest) -> str:
        logger = TraceLogger(
            agent=self.agent_name,
            skill=self.skill_name,
            input_query=request.query,
            input_params=request.model_dump(),
            trace_id=request.trace_id
        )

        clean_q = request.query
        if "<current_query>" in request.query:
            clean_match = re.search(r'<current_query>\s*(.*?)\s*</current_query>', request.query, re.DOTALL | re.IGNORECASE)
            if clean_match:
                clean_q = clean_match.group(1).strip()

        date_val = request.date
        if not date_val:
            # Match formats like "December 25 2099", "24 July 2026", "July 24", "24th July"
            months = "January|February|March|April|May|June|July|August|September|October|November|December"
            match = re.search(
                rf'(\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{months})(?:\s+\d{{2,4}})?|(?:{months})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,?\s*\d{{2,4}})?)',
                clean_q,
                re.IGNORECASE
            )
            if match:
                date_val = match.group(1).strip()
            else:
                date_val = None

        # STAGE 2: Retrieve the session's evidence (Driven by Router Strategy)
        strat = request.strategy or "exp1"
        
        # Calculate dynamic top_k context window size
        k_val = 40 if strat == "exp4" else (30 if strat in ("exp2", "exp3") else 20)

        chunks: List[EvidenceChunk] = retrieval_client.query_evidence(
            query=request.query,
            date=date_val,
            speaker=None,
            strategy=strat,
            use_reranker=(strat == "exp1"),
            top_k=k_val,
            agent_name="team",
            skill_name="session_catchup",
            trace_id=request.trace_id
        )

        chunk_ids = [c.chunk_id for c in chunks]
        logger.record_retrieval(chunk_ids)

        # FAILURE CHECK: Missing Evidence
        if not chunks:
            failure_msg = f"INSUFFICIENT_EVIDENCE: No transcript turns found for session date '{date_val}'."
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

        # STAGES 3–10: LLM Reasoning & Catch-up Production
        spec_path = os.path.join(os.path.dirname(__file__), "session_catchup.md")
        skill_spec = ""
        if os.path.exists(spec_path):
            with open(spec_path, "r", encoding="utf-8") as f:
                skill_spec = f.read()

        system_prompt = (
            "You are the Team Intelligence Agent.\n"
            "Your task is to answer the user's query about what happened in a training session.\n\n"
            f"=== OFFICIAL SKILL SPECIFICATION ===\n{skill_spec}\n\n"
            "CRITICAL COGNITIVE & CITATION RULES:\n"
            "0. QUERY ALIGNMENT & DATE STRICTNESS RULE (HIGHEST PRIORITY):\n"
            "   - When a specific Session Date is requested (e.g., 'July 28'), your answer MUST strictly report on discussions, decisions, and actions that occurred on THAT SPECIFIC DATE from <transcript_evidence>. Do NOT mix in or cite discussions from other dates.\n"
            "   - If the query asks a SPECIFIC question (e.g., 'what assignments were given?', 'what decisions were made?'), give a FOCUSED direct answer targeting exactly that.\n"
            "   - If the query asks for a FULL CATCH-UP (e.g., 'I missed the session, catch me up'), use the complete catch-up schema.\n"
            "1. Read all evidence turns in <transcript_evidence>.\n"
            "2. Focus strictly on what the mentee must know and do to resume work immediately.\n"
            "3. Discard chronological small talk, mic checks, and conversational chatter.\n"
            "4. CITATION RULE: Always cite as '[Date, Page — Speaker]' (e.g. '[28 July 2026, Page 18 — Siddharth Saminathan]'). NEVER use chunk IDs, hex numbers, or UUIDs in citations.\n"
            "5. PERSONALIZED ATTRIBUTION:\n"
            "   - If 'Requesting Trainee' is specified, use the name given in the query:\n"
            "     * Under 'Assignments and actions', ONLY output the bullet block for that requesting trainee and team-wide items ('- Team-Wide Action:').\n"
            "     * DO NOT output bullet blocks for other teammates.\n"
            "     * Under 'What you need to know or do', summarize only their individual next actions.\n"
            "   - If 'Requesting Trainee' is 'All Team Members' or omitted:\n"
            "     * Under 'Assignments and actions', separate tasks into distinct named blocks for each trainee and '- Team-Wide Action:'.\n"
            "   - NEVER use placeholder names like 'System Owner:'. Always use the actual trainee names from the transcripts.\n"
            "6. QUOTE QUALITY RULE: When selecting verbatim quotes, choose clear, technically meaningful statements. Avoid selecting conversational stutters, filler words ('uh', 'ah', 'oh', 'ok', 'wait'), or mic tests.\n"
            "7. DYNAMIC SESSION WHAT HAPPENED: Read the current query inside <current_query> carefully. Adapt the style, depth, length, and layout of the '### **Session · What happened**' section ONLY to satisfy the formatting instructions requested in the <current_query> (e.g., 'exhaustive recap', 'detailed analysis', 'short summary'). Do NOT carry over style instructions, word counts, or formatting requests from the <recent_conversation_turns> or <earlier_conversation_summary> blocks. If the <current_query> does not ask for a specific format or length, you MUST default to a clean, standard 1-2 sentence core objective.\n"
            "8. Present output in clean prose under short headers without markdown tables."
        )

        header_date_suffix = f" ({date_val})" if date_val else ""

        user_prompt = (
            f"Session Date: {date_val or 'All Sessions'}\n"
            f"Requesting Trainee: {request.trainee or 'All Team Members'}\n"
            f"Query: {request.query}\n\n"
            f"{xml_evidence}\n\n"
            "Generate the Team Session Catch-Up following the exact output schema:\n"
            f"### **Session · What happened{header_date_suffix}**\n"
            "### **Technical concepts discussed**\n"
            "### **Assignments and actions**\n"
            "### **Decisions**\n"
            "### **Important changes**\n"
            "### **What you need to know or do**"
        )

        try:
            catchup_text, model_name, pt, ct = llm_client.generate(
                system_instruction=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                trace_id=request.trace_id
            )
            logger.record_llm_call(model=model_name, prompt_tokens=pt, completion_tokens=ct)

            if not catchup_text.strip():
                failure_msg = "INSUFFICIENT_EVIDENCE: Generation produced empty output."
                logger.set_failure(failure_msg, status="INSUFFICIENT_EVIDENCE")
                return logger.complete(failure_msg, status="INSUFFICIENT_EVIDENCE").output

            return logger.complete(catchup_text, status="SUCCESS").output

        except Exception as e:
            err_msg = f"ERROR: Team session catchup failed during LLM stage: {str(e)}"
            logger.set_failure(err_msg, status="ERROR")
            return logger.complete(err_msg, status="ERROR").output


# Global singleton instance
team_session_catchup = TeamSessionCatchupSkill()
