"""
================================================================================
Enterprise FastAPI REST Server (api_server.py)
================================================================================
Exposes REST HTTP API endpoints for the 3-Agent RAG System.
Allows external clients (FastAPI, Postman, Web Apps, Mobile, Curl) to query 
the Router, Agents, and RAG Engine over standard REST HTTP endpoints.
"""

from fastapi import FastAPI, HTTPException, Header, Depends, Query
from pydantic import BaseModel
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(__file__))
from router import route_request
from agents.manager_agent import run_manager_agent
from agents.mentor_agent import run_mentor_agent
from agents.teammates_agent import run_teammates_agent

app = FastAPI(
    title="Multi-Agent RAG System REST API",
    description="FastAPI REST Interface for Router, Manager Agent, Mentor Agent, and Teammates Agent.",
    version="1.0.0"
)

# Request Models
class QueryRequest(BaseModel):
    prompt: str
    role: Optional[str] = "siddharth"
    target_member: Optional[str] = ""

class EvaluationRequest(BaseModel):
    member_name: str
    date: Optional[str] = ""

# API Endpoints for the 3 Agents Architecture
@app.get("/")
def root():
    return {
        "status": "online",
        "system": "3-Agent RAG System REST API",
        "agents": [
            {"agent": "Agent 1: Manager Agent", "endpoint": "/agents/manager"},
            {"agent": "Agent 2: Mentor Agent", "endpoint": "/agents/mentor"},
            {"agent": "Agent 3: Teammates Agent", "endpoint": "/agents/teammates"}
        ],
        "router": "/router/dispatch"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "vector_db": "qdrant_storage", "llm": "groq_llama_3.3"}

# ---------------------------------------------------------
# Agent 1: Manager Agent Endpoint
# ---------------------------------------------------------
@app.post("/agents/manager")
def manager_agent_endpoint(req: QueryRequest):
    """Agent 1: Manager Agent (Project status updates, milestones, and action items)."""
    try:
        response = run_manager_agent(req.prompt, target_member=req.target_member)
        return {"agent": "Manager Agent", "prompt": req.prompt, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# Agent 2: Mentor Agent Endpoint
# ---------------------------------------------------------
@app.post("/agents/mentor")
def mentor_agent_endpoint(req: QueryRequest):
    """Agent 2: Mentor Agent (Evaluation Scorecard Matrix & Technical Quiz Questions for Siddharth)."""
    try:
        response = run_mentor_agent(req.prompt, target_member=req.target_member)
        return {"agent": "Mentor Agent", "target": req.target_member, "prompt": req.prompt, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# Agent 3: Teammates Agent Endpoint
# ---------------------------------------------------------
@app.post("/agents/teammates")
def teammates_agent_endpoint(req: QueryRequest):
    """Agent 3: Teammates Agent (Codebase scanning, uploaded files Q&A, and reading materials)."""
    try:
        response = run_teammates_agent(req.prompt, user_name=req.role.capitalize())
        return {"agent": "Teammates Agent", "user": req.role, "prompt": req.prompt, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# Central Router Dispatcher Endpoint
# ---------------------------------------------------------
@app.post("/router/dispatch")
def router_dispatch_endpoint(req: QueryRequest):
    """Central Router: Receives role and prompt, automatically dispatches to correct Agent."""
    try:
        response = route_request(req.prompt, user_role=req.role, target_member=req.target_member)
        return {"dispatcher": "Router.py", "role": req.role, "prompt": req.prompt, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=True)
