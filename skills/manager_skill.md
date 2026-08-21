---
name: manager-agent-operations
description: "Operational skill for the Manager Agent. Provides step-by-step procedures to extract verified technical deliverables, diagnose blockers using SCQA, track strategic decisions, and map milestone timelines from meeting transcripts."
---

# Manager Agent — Operational Execution Skill

This skill defines the exact step-by-step operational procedures for analyzing multi-meeting transcripts to produce executive intelligence.

---

## 1. Operational Capabilities & Step-by-Step Instructions

### Capability 1: Verified Technical Deliverables (`MGR-01`)
Extract and synthesize the verified software components, architectures, and tools delivered across the training program.

**Step-by-Step Execution Procedure:**
1. **Identify Spoken Demos & Code Reviews**: Scan `<turn>` elements in `<transcript_evidence>`. Select turns where a trainee (Himaya, Ganesh, or Dakshinya) presents working code, demonstrates an API/tool, or receives confirmation from the lead mentor.
2. **Filter Out Unfinished Chores**: Ignore logistical chatter (scheduling, mic checks, homework assignments without demos). Only extract functional systems (e.g. NLP feature extraction, Qdrant vector caching, OpenPyXL parser, DeepSeek V4 Excel tools, Scroll API, LangGraph conversions).
3. **Determine Finished Status**: 
   - If the code was demonstrated, tested, or merged by the end of the cohort timeline, mark Status as `Completed`.
   - If the feature had open bugs discussed in the latest August sessions, mark `In Progress`.
4. **Synthesize the Engineering Mechanism (70% Synthesis)**: Write a 2-sentence technical description explaining *what* was built, the underlying libraries/algorithms used, and *how* it functions.
5. **Attach Concise Citation (30% Proof)**: Append `[Date, Page — Speaker]` referencing the primary review turn.
6. **Format Output**: Render as a Markdown table:
   ```markdown
   | Trainee | Synthesized Technical Deliverable | Status | Citation |
   | :--- | :--- | :---: | :--- |
   ```

---

### Capability 2: SCQA Blocker & Impediment Diagnosis (`MGR-02`)
Isolate technical impediments, rate limits, hardware bottlenecks, and misunderstandings encountered during development.

**Step-by-Step Execution Procedure:**
1. **Detect Complications**: Scan for turns containing errors, rate-limit failures, data corruption, mic bleed, or confusion (e.g. 401 DeepSeek rate limits, Git binary diff failures, openpyxl merged cell span bugs).
2. **Extract Situation (S)**: State the specific technical feature or assignment the mentee was actively developing.
3. **Extract Complication (C)**: State the exact technical impediment or error encountered.
4. **Formulate Impact Question (Q)**: Frame the core engineering challenge as an actionable question (e.g. *"How to handle multi-row cell spans without losing data?"*).
5. **Extract Answer / Mitigation (A)**:
   - If the transcript contains an agreed technical resolution, state the fix in 1-2 clear sentences.
   - If the meeting ended with the issue unresolved, explicitly write: **`None Agreed / Pending Decision`**.
6. **Format Output**: Render as a Markdown table:
   ```markdown
   | Trainee | Situation (Context) | Complication (Impediment) | Question (Impact) | Answer (Agreed Mitigation) |
   | :--- | :--- | :--- | :--- | :--- |
   ```

---

### Capability 3: Strategic Architectural Decisions (`MGR-03`)
Extract major technology choices, trade-offs, and resource commitments decided across sessions.

**Step-by-Step Execution Procedure:**
1. **Identify Decision Turns**: Locate turns where the mentor and team select a framework, database, or model over alternatives (e.g. Qdrant over Chroma, DeepSeek V4 over Llama, LangGraph over pure LangChain).
2. **Classify Decision Type**:
   - `Fact (Decided in Meeting)`: Explicitly agreed upon by the lead mentor during dialogue.
   - `Recommendation (Agent)`: Strategic improvement proposed by the agent based on transcript gaps.
3. **Isolate the Trade-off Given Up**: State what alternative or benefit was sacrificed (e.g. *"Sacrificed initial setup speed for sub-second retrieval latency"*).
4. **Format Output**: Render as a Markdown table:
   ```markdown
   | Owner | Decision Type | Synthesized Decision & Strategy | Trade-off Given Up | Citation |
   | :--- | :--- | :--- | :--- | :--- |
   ```

---

### Capability 4: Chronological Milestone Velocity (`MGR-04`)
Track task progression chronologically from baseline sessions through final wrap-up meetings.

**Step-by-Step Execution Procedure:**
1. **Group Evidence by Meeting Date**: Sort retrieved turns chronologically from early July to August.
2. **Extract Snapshot Status on That Date**: Document the task's status *as of that specific meeting date* (`In Progress`, `Blocked`, or `Completed`).
3. **Format Output**: Render as a Markdown table:
   ```markdown
   | Owner | Synthesized Milestone Description | Meeting Date | Status | Citation |
   | :--- | :--- | :---: | :---: | :--- |
   ```

---

## 2. Output Presentation Architecture (Pyramid Principle)

When delivering multi-section reports, organize the output top-down:
1. **Governing Thought**: A single executive summary sentence synthesizing the project's overall technical health.
2. **MECE Structured Tables**: Present data grouped into mutually exclusive, collectively exhaustive categories (Accomplishments, Blockers, Decisions, Milestones).
3. **70/30 Balance**: Keep tables scannable by dedicating 70% of cell space to engineering synthesis and 30% to clean citations `[Date, Page — Speaker]`.
