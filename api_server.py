"""
================================================================================
Production Multi-Agent REST API & Web Server (RAG_COMBINED)
================================================================================
Turnkey Web Server & REST API:
- Serves the Interactive Browser Dashboard at http://127.0.0.1:8080
- Automatically routes queries through the Agent Harness (harness.runner.run_agent)
- Supports capability endpoints: /api/v1/query, /api/v1/manager, /api/v1/mentor, /api/v1/teammate
- Provides live Excel generation & Google Drive deliverable downloads
================================================================================
"""

import os
import sys
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path

parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from harness.runner import run_agent
from harness.capabilities.loader import capability_registry
from agents.shared.logging import get_trace

try:
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


def format_output_to_markdown(output_data: Any, capability: str) -> str:
    """Formats verified JSON output into rich, readable GitHub-flavored Markdown for the UI."""
    if not output_data:
        return "*(No output generated)*"
    
    if isinstance(output_data, str):
        return output_data
        
    if not isinstance(output_data, dict):
        return f"```json\n{json.dumps(output_data, indent=2)}\n```"

    md = []
    
    # 1. Mentor Assessment formatting
    if capability == "mentor_assessment":
        person = output_data.get("person", "Trainee")
        overall = output_data.get("overall", "")
        md.append(f"## 🎓 Mentor Assessment: **{person}**\n")
        if overall:
            md.append(f"**Overall Evaluation:** {overall}\n")
            
        dims = output_data.get("dimensions", [])
        if dims:
            md.append("### 📊 Dimension Scores (1–10)")
            md.append("| Dimension | Score | Reason | Citations |")
            md.append("| :--- | :---: | :--- | :--- |")
            for d in dims:
                cites = ", ".join(f"`{cid}`" for cid in d.get("evidence_ids", [])) or "—"
                md.append(f"| **{d.get('name')}** | **{d.get('score')}** | {d.get('reason')} | {cites} |")
            md.append("")
            
        caps = output_data.get("demonstrated_capabilities", [])
        if caps:
            md.append("### ✅ Demonstrated Capabilities (*Taught != Understood Verified*)")
            for c in caps:
                cites = ", ".join(f"`{cid}`" for cid in c.get("evidence_ids", []))
                md.append(f"- **{c.get('concept')}**: {c.get('how_shown')} *(Citations: {cites})*")
            md.append("")

        gaps = output_data.get("knowledge_gaps", [])
        if gaps:
            md.append("### ⚠️ Knowledge Gaps")
            for g in gaps:
                md.append(f"- {g.get('gap')}")
            md.append("")

        action = output_data.get("next_teaching_action", "")
        if action:
            md.append(f"### 🎯 Recommended Teaching Action\n> {action}\n")

    # 2. Manager Rollup formatting
    elif capability == "manager_rollup":
        headline = output_data.get("headline", "Weekly Executive Rollup")
        md.append(f"## 👔 Executive Summary: **{headline}**\n")
        
        comp = output_data.get("completed", [])
        if comp:
            md.append("### ✅ Verified Completed Deliverables")
            for item in comp:
                cites = ", ".join(f"`{cid}`" for cid in item.get("evidence_ids", []))
                md.append(f"- **[{item.get('owner')}]** {item.get('item')} *(Proof: {cites})*")
            md.append("")

        inp = output_data.get("in_progress", [])
        if inp:
            md.append("### 🔄 In-Progress Work")
            for item in inp:
                md.append(f"- **[{item.get('owner')}]** {item.get('item')}")
            md.append("")

        blk = output_data.get("blocked", [])
        if blk:
            md.append("### 🛑 Active Blockers & Risks")
            for item in blk:
                md.append(f"- **[{item.get('owner')}]** {item.get('item')} — *Impact:* {item.get('impact')} | *Resolution:* `{item.get('agreed_resolution')}`")
            md.append("")

        decs = output_data.get("decisions", [])
        if decs:
            md.append("### ⚖️ Architecture & Team Decisions")
            for d in decs:
                md.append(f"- {d.get('decision')} *(Owner: {d.get('owner') or 'Team'})*")
            md.append("")

    # 3. Team Catchup formatting
    elif capability == "team_catchup":
        sdate = output_data.get("session_date", "Recent Session")
        md.append(f"## 👥 Session Catch-Up: **{sdate}**\n")
        md.append(f"**What Happened:** {output_data.get('what_happened', '')}\n")
        
        topics = output_data.get("technical_topics", [])
        if topics:
            md.append("### 💡 Technical Topics Covered")
            for t in topics:
                md.append(f"- **{t.get('topic')}**: {t.get('summary')}")
            md.append("")

        my_tasks = output_data.get("assignments_for_you", [])
        if my_tasks:
            md.append("### 📌 Action Items Assigned to YOU")
            for task in my_tasks:
                due = f" (Due: {task.get('due')})" if task.get('due') else ""
                md.append(f"- 🔴 **{task.get('task')}**{due}")
            md.append("")

        other_tasks = output_data.get("assignments_for_others", [])
        if other_tasks:
            md.append("### 📋 Assigned to Others")
            for task in other_tasks:
                md.append(f"- **{task.get('owner')}**: {task.get('task')}")
            md.append("")

        next_step = output_data.get("what_to_do_next", "")
        if next_step:
            md.append(f"### 🚀 What To Do Next\n> {next_step}\n")

    # 4. Ad-Hoc / General
    else:
        answer = output_data.get("answer", "")
        md.append(f"## 💡 Verified Agent Response\n\n{answer}\n")
        claims = output_data.get("claims", [])
        if claims:
            md.append("### 📑 Evidence Citations")
            for c in claims:
                cites = ", ".join(f"`{cid}`" for cid in c.get("evidence_ids", [])) or "—"
                md.append(f"- **Claim:** {c.get('assertion')} *(Evidence: {cites})*")
            md.append("")

    # Raw JSON collapsible section
    md.append("\n<details><summary>🔍 View Verified Raw JSON Payload</summary>\n\n```json\n" + json.dumps(output_data, indent=2) + "\n```\n</details>")
    return "\n".join(md)


