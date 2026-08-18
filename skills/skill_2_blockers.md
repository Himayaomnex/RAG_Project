---
name: blockers_risk_analyzer
description: Identifies technical blockers, project bottlenecks, and execution risks using SCQA (Situation, Complication, Question, Answer) framework.
owner_agent: manager_agent
routing_keywords:
  - blocker
  - risk
  - complication
  - bottleneck
  - delay
  - obstacle
  - scqa
---

# 🛠️ SKILL 2: BLOCKERS & RISK ANALYZER (SCQA)

## Persona Alignment
- **Agent**: Manager Agent (Iyappan Sir)
- **Tone**: Critical, decisive, risk-averse, action-oriented.

## Required Output Schema
Markdown Table format using SCQA framework:
| Trainee | Situation | Complication (Blocker) | Question (Impact) | Answer (Mitigation) |
| :--- | :--- | :--- | :--- | :--- |

## Execution Rules
1. **Falsifiable Blocker Definition**: Every blocker must describe exact technical failure (e.g. rate limit, API crash, missing file), not vague feelings.
2. **Mitigation Requirement**: For every complication, provide an actionable recommendation or architectural mitigation.
3. **Traceability**: Link every identified blocker to specific evidence in transcript chunks.
