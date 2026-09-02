"""
================================================================================
LangGraph Orchestration Engine  (graph.py)
================================================================================
Implements a proper StateGraph with:
- Shared AgentState carrying conversation history across turns
- LLM-based intent classification node (uses router.classify_intent)
- Dynamic retrieval strategy selection based on state slots
- Separate agent executor nodes for Manager / Mentor / Team
- Conditional edges that route based on state.agent_intent
- Conversation memory: last N turns are injected into every LLM prompt

Usage:
    from graph import run_graph, reset_session

    response = run_graph(
        query="How is Ganesh doing?",
        trainee="Ganesh",
        session_id="session-abc"          # optional, defaults to "default"
    )
    print(response["final_response"])
================================================================================
"""

import os
import time
import uuid
from typing import TypedDict, Optional, List, Dict, Any, Tuple
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents.manager.agent import manager_agent
from agents.mentor.agent import mentor_agent
from agents.team.agent import team_agent
from router import classify_intent


# ── Conversation memory store (Summary-Buffer Architecture) ───────────────────
# _SESSION_HISTORY: Keyed by session_id -> list of recent { role, content } dicts
# _SESSION_SUMMARIES: Keyed by session_id -> running compact summary of older turns
_SESSION_HISTORY: Dict[str, List[Dict[str, str]]] = {}
_SESSION_SUMMARIES: Dict[str, str] = {}
BUFFER_WINDOW_TURNS = 4   # keep exact verbatim dialogue for the last 4 exchanges (8 entries)

# LangGraph In-Memory Checkpointer for Thread State Persistence
_checkpointer = MemorySaver()


def reset_session(session_id: str = "default") -> None:
    """Clear conversation history, summary, and checkpointer state for a session."""
    _SESSION_HISTORY[session_id] = []
    _SESSION_SUMMARIES[session_id] = ""
    try:
        if hasattr(_checkpointer, "storage"):
            _checkpointer.storage.pop(session_id, None)
    except Exception:
        pass


def get_history(session_id: str) -> List[Dict[str, str]]:
    return _SESSION_HISTORY.get(session_id, [])


def get_summary(session_id: str) -> str:
    return _SESSION_SUMMARIES.get(session_id, "")


def _summarize_dropped_turns(dropped_entries: List[Dict[str, str]], current_summary: str) -> str:
    """
    Creates a compact summary update of older turns so context is never lost.
    """
    turn_snippets = []
    for entry in dropped_entries:
        role = entry.get("role", "user").capitalize()
        content = entry.get("content", "").replace("\n", " ").strip()
        # Truncate to avoid bloat
        snippet = content[:150] + "..." if len(content) > 150 else content
        turn_snippets.append(f"{role}: {snippet}")

    new_context = " | ".join(turn_snippets)
    if current_summary:
        return f"{current_summary}; [Earlier context]: {new_context}"
    return f"[Earlier context]: {new_context}"


def _append_history(session_id: str, role: str, content: str) -> None:
    if session_id not in _SESSION_HISTORY:
        _SESSION_HISTORY[session_id] = []
    if session_id not in _SESSION_SUMMARIES:
        _SESSION_SUMMARIES[session_id] = ""

    # For assistant responses, store a compact summary (up to 600 chars) to balance context depth & tokens
    stored_content = content[:600].strip() if role == "assistant" else content.strip()
    _SESSION_HISTORY[session_id].append({"role": role, "content": stored_content})

    # When history exceeds the buffer window, roll the oldest exchange into the running summary
    max_entries = BUFFER_WINDOW_TURNS * 2
    if len(_SESSION_HISTORY[session_id]) > max_entries:
        # Extract the oldest exchange (2 entries: user + assistant)
        dropped = _SESSION_HISTORY[session_id][:2]
        _SESSION_HISTORY[session_id] = _SESSION_HISTORY[session_id][2:]
        _SESSION_SUMMARIES[session_id] = _summarize_dropped_turns(dropped, _SESSION_SUMMARIES[session_id])


# ── Shared state schema ───────────────────────────────────────────────────────

class AgentState(TypedDict):
    # Input & entity slot fields
    query: str
    explicit_trainee: Optional[str]
    explicit_date: Optional[str]
    explicit_period: Optional[str]
    explicit_focus: Optional[str]
    trainee: Optional[str]
    date: Optional[str]
    period: Optional[str]
    focus_area: Optional[str]
    session_id: str
    strategy: Optional[str]

    # Populated by intent_classifier_node
    agent_intent: str       # "manager" | "mentor" | "team"

    # Populated by executor nodes
    final_response: str
    dispatched_agent: str
    latency_seconds: float
    trace_id: str

    # Conversation memory
    conversation_history: List[Dict[str, str]]
    conversation_summary: str


