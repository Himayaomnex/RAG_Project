"""Comprehensive verification test for all tools and skills in the ToolRegistry."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.tool_registry import registry
import harness.tools


def test_compute_tools():
    # 1. run_python
    code = "result = {'sum': 2 + 3, 'status': 'computed'}"
    items = registry.execute("run_python", {"code": code})
    assert len(items) == 1
    assert "computed" in items[0].content
    print("run_python passed:", items[0].content)

    # 2. write_artifact
    artifact_items = registry.execute("write_artifact", {"path": "test_output.txt", "content": "Hello artifact"})
    assert len(artifact_items) == 1
    assert "test_output.txt" in artifact_items[0].content
    print("write_artifact passed:", artifact_items[0].content)


def test_catch_up_skill():
    # Calling catch_up for an unknown session date
    items = registry.execute("catch_up", {"date": "2025-01-01"})
    assert len(items) >= 1
    assert items[0].origin.get("found_nothing") is True or "No recorded session" in items[0].content
    print("catch_up passed:", items[0].content)


if __name__ == "__main__":
    test_compute_tools()
    test_catch_up_skill()
    print("ALL TOOLS AND SKILLS TESTED SUCCESSFULLY!")
