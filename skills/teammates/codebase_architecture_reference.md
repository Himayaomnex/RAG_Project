# Codebase Architecture & Pipeline Technical Reference (Teammates Agent)

Supporting reference guide for `peer-technical-intelligence` skill.

## 1. Primary Workspace Modules

All technical peer Q&A must reference these local system files:

| File Name | Primary Role | Key Classes & Functions |
| :--- | :--- | :--- |
| [`pipeline.py`](file:///c:/Users/Omnex/RAG_COMBINED/pipeline.py) | **Knowledge Ingestion & Vector Storage** | `CachedEmbeddingModel`, `SemanticTranscriptParser`, `VectorDatabase`, `CustomMeetingReranker` |
| [`transcript_normalizer.py`](file:///c:/Users/Omnex/RAG_COMBINED/transcript_normalizer.py) | **Transcript Cleaning & Crosstalk Fixes** | `normalize_speaker_name()`, `clean_audio_artifacts()`, `reattribute_crosstalk_turn()` |
| [`llm_client.py`](file:///c:/Users/Omnex/RAG_COMBINED/llm_client.py) | **Multi-Provider LLM Orchestrator** | `generate_llm_response()`, `normalize_table_status_cells()`, `sanitize_markdown_table_pipes()` |
| [`prompt_builder.py`](file:///c:/Users/Omnex/RAG_COMBINED/prompt_builder.py) | **Modular Prompt Architecture** | `PromptBuilder`, `build_system_prompt()`, `build_user_prompt()` |
| [`router.py`](file:///c:/Users/Omnex/RAG_COMBINED/router.py) | **Dynamic Intent Routing Engine** | `route_query()`, `detect_agent_type()`, `resolve_target_trainee()` |
| [`api_server.py`](file:///c:/Users/Omnex/RAG_COMBINED/api_server.py) | **Production REST API Server** | `POST /api/v1/query`, `POST /api/v1/manager`, `POST /api/v1/mentor`, `POST /api/v1/teammates` |

---

## 2. Ingestion & Retrieval Flow Architecture

```
[Raw DOCX Transcripts] 
         │
         ▼
[transcript_normalizer.py] ── (Phonetic cleanup & Crosstalk reattribution)
         │
         ▼
[pipeline.py: Semantic Chunking] ── (Sentence boundaries + rolling overlap)
         │
         ▼
[sentence-transformers/all-MiniLM-L6-v2] ── (MD5 Embedding Caching)
         │
         ▼
[Qdrant Collection: teams_dense_collection] ── (384-dim dense vectors + payload metadata)
         │
         ▼
[CustomMeetingReranker] ── (Lexical Jaccard + Speaker Prior + Recency Boost)
         │
         ▼
[PromptBuilder & LLM Client] ── (Google Gemini Flash / Groq LLM Synthesis)
```
