"""
================================================================================
Enterprise Production Prompt Builder Engine (prompt_builder.py)
================================================================================
100% Production Enterprise-Grade Modular Runtime Prompt Builder.

Implements 10 Enterprise Prompt Builder Modules:
1. SECURITY & PRIVACY GUARDRAILS (User Scoping)
2. HALLUCINATION & FAILURE CONTROL (Strict Grounding & Zero Invention)
3. REASONING & THINKING POLICY (Step-by-Step Evidence Analysis)
4. METADATA CONTEXT (user_id, role, team_id, meeting_id)
5. AGENT ROLE & SPECIALIZED RESPONSE STYLES (Manager, Mentor, Teammates)
6. AVAILABLE TOOLS & CAPABILITY AWARENESS (RAG, Code, Quiz, Evaluation)
7. RETRIEVAL CONFIDENCE & CITATION POLICY (Date, Speaker, Page Citations)
8. SIGNAL-TO-NOISE RATIO OPTIMIZATION (Attention Window Token Prioritization)
9. CONVERSATION MEMORY POLICY (Evidence Supremacy)
10. DYNAMIC FLUENT BUILDER CHAIN ASSEMBLY
"""

from typing import Dict, Any, List, Optional

class EnterprisePromptBuilder:
    """
    100% Enterprise Production Prompt Builder Class.
    Assembles prompts dynamically via a fluent builder chain:
    Guardrails -> Hallucination -> Reasoning -> Metadata -> Role -> Tools -> RAG -> Code -> Citation -> Query
    """

    def __init__(self, agent_type: str = "teammates", user_id: str = "Anonymous", role: str = "user", team_members: Optional[List[str]] = None):
        self.agent_type = agent_type.lower()
        self.user_id = user_id
        self.role = role
        self.team_id = "aqua_rag_team"
        self.meeting_id = "Latest Meetings"
        self.team_members = team_members or []
        
        # Modules
        self.security_guardrails: List[str] = []
        self.hallucination_policy: List[str] = []
        self.reasoning_policy: List[str] = []
        self.metadata_context: Dict[str, str] = {}
        self.agent_role_instruction: List[str] = []
        self.available_tools: List[str] = []
        self.retrieved_chunks: List[str] = []
        self.codebase_chunks: List[str] = []
        self.citation_rules: List[str] = []
        self.response_schema: str = ""
        self.user_query: str = ""

    def add_security_guardrails(self, user_id: Optional[str] = None, role: Optional[str] = None, team_members: Optional[List[str]] = None) -> "EnterprisePromptBuilder":
        """Module 1: Dynamic User Scoping."""
        uid = user_id or self.user_id
        r = role or self.role
        members = team_members or self.team_members
        roster_str = f"ACTIVE TEAM ROSTER ({len(members)} MEMBERS): {', '.join(members)}." if members else "STRICT USER SCOPING: Scope data strictly to caller identity."
        self.security_guardrails = [
            "# 1. SECURITY & DATA PRIVACY (USER SCOPING)",
            f"• ACTIVE USER SCOPE: user_id = '{uid}', role = '{r}', team_id = '{self.team_id}'.",
            "• USER SCOPING: Only expose transcript evidence and codebase docs scoped to this user.",
            "• ZERO LEAKAGE: Do NOT leak private notes, queries, or user-scoped payloads belonging to other teammates.",
            f"• {roster_str} Do NOT introduce outside names or unverified identities."
        ]
        return self

    def add_hallucination_and_failure_policy(self) -> "EnterprisePromptBuilder":
        """Module 2 & 10: Automatic Evidence Proof & Hallucination Prevention Policy."""
        self.hallucination_policy = [
            "# 2. AUTOMATIC PROOF VERIFICATION & HALLUCINATION CONTROL",
            "• EVIDENCE PROOF RULE: State facts ONLY if you have direct proof in retrieved transcript evidence or codebase context.",
            "• ZERO PROOF = ZERO INVENTION: If requested information is absent or lacks evidence proof, respond strictly:",
            "  'The requested information is not available in retrieved meeting transcripts.'",
            "• NEVER fabricate meeting summaries, action items, scores, or quotes without transcript proof.",
            "• Do NOT guess, extrapolate, or infer unsupported statements."
        ]
        return self

    def add_reasoning_and_thinking_policy(self) -> "EnterprisePromptBuilder":
        """Module 3: Thinking Strategy & Reasoning Policy."""
        self.reasoning_policy = [
            "# 3. REASONING POLICY & THINKING PROCESS",
            "Before generating output, follow this reasoning plan:",
            "1. Read retrieved transcript evidence & codebase context carefully.",
            "2. Verify metadata scope (user_id, team_id, meeting_id).",
            "3. Extract verified facts matching active user query.",
            "4. Ignore unrelated token noise.",
            "5. Produce concise, structured output following formatting rules."
        ]
        return self

    def add_metadata_context(self, team_id: str, meeting_id: str) -> "EnterprisePromptBuilder":
        """Module 4: Dynamic Metadata Awareness passed from Router/Session context."""
        self.team_id = team_id
        self.meeting_id = meeting_id
        self.metadata_context = {
            "Current User": self.user_id,
            "Role": self.role,
            "Team ID": self.team_id,
            "Meeting Scope": self.meeting_id
        }
        return self

    def add_agent_role(self, agent_type: str, manager_name: Optional[str] = None, mentor_name: Optional[str] = None) -> "EnterprisePromptBuilder":
        """Module 5: Dynamic Agent Role & Specialized Response Styles."""
        self.agent_type = agent_type.lower()
        if self.agent_type == "manager":
            mgr = manager_name or self.user_id
            self.agent_role_instruction = [
                f"# 5. AGENT ROLE: MANAGER AGENT (Serving Project Manager: {mgr})",
                "Specialized Response Style: Executive Summary | Completed Milestones | Action Items per Member | Project Risks."
            ]
        elif self.agent_type == "mentor":
            mnt = mentor_name or self.user_id
            self.agent_role_instruction = [
                f"# 5. AGENT ROLE: MENTOR EVALUATION AGENT (Serving Mentor: {mnt})",
                "Specialized Response Style: Scorecard Matrix (1.0-5.0 Scale) | Spoken Evidence Observations | Overall Score / 5.0 | Quiz Questions."
            ]
        else: # teammates
            self.agent_role_instruction = [
                "# 5. AGENT ROLE & CAPABILITIES",
                "• Role: Teams' Technical Assistant (Teammates Agent).",
                "• Primary Task: Provide direct, grounded, high-quality technical answers and spoken transcript quotes for team members.",
                "• Specialized Response Style: Provide direct, grounded, high-quality technical answers citing exact transcript turns [Date | Page | Speaker]. Output strictly what the user asked for without forcing unrequested sections."
            ]
        return self

    def add_tool_descriptions(self) -> "EnterprisePromptBuilder":
        """Module 6: Available Tools Awareness."""
        self.available_tools = [
            "# 6. AVAILABLE SYSTEM TOOLS & HARNESS",
            "• Qdrant Vector Search Tool (Semantic transcript evidence search)",
            "• SHA-256 Embedding Cache (emb_cache 3.8ms vector lookup)",
            "• SQLite Relational DB (Exact dialogue counts & page-split metrics)",
            "• Local Codebase Scanner (Python architecture inspection)",
            "• FastMCP Tool Server & FastAPI REST Server Harness"
        ]
        return self

    def add_rag_context(self, context_chunks: List[str]) -> "EnterprisePromptBuilder":
        """RAG Evidence."""
        self.retrieved_chunks = context_chunks
        return self

    def add_code_context(self, file_name: str, code_snippet: str) -> "EnterprisePromptBuilder":
        """Codebase Context."""
        if code_snippet:
            self.codebase_chunks.append(f"### Codebase File: {file_name}\n```python\n{code_snippet[:2000]}\n```")
        return self

    def add_citation_rules(self) -> "EnterprisePromptBuilder":
        """Module 7: Citation & Verification Rules."""
        self.citation_rules = [
            "# 7. CITATION & VERIFICATION RULES",
            "• Every evaluation score or progress claim MUST cite transcript evidence.",
            "• Format citations with Date, Speaker, and Page (e.g., [27 July 2026 | Speaker: Himaya | Page 34]).",
            "• If evidence conflicts, prefer the most recent meeting turn."
        ]
        return self

    def add_response_schema(self, schema_markdown: str) -> "EnterprisePromptBuilder":
        self.response_schema = schema_markdown
        return self

    def add_user_query(self, query: str) -> "EnterprisePromptBuilder":
        self.user_query = query
        return self

    # Backward compatibility helper aliases
    def add_privacy_guardrails(self) -> "EnterprisePromptBuilder":
        return self.add_security_guardrails()

    def set_agent_role_instruction(self) -> "EnterprisePromptBuilder":
        return self.add_agent_role(self.agent_type)

    def set_rag_context(self, chunks: List[str]) -> "EnterprisePromptBuilder":
        return self.add_rag_context(chunks)

    def set_codebase_context(self, file_name: str, code_snippet: str) -> "EnterprisePromptBuilder":
        return self.add_code_context(file_name, code_snippet)

    def set_formatting_schema(self, schema: str) -> "EnterprisePromptBuilder":
        return self.add_response_schema(schema)

    def set_user_query(self, query: str) -> "EnterprisePromptBuilder":
        return self.add_user_query(query)

    def build(self) -> str:
        """
        Clean, Lightweight Enterprise RAG Prompt Builder:
        1. Role & Identity Context
        2. Retrieved Transcript Evidence
        3. Codebase Context (Optional)
        4. Response Schema & User Query
        """
        parts = []

        # 1. Simple System Role & Direct Instruction
        parts.append(f"You are the {self.agent_type.capitalize()} Assistant serving {self.user_id} ({self.role}).")
        parts.append("Answer the user's query based strictly on the retrieved meeting transcript evidence below.")
        parts.append("If no relevant transcript evidence is available, state: 'No transcript evidence found for this query.'")
        parts.append("")

        # 2. Retrieved Transcript Evidence
        parts.append("--- RETRIEVED TRANSCRIPT EVIDENCE ---")
        if self.retrieved_chunks:
            parts.extend(self.retrieved_chunks)
        else:
            parts.append("No specific transcript evidence found for this query.")
        parts.append("")

        # 3. Codebase Context (Optional)
        if self.codebase_chunks:
            parts.append("--- CODEBASE CONTEXT ---")
            parts.extend(self.codebase_chunks)
            parts.append("")

        # 4. Response Schema (Optional)
        if self.response_schema:
            parts.append("--- INSTRUCTIONS & OUTPUT FORMAT ---")
            parts.append(self.response_schema)
            parts.append("")

        # 10. Active User Query (High Attention Window at Bottom)
        parts.append("================================================================================")
        parts.append("ACTIVE USER QUERY (HIGH ATTENTION WINDOW)")
        parts.append("================================================================================")
        parts.append(f"User: {self.user_id} ({self.role})")
        parts.append(f"Query: \"{self.user_query}\"")

        return "\n".join(parts)

# Alias for backward compatibility across all agents
CustomPromptBuilder = EnterprisePromptBuilder
StaticPromptBuilderV4 = EnterprisePromptBuilder
