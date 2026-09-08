"""Test Skill Recipes: assess_person and summarize_period."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.tool_registry import registry
import harness.tools


def test_skills_registered():
    tools = {t["name"]: t for t in registry.list_tools()}
    assert "assess_person" in tools, "assess_person must be registered"
    assert "summarize_period" in tools, "summarize_period must be registered"
    print("Skills registration verified!")


def test_summarize_period_empty_window():
    # Calling summarize_period for an empty period returns found_nothing with reason
    items = registry.execute("summarize_period", {"period_start": "2025-01-01", "period_end": "2025-01-07"})
    assert len(items) == 1
    assert items[0].origin.get("found_nothing") is True
    assert items[0].origin.get("reason") == "no sessions in window"
    print("summarize_period empty window test passed:", items[0].content)


def test_assess_person_empty_handling():
    # Calling assess_person for unknown person handles empty safely
    items = registry.execute("assess_person", {"person": "NonexistentPerson123"})
    assert len(items) >= 1
    print("assess_person empty handling test passed:", items[0].content)


if __name__ == "__main__":
    test_skills_registered()
    test_summarize_period_empty_window()
    test_assess_person_empty_handling()
