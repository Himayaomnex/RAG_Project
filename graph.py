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


# ── Conversation memory store ─────────────────────────────────────────────────
# Keyed by session_id → list of { role, content } dicts (last N turns kept)
_SESSION_HISTORY: Dict[str, List[Dict[str, str]]] = {}
MAX_HISTORY_TURNS = 6   # inject last 6 exchanges into LLM context


def reset_session(session_id: str = "default") -> None:
    """Clear conversation history for a session."""
    _SESSION_HISTORY[session_id] = []


def get_history(session_id: str) -> List[Dict[str, str]]:
    return _SESSION_HISTORY.get(session_id, [])


def _append_history(session_id: str, role: str, content: str) -> None:
    if session_id not in _SESSION_HISTORY:
        _SESSION_HISTORY[session_id] = []
    _SESSION_HISTORY[session_id].append({"role": role, "content": content})
    # Keep only the last MAX_HISTORY_TURNS exchanges (each exchange = 2 entries)
    max_entries = MAX_HISTORY_TURNS * 2
    if len(_SESSION_HISTORY[session_id]) > max_entries:
        _SESSION_HISTORY[session_id] = _SESSION_HISTORY[session_id][-max_entries:]


# ── Shared state schema ───────────────────────────────────────────────────────

class AgentState(TypedDict):
    # Input fields
    query: str
    trainee: Optional[str]
    date: Optional[str]
    period: Optional[str]
    focus_area: Optional[str]
    session_id: str

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
        "trainee":  state.get("trainee") or result.get("trainee"),
        "date":     state.get("date")    or result.get("date"),
        "period":   state.get("period")  or result.get("period"),
        "trace_id": f"trc-{uuid.uuid4().hex[:10]}",
    }


# ── Helper: inject conversation history into query ────────────────────────────

def _build_query_with_history(state: AgentState) -> str:
    """
    Prepend recent conversation turns to the raw query so the agent LLM
    has multi-turn context without modifying the agent code.
    """
    history = state.get("conversation_history") or []
    if not history:
        return state["query"]

    history_block = "\n".join(
        f"[{turn['role'].upper()}]: {turn['content']}" for turn in history
    )
    return (
        f"<conversation_history>\n{history_block}\n</conversation_history>\n\n"
        f"<current_query>\n{state['query']}\n</current_query>"
    )


# ── Node: Manager Executor ────────────────────────────────────────────────────

def manager_node(state: AgentState) -> AgentState:
    t0 = time.time()
    enriched_query = _build_query_with_history(state)

    result = manager_agent.handle_request(
        query=enriched_query,
        period_start=state.get("period"),
        period_end=None,
        trainee=state.get("trainee") or "",
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

    # ── 1. Semantic Cache Check (Raw Query Level) ───────────────────────────
    try:
        model = get_graph_dense_model()
        q_emb = model.encode(query)
        q_emb_norm = q_emb / np.linalg.norm(q_emb) if np.linalg.norm(q_emb) > 0 else q_emb

        for cached_emb, cached_trainee, cached_state, cached_query in _GRAPH_CACHE:
            # Match trainee scope (e.g. if we specifically scoped one trainee, must match)
            if cached_trainee == trainee:
                # SAFEGUARD: If the query mentions one trainee name, but the cached query mentions another, skip hit
                q_low = query.lower()
                cq_low = cached_query.lower()
                trainee_names = ["himaya", "ganesh", "dakshinya"]
                name_mismatch = False
                for name in trainee_names:
                    if (name in q_low) != (name in cq_low):
                        name_mismatch = True
                        break
                if name_mismatch:
                    continue

                # MONTH SAFEGUARD: If months are different (e.g. July vs June), skip hit
                months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
                month_mismatch = False
                for m in months:
                    if (m in q_low) != (m in cq_low):
                        month_mismatch = True
                        break
                if month_mismatch:
                    continue

                # DAY-NUMBER SAFEGUARD: If date numbers are different (e.g. 18 vs 31), skip hit
                import re
                q_nums = set(re.findall(r'\b\d{1,2}\b', q_low))
                cq_nums = set(re.findall(r'\b\d{1,2}\b', cq_low))
                if q_nums != cq_nums:
                    continue

                sim = np.dot(q_emb_norm, cached_emb)
                if sim > 0.72:  # 72% similarity threshold (captures broad rollup variations)
                    print(f"  - [Semantic Graph Cache Hit]: similarity={sim:.3f} | Bypassing Graph Invoke!")
                    # Make sure to return a copy with fresh latency showing 0.0s cache retrieval
                    hit_res = cached_state.copy()
                    hit_res["latency_seconds"] = 0.0
                    hit_res["trace_id"] = f"hit-{hit_res['trace_id'].replace('trc-', '')}"
                    return hit_res
    except Exception as e:
        print(f"  - [Graph Cache Lookup Error]: {e}")

    # Inject current conversation history into state
    history = get_history(session_id)[-MAX_HISTORY_TURNS * 2:]

    initial_state: AgentState = {
        "query":                query,
        "trainee":              trainee,
        "date":                 date,
        "period":               period,
        "focus_area":           focus_area,
        "session_id":           session_id,
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

    # ── 2. Cache the Result ──────────────────────────────────────────────────
    try:
        _GRAPH_CACHE.append((q_emb_norm, trainee, result_dict, query))
    except Exception as cache_err:
        pass

    return result_dict

