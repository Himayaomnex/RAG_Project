"""Main LangGraph Harness implementing the dual-cycle agent loops."""

import json
import time
import uuid
from typing import Dict, Any, List, Literal, Optional
from langgraph.graph import StateGraph, END

from harness.state import AgentState, Status, Violation
from harness.budget import Budget
from harness.evidence_store import EvidenceStore, EvidenceItem
from harness.tool_registry import registry, ToolError
import harness.tools  # Ensure tools are registered
from harness.capabilities.loader import capability_registry
from harness.capabilities.base import Capability
from harness.verifier import RuleEngine
from harness.prompts import (
    get_harness_prompt,
    get_plan_prompt,
    get_compose_prompt,
    get_repair_prompt
)
from harness.llm import generate_json_object, clean_json_response, generate_with_retry


# ── Node Implementations ─────────────────────────────────────────────────────

def plan_node(state: AgentState) -> Dict[str, Any]:
    """Model decides next action: tool_call or ready_to_compose."""
    task = state.get("task", "")
    cap_name = state.get("capability") or "ad_hoc"
    cap = capability_registry.get_or_default(cap_name)

    budget: Budget = state["budget"]
    tool_calls_remaining = state.get("tool_calls_remaining", cap.max_tool_calls)
    tool_calls_total = state.get("tool_calls_total", cap.max_tool_calls)

    # Check hard guards before model call
    if tool_calls_remaining <= 0:
        return {
            "plan_history": state.get("plan_history", []) + [{
                "thought": "Exhausted all tool calls; advancing to assembly.",
                "action": "ready_to_compose"
            }]
        }

    if budget.remaining < 1500:
        return {
            "plan_history": state.get("plan_history", []) + [{
                "thought": "Budget remaining is too low for further queries; advancing to assembly.",
                "action": "ready_to_compose"
            }]
        }

    # Format plan prompt slots
    observations = state.get("observations", [])
    obs_summary = "\n".join([
        f"Turn {o.get('turn')}: {o.get('tool')}({o.get('args')}) -> {o.get('result_count')} items, {o.get('tokens_added')} tokens"
        for o in observations
    ]) or "None yet."

    evidence: EvidenceStore = state["evidence"]
    evidence_summary = evidence.render_summary()
    tool_registry_str = registry.render_descriptions()

    slots = {
        "task": task,
        "capability_name": cap.name,
        "capability_purpose": cap.purpose,
        "tool_registry": tool_registry_str,
        "observations": obs_summary,
        "evidence_summary": evidence_summary,
        "budget_remaining": budget.remaining,
        "budget_total": budget.total,
        "calls_remaining": tool_calls_remaining,
        "calls_total": tool_calls_total
    }

    system_prompt = get_harness_prompt()
    user_prompt = get_plan_prompt(slots)

    try:
        decision, model, pt, ct = generate_json_object(
            system_instruction=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            trace_id=state.get("trace_id")
        )
    except Exception as e:
        # Fallback if planning output couldn't parse: if we have evidence, compose; else abort
        if len(evidence) > 0:
            decision = {"thought": "Proceeding to compose after planner failure", "action": "ready_to_compose"}
        else:
            return {
                "status": Status.INSUFFICIENT_EVIDENCE.value,
                "error_message": f"Planning node failed: {e}"
            }

    thought_record = {
        "thought": decision.get("thought", ""),
        "action": decision.get("action", "ready_to_compose"),
        "tool": decision.get("tool"),
        "args": decision.get("args", {}),
        "status": decision.get("status")
    }

    return {
        "plan_history": state.get("plan_history", []) + [thought_record]
    }


def route_after_plan(state: AgentState) -> Literal["execute_tool", "assemble", "fail"]:
    if state.get("status") in [s.value for s in Status if s != Status.SUCCESS and s != Status.DEGRADED]:
        return "fail"

    history = state.get("plan_history", [])
    if not history:
        return "assemble"

    last_decision = history[-1]
    action = last_decision.get("action")

    if action == "tool_call" and last_decision.get("tool"):
        # Guard: tool calls remaining
        if state.get("tool_calls_remaining", 1) <= 0:
            return "assemble"
        return "execute_tool"
    elif action == "abort":
        return "fail"
    else:
        return "assemble"


