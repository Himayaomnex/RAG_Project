#  Multi-Agent Teams Transcript RAG System

An enterprise-grade, privacy-first Retrieval-Augmented Generation (RAG) system and Model Context Protocol (MCP) server designed to parse, index, search, and synthesize Microsoft Teams meeting transcripts (`.docx`).

---

## System Architecture

```text
Authenticated User
        │
        ▼
FastAPI REST Server / Streamlit Web UI
        │
        ▼
User Scoping (Scope Before Search)
        │
        ▼
Direct Metadata Payload Filtering
        │
        ▼
Central Multi-Agent Router (router.py)
        │
 ┌──────┼────────┐
 │      │        │
 ▼      ▼        ▼
Manager Agent    Mentor Agent    Teammates Agent
(Project Mgmt)  (Evaluation)    (Technical Assist)
        │
        ▼
Shared Skills (Search • Summary • Code Review)
        │
        ▼
Training Knowledge Base (.docx Transcripts)
        │
        ▼
Qdrant Vector Database (384-d Cosine Vectors)
        │
        ▼
Groq Llama 3.3 LLM Engine
        │
        ▼
Grounded Answer with Source Citations
```

---

## Component Architecture & Agent Roles

1. **Manager Agent (`agents/manager_agent.py`):**
   * Serves Manager Role (Iyappan Sir).
   * Aggregates weekly team deliverables, progress milestones, and project action items.

2. **Mentor Agent (`agents/mentor_agent.py`):**
   * Serves Mentor Role (Siddharth).
   * Generates technical reading topic assignments, key discussion summaries, and technical quizzes.

3. **Teammates Agent (`agents/teammates_agent.py`):**
   * Serves Teammate Roles (Himaya, Ganesh, Dakshinya).
   * Retrieves raw spoken transcript quotes and personal technical accomplishment summaries.

---

## Technical Specifications & Features

* **Sub-4ms Vector Lookup:** Persistent SHA-256 embedding cache (`emb_cache`) skips re-computation for instant vector lookups.
* **Multi-Model LLM Failover:** Automatic fallback pipeline (`llama-3.3-70b-versatile` → `llama-3.1-8b-instant` → `gemma2-9b-it`).
* **User Scoping:** Queries and vectors are scoped strictly to caller identity (`user_id` / `speaker`) prior to retrieval.
* **Grounding & Verification:** Every output is grounded in retrieved transcript content with exact source citations (`[Date | Page | Speaker]`).

---

## Quick Start & Execution Guide

### 1. Web Application UI
```powershell
streamlit run app.py
```

### 2. REST API Server
```powershell
uvicorn api_server:app --reload --port 8000
```

### 3. Interactive CLI Demo
```powershell
python run_multi_agent_demo.py
```

### 4. Background Transcript Watcher
```powershell
python auto_folder_watcher.py
```
