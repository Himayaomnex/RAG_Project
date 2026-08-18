# Deliverable 1: Production-Grade Agent Specifications

## 1. Manager Agent Specification

### User Profile
- **Role**: Executive Sponsor / Project Manager (Iyappan Sir).
- **Technical Level**: Executive / High-level oversight.
- **Time Available**: **60 Seconds** maximum.
- **Decisions Made**: Resource allocation, task re-assignment, blocker resolution, intervention priorities.

### Goal
- **Primary Goal**: Inform the Manager what requires immediate intervention and review today.
- **Explicit Non-Goal**: Never output generic project summaries or ungrounded optimistic updates.

### Inputs
- Retrieved transcript chunks from Qdrant vector database (`teams_dense_collection`).
- Payload metadata: `speaker`, `date`, `source_file`, `page`, `cut_reason`.
- Scope: Teammates **Himaya Perumal**, **Ganesh Krishna**, and **Dakshinya Nachimuthu**.

### Output Schema (Strict JSON & Markdown)
```json
{
  "completed_work": [
    { "member": "String", "accomplishment": "String", "citation": "[Date | Doc | Speaker | Page]" }
  ],
  "current_blockers": [
    { "member": "String", "blocker": "String", "impact": "High|Medium|Low", "citation": "[Date | Doc | Speaker | Page]" }
  ],
  "risks": [
    { "risk_description": "String", "severity": "Critical|High|Medium", "citation": "[Date | Doc | Speaker | Page]" }
  ],
  "decisions_required": [
    { "decision": "String", "owner": "Manager", "context": "String" }
  ],
  "citations": ["String"]
}
```

### Failure Modes & Mitigation Strategies
- **Failure Mode 1**: Attributing one teammate's completed task to another (Crosstalk leakage).
  - *Mitigation*: Pre-chunking speaker re-attribution and strict speaker metadata scoping (`speaker == Target`).
- **Failure Mode 2**: Hallucinating dates or page numbers when citations are missing.
  - *Mitigation*: Hard constraint in prompt: Never invent date string or page number; use exact string from evidence payload.

---

## 2. Mentor Agent Specification

### User Profile
- **Role**: Senior Technical Lead / Mentor (Siddharth Saminathan).
- **Technical Level**: Expert Engineer / RAG Systems Architect.
- **Time Available**: **10 Minutes**.
- **Decisions Made**: Assigning technical tasks, clearing misconceptions, creating testing quizzes, providing code guidance.

### Goal
- **Primary Goal**: Evaluate mentee learning progress (Himaya, Ganesh, Dakshinya) using concrete meeting quotes.
- **Explicit Non-Goal**: Never provide praise or criticism without citing specific transcript evidence.

### Inputs
- Speaker-isolated dialogue turns for target mentee.
- Vector retrieval scores & CustomMeetingReranker topic scores.
- Codebase architecture context from `pipeline.py`.

### Output Schema (Strict JSON & Markdown)
```json
{
  "target_mentee": "Himaya Perumal | Ganesh Krishna | Dakshinya Nachimuthu",
  "strengths": [
    { "concept": "String", "evidence_quote": "String", "citation": "[Date | Doc | Speaker | Page]" }
  ],
  "misconceptions": [
    { "misconception": "String", "flawed_reasoning_quote": "String", "correct_principle": "String", "citation": "[Date | Doc | Speaker | Page]" }
  ],
  "recommended_next_task": {
    "task_title": "String",
    "objective": "String",
    "rationale": "String"
  },
  "citations": ["String"]
}
```

### Failure Modes & Mitigation Strategies
- **Failure Mode 1**: Giving vague recommendations without evidence quotes.
  - *Mitigation*: Output schema validation enforcing non-empty `evidence_quote` and `citation` strings.

---

## 3. Team Intelligence Agent Specification

### User Profile
- **Role**: Team Lead / Technical Operations Analyst.
- **Technical Level**: Intermediate / Systems Analyst.
- **Time Available**: **30 Minutes**.
- **Decisions Made**: Identifying systemic knowledge gaps, organizing team training sessions, detecting repeated question clusters.

### Goal
- **Primary Goal**: Discover cross-meeting patterns, knowledge gaps, and recurring blockers across all July/August transcripts.
- **Explicit Non-Goal**: Never output single-meeting summaries; must synthesize multi-meeting patterns.

### Inputs
- Multi-meeting transcript chunks retrieved across dates (2 July 2026 - 4 August 2026).

### Output Schema (Strict JSON & Markdown)
```json
{
  "repeated_questions": [
    { "topic": "String", "frequency_count": "Number", "asked_by": ["String"], "question_examples": ["String"] }
  ],
  "knowledge_gaps": [
    { "domain": "String", "description": "String", "affected_members": ["String"] }
  ],
  "collaboration_patterns": [
    { "pattern_name": "String", "description": "String" }
  ],
  "citations": ["String"]
}
```

### Failure Modes & Mitigation Strategies
- **Failure Mode 1**: Listing a question as "repeated" when it only occurred once in a single meeting.
  - *Mitigation*: Explicit multi-meeting threshold logic (`frequency_count >= 2` across distinct dates).
