# Skill Specification: mentor_trainee_assessment

## Purpose
Evaluates a trainee's demonstrated technical progress for the Technical Mentor to decide what to teach next. Distinguishes what was merely taught from what was genuinely understood, maps diagnostic reasoning sequences, and isolates recurring misconceptions.

## Inputs
- `trainee`: Target trainee name string — required.
- `period`: Optional review window string (e.g. "July 2026", "2026-07-15 to 2026-07-24").
- `focus_area`: Optional technical domain (e.g. "NLP & Chunking", "Excel Manipulation", "ML Baselines").

## Required Workflow
1. **Identify the Trainee & Reporting Period**: Extract the target mentee and window.
2. **Retrieve Relevant Evidence**: Query the retrieval service for dialogue turns where the mentee speaks or is reviewed.
3. **Identify Concepts Taught**: Isolate the architectural ideas introduced by the mentor in those sessions.
4. **Identify What the Trainee Attempted**: Document the specific scripts, features, or assignments the mentee built.
5. **Identify Demonstrated Understanding**: Apply the cognitive ladder (`Taught` → `Attempted` → `Demonstrated` → `Correct`). Stronger states are only claimed with proof.
6. **Identify Gaps & Misconceptions**: Note flawed mental models that were corrected by the mentor.
7. **Compare with Previous Evidence**: Check whether feedback given in earlier sessions was successfully applied in later sessions.
8. **Identify Recurring Feedback**: Extract repeated guidance topics spoken by the mentor.
9. **Produce Assessment**: Synthesize clear, prose sections following the defined output schema.
10. **Self-Check Every Conclusion**: Ensure that every claim is backed by transcript turns; if unproven, state "Not demonstrated from available evidence."

## Evidence Requirements
- **Critical Rule: Taught ≠ Understood**. The appearance of a concept in a session proves nothing about the trainee.
- Stronger mastery states are only claimed when the mentee defends trade-offs or demonstrates verified working code.
- Cite `[Date, Page — Speaker]` for all key evaluation statements.

## Failure Behavior
- When evidence cannot establish understanding, output: "Not demonstrated from available evidence" (never assume understanding).
- If no dialogue turns exist for the requested mentee/period, return `INSUFFICIENT_EVIDENCE`.

## Output Schema
```
Trainee · Overall assessment
- 1-2 sentence honest verdict on demonstrated cognitive mastery.

Current work
- Discrete engineering modules currently under active development [Date, Page — Speaker].

Demonstrated capabilities
- Concepts where the mentee proved first-principles understanding through code or defense [Date, Page — Speaker].

Learning progress
- How the mentee's technical independence has evolved across the period.

Knowledge gaps
- Unresolved conceptual blind spots or incomplete implementations [Date, Page — Speaker].

Recurring misconceptions
- Specific instances where the mentee's mental model diverged from engineering reality and required mentor correction [Date, Page — Speaker].

Feedback signals
- Core coaching directives delivered by the mentor.

Change from previous period
- Direct comparison showing trajectory between early and recent sessions.

Evidence-backed conclusion
- Final pedagogical recommendation for the mentor's next teaching plan.
```
