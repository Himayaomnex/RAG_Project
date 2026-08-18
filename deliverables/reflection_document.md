# Deliverable 4: Engineering Reflection Document

This document reflects on the biggest failures, root causes, and architectural redesigns implemented across the three production-grade agents in **`RAG_COMBINED`**.

---

## 1. Manager Agent Reflection

### What was the biggest failure?
- **Symptom**: In early baseline testing, when asked for a team status update, the agent produced a generic summary stating *"The team worked on Python scripts and database tasks."* without attributing specific accomplishments or active blockers to individual teammates.
- **Root Cause**: The initial prompt lacked strict speaker isolation directives and did not enforce explicit section breakdowns for Completed Work vs Current Blockers.

### How was it redesigned?
- **Prompt Architecture Fix**: Implemented strict JSON schema requiring explicit `member`, `accomplishment`, `blocker`, `impact`, and `citation` strings.
- **Retrieval Fix**: Implemented metadata-scoped filtering (`speaker == Target`) in `DenseRetriever` to guarantee clean speaker attribution.

---

## 2. Mentor Agent Reflection

### What was the biggest failure?
- **Symptom**: The agent flagged mentee questions as "weaknesses" even when the mentee was asking a valid architectural question.
- **Root Cause**: The model interpreted any question asked by a teammate as a sign of incompetence rather than constructive learning.

### How was it redesigned?
- **Prompt Architecture Fix**: Introduced explicit 3-step reasoning instructions distinguishing between *Active Learning / Question Asking* (Strength) and *Flawed Technical Assumptions / Confident Errors* (Misconception).
- **Evidence Quote Enforcement**: Mandated that every misconception entry include an exact `flawed_reasoning_quote` directly copied from transcript turns.

---

## 3. Team Intelligence Agent Reflection

### What was the biggest failure?
- **Symptom**: The agent treated single-meeting topics as "team-wide recurring patterns".
- **Root Cause**: Lack of multi-meeting frequency threshold rules in the prompt logic.

### How was it redesigned?
- **Multi-Meeting Mining Fix**: Added an explicit directive forcing the model to verify occurrence across distinct meeting dates (`frequency_count >= 2`) before grouping topics into repeated question clusters or systemic knowledge gaps.

---

## 🔑 Key Engineering Takeaway
> *"The goal is not to write better prompts. The goal is to design better agent behavior through strict input scoping, explicit step-by-step reasoning, grounded evidence citations, and schema-enforced outputs."*
