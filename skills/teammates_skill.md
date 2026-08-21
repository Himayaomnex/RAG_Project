---
name: teammates-agent-operations
description: "Operational skill for the Teammates Agent. Provides step-by-step procedures to explain workspace codebase architecture, mine recurring cross-meeting technical patterns, and extract mentor engineering principles from meeting transcripts."
---

# Teammates Agent — Operational Execution Skill

This skill defines the step-by-step operational procedures for providing codebase explanations and cross-meeting peer intelligence.

---

## 1. Operational Capabilities & Step-by-Step Instructions

### Capability 1: Codebase Architecture & AST Grounding (`TI-01`)
Explain internal workspace Python classes, algorithms, and pipelines directly from source code.

**Step-by-Step Execution Procedure:**
1. **Inspect Workspace Source Files**: Read real source files (`pipeline.py`, `prompt_builder.py`, `llm_client.py`) to extract exact class and method definitions.
2. **Explain Internal Mechanics (70% Synthesis)**: Explain how the classes work (e.g. topic-shift semantic chunking, Qdrant HNSW indexing, SHA-256 caching).
3. **Format Output**: Render as a structured Markdown code walkthrough with verbatim class definitions.

---

### Capability 2: Cross-Meeting Pattern & Bottleneck Mining (`TI-02`)
Analyze recurring technical questions, vector DB locks, and schema issues across sessions.

**Step-by-Step Execution Procedure:**
1. **Identify Repeated Questions**: Scan dialogue turns across multiple dates to isolate shared developer questions (e.g. openpyxl merged cell anchor extraction, DeepSeek token limits, Qdrant lock errors).
2. **Synthesize Pattern Insights**: Explain how teammates collaborated to resolve the issue.
3. **Format Output**: Render as a Markdown table:
   ```markdown
   | Topic | Repeated Technical Question | Frequency | Relevant Citation (30% Proof) |
   | :--- | :--- | :---: | :--- |
   ```

---

### Capability 3: Core Mentor Engineering Principles (`TI-03`)
Extract mentor engineering directives for peer guidance.

**Step-by-Step Execution Procedure:**
1. **Isolate Engineering Directives**: Extract recurring mentor standards (e.g. *Quality & Completeness*, *Understanding Over Results*, *Independent Design*).
2. **Provide Practical Application**: Explain how peer developers should apply this principle in their daily code.
3. **Format Output**: Render as a Markdown table:
   ```markdown
   | Principle | Core Mentor Directive | Practical Team Application | Citation |
   | :--- | :--- | :--- | :--- |
   ```
