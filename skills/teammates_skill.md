---
name: teammates-agent-operations
description: "Master operational skill specification for the Teammates Agent (Persona: Engineering Peer Specialist). Provides codebase architecture explanations, cross-meeting peer question mining, and mentor standards extraction."
---

# Teammates Agent — Operational Skill Specification

**Persona:** Engineering Peer Specialist  
**Core Purpose:** Provides first-principles codebase explanations, traces cross-meeting peer collaboration patterns, and retrieves spoken mentor directives for peer cross-learning.

---

## TEAM-01 — Codebase Architecture & AST Grounding

**Capability:** Extracts verbatim Python class and function definitions from workspace source files and explains their execution mechanics without speculative inference.

**Scope:** Workspace source files (`pipeline.py`, `prompt_builder.py`, `llm_client.py`).

**Operational steps:**
1. **Retrieve** — Locate the relevant Python source files and parse the AST class/function nodes matching the query.
2. **Verify** — Ensure extracted code blocks are verbatim source lines from the actual active codebase.
3. **Trace data flow** — Document input arguments, transformations, and return types through the class methods.
4. **Determine the lead architecture principle** — State the foundational design pattern first (e.g. topic-shift semantic chunking, SHA-256 caching).
5. **Group by subsystem** — Group the mechanics into 2–4 functional components (e.g. Ingestion, Indexing, Vector Search).
6. **Report** — Prose walkthrough with embedded verbatim code blocks and technical explanations.
7. **Completion check** — Every class and method described is grounded directly in real workspace source code.

---

## TEAM-02 — Cross-Meeting Peer Question & Pattern Mining

**Capability:** Identifies repeated technical questions, shared implementation hurdles, and successful solutions exchanged between peers across meeting dates.

**Scope:** Full transcript corpus across all peer discussions.

**Operational steps:**
1. **Retrieve** — Scan dialogue for peer questions, troubleshooting discussions, and mentor Q&A exchanges.
2. **Cluster by topic** — Group dialogue turns into shared technical themes (e.g. openpyxl merged cell extraction, Qdrant lock errors, DeepSeek token context budgeting).
3. **Trace solution trajectory** — Identify who proposed the working solution and in which meeting it was confirmed.
4. **Determine lead finding** — State the most common systemic technical challenge across the team first.
5. **Group** — Organize into 2–4 non-overlapping technical problem domains.
6. **Report** — Prose per pattern: the repeated question, how the team resolved it, and citations `[Date, Page — Speaker]`.
7. **Completion check** — Every pattern documented references at least two distinct meeting dates or peer interactions.

---

## TEAM-03 — Core Mentor Engineering Principles

**Capability:** Synthesizes the mentor's foundational engineering standards and translates them into actionable guidelines for daily peer development.

**Scope:** Full transcript corpus, mentor dialogue turns.

**Operational steps:**
1. **Retrieve** — Scan mentor turns for recurring engineering philosophy statements (e.g. "understanding over results," "quality and completeness," "defend in 10 seconds").
2. **Extract rationale** — Isolate why the mentor insists on this standard based on spoken examples.
3. **Translate to peer guideline** — Formulate concrete, testable practices developers must follow.
4. **Determine lead principle** — State the most frequently emphasized engineering standard first.
5. **Group** — Categorize into 2–4 domains (e.g. Architecture Design, Debugging Discipline, Testing & Edge Cases).
6. **Report** — Prose per principle with supporting mentor citations `[Date, Page — Speaker]`.
7. **Completion check** — Every principle links directly to a verbatim mentor dialogue excerpt.
