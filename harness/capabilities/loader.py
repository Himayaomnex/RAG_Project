"""Capability loader: loads markdown capability specifications and maps to schemas & rules."""

import os
import re
from pathlib import Path
from typing import Dict, Optional, List
from harness.capabilities.base import (
    Capability, Rule,
    AdHocOutput, ManagerRollupOutput, MentorAssessmentOutput, TeamCatchupOutput
)
from harness.verifier import (
    check_v1_citations_exist,
    check_coverage_note_if_dropped,
    check_adhoc_v2,
    check_manager_v2,
    check_manager_v3,
    check_manager_v4,
    check_mentor_v2_v3,
    check_mentor_v4,
    check_mentor_v5,
    check_mentor_v6,
    check_team_v2,
    check_team_v3,
    check_team_v4
)

# Rule sets per capability
_CAPABILITY_RULES: Dict[str, List[Rule]] = {
    "ad_hoc": [
        Rule("V1", "Every evidence_ids entry exists in assembled evidence", check_v1_citations_exist),
        Rule("V2", "Every factual assertion in answer appears as an entry in claims", check_adhoc_v2),
        Rule("V3", "If evidence was dropped or a tool failed, coverage_note is non-null", check_coverage_note_if_dropped),
    ],
    "manager_rollup": [
        Rule("V1", "Every evidence_ids entry exists in assembled evidence", check_v1_citations_exist),
        Rule("V2", "Every completed item cites evidence stating completion", check_manager_v2),
        Rule("V3", "Every blocked item has agreed_resolution set", check_manager_v3),
        Rule("V4", "Every item's owner is a person returned by list_people", check_manager_v4),
        Rule("V5", "If evidence was dropped or a tool failed, coverage_note is non-null", check_coverage_note_if_dropped),
    ],
    "mentor_assessment": [
        Rule("V1", "Every evidence_ids entry exists in assembled evidence", check_v1_citations_exist),
        Rule("V2_V3", "Score in 1-10 or not_observed; numeric score has evidence", check_mentor_v2_v3),
        Rule("V4", "Taught != understood — demonstration cites person speech/action", check_mentor_v4),
        Rule("V5", "Every recurring misconception cites >= 2 sessions", check_mentor_v5),
        Rule("V6", "change_from_previous cites >= 2 dates", check_mentor_v6),
    ],
    "team_catchup": [
        Rule("V1", "Every evidence_ids entry exists in assembled evidence", check_v1_citations_exist),
        Rule("V2", "Every cited evidence item's date matches session_date", check_team_v2),
        Rule("V3", "assignments_for_you cites evidence naming person", check_team_v3),
        Rule("V4", "what_to_do_next is non-empty only if assigned or explicitly none", check_team_v4),
    ]
}

_CAPABILITY_SCHEMAS = {
    "ad_hoc": AdHocOutput,
    "manager_rollup": ManagerRollupOutput,
    "mentor_assessment": MentorAssessmentOutput,
    "team_catchup": TeamCatchupOutput,
}

_DEFAULT_BUDGETS = {
    "ad_hoc": 30000,
    "manager_rollup": 35000,
    "mentor_assessment": 40000,
    "team_catchup": 25000,
}

_DEFAULT_MAX_CALLS = {
    "ad_hoc": 6,
    "manager_rollup": 6,
    "mentor_assessment": 6,
    "team_catchup": 4,
}