# ── Node: Intent Classifier ───────────────────────────────────────────────────

def intent_classifier_node(state: AgentState) -> AgentState:
    """
    Uses LLM-based semantic classifier (router.classify_intent) to determine
    which agent should handle the query and to extract entity slots.

    Resolution Priority:
    1. Explicit caller arguments (e.g. CLI/API flags)
    2. Fresh query entity extraction (result)
    3. Inherited prior turn slots (state) for follow-up queries
    """
    history = state.get("conversation_history") or get_history(state.get("session_id", "default"))
    active_slots = {
        "trainee": state.get("explicit_trainee") or state.get("trainee"),
        "date": state.get("explicit_date") or state.get("date"),
        "period": state.get("explicit_period") or state.get("period"),
        "focus_area": state.get("explicit_focus") or state.get("focus_area")
    }

    result = classify_intent(
        query=state["query"],
        trainee_hint=state.get("explicit_trainee") or state.get("trainee"),
        conversation_history=history,
        active_context=active_slots
    )

    resolved_agent = state.get("agent_intent") or result.get("agent") or "manager"
    resolved_strategy = state.get("strategy") or result.get("strategy") or "exp1"
    
    # Priority: Explicit argument -> Fresh query extraction -> Inherited prior slot
    resolved_trainee = state.get("explicit_trainee") or result.get("trainee") or state.get("trainee")
    resolved_date = state.get("explicit_date") or result.get("date") or state.get("date")
    resolved_period = state.get("explicit_period") or result.get("period") or state.get("period")
    resolved_focus = state.get("explicit_focus") or result.get("focus_area") or state.get("focus_area")

    return {
        **state,
        "agent_intent": resolved_agent,
        "strategy":   resolved_strategy,
        "trainee":    resolved_trainee,
        "date":       resolved_date,
        "period":     resolved_period,
        "focus_area": resolved_focus,
        "trace_id":   f"trc-{uuid.uuid4().hex[:10]}",
    }


# ── Helper: inject conversation history into query ────────────────────────────

def _build_query_with_history(state: AgentState) -> str:
    """
    Prepend earlier summary + recent conversation turns to the raw query so the agent LLM
    has full multi-turn context with minimal token overhead.
    """
    session_id = state.get("session_id", "default")
    summary = state.get("conversation_summary") or get_summary(session_id)
    history = state.get("conversation_history") or get_history(session_id)

    parts = []
    if summary:
        parts.append(f"<earlier_conversation_summary>\n{summary}\n</earlier_conversation_summary>")

    if history:
        history_block = "\n".join(
            f"[{turn['role'].upper()}]: {turn['content']}" for turn in history
        )
        parts.append(f"<recent_conversation_turns>\n{history_block}\n</recent_conversation_turns>")

    if not parts:
        return state["query"]

    parts.append(f"<current_query>\n{state['query']}\n</current_query>")
    return "\n\n".join(parts)


# ── Node: Manager Executor ────────────────────────────────────────────────────

def manager_node(state: AgentState) -> AgentState:
    t0 = time.time()
    enriched_query = _build_query_with_history(state)

    result = manager_agent.handle_request(
        query=enriched_query,
        period_start=state.get("period"),
        period_end=None,
        trainee=state.get("trainee") or "",
        strategy=state.get("strategy"),
        trace_id=state["trace_id"]
    )

    latency = round(time.time() - t0, 3)
    if not result.startswith("INSUFFICIENT_EVIDENCE") and not result.startswith("RETRIEVAL_UNAVAILABLE"):
        _append_history(state["session_id"], "user", state["query"])
        _append_history(state["session_id"], "assistant", result[:500])

    updated_hist = get_history(state["session_id"])
    updated_summ = get_summary(state["session_id"])

    return {
        **state,
        "final_response": result,
        "dispatched_agent": "manager",
        "latency_seconds": latency,
        "conversation_history": updated_hist,
        "conversation_summary": updated_summ,
    }


# ── Node: Mentor Executor ─────────────────────────────────────────────────────

def mentor_node(state: AgentState) -> AgentState:
    t0 = time.time()
    enriched_query = _build_query_with_history(state)

    result = mentor_agent.handle_request(
        query=enriched_query,
        trainee=state.get("trainee") or "",
        period=state.get("period"),
        focus_area=state.get("focus_area"),
        strategy=state.get("strategy"),
        trace_id=state["trace_id"]
    )

    latency = round(time.time() - t0, 3)
    if not result.startswith("INSUFFICIENT_EVIDENCE") and not result.startswith("RETRIEVAL_UNAVAILABLE"):
        _append_history(state["session_id"], "user", state["query"])
        _append_history(state["session_id"], "assistant", result[:500])

    updated_hist = get_history(state["session_id"])
    updated_summ = get_summary(state["session_id"])

    return {
        **state,
        "final_response": result,
        "dispatched_agent": "mentor",
        "latency_seconds": latency,
        "conversation_history": updated_hist,
        "conversation_summary": updated_summ,
    }


