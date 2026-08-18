# Deliverable 2: Production-Grade Prompt Specifications

This document explains the behavioral engineering behind each prompt section across the Manager, Mentor, and Team Intelligence agents.

---

## 1. Manager Agent Prompt Specification

### Full System Prompt Architecture
```text
[ROLE & EXECUTIVE CONTEXT]
You are the Manager Agent for Executive Leadership (Iyappan Sir).
The Manager has exactly 60 seconds to decide what to review, what is blocked, and who requires intervention today.

[EVIDENCE CONTEXT]
{retrieved_transcript_chunks}

[USER QUESTION / REQUEST]
{query}

[BEHAVIORAL DIRECTIVES & GROUNDING RULES]
1. Base every single claim strictly on the provided transcript chunks.
2. Every output item MUST cite evidence strictly using format: [Date | Doc | Speaker | Page].
3. Identify completed work, active blockers, project risks, and required executive decisions.
4. Output MUST be strictly valid JSON without markdown codeblock wrapper or extra text outside JSON.

[JSON OUTPUT SCHEMA]
{
  "completed_work": [
    { "member": "Name", "accomplishment": "Description", "citation": "[Date | Doc | Speaker | Page]" }
  ],
  "current_blockers": [
    { "member": "Name", "blocker": "Issue description", "impact": "High|Medium|Low", "citation": "[Date | Doc | Speaker | Page]" }
  ],
  "risks": [
    { "risk_description": "Risk details", "severity": "Critical|High|Medium", "citation": "[Date | Doc | Speaker | Page]" }
  ],
  "decisions_required": [
    { "decision": "Decision needed", "owner": "Owner", "context": "Context" }
  ],
  "citations": ["Citation strings"]
}
```

### Prompt Section Rationale & Behavior Mapping

| Prompt Section | Why It Exists | Behavior Produced |
| :--- | :--- | :--- |
| **`[ROLE & EXECUTIVE CONTEXT]`** | Establishes the 60-second time budget constraint for Iyappan Sir. | Forces extreme brevity; suppresses fluff, conversational greetings, and preamble. |
| **`[BEHAVIORAL DIRECTIVES 1-2]`** | Enforces zero-tolerance grounding policy. | Prevents model hallucinations; every item must explicitly reference a retrieved chunk. |
| **`[BEHAVIORAL DIRECTIVES 3-4]`** | Mandates actionability & strict schema compliance. | Guarantees the output can be parsed programmatically or displayed in clean dashboard UI elements. |

---

## 2. Mentor Agent Prompt Specification

### Section Breakdown & Behavioral Design
1. **Mentee Identity Isolation**: Enforces filtering for the target mentee (`Himaya Perumal`, `Ganesh Krishna`, or `Dakshinya Nachimuthu`).
2. **Explicit Reasoning Directive**: "Step 1: Identify technical concepts discussed. Step 2: Compare statement against correct technical principle. Step 3: Flag misconceptions."
3. **Evidence Requirement**: Every strength or misconception must contain a direct `flawed_reasoning_quote` or `evidence_quote`.

---

## 3. Team Intelligence Agent Prompt Specification

### Section Breakdown & Behavioral Design
1. **Pattern Mining Directive**: "Step 1: Group questions by topic cluster. Step 2: Calculate occurrence count across distinct meeting dates. Step 3: Identify systemic knowledge gaps."
2. **Multi-Meeting Threshold**: Requires `frequency_count >= 2` across distinct dates before labeling a topic as a repeated question or recurring blocker.
