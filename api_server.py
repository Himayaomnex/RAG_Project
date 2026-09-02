"""
================================================================================
Production Multi-Agent REST API Server (RAG_COMBINED)
================================================================================
Clean REST API - NO UI, NO static files.
All requests are routed through the LangGraph StateGraph (graph.py).
Conversation history is maintained per session_id across turns.

Endpoints:
  POST /api/v1/query      - Auto-routes via LLM intent classifier
  POST /api/v1/manager    - Pinned to Manager agent
  POST /api/v1/mentor     - Pinned to Mentor agent
  POST /api/v1/teammate   - Pinned to Team Intelligence agent
  GET  /api/v1/trace/{id} - Execution trace inspector
  GET  /api/v1/history    - Conversation history for a session
  GET  /health            - Health check
"""

import os
import sys
import time
from typing import Dict, Any, Optional

parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


from graph import run_graph, get_history, reset_session
from agents.shared.logging import get_trace

try:
    from fastapi import FastAPI, Header, HTTPException, Depends
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

def get_active_llm_provider_name() -> str:
    if os.getenv("GEMINI_API_KEY", "").strip():
        model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash").strip()
        return f"Google Gemini ({model}) & Qdrant"
    elif os.getenv("GROQ_API_KEY", "").strip():
        return "Groq & Qdrant"
    return "OpenRouter Free Models & Qdrant"