# ── Node: Team Executor ───────────────────────────────────────────────────────

def team_node(state: AgentState) -> AgentState:
    t0 = time.time()
    enriched_query = _build_query_with_history(state)

    result = team_agent.handle_request(
        query=enriched_query,
        date=state.get("date"),
        trainee=state.get("trainee") or "",
        strategy=state.get("strategy"),
        trace_id=state["trace_id"]
    )

    latency = round(time.time() - t0, 3)
    if not result.startswith("INSUFFICIENT_EVIDENCE") and not result.startswith("RETRIEVAL_UNAVAILABLE"):
        _append_history(state["session_id"], "user", state["query"])
        _append_history(state["session_id"], "assistant", result[:500])

    updated_hist = get_history(state["session_id"])
    updated_summ = get_summary(state["session_id"])

    return {
        **state,
        "final_response": result,
        "dispatched_agent": "team",
        "latency_seconds": latency,
        "conversation_history": updated_hist,
        "conversation_summary": updated_summ,
    }


# ── Conditional router ────────────────────────────────────────────────────────

def _route_on_intent(state: AgentState) -> str:
    """Conditional edge: reads state.agent_intent and returns node name."""
    intent = state.get("agent_intent", "manager")
    if intent == "mentor":
        return "mentor_node"
    if intent == "team":
        return "team_node"
    return "manager_node"


# ── Build the StateGraph ──────────────────────────────────────────────────────

def _build_graph():
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("intent_classifier", intent_classifier_node)
    builder.add_node("manager_node",      manager_node)
    builder.add_node("mentor_node",       mentor_node)
    builder.add_node("team_node",         team_node)

    # Entry point
    builder.set_entry_point("intent_classifier")

    # Conditional routing after classification
    builder.add_conditional_edges(
        "intent_classifier",
        _route_on_intent,
        {
            "manager_node": "manager_node",
            "mentor_node":  "mentor_node",
            "team_node":    "team_node",
        }
    )

    # Each executor node goes straight to END
    builder.add_edge("manager_node", END)
    builder.add_edge("mentor_node",  END)
    builder.add_edge("team_node",    END)

    return builder.compile(checkpointer=_checkpointer)


# Compiled graph singleton with Checkpointer
_graph = _build_graph()


# ── Public API ────────────────────────────────────────────────────────────────

def run_graph(
    query: str,
    trainee: Optional[str] = None,
    date: Optional[str] = None,
    period: Optional[str] = None,
    focus_area: Optional[str] = None,
    session_id: str = "default",
    forced_agent: Optional[str] = None,    # "manager"|"mentor"|"team" to skip classifier
) -> Dict[str, Any]:
    """
    Primary entry point for the multi-agent system.
    Orchestrated by LangGraph StateGraph with MemorySaver thread checkpointing.
    """
    config = {"configurable": {"thread_id": session_id}}

    # Retrieve existing state values from checkpointer if available
    prior_state_values = {}
    try:
        prior = _graph.get_state(config)
        if prior and prior.values:
            prior_state_values = prior.values
    except Exception:
        pass

    # Inject conversation history into initial state
    history = get_history(session_id)[-BUFFER_WINDOW_TURNS * 2:]
    summary = get_summary(session_id)

    initial_state: AgentState = {
        "query":                query,
        "explicit_trainee":     trainee,
        "explicit_date":        date,
        "explicit_period":      period,
        "explicit_focus":       focus_area,
        "trainee":              prior_state_values.get("trainee"),
        "date":                 prior_state_values.get("date"),
        "period":               prior_state_values.get("period"),
        "focus_area":           prior_state_values.get("focus_area"),
        "session_id":           session_id,
        "strategy":             None,
        "agent_intent":         forced_agent or "",   # "" triggers classifier
        "final_response":       "",
        "dispatched_agent":     "",
        "latency_seconds":      0.0,
        "trace_id":             "",
        "conversation_history": history,
        "conversation_summary": summary,
    }

    # If forced_agent is set, skip the classifier node by pre-filling intent
    if forced_agent:
        initial_state["agent_intent"] = forced_agent

    final_state = _graph.invoke(initial_state, config=config)

    result_dict = {
        "final_response":   final_state["final_response"],
        "dispatched_agent": final_state["dispatched_agent"],
        "agent_intent":     final_state["agent_intent"],
        "strategy":         final_state.get("strategy", "exp1"),
        "latency_seconds":  final_state["latency_seconds"],
        "trace_id":         final_state["trace_id"],
        "session_id":       session_id,
    }

    return result_dict

