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
from typing import TypedDict, Optional, List, Dict, Any

from langgraph.graph import StateGraph, END
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


def reset_session(session_id: str = "default") -> None:
    """Clear conversation history and summary for a session."""
    _SESSION_HISTORY[session_id] = []
    _SESSION_SUMMARIES[session_id] = ""


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

    # For assistant responses, store a compact summary (first 250 chars) to avoid expensive token waste
    stored_content = content[:250].strip() if role == "assistant" else content.strip()
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
    # Input fields
    query: str
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

    # Conversation memory (injected from _SESSION_HISTORY before execution)
    conversation_history: List[Dict[str, str]]


# ── Node: Intent Classifier ───────────────────────────────────────────────────

def intent_classifier_node(state: AgentState) -> AgentState:
    """
    Uses LLM-based semantic classifier (router.classify_intent) to determine
    which agent should handle the query and to extract entity slots.

    Respects values already set by the caller (e.g. explicit trainee= flag).
    """
    result = classify_intent(state["query"], trainee_hint=state.get("trainee"))

    # Only override empty slots — caller-provided values take precedence
    return {
        **state,
        "agent_intent": result["agent"],
        "strategy":   state.get("strategy") or result.get("strategy") or "exp1",
        "trainee":    state.get("trainee") or result.get("trainee"),
        "date":       state.get("date")    or result.get("date"),
        "period":     state.get("period")  or result.get("period"),
        "focus_area": state.get("focus_area") or result.get("focus_area"),
        "trace_id":   f"trc-{uuid.uuid4().hex[:10]}",
    }


# ── Helper: inject conversation history into query ────────────────────────────

def _build_query_with_history(state: AgentState) -> str:
    """
    Prepend earlier summary + recent conversation turns to the raw query so the agent LLM
    has full multi-turn context with minimal token overhead.
    """
    session_id = state.get("session_id", "default")
    summary = get_summary(session_id)
    history = state.get("conversation_history") or []

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
    _append_history(state["session_id"], "user", state["query"])
    _append_history(state["session_id"], "assistant", result[:500])  # summary for context

    return {**state, "final_response": result, "dispatched_agent": "manager", "latency_seconds": latency}


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
    _append_history(state["session_id"], "user", state["query"])
    _append_history(state["session_id"], "assistant", result[:500])

    return {**state, "final_response": result, "dispatched_agent": "mentor", "latency_seconds": latency}


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
    _append_history(state["session_id"], "user", state["query"])
    _append_history(state["session_id"], "assistant", result[:500])

    return {**state, "final_response": result, "dispatched_agent": "team", "latency_seconds": latency}


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

    return builder.compile()


# Compiled graph singleton
_graph = _build_graph()


# ── Public API ────────────────────────────────────────────────────────────────

# ── Semantic Graph Cache Store ────────────────────────────────────────────────
# Stores tuples of (normalized_query_emb, trainee_scope, final_state_dict, raw_query)
_GRAPH_CACHE: List[Tuple[Any, Optional[str], Dict[str, Any], str]] = []
_GRAPH_DENSE_MODEL = None

def get_graph_dense_model():
    global _GRAPH_DENSE_MODEL
    if _GRAPH_DENSE_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _GRAPH_DENSE_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _GRAPH_DENSE_MODEL


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
    """
    import numpy as np

    # ── 1. Semantic Cache (DISABLED per Siddharth's Handoff: 100% Live Calls) ──
    # Cache disabled so every demo query performs live retrieval over HTTP

    # Inject current conversation history into state
    history = get_history(session_id)[-BUFFER_WINDOW_TURNS * 2:]

    initial_state: AgentState = {
        "query":                query,
        "trainee":              trainee,
        "date":                 date,
        "period":               period,
        "focus_area":           focus_area,
        "session_id":           session_id,
        "strategy":             None,
        "agent_intent":         forced_agent or "",   # "" triggers classifier
        "final_response":       "",
        "dispatched_agent":     "",
        "latency_seconds":      0.0,
        "trace_id":             "",
        "conversation_history": history,
    }

    # If forced_agent is set, skip the classifier node by pre-filling intent
    if forced_agent:
        initial_state["agent_intent"] = forced_agent

    final_state = _graph.invoke(initial_state)

    result_dict = {
        "final_response":   final_state["final_response"],
        "dispatched_agent": final_state["dispatched_agent"],
        "agent_intent":     final_state["agent_intent"],
        "latency_seconds":  final_state["latency_seconds"],
        "trace_id":         final_state["trace_id"],
        "session_id":       session_id,
    }

    return result_dict

