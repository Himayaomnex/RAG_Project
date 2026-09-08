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

            # Extract Consumer and Purpose
            consumer = "General"
            purpose = f"Execute {cap_name} capability."
            m_cons = re.search(r"## Consumer\s*\n+([^\n#]+)", content)
            if m_cons:
                consumer = m_cons.group(1).strip()
            m_purp = re.search(r"## Purpose\s*\n+([^\n#]+)", content)
            if m_purp:
                purpose = m_purp.group(1).strip()

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
                max_tool_calls=max_calls
            )

    def infer_capability(self, task: str) -> str:
        """Automatically infer the best matching capability contract from task semantics."""
        if not task:
            return "ad_hoc"
        
        t = task.lower()
        
        # Mentor assessment cues
        if any(k in t for k in ["assess", "evaluation", "evaluate", "trainee", "mentor", "conceptual understanding", "knowledge gap", "score", "misconception", "teaching action"]):
            return "mentor_assessment"
            
        # Manager rollup cues
        if any(k in t for k in ["rollup", "roll up", "roll-up", "weekly", "executive", "management", "blocker", "blockers", "deliverable", "deliverables", "intervention"]):
            return "manager_rollup"
            
        # Team catchup cues
        if any(k in t for k in ["catchup", "catch up", "catch-up", "missed", "session digest", "assigned to me", "mine to do", "assignments for you"]):
            return "team_catchup"
            
        return "ad_hoc"

    def get(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)

    def get_or_default(self, name: Optional[str], task: Optional[str] = None) -> Capability:
        if name and name in self._capabilities:
            return self._capabilities[name]
        
        # Auto-detect from task if not explicitly pinned
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

