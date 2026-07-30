# 🚀 Enterprise Multi-Agent Teams Transcript RAG System

An enterprise-grade, privacy-first **Multi-Agent Retrieval-Augmented Generation (RAG)** system and Model Context Protocol (MCP) server designed to parse, index, search, and synthesize Microsoft Teams meeting transcripts formatted in Word (`.docx`).

Featuring **Scope Before Search Identity Access Control**, **Direct Metadata Payload Filtering**, **Sub-4ms Persistent Vector Caching**, and **Multi-Model Groq LLM Failover**.

---

## 🎯 Production Runtime Workflow

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
Direct Metadata Payload Filtering (Speaker & Date Payloads)
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
Groq Llama 3.3 LLM (Multi-Model Failover)
        │
        ▼
Grounded Answer + Citations [Date | Page | Speaker]
```

---

## 🏛️ Multi-Agent Architecture & Roles

1. 👔 **Manager Agent (`agents/manager_agent.py`):**
   * Serves **Iyappan Sir (Manager)**.
   * Generates Executive Status Summaries, Team Milestones, and Action Item breakdowns.

2. 🎓 **Mentor Agent (`agents/mentor_agent.py`):**
   * Serves **Siddharth (Mentor)**.
   * Generates Technical Reading Topics, Spoken Discussion Summaries, and Technical Quiz Questions.

3. 👤 **Teammates Agent (`agents/teammates_agent.py`):**
   * Serves **Himaya Perumal**, **Ganesh Krishna**, and **Dakshinya Nachimuthu**.
   * Fetches exact Spoken Transcript Quotes (`[Date | Page | Speaker]`) and Personal Technical Accomplishments.

---

## ⚡ Technical Features & Performance

* **Sub-4ms Vector Lookup:** Persistent SHA-256 embedding cache (`emb_cache`) skips re-computation for instant vector lookups at $0.00 cost.
* **Multi-Model Groq Failover:** Automatically switches from `llama-3.3-70b-versatile` to `llama-3.1-8b-instant` and `gemma2-9b-it` when rate limits occur.
* **Identity Isolation (User Scoping):** Queries and vectors are scoped strictly to the caller's identity (`user_id` / `speaker`) before retrieval begins.
* **Zero Invention Guarantee:** If evidence is missing from retrieved transcript chunks, the system strictly outputs *"Information Not Available"*.

---

## 🚀 Execution Guide

```powershell
# 1. Run Main Streamlit Web Application (UI Dashboard)
streamlit run app.py

# 2. Run FastAPI REST Server
uvicorn api_server:app --reload --port 8000

# 3. Run Multi-Agent CLI Interactive Demo
python run_multi_agent_demo.py

# 4. Run Background Transcript Folder Watcher
python auto_folder_watcher.py
```

---

## 📄 Documentation & Reports
* 📁 **Master Word Report:** `SIDDHARTH_MOSCOW_MASTER_REPORT.docx` (Generated via `python generate_final_master_word_doc.py`)
* 🛠️ **FastMCP Server:** `mcp_server.py`
