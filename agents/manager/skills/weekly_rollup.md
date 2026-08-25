# Skill Specification: manager_weekly_rollup

## Purpose
Answers "what do I need to know about the state of the training program?" for the Executive Manager within a sixty-second reading budget. This is a state-of-work report determining what was completed, what is in progress, what is blocked, what needs executive intervention, and what important decisions or risks exist.

## Inputs
- `period_start`: Start date of the review period (e.g. "2026-07-21" or "21 July 2026")
- `period_end`: End date of the review period (e.g. "2026-07-28" or "28 July 2026")
- `trainee`: Optional trainee focus (or omitted for full cohort)

## Required Workflow
1. **Determine the reporting period**: Extract and resolve the target review window from inputs.
2. **Retrieve relevant evidence for the period**: Query the retrieval service across session files in the window with completeness-first breadth.
3. **Separate evidence by trainee**: Group dialogue turns for each individual trainee in the cohort.
4. **Identify assignments, progress, blockers, decisions**: Extract candidate deliverables and active work items.
5. **Cross-check every status against the evidence**:
   - Verify that "Completed" items were demonstrated and accepted, not merely planned.
   - Separate "Agreed Blockers" from "Contested Claims" and "Pending Decisions".
   - Never infer completion from absence of discussion.
6. **Identify changes and intervention points**: Highlight major architectural shifts and critical risks.
7. **Produce the executive report**: Synthesize short lists of concluded items ordered by importance to the executive reader.
8. **Self-check the report against the retrieved evidence**: Verify that every material status has an underlying chunk reference in the execution log.

## Evidence Requirements
- Every material status keeps its underlying chunk references in the execution log.
- A high-stakes status — a "Completed" — may carry at most one supporting quote in the report.
- Nothing else quotes. All other items state technical facts directly.
- Evidence lives in logs and is produced on demand when a row is challenged.

## Failure Behavior
- If evidence is insufficient, output `INSUFFICIENT_EVIDENCE` for that item or report.
- Completion is never inferred from absence of discussion.
- Status is never invented.

## Output Schema
```
### **Executive conclusion**
- Adapt this section dynamically to match the style, length, and formatting instructions requested in the user's query (e.g. write a multi-paragraph Pyramid Principle hierarchy if asked for a "pyramid principle breakdown", or write a short 1-2 sentence summary if asked for a simple rollup). Fulfill all styling and depth directives.

### **Completed**
- [Trainee Name] · [Deliverable Title]: [1-2 sentences on technical mechanics and significance]. Quote: "[One exact supporting quote]" [Date, Page — Speaker]

### **In Progress**
- [Trainee Name] · [Task Title]: [Current engineering state and next step] [Date, Page — Speaker]

### **Blocked or At Risk**
- [Trainee Name] · [Impediment]: [Details]. Resolution State: [Agreed/Contested/Pending Decision] [Date, Page — Speaker]

### **Important Changes**
- [Topic]: [What architectural or tool shift occurred] [Date, Page — Speaker]

### **Requires Attention**
- [Issue]: [Recommended executive intervention point] [Date, Page — Speaker]
```