if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="Omnex Production Agent Harness API",
        description="Autonomous AI Agent Harness powered by LangGraph, Supabase, Qdrant & Gemini.",
        version="3.0.0"
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
        session_id: Optional[str] = "default"

    class QueryResponse(BaseModel):
        agent_role: str
        response: str
        latency_seconds: float
        status: str = "success"
        trace_id: str = ""
        session_id: str = "default"
        llm_provider: str = "Google Gemini (gemini-2.5-flash) & Qdrant"
        excel_download_url: Optional[str] = None

    @app.get("/health")
    def health_check():
        return {
            "status": "healthy",
            "service": "Omnex Production Agent Harness v3.0 (LangGraph Dual-Loop)",
            "capabilities": capability_registry.list_names()
        }

    def execute_harness_query(task: str, capability: Optional[str] = None, session_id: str = "default") -> QueryResponse:
        t0 = time.time()
        try:
            result = run_agent(task=task, capability=capability, session_id=session_id)
            latency = round(time.time() - t0, 3)
            cap_used = result.get("capability", "ad_hoc")
            output_obj = result.get("output")
            formatted_md = format_output_to_markdown(output_obj, cap_used) if output_obj else f"Status: {result.get('status')}\nError: {result.get('error')}"

            # Check if any Excel deliverable was generated today
            deliverables_dir = Path(parent_dir) / "deliverables"
            excel_url = None
            if deliverables_dir.exists():
                excel_files = sorted(deliverables_dir.glob("*.xlsx"), key=os.path.getmtime, reverse=True)
                if excel_files:
                    excel_url = f"/api/v1/deliverables/{excel_files[0].name}"

            return QueryResponse(
                agent_role=cap_used,
                response=formatted_md,
                latency_seconds=latency,
                status=result.get("status", "SUCCESS"),
                trace_id=result.get("trace_id", ""),
                session_id=session_id,
                llm_provider="Google Gemini (gemini-2.5-flash) & Qdrant",
                excel_download_url=excel_url
            )
        except Exception as e:
            latency = round(time.time() - t0, 3)
            return QueryResponse(
                agent_role="error",
                response=f"### ❌ Agent Harness Execution Error\n`{str(e)}`",
                latency_seconds=latency,
                status="ERROR",
                trace_id="",
                session_id=session_id
            )

    @app.post("/api/v1/query", response_model=QueryResponse)
    def dispatch_query(req: QueryRequest, x_user_id: Optional[str] = Header("USR-OWNER-01")):
        """Auto-Intent Capability Router."""
        task = req.prompt
        if req.target_member and req.target_member.lower() not in task.lower():
            task = f"{task} (Focus on {req.target_member})"
        return execute_harness_query(task=task, capability=None, session_id=req.session_id or x_user_id)

    @app.post("/api/v1/manager", response_model=QueryResponse)
    def manager_endpoint(req: QueryRequest, x_user_id: Optional[str] = Header("USR-OWNER-01")):
        return execute_harness_query(task=req.prompt, capability="manager_rollup", session_id=req.session_id or x_user_id)

    @app.post("/api/v1/mentor", response_model=QueryResponse)
    def mentor_endpoint(req: QueryRequest, x_user_id: Optional[str] = Header("USR-OWNER-01")):
        return execute_harness_query(task=req.prompt, capability="mentor_assessment", session_id=req.session_id or x_user_id)

    @app.post("/api/v1/teammate", response_model=QueryResponse)
    def teammate_endpoint(req: QueryRequest, x_user_id: Optional[str] = Header("USR-OWNER-01")):
        return execute_harness_query(task=req.prompt, capability="team_catchup", session_id=req.session_id or x_user_id)

    @app.get("/api/v1/deliverables/{filename}")
    def download_deliverable(filename: str):
        """Allows direct download of generated Excel workbooks and reports."""
        file_path = Path(parent_dir) / "deliverables" / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Deliverable file not found.")
        return FileResponse(path=str(file_path), filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    @app.post("/api/v1/rollup/export")
    def export_rollup_endpoint():
        """Generates a multi-tab Daily Rollup Excel workbook and saves to Google Drive/local directory."""
        try:
            from daily_excel_generator import generate_daily_rollup_excel
            file_path = generate_daily_rollup_excel()
            file_name = Path(file_path).name
            return {"status": "success", "file_path": file_path, "download_url": f"/api/v1/deliverables/{file_name}"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Mount static assets for the Web Dashboard
    static_dir = Path(parent_dir) / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def start_server(port: int = 8080):
    if FASTAPI_AVAILABLE:
        import uvicorn
        print("=" * 70)
        print("🚀 OMNEX PRODUCTION AGENT HARNESS SERVER")
        print("=" * 70)
        print(f"  • Web Dashboard:  http://127.0.0.1:{port}")
        print(f"  • REST API:       http://127.0.0.1:{port}/api/v1/query")
        print("=" * 70 + "\n")
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    else:
        print("Error: fastapi / uvicorn not installed.")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    start_server(port=port)




