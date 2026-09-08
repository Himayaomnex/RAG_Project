"""Verification engine for validating structured outputs against capability rules."""

import re
from typing import List, Dict, Any, Set
from harness.evidence_store import EvidenceItem
from harness.state import Violation
from harness.capabilities.base import Capability


def _get_all_evidence_ids_from_dict(obj: Any, path: str = "") -> List[tuple[str, str]]:
    """Recursively collect (path, evidence_id) tuples from JSON structure."""
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = f"{path}.{k}" if path else k
            if k == "evidence_ids" and isinstance(v, list):
                for eid in v:
                    results.append((current_path, str(eid)))
            else:
                results.extend(_get_all_evidence_ids_from_dict(v, current_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            current_path = f"{path}[{idx}]"
            results.extend(_get_all_evidence_ids_from_dict(item, current_path))
    return results


def check_v1_citations_exist(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V1: Every evidence_ids entry exists in the assembled evidence."""
    violations: List[Violation] = []
    valid_ids: Set[str] = {item.id for item in assembled}

    for path, eid in _get_all_evidence_ids_from_dict(draft):
        if eid not in valid_ids:
            violations.append({
                "field": path,
                "rule": "V1: Every evidence_ids entry exists in assembled evidence",
                "found": eid,
                "why": f"Invented citation: evidence id '{eid}' was not present in assembled evidence."
            })
    return violations


def check_coverage_note_if_dropped(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """Checks that coverage_note is non-null if evidence was dropped or a tool failed."""
    violations: List[Violation] = []
    dropped_count = len(context.get("dropped_evidence", []))
    tools_failed = context.get("tools_failed", False)

    if (dropped_count > 0 or tools_failed) and not draft.get("coverage_note"):
        violations.append({
            "field": "coverage_note",
            "rule": "If evidence was dropped or a tool failed, coverage_note is non-null",
            "found": draft.get("coverage_note"),
            "why": f"Silent incompleteness: {dropped_count} evidence items dropped / tool failed, but coverage_note was null."
        })
    return violations


# ── Specific Capability Rule Implementations ─────────────────────────────────

# ad_hoc rules
def check_adhoc_v2(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V2: Every factual assertion in answer appears as an entry in claims."""
    violations = []
    answer = draft.get("answer", "")
    claims = draft.get("claims", [])
    if answer and not claims and "evidence does not answer" not in answer.lower():
        violations.append({
            "field": "claims",
            "rule": "V2: Every factual assertion in answer appears as an entry in claims",
            "found": claims,
            "why": "Unevidenced prose: 'answer' provided factual content but 'claims' list is empty."
        })
    return violations


# manager_rollup rules
def check_manager_v2(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V2: Every completed item cites evidence stating completion."""
    violations = []
    evidence_by_id = {item.id: item.content.lower() for item in assembled}
    completed_items = draft.get("completed", [])

    for idx, c in enumerate(completed_items):
        eids = c.get("evidence_ids", [])
        if not eids:
            violations.append({
                "field": f"completed[{idx}].evidence_ids",
                "rule": "V2: Every completed item cites evidence stating completion",
                "found": eids,
                "why": "Inferred completion: completed item carries no evidence citation."
            })
            continue

        has_completion_proof = False
        for eid in eids:
            content = evidence_by_id.get(eid, "")
            if any(term in content for term in ["delivered", "completed", "finish", "done", "merged", "closed"]):
                has_completion_proof = True
                break

        if not has_completion_proof:
            violations.append({
                "field": f"completed[{idx}]",
                "rule": "V2: Every completed item cites evidence stating completion",
                "found": c.get("item"),
                "why": "Inferred completion: cited evidence does not explicitly confirm completion."
            })
    return violations


def check_manager_v3(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V3: Every blocked item has agreed_resolution set, using 'none_agreed' where none was reached."""
    violations = []
    blocked = draft.get("blocked", [])
    for idx, b in enumerate(blocked):
        res = b.get("agreed_resolution")
        if not res or str(res).strip() == "":
            violations.append({
                "field": f"blocked[{idx}].agreed_resolution",
                "rule": "V3: Every blocked item has agreed_resolution set",
                "found": res,
                "why": "Invented mitigation: agreed_resolution must be non-empty or 'none_agreed'."
            })
    return violations


def check_manager_v4(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V4: Every item's owner is a person returned by list_people."""
    violations = []
    known_people = set(context.get("known_people", []))
    if not known_people:
        # Defaults
        known_people = {"Siddharth", "Ganesh Krishna", "Dakshinya", "Himaya", "Iyappan", "Preethi", "Kavya", "Vignesh", "everyone"}

    for section in ["completed", "in_progress", "blocked"]:
        items = draft.get(section, [])
        for idx, it in enumerate(items):
            owner = it.get("owner")
            if owner and not any(kp.lower() in owner.lower() for kp in known_people):
                violations.append({
                    "field": f"{section}[{idx}].owner",
                    "rule": "V4: Every item's owner is a person returned by list_people",
                    "found": owner,
                    "why": f"Invented owner: '{owner}' is not a known training participant."
                })
    return violations


# mentor_assessment rules
def check_mentor_v2_v3(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V2: score in 1-10 or 'not_observed'. V3: numeric score has >= 1 evidence id."""
    violations = []
    dimensions = draft.get("dimensions", [])
    for idx, d in enumerate(dimensions):
        score = d.get("score")
        eids = d.get("evidence_ids", [])
        if score != "not_observed":
            try:
                val = int(score)
                if val < 1 or val > 10:
                    violations.append({
                        "field": f"dimensions[{idx}].score",
                        "rule": "V2: Every dimension has a score in 1-10 or not_observed",
                        "found": score,
                        "why": "Score out of range 1-10."
                    })
                if not eids:
                    violations.append({
                        "field": f"dimensions[{idx}].evidence_ids",
                        "rule": "V3: Every dimension with a numeric score has >= 1 evidence id",
                        "found": eids,
                        "why": "Scored without evidence."
                    })
            except (ValueError, TypeError):
                violations.append({
                    "field": f"dimensions[{idx}].score",
                    "rule": "V2: Every dimension has a score in 1-10 or not_observed",
                    "found": score,
                    "why": "Invalid score type; must be integer 1-10 or 'not_observed'."
                })
    return violations


def check_mentor_v4(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V4: Taught != understood — every demonstrated_capabilities item cites evidence where person speaks/acts."""
    violations = []
    target_person = draft.get("person", "")
    evidence_by_id = {item.id: item for item in assembled}

    for idx, d in enumerate(draft.get("demonstrated_capabilities", [])):
        eids = d.get("evidence_ids", [])
        if not eids:
            violations.append({
                "field": f"demonstrated_capabilities[{idx}].evidence_ids",
                "rule": "V4: Taught != understood demonstration citation",
                "found": eids,
                "why": "Demonstration claimed without any cited evidence."
            })
            continue

        valid_action = False
        for eid in eids:
            ev = evidence_by_id.get(eid)
            if not ev:
                continue
            origin_speaker = ev.origin.get("speaker") or ""
            origin_person = ev.origin.get("person") or ""
            # If origin directly indicates the person spoke/answered/did
            if target_person.lower() in origin_speaker.lower() or target_person.lower() in origin_person.lower():
                valid_action = True
                break
            # Check content for direct speech or action
            if f"{target_person}:" in ev.content or "demonstrated" in ev.content.lower():
                valid_action = True
                break

        if not valid_action:
            violations.append({
                "field": f"demonstrated_capabilities[{idx}]",
                "rule": "V4: Taught != understood demonstration citation",
                "found": d.get("concept"),
                "why": f"Inferred demonstration: cited evidence does not show {target_person} speaking or acting."
            })
    return violations


def check_mentor_v5(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V5: Every recurring_misconceptions item cites >= 2 evidence items from different sessions."""
    violations = []
    evidence_by_id = {item.id: item for item in assembled}

    for idx, m in enumerate(draft.get("recurring_misconceptions", [])):
        eids = m.get("evidence_ids", [])
        if len(eids) < 2:
            violations.append({
                "field": f"recurring_misconceptions[{idx}].evidence_ids",
                "rule": "V5: Every recurring_misconceptions item cites >= 2 evidence items from different sessions",
                "found": eids,
                "why": f"'recurring' claimed with only {len(eids)} evidence items."
            })
            continue

        dates = set()
        for eid in eids:
            ev = evidence_by_id.get(eid)
            if ev and ev.origin.get("date"):
                dates.add(ev.origin["date"])

        if len(dates) < 2:
            violations.append({
                "field": f"recurring_misconceptions[{idx}].evidence_ids",
                "rule": "V5: Every recurring_misconceptions item cites >= 2 evidence items from different sessions",
                "found": list(dates),
                "why": "Recurring misconception cited from only 1 session date."
            })
    return violations


def check_mentor_v6(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V6: If change_from_previous is not not_observed, it cites evidence from >= 2 distinct dates."""
    violations = []
    cfp = draft.get("change_from_previous", "not_observed")
    if cfp and cfp != "not_observed":
        dates = set()
        for item in assembled:
            d = item.origin.get("date")
            if d:
                dates.add(d)
        if len(dates) < 2:
            violations.append({
                "field": "change_from_previous",
                "rule": "V6: Trajectory requires evidence from >= 2 distinct dates",
                "found": cfp,
                "why": "Trajectory without a baseline: evidence contains fewer than 2 distinct dates."
            })
    return violations


# team_catchup rules
def check_team_v2(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V2: Every cited evidence item's date matches session_date."""
    violations = []
    session_date = draft.get("session_date", "")
    evidence_by_id = {item.id: item for item in assembled}

    for path, eid in _get_all_evidence_ids_from_dict(draft):
        ev = evidence_by_id.get(eid)
        if ev:
            ev_date = ev.origin.get("date")
            if ev_date and session_date and ev_date != session_date:
                violations.append({
                    "field": path,
                    "rule": "V2: Every cited evidence item's date matches session_date",
                    "found": f"session_date={session_date}, evidence_date={ev_date}",
                    "why": f"Evidence from the wrong session ({ev_date} != {session_date})."
                })
    return violations


def check_team_v3(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V3: When person is set, every assignments_for_you cites evidence naming that person as owner."""
    violations = []
    person = context.get("person")
    if not person:
        return violations

    evidence_by_id = {item.id: item for item in assembled}
    for idx, a in enumerate(draft.get("assignments_for_you", [])):
        eids = a.get("evidence_ids", [])
        owner_matched = False
        for eid in eids:
            ev = evidence_by_id.get(eid)
            if ev:
                origin_person = ev.origin.get("person") or ""
                origin_spk = ev.origin.get("speaker") or ""
                if person.lower() in origin_person.lower() or person.lower() in origin_spk.lower() or person.lower() in ev.content.lower():
                    owner_matched = True
                    break
        if not owner_matched:
            violations.append({
                "field": f"assignments_for_you[{idx}]",
                "rule": "V3: Every assignments_for_you item cites evidence naming that person as owner",
                "found": a.get("task"),
                "why": f"Someone else's work handed to {person}."
            })
    return violations


def check_team_v4(draft: Dict[str, Any], assembled: List[EvidenceItem], context: Dict[str, Any]) -> List[Violation]:
    """V4: what_to_do_next is non-empty only if assignments_for_you is non-empty, or explicitly states nothing assigned."""
    violations = []
    what_next = draft.get("what_to_do_next", "")
    assignments = draft.get("assignments_for_you", [])
    if not assignments and what_next:
        lower = what_next.lower()
        if not any(phrase in lower for phrase in ["nothing assigned", "no assignments", "no pending", "none"]):
            violations.append({
                "field": "what_to_do_next",
                "rule": "V4: what_to_do_next requires assignments or explicit statement of nothing assigned",
                "found": what_next,
                "why": "Invented homework: tasks listed in what_to_do_next when nothing was assigned."
            })
    return violations


class RuleEngine:
    @staticmethod
    def verify(
        capability: Capability,
        draft: Dict[str, Any],
        assembled_evidence: List[EvidenceItem],
        context: Dict[str, Any]
    ) -> List[Violation]:
        """Runs schema validation and all registered verification rules for capability."""
        violations: List[Violation] = []

        # 1. Pydantic schema validation
        try:
            capability.output_schema.model_validate(draft)
        except Exception as e:
            violations.append({
                "field": "schema_root",
                "rule": "Schema conformity",
                "found": str(e),
                "why": f"Failed Pydantic schema validation: {e}"
            })

        # 2. Run all verification rules
        for rule in capability.verification_rules:
            try:
                rule_violations = rule.check_fn(draft, assembled_evidence, context)
                violations.extend(rule_violations)
            except Exception as ex:
                violations.append({
                    "field": rule.id,
                    "rule": rule.description,
                    "found": "exception",
                    "why": f"Rule checker raised exception: {ex}"
                })

        return violations
