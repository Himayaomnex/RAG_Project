# Skill Specification: mentor_trainee_assessment

## Purpose
Shows a trainee's demonstrated progress for the Technical Mentor to decide what to teach next and how to score trainees. Evaluates current work, demonstrated technical capability, learning gaps, recurring misconceptions, feedback received, and change from previous sessions.

## Inputs
- `trainee`: Target trainee name (e.g. "Himaya", "Ganesh", or "Dakshinya")
- `period`: Review period string (e.g. "July 2026" or "2026-07-21 to 2026-07-28")
- `focus_area`: Optional focus area (or omitted for general assessment)

## Required Workflow
1. **Identify the trainee and reporting period**: Resolve the target mentee and window.
2. **Retrieve relevant work and learning evidence**: Query the retrieval service for dialogue turns where the mentee speaks or is reviewed.
3. **Identify concepts taught**: Isolate the architectural ideas introduced by the mentor in those sessions.
4. **Identify what the trainee attempted**: Document specific scripts, features, or assignments the mentee built.
5. **Identify demonstrated understanding**: Apply the cognitive ladder (`Taught` → `Attempted` → `Demonstrated` → `Correct`). Stronger states are only claimed with proof.
6. **Identify gaps and misconceptions**: Note flawed mental models that were corrected by the mentor.
7. **Compare with previous evidence**: Check whether feedback given in earlier sessions was successfully applied in later sessions.
8. **Identify recurring feedback**: Extract repeated guidance topics spoken by the mentor.
9. **Produce the assessment**: Synthesize clear, prose sections following the defined output schema.
10. **Self-check every conclusion against evidence**: Ensure every claim is backed by transcript turns; if unproven, state "Not demonstrated from available evidence."

## Evidence Requirements
- **Critical Rule: Taught ≠ Understood**. The appearance of a concept in a training session proves nothing about the trainee.
- The agent may only claim a stronger state (e.g. "Demonstrated") when the evidence shows the mentee defending trade-offs or demonstrating verified code.
- Cite `[Date, Page — Speaker]` for all key evaluation statements.

## Failure Behavior
- When evidence cannot establish understanding, output: "Not demonstrated from available evidence" — never assume or invent understanding.
- If no dialogue turns exist for the requested mentee/period, return `INSUFFICIENT_EVIDENCE`.

## Output Schema
```
### **Trainee · Overall assessment**
- Adapt this section dynamically to match the style, length, and formatting instructions requested in the user's query (e.g. write a detailed Pyramid Principle hierarchy if asked for a "pyramid principle breakdown", or write a short 1-2 sentence summary if asked for a simple evaluation). Fulfill all styling and depth directives.

### **Current work**
- Discrete engineering modules currently under active development [Date, Page — Speaker].

### **Demonstrated capabilities**
- Concepts where the mentee proved first-principles understanding through code or defense [Date, Page — Speaker].

### **Learning progress**
- How the mentee's technical independence has evolved across the period.

### **Knowledge gaps**
- Unresolved conceptual blind spots or incomplete implementations [Date, Page — Speaker].

### **Recurring misconceptions**
- Specific instances where the mentee's mental model diverged from engineering reality and required mentor correction [Date, Page — Speaker].

### **Feedback signals**
- Core coaching directives delivered by the mentor.

### **Change from previous period**
- Direct comparison showing trajectory between early and recent sessions.

### **Evidence-backed conclusion**
- Final pedagogical recommendation for the mentor's next teaching plan.
```
