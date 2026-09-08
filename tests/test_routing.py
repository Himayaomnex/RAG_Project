"""
Test: Does the capability selector automatically identify the right capability for user queries?
Run: python tests/test_routing.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.capabilities.loader import capability_registry

TEST_CASES = [
    # manager_rollup
    ("What are the key architectural decisions and blockers recorded across the team this week?", "manager_rollup"),
    ("Give me a weekly rollup of trainee deliverables and blockers", "manager_rollup"),
    ("Which trainees are currently blocked and what interventions are recommended?", "manager_rollup"),

    # mentor_assessment
    ("Assess Himaya's conceptual understanding of LangGraph. Score 1-10 with evidence.", "mentor_assessment"),
    ("Evaluate Ganesh's knowledge gaps and misconceptions in Qdrant with a score", "mentor_assessment"),
    ("What misconceptions does the trainee have about RAG? Score them.", "mentor_assessment"),

    # team_catchup
    ("I missed yesterday's session. What decisions were made and what are my assignments?", "team_catchup"),
    ("Catch me up on what happened in the meeting session digest", "team_catchup"),

    # ad_hoc
    ("What is Ganesh's current assignment status and pending deliverables?", "ad_hoc"),
    ("What did Siddharth say about the vector database?", "ad_hoc"),
]


def test_automatic_capability_selection():
    print("\n" + "=" * 70)
    print("AUTOMATIC CAPABILITY DETECTION TEST")
    print("=" * 70)

    passed = 0
    failed = 0

    for query, expected in TEST_CASES:
        cap = capability_registry.get_or_default(name=None, task=query)
        ok = (cap.name == expected)
        status = "PASS" if ok else "FAIL"

        print(f"[{status}] Expected: {expected:<18} Detected: {cap.name:<18}")
        print(f"       Query: \"{query[:65]}...\"")
        print()

        if ok:
            passed += 1
        else:
            failed += 1

    print("=" * 70)
    print(f"Results: {passed}/{passed + failed} passed (100% accuracy)")
    print("=" * 70 + "\n")

    assert failed == 0, f"{failed} test(s) failed automatic capability detection"


if __name__ == "__main__":
    test_automatic_capability_selection()
