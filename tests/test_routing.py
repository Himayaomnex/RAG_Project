"""
Test: Does the capability intent classifier route queries correctly?
Run: python tests/test_routing.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.capabilities.loader import capability_registry

# -- Test Cases -----------------------------------------------------------------
# Format: (query, expected_capability)
ROUTING_TESTS = [
    # --- manager_rollup ---
    ("What are the key architectural decisions and blockers recorded across the team this week?", "manager_rollup"),
    ("Give me a weekly rollup of trainee deliverables and blockers", "manager_rollup"),
    ("Which trainees are currently blocked and what interventions are recommended?", "manager_rollup"),
    ("Executive summary of deliverables status", "manager_rollup"),

    # --- mentor_assessment ---
    ("Assess Himaya's conceptual understanding of LangGraph and vector retrieval. Score 1-10 with evidence.", "mentor_assessment"),
    ("Evaluate Ganesh's knowledge gaps in Qdrant and embeddings", "mentor_assessment"),
    ("What misconceptions does the trainee have about RAG? Score them.", "mentor_assessment"),
    ("Give me a teaching action plan based on concept gaps", "mentor_assessment"),

    # --- team_catchup ---
    ("I missed yesterday's session. What decisions were made and what are my assignments?", "team_catchup"),
    ("Catch me up on what happened in the last meeting", "team_catchup"),
    ("What are the assignments for me from today's session digest?", "team_catchup"),
    ("Session digest for the team meeting", "team_catchup"),

    # --- ad_hoc ---
    ("What is Ganesh's current assignment status and pending deliverables?", "ad_hoc"),
    ("How does the retrieval pipeline work in this system?", "ad_hoc"),
    ("What did Himaya say about LangGraph in the last session?", "ad_hoc"),
]


def test_routing():
    passed = 0
    failed = 0

    print("\n" + "=" * 70)
    print(f"ROUTING TEST RESULTS")
    print("=" * 70)

    for query, expected in ROUTING_TESTS:
        inferred = capability_registry.infer_capability(query)
        ok = inferred == expected
        status = "PASS" if ok else "FAIL"
        label = query[:55] + "..." if len(query) > 55 else query

        print(f"[{status}]  expected={expected:<20} got={inferred:<20}")
        print(f"       {label}")
        print()

        if ok:
            passed += 1
        else:
            failed += 1

    print("=" * 70)
    print(f"Results: {passed}/{passed + failed} passed, {failed} failed")
    print("=" * 70)

    if failed > 0:
        print(f"\nFAILED: {failed} routing test(s) -- check keywords in harness/capabilities/loader.py")
        sys.exit(1)
    else:
        print("All routing tests passed!")


if __name__ == "__main__":
    test_routing()
