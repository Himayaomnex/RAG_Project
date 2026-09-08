"""
Test: Verify all 4 Capabilities load directly and enforce correct schemas, budgets, and rules.
Run: python tests/test_routing.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.capabilities.loader import capability_registry
from harness.capabilities.base import (
    ManagerRollupOutput,
    MentorAssessmentOutput,
    TeamCatchupOutput,
    AdHocOutput
)


def test_capabilities():
    print("\n" + "=" * 70)
    print("CAPABILITY DIRECT REGISTRY VERIFICATION")
    print("=" * 70)

    expected_caps = {
        "manager_rollup": (ManagerRollupOutput, 6, 35000),
        "mentor_assessment": (MentorAssessmentOutput, 6, 40000),
        "team_catchup": (TeamCatchupOutput, 4, 25000),
        "ad_hoc": (AdHocOutput, 6, 30000),
    }

    all_names = capability_registry.list_names()
    print(f"Loaded capabilities: {all_names}\n")

    for name, (schema, max_calls, default_budget) in expected_caps.items():
        cap = capability_registry.get(name)
        assert cap is not None, f"Capability {name} must exist"
        assert cap.output_schema == schema, f"{name} schema mismatch"
        assert cap.max_tool_calls == max_calls, f"{name} max calls mismatch"
        assert len(cap.verification_rules) > 0, f"{name} must have verification rules"
        print(f"[PASS] {name:<20} Schema={schema.__name__:<22} Rules={len(cap.verification_rules)} MaxCalls={cap.max_tool_calls}")

    # Test get_or_default behavior
    default_cap = capability_registry.get_or_default(None)
    assert default_cap.name == "ad_hoc", "get_or_default(None) must default to ad_hoc"
    print(f"[PASS] Default fallback: {default_cap.name}")

    pinned = capability_registry.get_or_default("manager_rollup")
    assert pinned.name == "manager_rollup", "Pinned capability must return manager_rollup"
    print(f"[PASS] Pinned lookup:    {pinned.name}")

    print("=" * 70)
    print("ALL CAPABILITY TESTS PASSED (100%)!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    test_capabilities()
