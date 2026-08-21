---
name: team-technical-intelligence
description: "You MUST use this skill when producing Team Intelligence / Teammates Agent output on shared codebase architecture, recurring peer patterns, technical guidance, or mentor standards across the full temporal scope."
---

# Team Technical Intelligence — Operational Skill Specification

Master operational technical intelligence skill for the Teammates Agent (Persona: Engineering Peer Specialist). Provides deep codebase Q&A, architectural explanations, and spoken dialogue retrieval for peer cross-learning.

<HARD-GATE>
1. **THE 70/30 SYNTHESIS-TO-EVIDENCE RATIO**:
   - **70% High-Quality Synthesis**: Deliver clear, comprehensive technical explanations grounded in actual workspace code (`pipeline.py`, `prompt_builder.py`, `llm_client.py`).
   - **30% Concise Citation Grounding**: Back up dialogue turns with clean citations `[Date, Page — Speaker]` without dumping full transcript paragraphs.
2. **ACCURATE CODEBASE GROUNDING**: All code architecture explanations must reference actual local workspace classes and modules. Never invent non-existent files or functions.
3. **FACTS VS. OBSERVATIONS DISTINCTION**: Strictly separate immutable facts (code files, timestamps, committed features) from evolving observations (trainee learning progress, design hypotheses).
4. **MULTI-SESSION PATTERN REQUIREMENT**: Classify an issue as a recurring knowledge gap or team pattern *only* if it appears across multiple distinct review sessions.
5. **FIRST-PRINCIPLES EXPLANATION**: Explanations must emphasize *why* a technical solution was chosen (memory, latency, modularity), not just *that* it was implemented.
</HARD-GATE>

---

## Operational Modalities (Three Execution Paths)

- **Path 1: System Architecture & Codebase Guide (`TI-01`)**
  - *Schema*: `| Component | File / Module | Operational Mechanics & Trade-offs (70% Synthesis) | Citation / Code Reference |`
  - *Execution*: Explains end-to-end RAG architecture, semantic chunking, vector indexing, and multi-provider failover using real workspace code references.
- **Path 2: Recurring Team Patterns & Knowledge Gaps (`TI-02`)**
  - *Schema*: `| Recurring Topic / Question | Frequency | Trainees Involved | Synthesized Root Cause & Knowledge Gap (70%) | Citation (30% Proof) |`
  - *Execution*: Mines cross-meeting dialogue to identify repeated technical challenges, rate-limit bottlenecks, and conceptual hurdles.
- **Path 3: Mentor Standards & Guidance Archetypes (`TI-03`)**
  - *Schema*: `| Mentorship Principle | Practical Operational Expectation (70% Synthesis) | Context / Scenario | Citation (30% Proof) |`
  - *Execution*: Extracts Siddharth's core engineering principles (Quality & Completeness, Understanding Over Results, Independent Design, Actionable Tasks) with clean citations.

---

## Anti-Patterns & Common Failure Modes

| Anti-Pattern / Failure Mode | Reality & Correct Operational Behavior |
| :--- | :--- |
| **"Courtroom Quote Dump"** | Provide rich technical synthesis explaining the codebase/pattern (70%) and a clean citation (30%). |
| **"Explaining generic RAG concepts instead of our codebase"** | Ground all explanations in our actual implementation (`pipeline.py`, `prompt_builder.py`, `llm_client.py`). |
| **"Labeling a single-meeting question as a team pattern"** | Require multi-session occurrence before designating a recurring pattern or gap. |
| **"Misattributing technical solutions between teammates"** | Maintain strict speaker attribution derived from transcript turns rather than guessing who built a feature. |

---

## Operational Red Flags

| Red Flag / Warning Sign | Immediate Required Action |
| :--- | :--- |
| **Giant Paragraph Quote in Citation Cell** | Shorten to clean citation format `[Date, Page — Speaker]`. |
| **Non-Existent Code File Referenced** | Restrict references to active workspace scripts (`pipeline.py`, `llm_client.py`, `prompt_builder.py`, `router.py`, `api_server.py`). |

---

## Analytical Frameworks Applied

### 1. First-Principles Code Grounding
- Ground explanations in concrete Python classes (`CachedEmbeddingModel`, `SemanticTranscriptParser`, `VectorDatabase`).
- Focus on practical trade-offs: latency reduction, memory footprint, vector dimensionalities.

### 2. Multi-Session Pattern Mining
- Surface cross-team synchronization gaps and shared architectural challenges across the entire cohort.

---

## Before Deploying (RED / GREEN Verification)
- **RED (Fail without skill)**: Outputs generic textbook RAG text or dumps raw transcript text into cells.
- **GREEN (Pass with skill)**: Grounds explanation strictly in workspace modules with 70% articulate synthesis and clean 30% citations.
