---
name: meeting-transcript-analyzer
description: "You MUST use this skill whenever analyzing, retrieving, or extracting intelligence from MS Teams audio meeting transcripts. Implements the Pyramid Principle, SCQA framework, Delta tracking, and strict verbatim citation protocols across multi-agent workflows."
---

# Meeting Transcript Analyzer — Operational Skill Specification

Master operational intelligence skill for ingesting, indexing, analyzing, and synthesizing MS Teams audio transcripts of technical training sessions. Transforms unstructured conversation transcripts into grounded, structured, and auditable deliverables.

<HARD-GATE>
1. **ZERO UNGROUNDED SYNTHESIS**: Every factual assertion, score, task status, or technical evaluation MUST be supported by an exact verbatim citation quote with `[Date — Source Document — Page — Speaker]`.
2. **STRICT PIPE TABLE FORMAT**: When presenting structured intelligence, format the ENTIRE output inside a single, valid Markdown Pipe Table with header alignment rows (`| :--- | :--- |`).
3. **DYNAMIC EVIDENCE-BASED STATUS**: Deliverable status (Completed, In Progress, Blocked) must be derived dynamically from transcript evidence — never defaulted or assumed without verified spoken proof.
4. **FULL CHRONOLOGICAL TIMELINE**: Analysis must sweep across the full temporal scope of retrieved evidence, tracking baseline discussions through final wrap-up sessions.
5. **NO PROMPT LEAKAGE**: Never output internal reasoning, thinking tags (`<think>`), or markdown conversational preamble outside the requested analytical structure.
</HARD-GATE>

---

## Operational Modalities (Three Execution Paths)

Before initiating retrieval and synthesis, classify the request into one of the three operational paths:

- **Path 1: Full Corpus Map-Reduce Scan (Multi-Transcript Synthesis)**
  - *Scope*: System-wide overview queries (e.g. "What did the team accomplish across all sessions?", "What are the overall project milestones?").
  - *Execution*: Iterates across the complete chronological scope of the corpus, performs dense semantic retrieval and cross-encoder reranking, maps evidence into structured buckets, and reduces into balanced tables with grounded coverage across all team members.
- **Path 2: Targeted Trainee / Topic Drilldown (Deep Entity Analysis)**
  - *Scope*: Focused single-mentee or single-topic investigations.
  - *Execution*: Applies targeted speaker payload filtering and semantic query expansion, aggregates chronologically ordered evidence turns, and outputs detailed SCQA or task verification tables.
- **Path 3: Direct Dialogue Verification & Citation Audit (Verbatim Grounding)**
  - *Scope*: Exact quote lookups, decision dispute resolution, and crosstalk attribution audits.
  - *Execution*: Scans normalized transcript turns, re-attributes crosstalk turns, verifies verbatim quote strings, and provides exact timestamped citations.

---

## Anti-Patterns & Common Failure Modes

| Anti-Pattern / Failure Mode | Reality & Correct Operational Behavior |
| :--- | :--- |
| **"Assuming deliverable status without evidence"** | If a transcript shows active work or unresolved issues, mark `In Progress` or `Blocked`. Only mark `Completed` when verified by transcript proof. |
| **"Padded or forced row counts"** | Report what is genuinely supported in the transcripts. Quality and authenticity of citations take precedence over cosmetic balance. |
| **"Paraphrasing or fabricating quotes"** | Quotes must be exact character-level verbatim substrings from the transcripts. Never reconstruct or summarize quotes inside quotation marks. |
| **"Outputting unstructured conversational summaries"** | Executives and mentors require scannable, structured Markdown Pipe Tables. Do not output walls of text. |
| **"Table pipe shifting due to unescaped pipes in citations"** | All internal pipe characters (`\|`) inside quote strings must be sanitized using `sanitize_markdown_table_pipes()` to prevent breaking table alignment. |

---

## Operational Red Flags

| Red Flag / Warning Sign | Immediate Required Action |
| :--- | :--- |
| **Speaker Crosstalk Artifact** (e.g., Trainee credited with mentor's words) | Pass through `transcript_normalizer.reattribute_crosstalk_turn()` to split and assign turns accurately. |
| **Missing Verbatim Proof in Table Cell** | Trigger secondary Qdrant dense vector search specifically targeting the missing entity to retrieve exact textual evidence. |
| **Descriptive Ongoing Status Phrases** (e.g. *"In progress, results expected Monday"*) | Run through `normalize_table_status_cells()` to standardize table status syntax while preserving grounded progress state. |
| **Token Truncation on Large Tables** | Ensure `maxOutputTokens` is configured to `4096` to prevent multi-row tables with citations from cutting off mid-sentence. |

---

## Execution Lifecycle Checklist

1. **[Context & Corpus Retrieval]**: Query Qdrant vector database (`teams_dense_collection`) using `sentence-transformers/all-MiniLM-L6-v2` dense embeddings.
2. **[Semantic Reranking]**: Score retrieved candidates using `CustomMeetingReranker` (Lexical Jaccard + Speaker Prior + Recency Boost).
3. **[Speaker & Text Normalization]**: Standardize phonetic mishearings, clean audio artifacts (`[Music]`, `[Applause]`), and re-attribute crosstalk.
4. **[Evidence Grounding]**: Format retrieved context blocks with complete metadata `[Date — Source Document — Page — Speaker]`.
5. **[Multi-Provider LLM Synthesis]**: Route prompt to Google Gemini (`gemini-2.5-flash` / `gemini-2.5-pro`) with failover to Groq (`openai/gpt-oss-120b`).
6. **[Table Formatting & Pipe Sanitization]**: Clean reasoning tokens, sanitize pipes, ensure single header row, and format clean markdown pipe tables.
7. **[Final Verification]**: Ensure all table columns match the requested schema and all citations contain authentic verbatim dialogue.

---

## Process Flow (State Machine)

```mermaid
graph TD
    A["Raw User Query Received"] --> B{"Classify Query Intent"}
    B -->|"Executive Status / Decisions"| C["Manager Agent Workflow"]
    B -->|"Trainee Scoring / Pedagogy"| D["Mentor Agent Workflow"]
    B -->|"Codebase / Peer Q&A"| E["Teammates Agent Workflow"]

    C & D & E --> F["Qdrant Dense Vector Retrieval (Top-K)"]
    F --> G["Cross-Encoder Semantic Reranking & Recency Boost"]
    G --> H["Speaker Normalization & Crosstalk Reattribution"]
    H --> I["Multi-Provider LLM Synthesis (Gemini Flash / Pro)"]
    I --> J["Pipe Sanitization & Status Enforcement (normalize_table_status_cells)"]
    J --> K["Structured Markdown Pipe Table Response"]
```

---

## Analytical Frameworks Applied

### 1. The Pyramid Principle & MECE Accomplishments
- **Governing Thought**: A single, falsifiable executive summary sentence synthesizing the core state.
- **MECE Categories**: Mutually Exclusive, Collectively Exhaustive grouping of trainee work (Architecture, Data Pipelines, ML Models, Integrations).

### 2. SCQA Blocker Analysis
- **Situation**: Context and objective of the trainee's assignment.
- **Complication**: Impediment, hardware constraint, or rate limit encountered.
- **Question**: Business or technical impact on project trajectory.
- **Answer**: Concrete mitigation strategy agreed upon during the meeting.

### 3. Binary Action Item Verification
- Action items must use testable, binary verification criteria (e.g., *"Show Excel diffing demo with 3 test files"* instead of *"Understand Excel manipulation"*).
