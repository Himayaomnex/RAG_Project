# Omnex Training-Program Multi-Agent Intelligence & RAG System
## Complete Project Overview & Presentation Context for Claude

---

## 1. Executive Summary

This project is an **enterprise-grade, multi-agent RAG intelligence platform** developed for Omnex to monitor, assess, and synthesize progress across an engineering training program.

The system synthesizes two core data streams:
1. **Verbatim Dialogue (Unstructured Transcripts)**: Extracted from Teams meeting transcripts and indexed into **Qdrant Cloud** vector collections.
2. **Structured Facts (PostgreSQL Knowledge Base)**: Extracted into a relational **Supabase PostgreSQL** database (`kb` schema) capturing tasks, concept demonstrations, mentor QA, and architectural decisions.

The platform provides both an **on-demand conversational AI agent harness** (powered by LangGraph and Gemini 2.5) and an **autonomous 24/7 background cron daemon** that compiles daily multi-tab Excel rollups and synchronizes them directly to Google Drive.

---

## 2. Major Architectural Transformation: Before vs. Now

### ❌ What Was Replaced (The Legacy System)
* **Three Agent Silos**: Three isolated sub-agents (`agents/manager`, `agents/mentor`, `agents/team`), each having redundant, duplicating logic.
* **Brittle Router Agent**: A `router.py` script that used hardcoded keyword lists and regex heuristics to guess which agent to trigger.
* **Lack of Output Guarantees**: No verification loops, leading to potential hallucinated citations or unverified assertions.

### ✅ What Exists Now (The First-Principles LangGraph Harness)
* **Single Unified Dual-Loop Agent**: Replaced the 3 sub-agents with a single, highly extensible LangGraph StateGraph (`harness/graph.py`).
  * **Inner Loop (Planning & Execution)**: The agent autonomously chooses from **21 registered tools**, inspects token budgets, and retrieves evidence until satisfied.
  * **Outer Loop (Verification & Repair)**: Enforces strict Pydantic contract schemas and deterministic verification rules (V1–V6). If any hallucination or citation error is detected, the **Repair Node** sends the violation back to the LLM for automated self-correction before returning to the user.
* **Direct Capability Classification (No Router)**: Zero routing agent. Queries are dynamically matched directly to **Capability Contracts** defined in Markdown (`capabilities/*.md`).

---

## 3. Team Integrations & Microservice Architecture

The project acts as the central intelligence hub consuming services built by team members:

```
                          ┌────────────────────────────────────────────────────────┐
                          │         LangGraph Dual-Loop Agent Harness              │
                          │   (harness/graph.py - Planner, Composer, Verifier)     │
                          └───────▲────────────────────────▲───────────────▲───────┘
                                  │                        │               │
            HTTP POST /retrieve   │          psycopg (SQL) │               │ MCP Protocol
                                  │                        │               │
        ┌─────────────────────────┴─────────┐  ┌───────────┴─────────────┐ ┌┴──────────────────────────┐
        │ Dakshinya's Retrieval Microservice│  │ Ganesh's Knowledge Base │ │ GitHub MCP Client         │
        │ - FastAPI server (Port 8000)      │  │ - Supabase PostgreSQL   │ │ - Reads live repo code    │
        │ - Qdrant Cloud vector search      │  │ - kb_readonly connection│ │   from Himayaomnex/       │
        │ - 4 strategies (exp1 to exp4)     │  │ - 9 structured SQL views│ │   RAG_Project via Model   │
        │ - BGE reranker integration        │  │   (tasks, feedback, QA) │ │   Context Protocol        │
        └───────────────────────────────────┘  └─────────────────────────┘ └───────────────────────────┘
```

