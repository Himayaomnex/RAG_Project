"""Top-level runner for invoking the Agent Harness with full trace tracking."""

import uuid
from typing import Dict, Any, Optional
from harness.state import AgentState, Status
from harness.budget import Budget
from harness.evidence_store import EvidenceStore
from harness.capabilities.loader import capability_registry
from harness.graph import agent_app


def run_agent(
    task: str,
    capability: Optional[str] = None,
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute the Agent Harness on a given task and capability contract.
    
    Returns the complete terminal state including output draft, status, plan history, and observations.
    """
    cap = capability_registry.get_or_default(capability, task=task)
    sid = session_id or f"sess-{uuid.uuid4().hex[:8]}"
    tid = trace_id or f"trc-{uuid.uuid4().hex[:8]}"

    initial_state: AgentState = {
        "task": task,
        "capability": cap.name if capability else None,
        "session_id": sid,
        "trace_id": tid,
        "plan_history": [],
        "observations": [],
        "tool_calls_used": 0,
        "tool_calls_remaining": cap.max_tool_calls,
        "tool_calls_total": cap.max_tool_calls,
        "evidence": EvidenceStore(),
        "budget": Budget(total=cap.default_budget),
        "assembled_evidence": [],
        "dropped_evidence": [],
        "draft": None,
        "violations": [],
        "repair_attempts": 0,
        "max_repair_attempts": 2,
        "status": "RUNNING"
    }

    final_state = agent_app.invoke(initial_state)

    # Format user-friendly response dictionary
    status = final_state.get("status", Status.SUCCESS.value)
    draft = final_state.get("draft")
    err = final_state.get("error_message")

    return {
        "trace_id": tid,
        "capability": cap.name,
        "status": status,
        "output": draft if status in [Status.SUCCESS.value, Status.DEGRADED.value] else None,
        "error": err,
        "violations": final_state.get("violations", []),
        "plan_history": final_state.get("plan_history", []),
        "observations": final_state.get("observations", []),
        "tool_calls_used": final_state.get("tool_calls_used", 0)
    }
