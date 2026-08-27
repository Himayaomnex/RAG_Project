"""
================================================================================
Manager Skill: weekly_rollup (agents/manager/skills/weekly_rollup.py)
================================================================================
Implements the 8-stage operational workflow for manager_weekly_rollup:
1. Determine the reporting period
2. Retrieve relevant evidence for the period (via retrieval_client)
3. Separate evidence by trainee
4. Identify assignments, progress, blockers, decisions
5. Cross-check every status against evidence
6. Identify changes and intervention points
7. Produce the executive report
8. Self-check the report against evidence & log trace
"""

import os
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
            input_params=request.model_dump(),
            trace_id=request.trace_id
        )

        # STAGE 1: Determine Reporting Period & Trainee Filters
        period_str = f"{request.period_start or ''} to {request.period_end or ''}".strip(" to ")
        target_trainee = request.trainee if request.trainee and request.trainee.lower() not in ["all", "team"] else None

        # STAGE 2: Retrieve Relevant Evidence (Driven by Router Strategy)
        strat = request.strategy or "exp4"
        chunks: List[EvidenceChunk] = retrieval_client.query_evidence(
            query=request.query,
            speaker=target_trainee,
            date=period_str or None,
            strategy=strat,
            use_reranker=(strat == "exp1"),
            agent_name="manager",
            skill_name="weekly_rollup",
            trace_id=request.trace_id
        )
        
        chunk_ids = [c.chunk_id for c in chunks]
        logger.record_retrieval(chunk_ids)

        # FAILURE CHECK: Missing or Empty Evidence
        if not chunks:
            failure_msg = "INSUFFICIENT_EVIDENCE: No transcript evidence available for the requested review period."
            logger.set_failure(failure_msg, status="INSUFFICIENT_EVIDENCE")
            return logger.complete(failure_msg, status="INSUFFICIENT_EVIDENCE").output

        # STAGE 3: Dynamically Separate Evidence by Speaker
        trainee_chunks: Dict[str, List[EvidenceChunk]] = {}
        for c in chunks:
            spk = c.speaker.strip() or "General"
            if spk not in trainee_chunks:
                trainee_chunks[spk] = []
            trainee_chunks[spk].append(c)

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

        # STAGES 4, 5, 6 & 7: LLM Reasoning & Executive Report Production
        # Dynamically load the skill specification markdown file
        spec_path = os.path.join(os.path.dirname(__file__), "weekly_rollup.md")
        skill_spec = ""
        if os.path.exists(spec_path):
            with open(spec_path, "r", encoding="utf-8") as f:
                skill_spec = f.read()

        system_prompt = (
            "You are the Executive Engineering Manager.\n"
            "Your task is to answer the user's query using evidence from the transcript records.\n\n"
            f"=== OFFICIAL SKILL SPECIFICATION ===\n{skill_spec}\n\n"
            "CRITICAL FORMATTING & EVIDENCE RULES:\n"
            "0. QUERY ALIGNMENT RULE (HIGHEST PRIORITY): Read the exact query carefully. Your answer MUST directly and specifically address what was asked. Match the answer scope to the question scope:\n"
            "   - If the query asks a SPECIFIC question (e.g., 'what did a specific trainee complete?', 'list the blockers for a trainee', 'what decisions were made on a specific date?'), give a FOCUSED direct answer targeting exactly that — do NOT produce all 5 schema sections when only one is relevant.\n"
            "   - If the query asks for a FULL STATUS REPORT or ROLLUP (e.g., 'give me the weekly rollup', 'full project status', 'executive report'), THEN use the complete output schema with all sections.\n"
            "   - The answer length and structure must be PROPORTIONAL to the question. A narrow question → a focused answer. A broad rollup request → the full schema.\n"
            "1. Read all evidence turns in <transcript_evidence>.\n"
            "2. Avoid vague generalities. Always name specific systems (RAG, Qdrant, Excel openpyxl, Random Forest, BM25, MCP, etc.).\n"
            "3. Completed: Must use exact format: '- [Trainee Name] · [Deliverable Title]: [1-2 sentences explaining technical mechanics]. Quote: \"[Exact supporting quote]\" [Date, Page — Speaker]'\n"
            "4. In Progress: Must use exact format: '- [Trainee Name] · [Task Title]: [Current engineering state and next step] [Date, Page — Speaker]'\n"
            "5. Blocked or At Risk: Must use exact format: '- [Trainee Name] · [Impediment]: [Details]. Resolution State: [Agreed/Contested/Pending Decision] [Date, Page — Speaker]'\n"
            "6. Important Changes: Must use exact format: '- [Topic]: [What architectural or tool shift occurred] [Date, Page — Speaker]'\n"
            "7. Requires Attention: Must use exact format: '- [Issue]: [Recommended executive intervention point] [Date, Page — Speaker]'\n"
            "8. CITATION RULE: Every citation MUST be formatted as '[Date, Page — Speaker]' (e.g. '[28 July 2026, 18 — Siddharth Saminathan]'). NEVER output raw UUIDs, hex strings, or chunk IDs in citations.\n"
            "9. QUOTE QUALITY RULE: When selecting verbatim quotes, choose clear, technically meaningful statements. Avoid selecting conversational stutters, fillers ('uh', 'ah', 'wait', 'oh', 'ok'), or mic testing dialogue unless absolutely no other quote exists.\n"
            "10. DYNAMIC EXECUTIVE CONCLUSION: Read the current query inside <current_query> carefully. Adapt the style, depth, length, and layout of the '### **Executive conclusion**' section ONLY to satisfy the formatting instructions requested in the <current_query> (e.g., 'pyramid principle breakdown', 'exhaustive', 'short summary'). Do NOT carry over style instructions, word counts, or formatting requests from the <conversation_history> block. If the <current_query> does not ask for a specific format or length, you MUST default to a clean, standard 1-2 sentence governing takeaway.\n"
            "11. Never invent facts or infer completion from absence of discussion.\n"
            "12. If evidence for a mentee is missing, state '- [Trainee Name]: INSUFFICIENT_EVIDENCE'."
        )

        # STAGE 8: Incorporate GitHub MCP Live Repo Context
        github_context = ""
        try:
            from github_mcp_client import github_mcp
            github_context = github_mcp.format_github_context_for_llm()
        except Exception as e:
            print(f"  - [GitHub MCP Injection Fail]: {e}")

        # Detect if the user has requested a custom output format
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
                "Generate the Executive State-of-Work Report.\n"
                "IMPORTANT FORMAT DIRECTIVE: The user has requested a specific output format in their query. "
                "You MUST honour this format request exactly — adapt the structure, length, depth, and layout "
                "to match what the user asked for (e.g., Pyramid Principle, exhaustive breakdown, brief summary). "
                "Ground every claim strictly in the transcript evidence provided. "
                "Always cite as '[Date, Page — Speaker]'. Do NOT default to the standard section schema."
            )
        else:
            schema_instruction = (
                "Generate the Executive State-of-Work Report following the exact output schema:\n\n"
                "### **Executive conclusion**\n"
                "[Adapt this text dynamically to fulfill any specific styling, structure (e.g., Pyramid Principle), or length instructions in the user's query]\n\n"
                "### **Completed**\n"
                "- [Trainee Name] · [Deliverable Title]: [Details]. Quote: \"[One exact supporting quote]\" [Date, Page — Speaker]\n\n"
                "### **In Progress**\n"
                "- [Trainee Name] · [Task Title]: [Current engineering state and next step] [Date, Page — Speaker]\n\n"
                "### **Blocked or At Risk**\n"
                "- [Trainee Name] · [Impediment]: [Details]. Resolution State: [Agreed/Contested/Pending Decision] [Date, Page — Speaker]\n\n"
                "### **Important Changes**\n"
                "- [Topic]: [What architectural or tool shift occurred] [Date, Page — Speaker]\n\n"
                "### **Requires Attention**\n"
                "- [Issue]: [Recommended executive intervention point] [Date, Page — Speaker]"
            )

        user_prompt = (
            f"Review Period: {period_str or 'Full Review Window'}\n"
            f"Target Trainee: {target_trainee or 'All Trainees'}\n"
            f"Query: {request.query}\n\n"
            f"{github_context}\n\n"
            f"{xml_evidence}\n\n"
            f"{schema_instruction}"
        )

        try:
            report_text, model_name, pt, ct = llm_client.generate(
                system_instruction=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                trace_id=request.trace_id
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
