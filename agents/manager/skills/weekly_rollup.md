# Skill Specification: manager_weekly_rollup

## Purpose
Answers "what do I need to know about the state of the training program?" for Iyappan within a 60-second reading budget. Determines what was completed, what is in progress, what is blocked or at risk, what important changes occurred, and what requires executive attention.

## Inputs
- `period_start`: Optional start date string (e.g. "2026-07-21" or "21 July 2026")
- `period_end`: Optional end date string (e.g. "2026-07-28" or "28 July 2026")
- `trainee`: Optional target mentee filter ("Himaya", "Ganesh", "Dakshinya", or omitted for full cohort)

## Required Workflow
1. **Determine the Reporting Period**: Resolve the requested time window from the query or default to the full review window.
2. **Retrieve Evidence for the Period**: Query the retrieval service across session files in the window with completeness-first breadth.
3. **Separate Evidence by Trainee**: Group dialogue turns for Himaya Perumal, Ganesh Krishna, and Dakshinya Nachimuthu.
4. **Identify Candidates**: Extract candidate completed deliverables, active progress, unresolved blockers, and decisions.
5. **Cross-Check Every Status Against Evidence**:
   - Verify that "Completed" items were demonstrated and accepted, not merely planned.
   - Separate "Agreed Blockers" from "Contested Claims" and "Resolved Issues".
   - Never infer completion from silence.
6. **Identify Changes & Intervention Points**: Highlight major architecture shifts and risks that threaten project delivery.
7. **Produce Executive Report**: Synthesize concise prose entries ordered by importance to the executive reader.
8. **Self-Check**: Verify that every material status has an underlying chunk reference in the trace log.

## Evidence Requirements
- Every material status keeps its underlying chunk references in the execution log.
- High-stakes statuses ("Completed") carry at most ONE supporting quote in the report.
- All other items state the technical facts directly without quoting dialogue.

## Failure Behavior
- If no transcript chunks exist for the requested period, output `INSUFFICIENT_EVIDENCE`.
- If evidence is missing for a specific trainee, state explicitly: "INSUFFICIENT_EVIDENCE for [Trainee]".
- Never invent facts, status, or deliverables.

## Output Schema
```
Executive conclusion
- 1-2 sentence governing takeaway on project health and trajectory.

Completed
- [Trainee Name] · [Deliverable Title]: [1-2 sentences on technical mechanics and significance]. Quote: "[One exact supporting quote]" [Date, Page — Speaker]

In Progress
- [Trainee Name] · [Task Title]: [Current engineering state and next step] [Date, Page — Speaker]

Blocked or At Risk
- [Trainee Name] · [Impediment]: [Situation, Complication, Question, Resolution State: Agreed/Contested/Pending Decision] [Date, Page — Speaker]

Important Changes
- [Topic]: [What architectural or tool shift occurred] [Date, Page — Speaker]

Requires Attention
- [Issue]: [Recommended executive intervention point] [Date, Page — Speaker]
```