def execute_tool_node(state: AgentState) -> Dict[str, Any]:
    """Execute the requested tool and update budget & evidence store."""
    history = state.get("plan_history", [])
    last_decision = history[-1]
    tool_name = last_decision.get("tool")
    tool_args = last_decision.get("args", {}) or {}

    turn_num = len(state.get("observations", [])) + 1
    t0 = time.time()
    evidence: EvidenceStore = state["evidence"]
    budget: Budget = state["budget"]

    try:
        items = registry.execute(tool_name, tool_args)
        latency = round(time.time() - t0, 3)

        tokens_added = 0
        for item in items:
            added = evidence.add(item)
            if added:
                tokens_added += item.tokens
                budget.admit(item.tokens)

        obs = {
            "turn": turn_num,
            "tool": tool_name,
            "args": tool_args,
            "result_count": len(items),
            "tokens_added": tokens_added,
            "latency": latency,
            "summary": f"Retrieved {len(items)} items ({tokens_added} tokens)",
            "ok": True
        }

        return {
            "observations": state.get("observations", []) + [obs],
            "tool_calls_used": state.get("tool_calls_used", 0) + 1,
            "tool_calls_remaining": state.get("tool_calls_remaining", 1) - 1,
        }

    except ToolError as te:
        latency = round(time.time() - t0, 3)
        err_msg = str(te)
        obs = {
            "turn": turn_num,
            "tool": tool_name,
            "args": tool_args,
            "result_count": 0,
            "tokens_added": 0,
            "latency": latency,
            "summary": f"Tool error: {err_msg}",
            "ok": False
        }

        updates: Dict[str, Any] = {
            "observations": state.get("observations", []) + [obs],
            "tool_calls_used": state.get("tool_calls_used", 0) + 1,
            "tool_calls_remaining": state.get("tool_calls_remaining", 1) - 1,
        }

        # Check for non-negotiable failure status triggers
        if "KB_UNAVAILABLE" in err_msg:
            updates["status"] = Status.KB_UNAVAILABLE.value
            updates["error_message"] = err_msg
        elif "RETRIEVAL_UNAVAILABLE" in err_msg:
            updates["status"] = Status.RETRIEVAL_UNAVAILABLE.value
            updates["error_message"] = err_msg

        return updates


def route_after_tool(state: AgentState) -> Literal["plan", "fail"]:
    status = state.get("status")
    if status in [Status.KB_UNAVAILABLE.value, Status.RETRIEVAL_UNAVAILABLE.value]:
        return "fail"
    return "plan"


def assemble_node(state: AgentState) -> Dict[str, Any]:
    """Selects from the evidence store into the final prompt under budget limit."""
    evidence: EvidenceStore = state["evidence"]
    budget: Budget = state["budget"]

    # Budget available for evidence in composition
    admitted, dropped = evidence.assemble(budget_limit=budget.remaining)

    return {
        "assembled_evidence": admitted,
        "dropped_evidence": dropped
    }


def compose_node(state: AgentState) -> Dict[str, Any]:
    """Writes the answer against capability output schema in JSON mode."""
    task = state.get("task", "")
    cap_name = state.get("capability") or "ad_hoc"
    cap = capability_registry.get_or_default(cap_name)

    evidence: EvidenceStore = state["evidence"]
    admitted = state.get("assembled_evidence", [])
    dropped = state.get("dropped_evidence", [])

    assembled_str = evidence.render_assembled(admitted)

    dropped_notice = ""
    if dropped:
        lowest_rel = min(d["relevance"] for d in dropped)
        dropped_notice = (
            f"\n> [!NOTE]\n> {len(dropped)} items were dropped to fit the budget. "
            f"The lowest relevance admitted was {lowest_rel:.2f}. "
            "Take this into account — set coverage_note if anything is missing.\n"
        )

    # Capability contract description
    schema_json = json.dumps(cap.output_schema.model_json_schema(), indent=2)
    contract_str = f"Name: {cap.name}\nPurpose: {cap.purpose}\nConsumer: {cap.consumer}\nJSON Schema:\n{schema_json}"

    slots = {
        "task": task,
        "capability_contract": contract_str,
        "assembled_evidence": assembled_str,
        "dropped_notice": dropped_notice,
        "style_directives": "Provide clean, direct, factual synthesis without conversational filler."
    }

    system_prompt = get_harness_prompt()
    user_prompt = get_compose_prompt(slots)

    try:
        draft, model, pt, ct = generate_json_object(
            system_instruction=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            trace_id=state.get("trace_id")
        )
        return {"draft": draft}
    except Exception as e:
        return {
            "status": Status.VERIFICATION_FAILED.value,
            "error_message": f"Compose failed: {e}"
        }


