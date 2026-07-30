# 🚀 Enterprise Multi-Agent Teams Transcript RAG System

An enterprise-grade, privacy-first **Multi-Agent Retrieval-Augmented Generation (RAG)** system and Model Context Protocol (MCP) server designed to parse, index, search, and synthesize Microsoft Teams meeting transcripts formatted in Word (`.docx`).

Featuring **Scope Before Search Identity Access Control**, **Simple Substring & Day Matching**, **Sub-4ms Persistent Vector Caching**, and **Multi-Model Groq Failover**.

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
Entity Normalization (Name • Date • References)
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
Shared Skills (Search • Summary • Normalization • Code Review)
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

1. 👔 **Manager Agent (Project Management):**
   * Serves **Iyappan Sir (Manager)**.
   * Generates Executive Status Summaries, Team Milestones, and Action Item breakdowns.

2. 🎓 **Mentor Agent (Evaluation & Feedback):**
   * Serves **Siddharth (Mentor)**.
   * Generates Technical Reading Topics, Spoken Discussion Summaries, and Technical Quiz Questions.

3. 👤 **Teammates Agent (Technical Assistance):**
   * Serves **Himaya Perumal**, **Ganesh Krishna**, and **Dakshinya Nachimuthu**.
   * Fetches exact Spoken Transcript Quotes (`[Date | Page | Speaker]`) and Personal Technical Accomplishments.

---

## 📊 Project Prioritization Framework (MoSCoW)

### 🔴 Must Have (Core Architecture)
* **Training Transcript Ingestion from Word Documents (.docx):** Primary input source parsing and indexing of Microsoft Teams meeting transcripts.
* **User Scoping (Scope Before Search):** Scope all queries, vectors, and responses strictly to caller identity (`user_id` / `speaker`) before retrieval.
* **Semantic Transcript Retrieval using Qdrant:** 2,843 384-dimensional vector chunks indexed with Cosine similarity search.
* **Persistent SHA-256 Embedding Cache (emb_cache):** Sub-4ms instant vector lookups at $0.00 cost (Implemented).
* **Grounded AI Responses with Proof:** Grounded answers generated strictly from retrieved transcript context.
* **Exact Source Citations:** Citing Date, Page, and Speaker `[Date | Page | Speaker]` with zero guessing.
* **FastAPI REST APIs & Agent Access:** Programmatic endpoints for multi-agent dispatching.

### 🟡 Should Have (Implemented Enhancements)
* **GitHub Repository Integration & Automatic Code Review:** Connecting directly to GitHub repositories for automatic code reviews so trainees focus on building rather than debugging.
* **Interactive Code Debugging & Guided Learning Assistant:** AI guidance explaining how trainees can debug code to foster learning through problem-solving.
* **Automatic Folder Watcher (`auto_folder_watcher.py`):** Background daemon automatically indexing new transcript files live.
* **Quick Preset Action Buttons:** Interactive buttons for Quiz Generation, Reading Topics, Action Items, and Spoken Quotes.

### 🟢 Could Have (Future Productivity Enhancements)
* Microsoft Teams live transcript ingestion via Graph API.
* Whisper-Based Speech-to-Text running locally on laptops.
* Live In-Meeting Real-Time Prompt Assistant (Teams / Slack).
* Export Evaluation Reports directly to Word/PDF.
* Visual Analytics Dashboard for team participation metrics.
* Qdrant Cloud Synchronization for remote team access.

---

## 💡 First Principles of Our RAG System

1. **Understand Meaning, Not Just Keywords:** The system uses 384-dimensional semantic vector search to understand the intent behind a query, even when users phrase it differently.
2. **Scope Before Search:** Every query is first scoped to the appropriate user, speaker, or meeting context before any retrieval begins to ensure privacy and relevance.
3. **Direct Metadata Filtering (Speaker & Date Payloads):** Rather than running pre-processing data transformation pipelines, the system leverages native Qdrant metadata payload filtering (`speaker` and `date` fields) combined with semantic vector search to resolve names and dates naturally during retrieval.
4. **No Guessing, Only Evidence:** Every response is grounded in retrieved transcript content with citations `[Date | Page | Speaker]`. If no evidence exists, the system returns *"Information Not Available"*.

---

## 🚀 Execution Guide

```powershell
# 1. Run Streamlit Dashboard
streamlit run app.py

# 2. Run FastAPI Server
uvicorn api_server:app --reload --port 8000

# 3. Run Multi-Agent CLI Demo
python run_multi_agent_demo.py

# 4. Generate Master Word Report
python generate_final_master_word_doc.py
```
* Download Master Word Report: `SIDDHARTH_MOSCOW_MASTER_REPORT.docx`
