"""Test Step 4: KB outage raises KBUnavailableError and triggers KB_UNAVAILABLE terminal status."""

import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.shared.kb_client import KBUnavailableError
from harness.tool_registry import registry, ToolError
from harness.state import AgentState, Status
from harness.graph import execute_tool_node, route_after_tool
from harness.budget import Budget
from harness.evidence_store import EvidenceStore


def test_kb_outage_raises_tool_error():
    # Simulate broken KB connection in kb_client._query
    with patch("agents.shared.kb_client.kb_client._query", side_effect=KBUnavailableError("Connection refused to Supabase")):
        try:
            registry.execute("get_person_state", {"person": "Ganesh"})
            assert False, "Should have raised ToolError on KB failure"
        except ToolError as te:
            assert "KB_UNAVAILABLE" in str(te)
            print("Successfully caught ToolError with KB_UNAVAILABLE:", te)

    print("Step 4 Tool Error Raising Passed Successfully!")


def test_kb_outage_graph_routing():
    # Verify execute_tool_node transitions state to KB_UNAVAILABLE
    with patch("agents.shared.kb_client.kb_client._query", side_effect=KBUnavailableError("Connection refused to Supabase")):
        state: AgentState = {
            "task": "What is Ganesh's state?",
            "capability": "ad_hoc",
            "budget": Budget(),
            "evidence": EvidenceStore(),
            "plan_history": [{"thought": "Check state", "action": "tool_call", "tool": "get_person_state", "args": {"person": "Ganesh"}}],
            "observations": [],
            "tool_calls_remaining": 5
        }

        updates = execute_tool_node(state)
        state.update(updates)

        assert state.get("status") == Status.KB_UNAVAILABLE.value, f"Expected KB_UNAVAILABLE, got {state.get('status')}"
        next_route = route_after_tool(state)
        assert next_route == "fail", f"Expected route to fail, got {next_route}"

    print("Step 4 Graph Routing to KB_UNAVAILABLE Passed Successfully!")


if __name__ == "__main__":
    test_kb_outage_raises_tool_error()
    test_kb_outage_graph_routing()