def verify_node(state: AgentState) -> Dict[str, Any]:
    """Parses output against capability schema & verification rules."""
    draft = state.get("draft")
    if not draft:
        return {
            "violations": [{
                "field": "root",
                "rule": "Draft presence",
                "found": None,
                "why": "No draft produced by compose node."
            }]
        }

    cap_name = state.get("capability") or "ad_hoc"
    cap = capability_registry.get_or_default(cap_name)
    admitted = state.get("assembled_evidence", [])

    context = {
        "dropped_evidence": state.get("dropped_evidence", []),
        "tools_failed": any(not o.get("ok", True) for o in state.get("observations", [])),
        "person": state.get("task", "")  # or parsed person
    }

    violations = RuleEngine.verify(cap, draft, admitted, context)
    if not violations:
        return {"violations": [], "status": Status.SUCCESS.value}
    return {"violations": violations}


def route_after_verify(state: AgentState) -> Literal["end_success", "repair", "degrade"]:
    violations = state.get("violations", [])
    if not violations:
        return "end_success"

    repair_attempts = state.get("repair_attempts", 0)
    max_repair = state.get("max_repair_attempts", 2)

    if repair_attempts < max_repair:
        return "repair"
    return "degrade"


def repair_node(state: AgentState) -> Dict[str, Any]:
    """Feeds violations back to compose with repair prompt."""
    violations = state.get("violations", [])
    draft = state.get("draft", {})
    evidence: EvidenceStore = state["evidence"]
    admitted = state.get("assembled_evidence", [])
    assembled_str = evidence.render_assembled(admitted)

    violation_lines = []
    for v in violations:
        violation_lines.append(
            f"field: {v.get('field')}\nrule:  {v.get('rule')}\nfound: {v.get('found')}\nwhy:   {v.get('why')}\n"
        )
    violations_str = "\n".join(violation_lines)

    slots = {
        "violations": violations_str,
        "previous_draft": json.dumps(draft, indent=2),
        "assembled_evidence": assembled_str
    }

    system_prompt = get_harness_prompt()
    user_prompt = get_repair_prompt(slots)

    try:
        new_draft, model, pt, ct = generate_json_object(
            system_instruction=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            trace_id=state.get("trace_id")
        )
        return {
            "draft": new_draft,
            "repair_attempts": state.get("repair_attempts", 0) + 1
        }
    except Exception as e:
        return {
            "repair_attempts": state.get("repair_attempts", 0) + 1,
            "error_message": f"Repair call failed: {e}"
        }


def degrade_node(state: AgentState) -> Dict[str, Any]:
    """Produces partial output with failed items flagged."""
    draft = state.get("draft", {}) or {}
    violations = state.get("violations", [])
    violation_reasons = "; ".join(f"{v['field']}: {v['why']}" for v in violations)

    if "coverage_note" in draft:
        prev_note = draft.get("coverage_note") or ""
        draft["coverage_note"] = f"{prev_note} [DEGRADED: {violation_reasons}]".strip()

    return {
        "status": Status.DEGRADED.value,
        "draft": draft,
        "response": draft
    }


def fail_node(state: AgentState) -> Dict[str, Any]:
    """Terminates with a named status. Never returns an invented answer."""
    status = state.get("status") or Status.VERIFICATION_FAILED.value
    err = state.get("error_message") or f"Execution terminated with status {status}"

    return {
        "status": status,
        "error_message": err,
        "response": {
            "status": status,
            "error": err
        }
    }


# ── Build LangGraph Workflow ─────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("plan", plan_node)
    builder.add_node("execute_tool", execute_tool_node)
    builder.add_node("assemble", assemble_node)
    builder.add_node("compose", compose_node)
    builder.add_node("verify", verify_node)
    builder.add_node("repair", repair_node)
    builder.add_node("degrade", degrade_node)
    builder.add_node("fail", fail_node)

    builder.set_entry_point("plan")

    builder.add_conditional_edges(
        "plan",
        route_after_plan,
        {
            "execute_tool": "execute_tool",
            "assemble": "assemble",
            "fail": "fail"
        }
    )

    builder.add_conditional_edges(
        "execute_tool",
        route_after_tool,
        {
            "plan": "plan",
            "fail": "fail"
        }
    )

    builder.add_edge("assemble", "compose")
    builder.add_edge("compose", "verify")

    builder.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "end_success": END,
            "repair": "repair",
            "degrade": "degrade"
        }
    )

    builder.add_edge("repair", "verify")
    builder.add_edge("degrade", END)
    builder.add_edge("fail", END)

    return builder.compile()


agent_app = build_agent_graph()
