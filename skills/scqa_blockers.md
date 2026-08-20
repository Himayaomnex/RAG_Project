---
name: scqa-blockers-and-risks
description: "Use when an agent needs to diagnose, structure, and synthesize active technical complications, impediments, and agreed mitigations from meeting transcripts using the SCQA framework."
---

# SCQA Blockers & Risk Diagnosis — Operational Skill Specification

## 1. Skill Purpose & Scope
This skill defines a single, repeatable executive diagnostic task: **identifying active technical complications, bottlenecks, and agreed mitigations** faced by engineering trainees across review meeting transcripts using the SCQA (Situation, Complication, Question, Answer) framework.

---

## 2. Input Specification (What the LLM Receives)
The LLM is provided with:
1. **Target Entity / Scope**: Specific trainee names or `All Team Members`.
2. **Raw Transcript Evidence Chunks**: Meeting turns containing:
   - `<turn date="[Date]" doc="[Filename]" page="[Page]" speaker="[Speaker]"> spoken text </turn>`

---

## 3. Output Specification (What the LLM Must Produce)
The LLM must output **strictly a single Markdown Pipe Table** with this exact schema:

```markdown
| Trainee | Situation (Context) | Complication (Impediment) | Question (Impact) | Answer (Agreed Mitigation) |
| :--- | :--- | :--- | :--- | :--- |
```

### Table Column Invariants:
- **Column 1 (Trainee)**: Trainee name (`Himaya Perumal`, `Ganesh Krishna`, `Dakshinya Nachimuthu`).
- **Column 2 (Situation)**: 1-sentence technical context (the module or pipeline being built).
- **Column 3 (Complication)**: The specific technical hurdle, mic-bleed, rate limit, or bug encountered. (Do NOT write "Completed" here).
- **Column 4 (Question)**: The engineering question or impact caused by the hurdle (e.g. *"How to prevent 401 rate-limits on large batch context?"*).
- **Column 5 (Answer / Mitigation)**: The concrete technical fix agreed upon in the meeting with a clean citation reference `[Date, Page — Speaker]`.
- **THE ESCAPE HATCH**: If no mitigation was agreed during the meeting, write: **`None Agreed / Pending Decision`**.

---

## 4. The 70/30 Golden Synthesis Rule (Non-Negotiable)
- **70% Technical Diagnosis (Columns 2, 3, 4, 5)**: Explain the exact architectural problem and resolution mechanics.
- **30% Concise Citation**: In Column 5, attach `[Date, Page — Speaker]` without dumping multi-line transcript quotes.

---

## 5. Step-by-Step Execution Workflow (For Raw LLM)

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Scan for Blocker & Friction Keywords in Turns       │
│         (e.g., stuck, error, failing, rate limit, bleed)    │
├─────────────────────────────────────────────────────────────┤
│ Step 2: Apply SCQA Decomposition                            │
│         - S: What was the goal?                             │
│         - C: What failed or caused confusion?               │
│         - Q: What core question must be resolved?           │
│         - A: What was the agreed technical mitigation?      │
├─────────────────────────────────────────────────────────────┤
│ Step 3: Check Mitigation Agreement (Apply Escape Hatch)     │
│         (If unresolved -> "None Agreed / Pending Decision") │
├─────────────────────────────────────────────────────────────┤
│ Step 4: Render Strict Markdown Table & Escape Internal Pipes│
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Examples (Good vs. Bad)

### ❌ BAD (Vague Summary / Missing SCQA Structure):
| Trainee | Situation | Complication | Question | Answer |
| :--- | :--- | :--- | :--- | :--- |
| Dakshinya | DeepSeek | Rate limit error | How to fix? | Siddharth told her to fix it |

### ✅ GOOD (70% Deep Technical Diagnosis with Clean Citation):
| Trainee | Situation (Context) | Complication (Impediment) | Question (Impact) | Answer (Agreed Mitigation) |
| :--- | :--- | :--- | :--- | :--- |
| **Dakshinya Nachimuthu** | Large-scale transcript batching using DeepSeek API | Hit 401 rate limit errors after sending 400+ un-optimized requests exceeding API quotas | How to utilize the 1M context window without hitting provider request rate limits? | Perform context engineering to pack multiple session turns into single larger context payloads before dispatching batches `[7 August 2026, Page 2-3 — Siddharth Saminathan]` |
| **Himaya Perumal** | Speaker attribution across multi-party audio transcripts | Mic-bleed and crosstalk caused trainee turns to be misattributed to mentor in raw docx | How to guarantee exact speaker attribution in Qdrant payloads? | Implemented `transcript_normalizer.py` pre-processing layer to split and re-attribute turns before embedding `[22 July 2026, Page 1-2 — Siddharth Saminathan]` |