### 1. Dakshinya's Retrieval Microservice (System 2 RAG)
* **Interface**: Dedicated HTTP client ([`agents/shared/retrieval_client.py`](file:///c:/Users/Omnex/RAG_COMBINED/agents/shared/retrieval_client.py)) calling `POST http://127.0.0.1:8000/retrieve`.
* **Collection**: Targets `teams_dense_collection_normalized` in Qdrant Cloud.
* **4 Retrieval Strategies (Passed dynamically by query intent)**:
  * `exp1` (Precision-First): Scroll + Cross-Encoder Reranker for specific claims, named persons, or known dates.
  * `exp2` (Completeness-First): Expanded scroll for broad sweeps across a concept.
  * `exp3` (Document-Balanced): ~1 chunk per session for cross-program longitudinal coverage.
  * `exp4` (Full Corpus): Single-pass whole-corpus search for heavy questions.

### 2. Ganesh's Knowledge Base (Supabase PostgreSQL)
* **Interface**: Read-only PostgreSQL interface ([`agents/shared/kb_client.py`](file:///c:/Users/Omnex/RAG_COMBINED/agents/shared/kb_client.py)) connecting via `kb_readonly` role.
* **Exposed Views**:
  * `kb.v_person_state`: Aggregated progress metrics (assignments open/delivered, concepts confused/demonstrated, feedback count).
  * `kb.v_assignments_current`: Live deliverables, deadlines, and delivery statuses.
  * `kb.v_concepts`: Trainee understanding categorized by cognitive state (`confused`, `partial`, `demonstrated`).
  * `kb.v_decisions`: Architectural decisions with owners, rationale, and session dates.
  * `kb.v_feedback`: Verbatim mentor feedback items with sentiment classification.
  * `kb.v_qa`: Session question-and-answer exchanges with accuracy scoring.
  * `kb.v_digests`: Per-session meeting summaries and trainee delta JSONB.

### 3. Live GitHub MCP Integration (Code-Reading Proof of Work)
* **Interface**: Model Context Protocol client ([`harness/tools/mcp.py`](file:///c:/Users/Omnex/RAG_COMBINED/harness/tools/mcp.py)).
* **Tools**:
  * `github_read_file`: Reads verbatim source code files directly from the GitHub repository (`Himayaomnex/RAG_Project`) over MCP.
  * `github_search_code`: Searches repository commits, PRs, and code files to verify whether student technical claims match live implementations.

---

## 4. Capability Contracts & Dynamic Zero-Hardcoding Inference

Instead of hardcoded routing logic, capabilities are defined in Markdown specification files ([`capabilities/*.md`](file:///c:/Users/Omnex/RAG_COMBINED/capabilities/)):

| Capability | Target Consumer | Purpose & Pydantic Schema | Verification Rules |
| :--- | :--- | :--- | :--- |
| **`manager_rollup`** | Executive Manager | High-level 60-second summary: blockers, interventions needed, decisions, and completed vs in-progress tasks. | V1 (Citations), V2 (Delivered proof), V3 (Agreed resolution), V4 (Valid person names), V5 (Coverage note). |
| **`mentor_assessment`** | Technical Mentor | Trainee progression, 1–10 rubric scores across 4 dimensions, recurring misconceptions, next focus areas. | V1 (Citations), V2/V3 (1-10 range & proof), V4 (**Taught != Understood** demonstration rule), V5/V6 (Multi-session citations). |
| **`team_catchup`** | Trainee | Briefing for missed sessions: what happened, technical topics, decisions, and personal action items. | V1 (Citations), V2 (Date match), V3 (Personal task filter), V4 (What to do next). |
| **`ad_hoc`** | Anyone | Freeform factual answers, specific quotes, or custom questions outside predefined schemas. | V1 (Citations), V2 (Every assertion in claims list), V3 (Coverage note on truncation). |

### Zero-Hardcoding Classification Engine ([`harness/capabilities/loader.py`](file:///c:/Users/Omnex/RAG_COMBINED/harness/capabilities/loader.py))
* **100% Dynamic Context**: Dynamically extracts `Consumer`, `Purpose`, `Inputs`, `Tool hints`, and `When to choose` from the `.md` files at runtime.
* **Deterministic LLM Inference**: Queries `gemini-2.5-flash` at `temperature=0.0` in strict JSON mode.
* **In-Memory Session Cache**: Caches resolved queries in `_infer_cache` so identical repeat queries resolve in **0ms**.
* **Zero Manual Flags**: Running `python run_agent_cli.py "<query>"` automatically determines the capability, sets the budget, and formats the verified schema.

---

## 5. Tool Action Space & Composite Harness Skills

The agent operates in a typed action space of **21 registered tools**:

### Composite Harness Skills (Multi-Call Recipes)
In [`harness/skills/__init__.py`](file:///c:/Users/Omnex/RAG_COMBINED/harness/skills/__init__.py), complex recurring workflows are packaged as single composite tools:
1. **`assess_person(person, period)`**: In a single autonomous tool turn, it gathers:
   - Concepts (`get_concepts`)
   - QA performance (`get_qa_events`)
   - Mentor feedback (`get_feedback`)
   - Current tasks (`get_assignments`)
   - Supporting transcript quotes (`search_transcripts`)
2. **`catch_up(date, person)`**: Bundles session digest, date-specific assignments, decisions, and verbatim dialogue in one step.
3. **`summarize_period(period_start, period_end, person)`**: Pulls cohort deliverables, blockers, and decisions over a date window.

---

## 6. Autonomous Background Daemon & Excel Automation

### 1. Multi-Tab Master Excel Workbook ([`daily_excel_generator.py`](file:///c:/Users/Omnex/RAG_COMBINED/daily_excel_generator.py))
Generates a styled, corporate-ready workbook with 5 dedicated sheets:
* **Sheet 1: Executive Summary**: High-level KPI scorecard for the entire cohort:
  * *Live Database State:* **84 Open Assignments | 13 Delivered | 4 Late | 38 Confused Concepts | 110 Mentor Feedback Items**
* **Sheet 2: Deliverables & Tasks**: Detailed task register with ownership and status.
* **Sheet 3: Concept Gaps & Learning**: In-depth breakdown of confused vs demonstrated ideas.
* **Sheet 4: Decisions Register**: Architectural decisions with owners and rationale.
* **Sheet 5: Mentor Feedback & QA**: All 110 verbatim feedback points and technical QA.
* **Persistence**: Updates a single persistent file ([`deliverables/training_master_rollup.xlsx`](file:///c:/Users/Omnex/RAG_COMBINED/deliverables/training_master_rollup.xlsx)) while saving dated snapshots into `deliverables/archive/`.

### 2. Autonomous Background Daemon ([`daily_pipeline_cron.py`](file:///c:/Users/Omnex/RAG_COMBINED/daily_pipeline_cron.py))
* **Folder Watcher**: Actively scans the `Downloads` directory for newly downloaded `.docx` meeting transcripts and auto-ingests them within 15 seconds.
* **5:00 PM Daily Schedule**: Automatically executes every day at **17:00 IST**, pulls the latest Supabase facts, updates the master workbook, and uploads it to Google Drive.
* **Silent Windows Startup**: Registered via `register_startup_task.ps1` and `OmnexAgentDaemon.vbs` in the Windows Startup folder (`shell:startup`)—starts automatically with Windows in a hidden background window (`WindowStyle 0`) with **zero popups and zero command-line windows**.

---

## 7. Slide-by-Slide Presentation Content (Weeks 5, 6 & 7)

### **WEEK 5: 17/08/2026 to 21/08/2026**

#### **Slide 1 — Day 1: Monday (17/08/2026)**
* **Ganesh's Supabase PostgreSQL Integration**: Connected to Ganesh's hosted Supabase Knowledge Base via read-only credentials (`kb_readonly`), querying structured views for deterministic task counts, decisions, and concepts.
* **Dakshinya's HTTP Retrieval Client**: Built a dedicated HTTP client in `agents/shared/retrieval_client.py` targeting Dakshinya's FastAPI endpoint (`POST /retrieve`) against the `teams_dense_collection_normalized` vector store.
* **Unified Tool Registry Creation**: Established a centralized action space registering both SQL database calls and semantic vector queries as typed, budget-aware agent tools.
* **Multi-Tab Daily Excel Prototype**: Engineered an initial OpenPyXL workbook script generating styled tables for cohort progress, assignments, and architectural decisions.
* **Cross-Service Health Auditing**: Implemented connectivity health checks verifying real-time availability of Dakshinya's API on port 8000 alongside PostgreSQL connection pooling.

#### **Slide 2 — Day 2: Tuesday (18/08/2026)**
* **GitHub MCP Live Code Reader Integration**: Built `github_mcp_client.py` over Model Context Protocol (MCP) to read live source code and diffs directly from `Himayaomnex/RAG_Project` for technical verification.
* **Query Normalization & XML Sanitization**: Implemented prompt cleaning in the retrieval client to strip conversational XML wrappers and avoid polluting vector embeddings.
* **Cross-Source Evidence Modeling**: Standardized all retrieved KB records and vector chunks into immutable `EvidenceItem` objects with unique, non-inventable citation IDs.
* **Elimination of Hardcoded Codebase Values**: Refactored credential and connection strings into secure `.env` variables following mentor review feedback on code quality.
* **Automated Downloads Folder Watcher**: Built a file-system listener watching for newly downloaded Teams meeting transcript `.docx` files for immediate background processing.

#### **Slide 3 — Day 3: Wednesday (19/08/2026)**
* **Four Retrieval Strategies Exposure**: Configured Dakshinya's HTTP parameters to support all 4 pipeline strategies (`exp1` precision scroll, `exp2` broad sweep, `exp3` document-balanced, and `exp4` full corpus).
* **Cross-Encoder Reranking Integration**: Enabled server-side reranking (`use_reranker=True`) over the HTTP wire to maximize relevance scoring on precision-first queries.
* **Executive Summary Sheet Styling**: Designed corporate Navy headers, zebra striping, and dynamic `=SUM()` formula calculations for the daily Excel KPI scorecard.
* **Date Normalization Engine**: Engineered natural language date parsing to translate informal references ("July 14", "last week") into ISO format for database filtering.
* **Subprocess Isolation**: Decoupled local retrieval invocations to prevent external API latency from blocking the main orchestrator thread.

#### **Slide 4 — Day 4: Thursday (20/08/2026)**
* **Dynamic Active Trainee Discovery**: Replaced static name lists with live API calls to `/filters/metadata` to dynamically resolve active cohort speaker names.
* **GitHub MCP Repository Search**: Added `github_search_code` over MCP to query code commits, PRs, and issues when queries require validating code deliverables against student claims.
* **Master Excel Persistence Architecture**: Re-architected workbook saving to maintain a persistent `training_master_rollup.xlsx` alongside dated backups in an `archive/` directory.
* **Citation Fabrications Safeguard**: Formulated initial verification logic flagging any LLM claim that references a chunk ID not returned by active tools.
* **Google Drive Cloud Sync Bridge**: Added direct Google Drive API upload hooks ensuring refreshed daily spreadsheets automatically sync to the shared drive.

#### **Slide 5 — Day 5: Friday (21/08/2026)**
* **First-Principles Architecture Assessment**: Audited the legacy 3-agent silo system, identifying brittle keyword routing and lack of output guarantees.
* **Capability Contract Specification**: Began drafting markdown specification contracts (`capabilities/*.md`) defining explicit consumer requirements and Pydantic output schemas.
* **Token Budget Tracking Prototype**: Designed budget tracking objects to measure input/output token consumption per tool call against strict request limits.
* **Decisions Register Automation**: Integrated SQL queries extracting architectural decisions, ownership attribution, and rationale into Sheet 4 of the master workbook.
* **End-of-Week Cohort State Snapshot**: Successfully generated and synced the cumulative Week 5 rollup workbook summarizing deliverables and feedback metrics.

---

### **WEEK 6: 24/08/2026 to 28/08/2026**

#### **Slide 6 — Day 6: Monday (24/08/2026)**
* **Decommissioning Obsolete Router**: Permanently removed `router.py` and hardcoded intent-classification keyword dictionaries in favor of direct capability contract execution.
* **Dual-Loop LangGraph Harness**: Built `harness/graph.py` featuring an inner planning/tool-execution cycle and an outer schema composition/verification cycle.
* **Pydantic Contract Schemas**: Implemented strict typed schemas (`ManagerRollupOutput`, `MentorAssessmentOutput`, `TeamCatchupOutput`, and `AdHocOutput`).
* **Dynamic Markdown Capability Loader**: Built `harness/capabilities/loader.py` to parse Consumer, Purpose, Inputs, and Rules directly from disk at runtime.
* **Deterministic Tool Action Space**: Registered 21 discrete tools spanning Supabase SQL views, vector transcript search, GitHub MCP, and composite skills into the harness.

#### **Slide 7 — Day 7: Tuesday (25/08/2026)**
* **Evidence Assembler & Priority Truncation**: Created `harness/evidence_store.py` to collect, deduplicate, and score evidence, cleanly dropping low-ranked items when budgets exhaust.
* **Rule Engine Implementation**: Coded verification rule classes (`V1` to `V6`) enforcing citation validity, absence of invented claims, and valid person names.
* **The Cognitive Ladder in Verification**: Implemented mentor rule V4 enforcing that *"Taught is not Understood"*—requiring demonstration evidence for high rubric scores.
* **Repair Node with Violation Feedback**: Built the LangGraph repair cycle (`repair_node`) that feeds rule violations directly back to the model for automated self-correction.
* **Live Supabase View Testing**: Verified deterministic SQL retrieval for open vs delivered assignments across all active cohort members.

#### **Slide 8 — Day 8: Wednesday (26/08/2026) — [DEDICATED: TOOL CALLS & CAPABILITY CLASSIFICATION]**
*(Include screenshot of terminal tool execution and GitHub MCP live code reading here)*
* **21 Typed Tools & Zero-Router Direct Classification**: Eliminated the router layer; queries are matched directly to capabilities (`capabilities/*.md`), giving the agent a uniform action space of 21 registered tools.
* **Composite Harness Skills (Recipes)**: Built composite tools (`assess_person`, `catch_up`, `summarize_period`) that execute multi-step database and transcript recipes in a single autonomous tool turn.
* **Live GitHub MCP Code Reading**: The agent executes `github_read_file` to fetch verbatim code directly from GitHub repositories over Model Context Protocol to prove whether code was actually built.
* **Dual-Source Evidence Orchestration**: Tool calls seamlessly balance structured PostgreSQL facts from Supabase with verbatim quotes from Dakshinya's HTTP retrieval API (`POST /retrieve`).
* **Hard Tool & Budget Enforcers**: The planner strictly monitors `calls_remaining` and `budget_remaining` per turn, terminating retrieval when sufficient evidence is assembled.

#### **Slide 9 — Day 9: Thursday (27/08/2026)**
* **Dynamic Capability Inference**: Engineered `infer_capability()` to automatically map natural language user queries to the correct capability spec with zero manual `-c` flags.
* **Pure Specification Prompts**: Eliminated all hardcoded persona names and rules from the classifier prompt, dynamically deriving context from the mentor's `.md` files.
* **In-Memory Query Routing Cache**: Implemented session-level query caching ensuring identical repeat queries resolve capabilities instantly in 0ms.
* **Automated Routing Test Suite**: Created `tests/test_routing.py` with 10 comprehensive queries covering all capabilities, achieving a 100% pass rate.
* **Transcript Normalizer Integration**: Documented the data-engineering pipeline preparing speaker-attributed meeting transcripts for downstream vector indexing.

#### **Slide 10 — Day 10: Friday (28/08/2026)**
* **Codebase Refactoring & Cleanup**: Deleted obsolete legacy files (`router.py`, root `graph.py`, `main.py`, `agent_keywords.json`) to establish a clean repository.
* **Untracked Trace Cache Sanitization**: Purged hundreds of temporary runtime telemetry files (`logs/traces/trc-*.json`) from Git to preserve repository hygiene.
* **Git Repository Synchronization**: Pushed the unified First-Principles LangGraph harness to GitHub repository (`Himayaomnex/RAG_Project`) on `main`.
* **Master Workbook Visual Verification**: Validated that Sheet 1 Executive Summary displays verified Supabase numbers (84 assignments open, 13 delivered, 110 feedback items).
* **Week 6 Validation Reporting**: Documented the architectural shift from siloed sub-agents to a single unified harness in `deliverables/validation_report.md`.

---

### **WEEK 7: 31/08/2026 to 03/09/2026**

#### **Slide 11 — Day 11: Monday (31/08/2026)**
* **Zero-Permission Windows Daemon**: Created `register_startup_task.ps1` and `OmnexAgentDaemon.vbs` to auto-launch the agent on Windows login without admin rights.
* **Headless Background Execution**: Guarded stdout/stderr streams to allow silent execution under `pythonw.exe` without terminal popups or interruption.
* **Unified 5:00 PM Cron Pipeline**: Configured `daily_pipeline_cron.py` to automatically trigger daily at 17:00 IST, regenerate the master workbook, and push to Drive.
* **Windows Console Encoding Fix**: Resolved `charmap` Unicode errors on Windows cp1252 consoles by standardizing terminal outputs to clean ASCII indicators.
* **Continuous File-Drop Automation**: Verified that dropping a new transcript into `Downloads/` triggers ingestion and updates the knowledge base within 15 seconds.

#### **Slide 12 — Day 12: Tuesday (01/09/2026)**
* **Quotation Sanitization in Interactive CLI**: Upgraded `run_agent_cli.py` to automatically strip quotation marks from user inputs, preventing query classification errors.
* **Domain Priority Boundary Calibration**: Refined classification prompts to accurately separate cross-team managerial rollups from single-person ad-hoc lookups.
* **End-to-End Decision Extraction Test**: Executed full live queries against Supabase, successfully extracting 33 architectural decisions into verified JSON.
* **Interactive vs Command-Line Parity**: Ensured both direct CLI arguments (`python run_agent_cli.py "<query>"`) and interactive prompts behave identically.
* **Git Commit & Regression Testing**: Re-ran the complete test suite (`test_step1.py`, `test_step3.py`, `test_routing.py`) with 100% success across all modules.

#### **Slide 13 — Day 13: Wednesday / Thursday (02/09/2026 & 03/09/2026)**
* **Deliverables Folder Hygiene**: Removed obsolete legacy rollups (`daily_rollups/`), preserving strictly the Master Workbook and clean `archive/` backups.
* **Gitignore Optimization**: Configured `.gitignore` to exclude temporary Microsoft Excel lock files (`~$*`) and historical archive snapshots from Git tracking.
* **Mentor Skill Specification Alignment**: Refined `agents/mentor/skills/trainee_assessment.md` ensuring full consistency between written specs and live harness tools.
* **Production Health Validation**: Confirmed continuous operation of Dakshinya's Retrieval API (PID 12480) and the autonomous Omnex daemon (PID 22276).
* **Final Presentation & GitHub Push**: Synchronized all code, specifications, and walkthrough documentation to GitHub `origin/main` with a clean working tree.
