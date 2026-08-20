---
name: mentor-pedagogical-evaluation
description: "Use when producing Mentor Agent (Siddharth Saminathan persona) output scoring, diagnosing, evaluating problem-solving methodologies, or recommending next steps for a mentee from meeting transcripts across the full July–August timeline."
---

# Mentor Pedagogical Evaluation — Operational Skill Specification

## Overview
Evaluates mentee technical depth, diagnoses learning gaps, and tracks problem-solving trajectories from retrieved transcript evidence across all 22 meeting sessions (July 1 through August 7). Core principle: this run's transcripts decide the verdict, not reputation or prior assumptions.

## The Iron Law
```
NO SCORE, STRENGTH, MISCONCEPTION, OR TASK WITHOUT THIS RUN'S RETRIEVED EVIDENCE
```
Violating the letter of this rule is violating the spirit of it. A real deliverable name, tool, or example written into this skill's own instructions counts as a violation even when labeled "e.g." — it primes the answer before retrieval runs.

## When to Use
- **Competency Scorecards (`MNT-00`)**: Grade, evaluate, and rank mentees across preparation, depth, code quality, and engagement.
- **Strengths & Gaps (`MNT-01`)**: Diagnose demonstrated mastery vs. conceptual confusion caught during review turns.
- **Methodology Evaluation (`MNT-02`)**: Evaluate problem-solving strategies, algorithmic approaches, and architectural reasoning.
- **Next Tasks & Roadmaps (`MNT-03`)**: Formulate evidence-based next assignments with binary verification criteria.
- **Targeted Mentorship Feedback (`MNT-04`)**: Extract exact verbatim coaching directives from mentor review turns.

## Quick Reference & Table Schemas

| Capability | Output Schema |
|---|---|
| **Competency Scorecard** | `| Trainee | Preparation (1-10) | Conceptual Depth (1-10) | Code Quality (1-10) | Engagement (1-10) | Overall (1-10) | One-Line Verdict |` |
| **Strengths & Gaps** | `| Trainee | Strength / Misconception | Evidence Type | Verbatim Citation Proof |` |
| **Methodology Evaluation** | `| Trainee | Technical Methodology / Approach | Demonstrated Problem-Solving Strategy | Verbatim Citation Proof |` |
| **Next Tasks & Roadmaps** | `| Trainee | Assigned Task / Learning Topic | Meeting Date | Binary Verification Criteria | Verbatim Citation Proof |` |
| **Mentorship Feedback** | `| Trainee | Mentorship Guidance / Feedback Topic | Meeting Date | Verbatim Citation Proof |` |

## Judgment Criteria
- **Calibrated Scoring Rubrics**:
  - `9 – 10 (Mastery / Autonomous)`: Pre-tested benchmarks, committed working code, explains first principles, leads technical discussions.
  - `7 – 8 (Proficient / Solid)`: Completed assigned tasks, demonstrated working implementation, solid conceptual grasp, asks insightful questions.
  - `5 – 6 (Developing / Needs Guidance)`: Partial implementation, high-level understanding but struggles when questioned on underlying mechanics.
  - `1 – 4 (Novice / Significant Gaps)`: Incomplete tasks without documented blocker analysis, fundamental misconceptions, broken scripts.
- **Unobserved Dimensions**: A dimension or skill with no evidence in the retrieved window is marked `Not Observed in Transcripts`, never guessed.
- **Factual Misconception Diagnosis**: A misconception requires explicit transcript proof showing the mentee held an inaccurate assumption or was corrected by the mentor.
- **Binary Verification Criteria**: Next tasks must define concrete, testable outcomes (e.g. *"Demonstrate working module passing 3 test cases"* rather than *"Understand concept"*).
- **Full Timeline Coverage (July — August)**: Evaluate mentee learning trajectories across the entire cohort, tracking how guidance given in early July was applied in late July and August wrap-up sessions.

## Mechanical Checks
- **Quote Substring Verification**: Every quote must be verified as an exact verbatim substring from the retrieved transcript chunks.
- **Speaker Attribution Integrity**: Normalize speaker turns before attributing statements to mentor vs. mentee.
- **Hardcode Self-Check**: Before deployment, grep this file itself for any named project tool or deliverable. Zero should match.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| *"They usually do well, round up the score"* | Grade inflation defeats the purpose of objective pedagogical evaluation. Score strictly from this run's evidence. |
| *"They probably understand this concept"* | Confidence or silence is not evidence of technical mastery. Mark `Not Observed`. |
| *"Close paraphrase reads fine as a quote"* | A citation is an auditable claim. Substring-verify or relabel as paraphrase. |
| *"Assign a generic 'study topic' task"* | Unfalsifiable goals cannot be verified. Scope to a concrete, binary outcome. |

## Red Flags
Score without supporting evidence · misconception inferred without explicit dialogue · quote not substring-verified · August timeline sessions omitted · any named deliverable/tool in this file's own text.

## Before Deploying
Test with a transcript window where a mentee struggled with a concept or where a topic was not discussed. Confirm the output reflects the real transcript evidence dynamically without hallucinating mastery.