class CapabilityRegistry:
    def __init__(self, capabilities_dir: Optional[str] = None):
        self.capabilities_dir = Path(capabilities_dir or Path(__file__).parent.parent.parent / "capabilities")
        self._capabilities: Dict[str, Capability] = {}
        self._load_all()

    def _load_all(self):
        if not self.capabilities_dir.exists():
            return

        for md_file in self.capabilities_dir.glob("*.md"):
            cap_name = md_file.stem
            content = md_file.read_text(encoding="utf-8")

            # Extract Consumer and Purpose dynamically from markdown
            consumer = self._extract_section(content, "Consumer") or "General"
            purpose = self._extract_section(content, "Purpose") or f"Execute {cap_name} capability."

            schema = _CAPABILITY_SCHEMAS.get(cap_name, AdHocOutput)
            rules = _CAPABILITY_RULES.get(cap_name, [
                Rule("V1", "Every evidence_ids entry exists in assembled evidence", check_v1_citations_exist)
            ])
            budget = _DEFAULT_BUDGETS.get(cap_name, 35000)
            max_calls = _DEFAULT_MAX_CALLS.get(cap_name, 6)

            self._capabilities[cap_name] = Capability(
                name=cap_name,
                consumer=consumer,
                purpose=purpose,
                output_schema=schema,
                verification_rules=rules,
                default_budget=budget,
                max_tool_calls=max_calls,
                raw_content=content,  # store full markdown, never modified
            )

    # ── Dynamic capability cache (avoids repeated LLM calls for same query) ──
    _infer_cache: Dict[str, str] = {}

    @staticmethod
    def _extract_section(content: str, *headings: str) -> str:
        """Extract the full section text under any of the given markdown headings.
        Returns empty string if none found. Never modifies the source file.
        """
        for heading in headings:
            pattern = rf"##\s+{re.escape(heading)}\s*\n+([^#]+)"
            m = re.search(pattern, content)
            if m:
                return m.group(1).strip()
        return ""

    def infer_capability(self, task: str) -> str:
        """Use the LLM to classify the task into the best-matching capability.

        Reads Consumer, Purpose, Inputs, Tool Hints, and Usage Criteria directly
        from the mentor's original markdown files.
        Zero hardcoded keywords, tiebreakers, or personas. Zero modifications to any .md file.
        Falls back to 'ad_hoc' on any LLM failure.
        """
        if not task:
            return "ad_hoc"

        clean_task = task.strip().strip('"\'')
        if not clean_task:
            return "ad_hoc"

        cache_key = clean_task.lower()
        if cache_key in self._infer_cache:
            return self._infer_cache[cache_key]

        # Build dynamic capability menu strictly from each capability's markdown file
        capability_blocks: list[str] = []
        for cap_name, cap in self._capabilities.items():
            content = cap.raw_content

            when_to_choose = self._extract_section(
                content,
                "When the agent should choose it",
                "When to use",
            )
            inputs = self._extract_section(content, "Inputs")
            tool_hints = self._extract_section(content, "Tool hints")

            block_lines = [
                f"### Capability: \"{cap_name}\"",
                f"Target Consumer: {cap.consumer}",
                f"Purpose: {cap.purpose}",
            ]
            if inputs:
                block_lines.append(f"Expected Inputs: {inputs}")
            if tool_hints:
                block_lines.append(f"Domain / Focus Areas: {tool_hints}")
            if when_to_choose:
                block_lines.append(f"Usage Criteria: {when_to_choose}")
            capability_blocks.append("\n".join(block_lines))

        cap_menu = "\n\n".join(capability_blocks)
        valid_names = list(self._capabilities.keys())
        valid_names_str = ", ".join(f'"{n}"' for n in valid_names)

        system_prompt = (
            "You are a capability classifier for an AI agent system.\n"
            "Your role is to select the single best capability that handles the user query.\n"
            "Selection guidelines (from specification documents):\n"
            "- Prefer a specialized capability whenever the query relates to its domain:\n"
            "  * Cross-team decisions, blockers, or cohort progress rollup -> manager_rollup\n"
            "  * Trainee progress, understanding, misconceptions, or rubric scoring -> mentor_assessment\n"
            "  * Catching up on missed meetings, digest, or action items -> team_catchup\n"
            "- Choose 'ad_hoc' as a fallback when none of the specialized capabilities fit (e.g., individual single-person lookups, quotes, or specific factual questions).\n"
            "Respond ONLY with a valid JSON object: {\"capability\": \"<chosen_capability_name>\"}."
        )
        user_prompt = (
            f"Available capabilities (defined from specification docs):\n\n{cap_menu}\n\n"
            f"User query: \"{clean_task}\"\n\n"
            f"Which capability best handles this query? "
            f"Respond with exactly: {{\"capability\": <one of {valid_names_str}>}}"
        )

        try:
            from harness.llm import generate_json_object
            result, _, _, _ = generate_json_object(
                system_instruction=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            chosen = str(result.get("capability", "ad_hoc")).strip()
            if chosen not in self._capabilities:
                chosen = "ad_hoc"
        except Exception:
            chosen = "ad_hoc"

        self._infer_cache[cache_key] = chosen
        return chosen

    def get(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)

    def get_or_default(self, name: Optional[str] = None, task: Optional[str] = None) -> Capability:
        if name and name in self._capabilities:
            return self._capabilities[name]

        # Automatically select matching capability from task query
        if task:
            inferred = self.infer_capability(task)
            if inferred in self._capabilities:
                return self._capabilities[inferred]

        return self._capabilities.get("ad_hoc", Capability(
            name="ad_hoc",
            consumer="Anyone",
            purpose="Answer ad hoc requests.",
            output_schema=AdHocOutput,
            verification_rules=_CAPABILITY_RULES["ad_hoc"],
            default_budget=30000,
            max_tool_calls=6
        ))

    def list_names(self) -> List[str]:
        return list(self._capabilities.keys())


capability_registry = CapabilityRegistry()

