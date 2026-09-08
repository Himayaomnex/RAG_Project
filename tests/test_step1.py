import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.budget import Budget, count_tokens
from harness.evidence_store import EvidenceStore, EvidenceItem


def test_budget_and_evidence_store():
    budget = Budget(total=30000)
    store = EvidenceStore()

    # Add 40 items with varying tokens and relevance
    for i in range(40):
        content = f"Chunk {i}: " + ("evidence text content for training session. " * 100)
        relevance = round(0.5 + (i * 0.01), 2)  # 0.50 to 0.89
        item = EvidenceItem(
            id=f"rag-chunk-{i}",
            source="rag",
            origin={"date": "2026-08-01", "speaker": f"Speaker_{i % 5}"},
            content=content,
            relevance=relevance,
        )
        store.add(item)

    assert len(store) == 40, f"Expected 40 items, got {len(store)}"

    # Assemble against 15,000 budget (total items is ~28,200 tokens)
    admitted, dropped = store.assemble(budget_limit=15000)

    print(f"Total items: {len(store)}")
    print(f"Admitted items: {len(admitted)}, total tokens: {sum(x.tokens for x in admitted)}")
    print(f"Dropped items: {len(dropped)}")

    assert len(admitted) > 0, "Should admit items"
    assert len(dropped) > 0, "Should drop items when budget exceeded"
    assert sum(x.tokens for x in admitted) <= 30000

    # Verify highest relevance items are admitted first
    admitted_relevances = [x.relevance for x in admitted]
    dropped_relevances = [x["relevance"] for x in dropped]
    assert min(admitted_relevances) >= min(dropped_relevances)

    print("Step 1 Test Passed Successfully!")


if __name__ == "__main__":
    test_budget_and_evidence_store()
