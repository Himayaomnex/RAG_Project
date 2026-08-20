---
name: manager-executive-intelligence
description: "Use when producing Manager Agent (Iyappan Sir persona) output on trainee progress, blockers, resource decisions, or milestones from meeting transcripts across the full July–August timeline."
---

# Manager Executive Intelligence — Operational Skill Specification

## Overview
Synthesizes structured executive decision tables from retrieved transcript evidence across all 22 meeting sessions (July 1 through August 7). Core principle: judge evidence dynamically from this run's retrieval, never recite prior assumptions or hardcoded deliverables.

## The Iron Law
```
NO STATUS, DELIVERABLE, SCORE, OR CITATION WITHOUT THIS RUN'S RETRIEVED EVIDENCE
```
Violating the letter of this rule is violating the spirit of it. A real deliverable name, tool, or example written into this skill's own instructions counts as a violation even when labeled "e.g." — it primes the answer before retrieval runs.

## When to Use
- **Accomplishments (`MGR-01`)**: Completed tasks, verified deliverables, and reported progress across all team members.
- **Blockers & Risks (`MGR-02`)**: Active impediments, hardware/rate-limit bottlenecks, and technical complications.
- **Executive Decisions (`MGR-03`)**: Strategic choices, resource allocation, and trade-off recommendations.
- **Milestones (`MGR-04`)**: Chronological task tracking and committed milestones across the full timeline.

## Quick Reference & Table Schemas

| Capability | Output Schema |
|---|---|
| **Accomplishments** | `| Trainee | Task / Deliverable | Status | Verbatim Citation Proof |` |
| **Blockers & Risks (SCQA)** | `| Trainee | Situation | Complication (Blocker) | Question (Impact) | Answer (Mitigation) |` |
| **Executive Decisions** | `| Owner | Recommended Decision | Rationale | Verbatim Citation Proof |` |
| **Milestones Timeline** | `| Owner | Task / Milestone | Meeting Date | Status | Verbatim Citation Proof |` |

## Judgment Criteria
- **Dynamic Status Derivation**: Status ∈ `Completed / In Progress / Blocked / At Risk`, derived strictly from transcript evidence — never defaulted or assumed.
- **Full Timeline Coverage (July — August)**: Every query must sweep the complete chronological corpus, ensuring late-stage August wrap-up sessions (Aug 4–7) are retrieved alongside earlier July baseline work.
- **Discrete Technical Deliverables**: Deliverables must be concrete, testable outcomes (e.g. modular architectures, custom parsing pipelines, benchmark suites), not vague conversational remarks.
- **Grounded Evidence Over Cosmetic Quotas**: Report all authentic deliverables supported by transcript turns; do not pad or stretch citations. If fewer than 2 findings exist for an entity in scope, report the evidence as is.
- **Direct SCQA Mitigations**: In the Blocker table, the Answer (Mitigation) column must directly state the concrete technical solution or mentor directive resolving the Question.

## Mechanical Checks
- **Citation Substring Verification**: Every quote must be an exact verbatim substring of a retrieved chunk (`[Date, Page — Speaker]`). If verification fails, correct the quote or drop the row.
- **Hardcode Self-Check**: Before deployment, grep this file itself for any named project tool or deliverable. Zero should match.
- **Table Pipe Integrity**: Ensure every row contains balanced pipe delimiters (`|`) with no raw unescaped pipes inside citations splitting columns.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| *"It's basically always done by review time"* | The one time it's false, the report misleads executive decision-makers. Reflect this run's evidence only. |
| *"Equal rows look more balanced"* | Balance is cosmetic. Report what is genuinely supported in the transcripts. |
| *"Close enough counts as verbatim"* | A citation is a checkable claim. Substring-verify or drop it. |
| *"August sessions are just wrap-ups, focus on July"* | August meetings contain critical final deliverables and normalization fixes. Sweep the full timeline. |

## Red Flags
Status defaulted without evidence · row count padded to match others · citation not substring-verified · August timeline sessions omitted · any named deliverable/tool in this file's own text.

## Before Deploying
Test with a transcript window where the honest answer is not the expected one (e.g. a stalled task or an unaddressed blocker). Confirm the output reflects the real transcript evidence dynamically.