if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="Enterprise Multi-Agent RAG Service",
        description="Production API: Manager, Mentor, and Teammates Agents powered by Qdrant & Google Gemini. Orchestrated by LangGraph.",
        version="2.0.0",
        docs_url=None,     # Disable Swagger UI to enforce terminal-only use
        redoc_url=None     # Disable ReDoc UI to enforce terminal-only use
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class QueryRequest(BaseModel):
        prompt: str
        target_member: Optional[str] = ""
        session_id: Optional[str] = "default"   # multi-turn conversation session

    class QueryResponse(BaseModel):
        agent_role: str
        response: str
        latency_seconds: float
        status: str = "success"
        trace_id: str = ""
        session_id: str = "default"
        llm_provider: str = "Google Gemini (gemini-2.5-flash) & Qdrant"

    @app.on_event("startup")
    def startup_warmup():
        print("\n" + "=" * 70)
        print("[API Server Warmup]: Checking Retrieval Microservice (Port 8000)...")
        try:
            from agents.shared.retrieval_client import retrieval_client
            retrieval_client.query_evidence(query="warmup", strategy="exp1", agent_name="system", skill_name="warmup", top_k=1)
            print("[API Server Warmup]: Retrieval Microservice Connected.")
        except Exception as e:
            print(f"[API Server Warmup Notice]: Retrieval Microservice not reachable yet ({e}). Will connect on-demand.")
        print("=" * 70 + "\n")

    @app.get("/health")
    def health_check():
        return {
            "status": "healthy",
            "service": "RAG_COMBINED Multi-Agent Service v2.0 (LangGraph)",
            "agents": ["manager", "mentor", "teammates"]
        }

    @app.get("/api/v1/history")
    def get_agent_history(session_id: Optional[str] = "default"):
        """Returns conversation history for a given session_id."""
        return {"session_id": session_id, "history": get_history(session_id)}

    @app.post("/api/v1/history/reset")
    def reset_agent_history(session_id: Optional[str] = "default"):
        """Clears conversation history for a session."""
        reset_session(session_id)
        return {"status": "cleared", "session_id": session_id}

    @app.post("/api/v1/query", response_model=QueryResponse)
    def dispatch_query(req: QueryRequest, x_user_id: Optional[str] = Header("USR-OWNER-01")):
        """Auto-Router: LangGraph StateGraph classifies intent and dispatches to the correct agent."""
        t0 = time.time()
        effective_session = req.session_id if (req.session_id and req.session_id != "default") else (x_user_id or "default")
        print(f"\n[API /query] prompt={req.prompt!r} session={effective_session} trainee={req.target_member}")
        try:
            result = run_graph(
                query=req.prompt,
                trainee=req.target_member or None,
                session_id=effective_session,
            )
            status = "success"
        except Exception as e:
            print(f"[API /query Error]: {e}")
            result = {"final_response": f"Server error: {str(e)}", "dispatched_agent": "unknown",
                      "latency_seconds": 0.0, "trace_id": "", "session_id": effective_session}
            status = "error"

        return QueryResponse(
            agent_role=result["dispatched_agent"],
            response=result["final_response"],
            latency_seconds=result["latency_seconds"],
            status=status,
            trace_id=result.get("trace_id", ""),
            session_id=result.get("session_id", effective_session),
            llm_provider=get_active_llm_provider_name()
        )

    @app.post("/api/v1/manager", response_model=QueryResponse)
    def manager_agent_endpoint(req: QueryRequest, x_user_id: Optional[str] = Header("USR-OWNER-01")):
        """Manager Agent: pinned — always runs manager_weekly_rollup."""
        t0 = time.time()
        effective_session = req.session_id if (req.session_id and req.session_id != "default") else (x_user_id or "default")
        print(f"\n[Manager Endpoint] prompt={req.prompt!r} session={effective_session}")
        try:
            result = run_graph(
                query=req.prompt,
                trainee=req.target_member or None,
                session_id=effective_session,
                forced_agent="manager"
            )
            status = "success"
        except Exception as e:
            print(f"[Manager Error]: {e}")
            result = {"final_response": f"Manager Agent Error: {str(e)}", "dispatched_agent": "manager",
                      "latency_seconds": 0.0, "trace_id": "", "session_id": effective_session}
            status = "error"
        return QueryResponse(
            agent_role="manager",
            response=result["final_response"],
            latency_seconds=result["latency_seconds"],
            status=status,
            trace_id=result.get("trace_id", ""),
            session_id=result.get("session_id", effective_session),
            llm_provider=get_active_llm_provider_name()
        )

    @app.post("/api/v1/mentor", response_model=QueryResponse)
    def mentor_agent_endpoint(req: QueryRequest, x_user_id: Optional[str] = Header("USR-OWNER-01")):
        """Mentor Agent: pinned — always runs mentor_trainee_assessment."""
        t0 = time.time()
        effective_session = req.session_id if (req.session_id and req.session_id != "default") else (x_user_id or "default")
        print(f"\n[Mentor Endpoint] prompt={req.prompt!r} session={effective_session}")
        try:
            result = run_graph(
                query=req.prompt,
                trainee=req.target_member or None,
                session_id=effective_session,
                forced_agent="mentor"
            )
            status = "success"
        except Exception as e:
            print(f"[Mentor Error]: {e}")
            result = {"final_response": f"Mentor Agent Error: {str(e)}", "dispatched_agent": "mentor",
                      "latency_seconds": 0.0, "trace_id": "", "session_id": effective_session}
            status = "error"
        return QueryResponse(
            agent_role="mentor",
            response=result["final_response"],
            latency_seconds=result["latency_seconds"],
            status=status,
            trace_id=result.get("trace_id", ""),
            session_id=result.get("session_id", effective_session),
            llm_provider=get_active_llm_provider_name()
        )

    @app.post("/api/v1/teammate", response_model=QueryResponse)
    def teammate_agent_endpoint(req: QueryRequest, x_user_id: Optional[str] = Header("USR-OWNER-01")):
        """Team Agent: pinned — always runs team_session_catchup."""
        t0 = time.time()
        effective_session = req.session_id if (req.session_id and req.session_id != "default") else (x_user_id or "default")
        print(f"\n[Teammate Endpoint] prompt={req.prompt!r} session={effective_session}")
        try:
            result = run_graph(
                query=req.prompt,
                trainee=req.target_member or None,
                session_id=effective_session,
                forced_agent="team"
            )
            status = "success"
        except Exception as e:
            print(f"[Teammate Error]: {e}")
            result = {"final_response": f"Team Agent Error: {str(e)}", "dispatched_agent": "team",
                      "latency_seconds": 0.0, "trace_id": "", "session_id": effective_session}
            status = "error"
        return QueryResponse(
            agent_role="team",
            response=result["final_response"],
            latency_seconds=result["latency_seconds"],
            status=status,
            trace_id=result.get("trace_id", ""),
            session_id=result.get("session_id", "default"),
            llm_provider=get_active_llm_provider_name()
        )

    @app.get("/api/v1/trace/{trace_id}")
    def get_execution_trace_endpoint(trace_id: str):
        """Trace Inspector: expand trace by ID to see chunk IDs and token usage."""
        trace_data = get_trace(trace_id)
        if not trace_data:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found.")
        return trace_data


if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        import uvicorn
        print("=" * 70)
        print("[API Server] Starting RAG_COMBINED Multi-Agent API (LangGraph v2)")
        print("[API Server] Endpoints: /api/v1/query  /api/v1/manager  /api/v1/mentor  /api/v1/teammate")
        print("[API Server] Use cli.py for interactive terminal sessions.")
        print("=" * 70)
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    else:
        print("FastAPI not installed. Run: pip install fastapi uvicorn")



