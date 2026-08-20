---
name: milestones-timeline-tracking
description: "Use when an agent needs to track chronological project milestones, commitments, and completion trajectories across meeting transcripts."
---

# Milestones Timeline Tracking — Operational Skill Specification

## 1. Skill Purpose & Scope
This skill defines a single, repeatable task: **tracking chronological project milestones and commitments** across the full temporal span of meeting transcripts.

---

## 2. Input Specification (What the LLM Receives)
1. **Target Entity / Scope**: Full cohort or individual trainees.
2. **Raw Transcript Evidence Chunks**: `<turn date="..." doc="..." page="..." speaker="..."> spoken text </turn>`

---

## 3. Output Specification (What the LLM Must Produce)
A single, valid Markdown Pipe Table with this exact schema:

```markdown
| Owner | Synthesized Milestone Description (70%) | Meeting Date | Status | Citation (30% Proof) |
| :--- | :--- | :---: | :---: | :--- |
```

### Invariant Rules:
- **Full Chronological Span**: Sweep across early baseline work, mid-stage features, and final wrap-up integrations.
- **Dynamic Status**: `Completed`, `In Progress`, `Blocked`, or `At Risk` based strictly on verified transcript dialogue.
- **The 70/30 Rule**: 70% articulate milestone description; 30% clean citation `[Date, Page — Speaker]`.

---

## 4. Step-by-Step Execution Workflow (For Raw LLM)
1. **Scan for Milestone Commitments**: Extract roadmap milestones, demo goals, and review deadlines.
2. **Sort Chronologically**: Order entries by meeting date.
3. **Derive Progress State**: Verify whether the milestone was delivered or remained active.
4. **Render Markdown Table**: Populate the schema with clean citation references.
