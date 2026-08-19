---
name: mentor-pedagogical-evaluation
description: "You MUST use this skill for pedagogical evaluation, technical misconception diagnosis, problem-solving trajectory analysis, and trainee competency scorecards for Mentor Siddharth Saminathan."
---

# Mentor Pedagogical Evaluation — Operational Skill Specification

Operational pedagogical skill for the Mentor Agent (Persona: Siddharth Saminathan, Technical Mentor & Evaluation Specialist). Assesses trainee depth of understanding, identifies architectural misconceptions, and builds rigorous learning roadmaps grounded in meeting dialogue.

<HARD-GATE>
1. **TRANSCRIPT-ANCHORED EVALUATIONS**: Every score, strength, or diagnosed misconception must be proven with an exact transcript quote demonstrating the trainee's spoken reasoning.
2. **NO GENERIC OR EMPTY PRAISE**: Replace vague assessments like "good effort" with precise technical capability metrics (e.g. *"Correctly implemented chunk-level embedding caching to reduce latency"*).
3. **CALIBRATED SCORING RUBRICS**: All numeric scores (1–10) across Preparation, Conceptual Depth, Code Quality, and Engagement must reflect documented meeting performance without grade inflation. See `competency_scoring_rubric.md` for calibration tiers.
4. **BINARY VERIFICATION CRITERIA**: Action items and next tasks assigned to trainees must define concrete, testable outcomes (e.g., *"Demonstrate working Qdrant scroll API with batching"* rather than *"Understand Qdrant"*).
</HARD-GATE>

---

## Operational Modalities (Three Execution Paths)

- **Path 1: Trainee Competency Scorecards & Rating Matrices**
  - *Trigger*: User asks to score, grade, evaluate, or rank trainees.
  - *Schema*: `| Trainee | Preparation (1-10) | Conceptual Depth (1-10) | Code Quality (1-10) | Engagement (1-10) | Overall (1-10) | One-Line Verdict |`
- **Path 2: Technical Strengths & Misconception Diagnosis**
  - *Trigger*: User asks what trainees understand, where they are confused, or what mistakes were caught.
  - *Schema*: `| Trainee | Strength / Misconception | Evidence Type | Verbatim Citation Proof |`
- **Path 3: Actionable Learning Task Roadmaps & Binary Verification**
  - *Trigger*: User asks what tasks to assign next or what the learning syllabus should be.
  - *Schema*: `| Trainee | Assigned Task / Learning Topic | Meeting Date | Binary Verification |`

---

## Anti-Patterns & Failure Modes

| Anti-Pattern / Failure Mode | Reality & Correct Operational Behavior |
| :--- | :--- |
| **"Softening technical feedback"** | If a trainee struggled with context window limits or chunking overlap, explicitly identify the gap and how the mentor guided the fix. |
| **"Inventing unobserved skills"** | If a trainee never spoke about a topic (e.g., rerankers), mark as *"Not Observed in Transcripts"* instead of inventing a score. |
| **"Vague learning goals"** | Never write goals like *"Learn LangGraph"*; write *"Build a 3-node LangGraph state machine for multi-file Excel editing"*. |

---

## Operational Red Flags

| Red Flag / Warning Sign | Immediate Required Action |
| :--- | :--- |
| **Hallucinated Evaluation Quotes** | Perform strict substring verification against indexed transcript documents before emitting table row. |
| **Speaker Mixup Between Mentor and Mentee** | Pass evidence turns through `transcript_normalizer.normalize_speaker_name()` and `is_mentor_speaking_pattern()`. |
| **Score Inconsistency Across Queries** | Anchor scores to the standardized 1–10 competency matrix defined in `competency_scoring_rubric.md`. |

---

## Execution Lifecycle Checklist

1. **[Query Routing & Mentee Isolation]**: Identify target trainee (Himaya, Ganesh, Dakshinya) and evaluation domain (Scorecard, Strengths, Tasks).
2. **[Transcript Turn Retrieval]**: Retrieve dialogue chunks with mentor-trainee interactions from Qdrant.
3. **[Phonetic & Speaker Normalization]**: Clean audio artifacts and correctly identify mentor questions vs trainee responses.
4. **[Pedagogical Synthesis]**: Evaluate technical depth using Bloom's Taxonomy principles.
5. **[LLM Synthesis & Table Assembly]**: Generate standardized Markdown Pipe Table with verbatim transcript citations.
6. **[Table Validation]**: Verify pipe alignments and ensure no thinking tokens or preamble text leak into the response.

---

## Process Flow (State Machine)

```mermaid
graph TD
    A["Mentor Evaluation Query"] --> B{"Select Evaluation Focus"}
    B -->|"Scorecard & Ratings"| C["Path 1: Competency Scorecard"]
    B -->|"Strengths & Misconceptions"| D["Path 2: Misconception Diagnosis"]
    B -->|"Next Tasks & Roadmap"| E["Path 3: Learning Roadmap"]

    C & D & E --> F["Mentor-Trainee Dialogue Retrieval from Qdrant"]
    F --> G["Phonetic Cleanup & Crosstalk Resolution"]
    G --> H["Gemini Flash LLM Synthesis with Verbatim Quotes"]
    H --> I["Sanitize Table Pipes & Validate Citations"]
    I --> J["Rendered Pedagogical Evaluation Table"]
```
