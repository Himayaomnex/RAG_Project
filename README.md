# 🚀 Enterprise Teams Transcript RAG & Custom MCP Server

An enterprise-grade Retrieval-Augmented Generation (RAG) system and Model Context Protocol (MCP) server designed to parse, index, search, and synthesize Microsoft Teams meeting transcripts with **sub-millisecond persistent vector caching** and **role-based secret token authentication**.

---

## 🎯 Architecture Overview

```text
 Microsoft Teams Transcripts (.docx)
                 │
  [Speaker-Turn & Page XML Chunker]  <-- 300-word Monologue Safeguard
                 │
  [SHA-256 Hashing & emb_cache]      <-- Sub-millisecond $0 Startup Vector Caching
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
 [Qdrant Vector DB]   [SQLite Relational DB]
 (Cosine Semantic)    (Leaderboards & SQL)
    │                         │
    └────────────┬────────────┘
                 ▼
  [Qdrant Scroll API + Domain Reranker]
                 │ (5,000 Char Context Cap)
                 ▼
     [Groq API: Llama 3.3 LLM]
                 │
  ┌──────────────┴──────────────┐
  ▼                             ▼
[Interactive RAG Demo]   [Custom FastMCP Server]
(run_demo.bat)           (mcp_server.py + mcp_config.json)
```

---

## 📦 Setup & Installation

### 1. Prerequisites
* Python 3.10+
* Groq API Key (Set in environment variable `GROQ_API_KEY`)

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 🚀 Execution & Usage Guide

### 1. Run Interactive RAG Demonstration
```powershell
.\run_demo.bat
```

### 2. Run Custom Enterprise RAG MCP Server
```powershell
python mcp_server.py
```

### 3. Generate Measured Cache Savings Report
```powershell
python cache_reuse_report.py
```

### 4. Run Automatic Downloads Folder Watcher Daemon
```powershell
python auto_folder_watcher.py
```

---

## 🔐 MCP Server Tools Exposed (`mcp_server.py`)

1. `search_transcripts(auth_token, query)` — Vector search over transcript chunks.
2. `get_meeting(auth_token, date)` — Retrieves transcript context for a specific date.
3. `get_speaker_history(auth_token, name)` — Scrolled dialogue history for a speaker.
4. `summarize_meeting(auth_token, date)` — Generates an AI meeting summary.
5. `list_meetings(auth_token, month)` — Lists available meeting dates.
6. `get_action_items(auth_token)` — Extracts action items (`setup.py`, `cron job`).

---

## 📊 Performance & Optimization Summary
* **Startup Speed:** Sub-millisecond (5.3 ms) vector loading via `emb_cache`.
* **Token Safety:** 5,000-character context cap prevents `HTTP 413` API rate limits.
* **Monologue Guard:** Bounded at 300 words max per chunk to maintain focused vector quality.
