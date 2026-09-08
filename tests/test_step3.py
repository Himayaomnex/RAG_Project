"""Test Step 3: Verifier and Repair/Degrade cycle catching fabricated citations."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.capabilities.loader import capability_registry
from harness.evidence_store import EvidenceItem
from harness.verifier import RuleEngine


def test_fabricated_citation_caught():
    cap = capability_registry.get("ad_hoc")
    assert cap is not None, "ad_hoc capability must exist"

    assembled_evidence = [
        EvidenceItem(
            id="rag-chunk-valid1",
            source="rag",
            origin={"date": "2026-08-01"},
            content="Ganesh implemented the database schema in Supabase."
        )
    ]

    # Fabricated draft with invented citation
    draft = {
        "question": "Who created the DB?",
        "answer": "Ganesh created the DB.",
        "claims": [
            {"claim": "Ganesh created the DB", "evidence_ids": ["invented-chunk-999"]}
        ],
        "uncertainty": None,
        "coverage_note": None
    }

    violations = RuleEngine.verify(cap, draft, assembled_evidence, context={})
    print("Caught violations:", violations)

    assert len(violations) > 0, "Must catch invented citation"
    assert any("invented" in v["why"].lower() for v in violations), "Violation must mention invented citation"
    print("Step 3 Fabrication Detection Test Passed Successfully!")


def test_valid_citation_passes():
    cap = capability_registry.get("ad_hoc")

    assembled_evidence = [
        EvidenceItem(
            id="rag-chunk-valid1",
            source="rag",
            origin={"date": "2026-08-01"},
            content="Ganesh implemented the database schema in Supabase."
        )
    ]

    # Valid draft
    draft = {
        "question": "Who created the DB?",
        "answer": "Ganesh created the DB.",
        "claims": [
            {"claim": "Ganesh created the DB", "evidence_ids": ["rag-chunk-valid1"]}
        ],
        "uncertainty": None,
        "coverage_note": None
    }

    violations = RuleEngine.verify(cap, draft, assembled_evidence, context={})
    assert len(violations) == 0, f"Valid draft should have 0 violations, got {violations}"
    print("Step 3 Valid Citation Test Passed Successfully!")


if __name__ == "__main__":
    test_fabricated_citation_caught()
    test_valid_citation_passes()
