---
name: mentor-agent-operations
description: "Operational skill for the Mentor Agent. Provides step-by-step procedures to grade cognitive depth using Bloom's Taxonomy, diagnose misconceptions, extract coaching directives, and define binary-verifiable next tasks from meeting transcripts."
---

# Mentor Agent — Operational Execution Skill

This skill defines the step-by-step operational procedures for pedagogical assessment and mentee diagnosis from meeting transcripts.

---

## 1. Operational Capabilities & Step-by-Step Instructions

### Capability 1: Bloom's Taxonomy Cognitive Scoring (`MNT-01`)
Grade trainees across 4 core technical pillars based on demonstrated first-principles understanding.

**Step-by-Step Execution Procedure:**
1. **Filter Mentee Demonstration Turns**: Locate turns where the mentee presents code, answers review questions, or defends architectural choices.
2. **Apply Bloom's Rubrics (1-10 Scale)**:
   - `9-10 (Mastery)`: Explains *why* the architecture works, defends design trade-offs, and demonstrates verified working code.
   - `7-8 (Proficient)`: Implements working features but requires minor guidance on optimization or edge cases.
   - `5-6 (Developing)`: Understands concepts theoretically but struggles with practical implementation or debugging.
   - `1-4 (Novice)`: Copies code without understanding underlying mechanics or fails fundamental defense questions.
3. **Format Output**: Render as a Markdown table:
   ```markdown
   | Trainee | Preparation (1-10) | Conceptual Depth (1-10) | Code Quality (1-10) | Engagement (1-10) | Overall (1-10) | One-Line Verdict |
   | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
   ```

---

### Capability 2: Diagnostic Strengths & Misconceptions (`MNT-02`)
Isolate genuine engineering strengths from flawed mental models.

**Step-by-Step Execution Procedure:**
1. **Differentiate Curiosity vs Misconceptions**:
   - Asking clarifying questions or exploring options is an **Engineering Strength**.
   - Defending an incorrect technical assumption (e.g. thinking retrieval alone answers a question, or caching raw user queries instead of embeddings) is a **Misconception**.
2. **Synthesize Feedback (70% Synthesis)**: Explain the flawed mental model and the mentor's correction in 1-2 clear sentences.
3. **Attach Citation (30% Proof)**: Append `[Date, Page — Speaker]`.
4. **Format Output**: Render as a Markdown table:
   ```markdown
   | Trainee | Strength / Misconception (70% Synthesis) | Category | Citation (30% Proof) |
   | :--- | :--- | :---: | :--- |
   ```

---

### Capability 3: Mentorship Directives & Guidance Log (`MNT-03`)
Extract coaching feedback and architectural standards spoken by the lead mentor.

**Step-by-Step Execution Procedure:**
1. **Extract Mentor Review Turns**: Scan turns spoken by the lead mentor containing architectural directives (e.g. *Quality & Completeness*, *Understanding Over Results*, *Testing Edge Cases*).
2. **Synthesize Directive**: Summarize the core instruction and its engineering rationale.
3. **Format Output**: Render as a Markdown table:
   ```markdown
   | Trainee | Mentorship Guidance / Feedback Topic | Meeting Date | Citation (30% Proof) |
   | :--- | :--- | :---: | :--- |
   ```

---

### Capability 4: Actionable Binary Next Tasks (`MNT-04`)
Formulate testable, binary-verifiable next steps for mentees.

**Step-by-Step Execution Procedure:**
1. **Convert Feedback to Acceptance Criteria**: Never assign vague goals (e.g. *"Read about X"*). Always define binary pass/fail criteria (e.g. *"Demonstrate script extracting Excel rows into valid JSON with 3 test files"*).
2. **Format Output**: Render as a Markdown table:
   ```markdown
   | Trainee | Assigned Task / Learning Topic | Meeting Date | Binary Verification Criteria |
   | :--- | :--- | :---: | :--- |
   ```
