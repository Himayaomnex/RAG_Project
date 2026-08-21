"""
================================================================================
Production Multi-Agent REST API Server (RAG_COMBINED)
================================================================================
Provides clean REST API endpoints for external applications, microservices,
or web UIs to connect to and consume your 3 Production Agents.

Enforces Strict Role Scoping (RBAC) & Boundary Isolation:
- Manager Endpoint (/api/v1/manager): Executive review, status & decisions.
- Mentor Endpoint (/api/v1/mentor): Mentee evaluation, scorecards & quizzes.
- Teammate Endpoint (/api/v1/teammate): Code assistance & spoken meeting quotes.
- Router Endpoint (/api/v1/query): Central Intent Router with automatic agent dispatch.
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


from router import route_request, route_request_with_role, detect_agent_intent
from agents.manager.agent import manager_agent
from agents.mentor.agent import mentor_agent
from agents.team.agent import team_agent
from agents.shared.logging import get_trace

try:
    from fastapi import FastAPI, Header, HTTPException, Depends
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

def get_active_llm_provider_name() -> str:
    if os.getenv("GEMINI_API_KEY", "").strip():
        model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash").strip()
        return f"Google Gemini ({model}) & Qdrant"
    elif os.getenv("GROQ_API_KEY", "").strip():
        return "Groq (openai/gpt-oss-120b) & Qdrant"
    return "OpenRouter Free Models & Qdrant"

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="Enterprise Multi-Agent RAG Service",
        description="Production API serving Manager, Mentor, and Teammates Agents powered by Qdrant & Google Gemini LLM.",
        version="1.0.0"
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

    class QueryResponse(BaseModel):
        agent_role: str
        response: str
        latency_seconds: float
        status: str = "success"
        llm_provider: str = "Google Gemini (gemini-2.5-flash) & Qdrant"

    AGENT_HISTORY = {
        "manager": [],
        "mentor": [],
        "teammate": []
    }

    @app.on_event("startup")
    def startup_warmup():
        print("\n" + "=" * 80)
        print("🚀 [API Server Warmup]: Pre-loading Vector DB & Embedding Models...")
        try:
            from pipeline import ensure_pipeline_initialized
            ensure_pipeline_initialized()
            print("✅ [API Server Warmup]: Vector DB initialized and ready for instant queries!")
        except Exception as e:
            print(f"⚠️ [API Server Warmup Notice]: {e}")
        print("=" * 80 + "\n")

    @app.get("/health")
    def health_check():
        return {
            "status": "healthy",
            "service": "RAG_COMBINED Multi-Agent Service",
            "agents": ["manager", "mentor", "teammates"]
        }

    @app.get("/api/v1/history")
    def get_agent_history(role: Optional[str] = "all"):
        """Returns stored conversation history for specified agent role or all agents."""
        if role in AGENT_HISTORY:
            return {role: AGENT_HISTORY[role]}
        return AGENT_HISTORY

    @app.post("/api/v1/query", response_model=QueryResponse)
    def dispatch_query(req: QueryRequest, x_user_role: Optional[str] = Header("auto"), x_user_id: Optional[str] = Header("USR-OWNER-01")):
        """Central Auto-Router Endpoint: Dynamically routes query based on user role or prompt intent."""
        t0 = time.time()
        print(f"\n📥 [API Server - Auto Router] Request Received:")
        print(f"   • Prompt: \"{req.prompt}\"")
        print(f"   • User Role: {x_user_role} | Target Mentee: {req.target_member or 'Auto-Detect'}")
        
        try:
            result, dispatched_role = route_request_with_role(req.prompt, user_role=x_user_role or "auto", target_member=req.target_member or "")
            status = "success"
        except Exception as e:
            print(f"❌ [API Server Error]: {e}")
            result = f"⚠️ Server Error encountered while processing query: {str(e)}"
            dispatched_role = x_user_role or "manager"
            status = "error"
            
        latency = round(time.time() - t0, 3)
        print(f"📤 [API Server - Auto Router] Completed in {latency}s | Status: {status} | Dispatched Agent: {dispatched_role}")
        
        target_key = "manager" if "manager" in dispatched_role.lower() else ("mentor" if "mentor" in dispatched_role.lower() or "siddharth" in dispatched_role.lower() else "teammate")
        AGENT_HISTORY[target_key].append({
            "timestamp": time.strftime("%H:%M:%S"),
            "user_id": x_user_id,
            "prompt": req.prompt,
            "response": result,
            "latency": latency
        })

        return QueryResponse(
            agent_role=dispatched_role,
            response=result,
            latency_seconds=latency,
            status=status,
            llm_provider=get_active_llm_provider_name()
        )

    @app.post("/api/v1/manager", response_model=QueryResponse)
    def manager_agent_endpoint(req: QueryRequest, x_user_role: Optional[str] = Header("manager"), x_user_id: Optional[str] = Header("USR-OWNER-01")):
        """Manager Agent Endpoint: Executive progress status, active blockers, risks, and required decisions."""
        t0 = time.time()
        print(f"\n👔 [Manager Agent Endpoint] Request Received: \"{req.prompt}\"")
        
        try:
            result = manager_agent.handle_request(req.prompt, trainee=req.target_member or "")
            status = "success"
        except Exception as e:
            print(f"❌ [Manager Agent Error]: {e}")
            result = f"⚠️ Manager Agent Error: {str(e)}"
            status = "error"
            
        latency = round(time.time() - t0, 3)
        return QueryResponse(
            agent_role="manager",
            response=result,
            latency_seconds=latency,
            status=status,
            llm_provider=get_active_llm_provider_name()
        )

    @app.post("/api/v1/mentor", response_model=QueryResponse)
    def mentor_agent_endpoint(req: QueryRequest, x_user_role: Optional[str] = Header("siddharth"), x_user_id: Optional[str] = Header("USR-OWNER-01")):
        """Mentor Agent Endpoint: Mentee evaluation scorecards, technical quizzes, and next assignments."""
        t0 = time.time()
        print(f"\n🎓 [Mentor Agent Endpoint] Request Received: \"{req.prompt}\"")
        
        try:
            result = mentor_agent.handle_request(req.prompt, trainee=req.target_member or "")
            status = "success"
        except Exception as e:
            print(f"❌ [Mentor Agent Error]: {e}")
            result = f"⚠️ Mentor Agent Error: {str(e)}"
            status = "error"
            
        latency = round(time.time() - t0, 3)
        return QueryResponse(
            agent_role="mentor",
            response=result,
            latency_seconds=latency,
            status=status,
            llm_provider=get_active_llm_provider_name()
        )

    @app.post("/api/v1/teammate", response_model=QueryResponse)
    def teammate_agent_endpoint(req: QueryRequest, x_user_name: Optional[str] = Header("Himaya"), x_user_id: Optional[str] = Header("USR-OWNER-01")):
        """Team Intelligence Agent Endpoint: Missed session catch-up, peer action items, and codebase requirements."""
        t0 = time.time()
        print(f"\n👥 [Team Intelligence Agent Endpoint] Request Received: \"{req.prompt}\"")
        
        try:
            result = team_agent.handle_request(req.prompt, trainee=req.target_member or x_user_name or "Himaya")
            status = "success"
        except Exception as e:
            print(f"❌ [Team Intelligence Error]: {e}")
            result = f"⚠️ Team Intelligence Agent Error: {str(e)}"
            status = "error"
            
        latency = round(time.time() - t0, 3)
        return QueryResponse(
            agent_role="team",
            response=result,
            latency_seconds=latency,
            status=status,
            llm_provider=get_active_llm_provider_name()
        )

    @app.get("/api/v1/trace/{trace_id}")
    def get_execution_trace_endpoint(trace_id: str):
        """Trace Inspection Endpoint: Expands challenged rows with underlying chunk IDs and telemetry."""
        trace_data = get_trace(trace_id)
        if not trace_data:
            raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found.")
        return trace_data

    # Mount static web frontend files LAST so API routes take precedence
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")



if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        import uvicorn
        import webbrowser
        import threading

        def open_browser():
            time.sleep(1.2)
            webbrowser.open("http://127.0.0.1:8000")

        threading.Thread(target=open_browser, daemon=True).start()

        print("=" * 80)
        print("🚀 MULTI-AGENT REST API & WEB UI SERVER IS RUNNING!")
        print("👉 Opening your web browser automatically at: http://127.0.0.1:8000")
        print("=" * 80)
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    else:
        print("FastAPI not installed. Run 'pip install fastapi uvicorn' to enable REST API server.")


