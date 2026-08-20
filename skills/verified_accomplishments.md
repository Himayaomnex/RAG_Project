---
name: verified-technical-accomplishments
description: "Use when an agent needs to synthesize a chronological, executive-grade verified accomplishments table from meeting transcripts across technical trainees."
---

# Verified Technical Accomplishments — Operational Skill Specification

## 1. Skill Purpose & Scope
This skill defines a single, repeatable, executive-grade task: **extracting, synthesizing, and auditing verified technical deliverables** completed by engineering trainees across review meeting transcripts.

---

## 2. Input Specification (What the LLM Receives)
The LLM is provided with:
1. **Target Entity / Scope**: Specific trainee names (`Himaya Perumal`, `Ganesh Krishna`, `Dakshinya Nachimuthu`) or `All Team Members`.
2. **Raw Transcript Evidence Chunks**: Meeting turns containing:
   - `<turn date="[Date]" doc="[Filename]" page="[Page]" speaker="[Speaker]"> spoken text </turn>`

---

## 3. Output Specification (What the LLM Must Produce)
The LLM must output **strictly a single Markdown Pipe Table** with this exact schema:

```markdown
| Trainee | Synthesized Technical Deliverable (70% Quality) | Status | Citation (30% Proof) |
| :--- | :--- | :---: | :--- |
```

### Tone & Framing Standards:
- **Tone**: Humanized, highly professional, executive-ready (Pyramid Principle: leading with the core technical accomplishment).
- **No Conversation Padding**: Do not output conversational narrative greetings (e.g. *"Here is the summary..."*), internal thinking tags, or post-table remarks.

---

## 4. The 70/30 Golden Synthesis Rule (Non-Negotiable)
- **70% Technical Synthesis (Column 2)**: 
  - Explain *what* was built, *how* it works, and its *architectural impact*.
  - Name concrete engineering concepts (e.g., *OpenPyXL row manipulation*, *vector caching layer*, *async LangGraph workflows*, *TF-IDF with TSNE visualization*).
  - Do NOT write lazy 2-word summaries (e.g. *"Excel diff"*).
- **30% Concise Citation Proof (Column 4)**:
  - Provide a clean, compact citation: `[Date, Page — Speaker]`.
  - **NO Courtroom Quote Dumps**: Do NOT dump full paragraphs of spoken dialogue into table cells.

---

## 5. Step-by-Step Execution Workflow (For Raw LLM)

Follow this exact step-by-step cognitive procedure:

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Scan & Filter Candidate Turns by Trainee / Speaker │
├─────────────────────────────────────────────────────────────┤
│ Step 2: Filter for Genuine Technical Deliverables           │
│         (Ignore administrative small talk, greetings, etc.) │
├─────────────────────────────────────────────────────────────┤
│ Step 3: Group Deliverables Chronologically Across Dates    │
│         (Sweep early baseline, mid-stage, & final wrap-ups)│
├─────────────────────────────────────────────────────────────┤
│ Step 4: Derive Real Evidence Status                         │
│         (Completed = verified working / demoed / committed) │
│         (In Progress = active work discussed but incomplete)│
├─────────────────────────────────────────────────────────────┤
│ Step 5: Synthesize 70% Description + 30% Clean Citation    │
├─────────────────────────────────────────────────────────────┤
│ Step 6: Render Valid Markdown Pipe Table & Verify Delimiters│
└─────────────────────────────────────────────────────────────┘
```

### Detailed Steps:

#### Step 1: Evidence Ingestion & Entity Filtering
Scan all provided `<turn>` blocks. For each target trainee, identify spoken turns where the trainee presents work or the mentor reviews their code/architecture.

#### Step 2: Isolate Verified Deliverables
Filter out conversational chatter (e.g. mic checks, schedule discussions). Only retain turns discussing concrete technical artifacts, scripts, models, databases, or pipelines.

#### Step 3: Chronological Multi-Date Spread
Group findings by meeting date. Ensure deliverables cover the full project timeline from early foundational work through mid-stage features to final wrap-up integrations.

#### Step 4: Dynamic Status Derivation
- Mark **`Completed`** only when the transcript confirms the script/feature is working, tested, demoed, or committed.
- Mark **`In Progress`** if the trainee is actively debugging, waiting on review, or still building.
- Mark **`Blocked`** if an impediment stopped progress.

#### Step 5: High-Quality 70/30 Formatting
Write the synthesized deliverable in Column 2 using active engineering verbs (*"Developed..."*, *"Implemented..."*, *"Engineered..."*). Format Column 4 with the concise citation `[Date, Page — Speaker]`.

#### Step 6: Pipe Integrity & Sanitation
Ensure all pipe characters (`|`) inside cells are escaped or sanitized so the table renders cleanly in Markdown.

---

## 6. Examples (Good vs. Bad)

### ❌ BAD (Courtroom Quote Dump — What Mentor Dislikes):
| Trainee | Task | Status | Citation |
| :--- | :--- | :--- | :--- |
| Ganesh | Excel | Completed | `[24 July 2026, Page 1 — Ganesh Krishna]: "I have basically completed everything in the scope. Excel legend could take an input to like say for inserting a row, inserting a row, like editing a cell value or editing the color of the cell, it could do it seamlessly..."` |

### ✅ GOOD (70% Quality Synthesis + 30% Concise Citation — What Mentor Demands):
| Trainee | Synthesized Technical Deliverable (70% Quality) | Status | Citation (30% Proof) |
| :--- | :--- | :---: | :--- |
| **Ganesh Krishna** | **Multi-Row Excel Editing & Diff Pipeline**: Built an automated OpenPyXL manipulation engine capable of inserting rows across merged cells, editing cell values, applying green/red conditional formatting, and tracking row-level diffs via JSON. | **Completed** | `[24 July 2026, Page 1 — Ganesh Krishna]` |

---

## 7. Operational Anti-Patterns & Red Flags
- 🚩 **Lazy 2-word deliverable names**: Refactor into a 2-sentence technical synthesis.
- 🚩 **Paragraph-length quote dump in citation**: Shorten to `[Date, Page — Speaker]`.
- 🚩 **Defaulting all rows to Completed**: Check transcript context to verify real progress state.
- 🚩 **Clustering all rows into 1 single date**: Sweep multiple distinct meeting dates across the timeline.
