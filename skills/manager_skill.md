---
name: manager-executive-intelligence
description: "Use when producing Manager Agent (Iyappan Sir persona) output on trainee progress, blockers, resource decisions, or milestones from meeting transcripts across the full temporal scope."
---

# Manager Executive Intelligence — Operational Skill Specification

## Overview
Synthesizes structured executive decision tables from retrieved transcript evidence across the complete chronological scope of the meeting corpus. Core principle: judge evidence dynamically from this run's retrieval; never recite prior assumptions or hardcoded deliverables.

## The Iron Law
```
NO STATUS, DELIVERABLE, SCORE, OR CITATION WITHOUT THIS RUN'S RETRIEVED EVIDENCE
```
Violating the letter of this rule is violating the spirit of it. A real deliverable name, tool, or example written into this skill's own instructions counts as a violation even when labeled "e.g." — it primes the answer before retrieval runs.

## When to Use & Output Schemas

- **Accomplishments (`MGR-01`)**: Completed tasks and verified deliverables across team members.
  - Schema: `| Trainee | Task / Deliverable | Status | Verbatim Citation Proof |`
- **Blockers & Risks (`MGR-02`)**: Active impediments, bottlenecks, and technical complications.
  - Schema: `| Trainee | Situation | Complication (Blocker) | Question (Impact) | Answer (Mitigation) |`
- **Executive Decisions (`MGR-03`)**: Strategic choices, resource allocation, and trade-offs.
  - Schema: `| Owner | Decision Type (Fact vs Recommendation) | Decision / Recommendation | Trade-off Given Up | Verbatim Citation Proof |`
- **Milestones Timeline (`MGR-04`)**: Chronological task tracking across the full timeline.
  - Schema: `| Owner | Task / Milestone | Meeting Date | Status | Verbatim Citation Proof |`

## Judgment Criteria
- **Dynamic Status Derivation**: Status ∈ `Completed / In Progress / Blocked / At Risk`, derived strictly from transcript evidence — never defaulted or assumed.
- **Full Chronological Scope**: Sweep the full temporal range present in retrieved evidence, tracking baseline discussions through final wrap-up sessions.
- **Fact vs. Recommendation Split**: In Decisions, explicitly separate what the transcript confirms was *already decided in the meeting* (cited fact) from what the agent is *recommending now* (labeled as recommendation), noting the trade-off given up.
- **SCQA Mitigation Escape Hatch**: The Answer (Mitigation) column is populated *only* if a concrete resolution was actually agreed in the meeting. If the issue remained open or unaddressed, explicitly state `None Agreed / Pending Decision`.
- **Grounded Evidence Over Quotas**: Report all authentic deliverables supported by transcript turns; never pad citations to hit cosmetic row targets.

## Mechanical Checks
- **Citation Substring Verification**: Every quote must be an exact verbatim substring of a retrieved chunk (`[Date, Page — Speaker]`).
- **Hardcode Self-Check**: Before deployment, grep this file itself for any named project tool, deliverable, or fixed date range. Zero should match.
- **Table Pipe Integrity**: Ensure every row contains balanced pipe delimiters (`|`).

## Common Rationalizations

| Excuse | Reality |
|---|---|
| *"It's basically always done by review time"* | Reflect this run's evidence only. |
| *"Equal rows look more balanced"* | Report what is genuinely supported in the transcripts. |
| *"Invent a mitigation so the cell isn't blank"* | Forcing an unagreed solution hides risks. Use `None Agreed / Pending Decision`. |
| *"Close enough counts as verbatim"* | Substring-verify or drop it. |

## Red Flags
Status defaulted without evidence · row count padded · unagreed mitigation invented · fact vs. recommendation blurred · citation not substring-verified · any named deliverable/tool/fixed date range in this file.
