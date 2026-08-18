---
name: action_item_delta_tracker
description: Tracks action items, task commitments, trajectory changes (Delta Analysis), and binary verification criteria across meetings.
owner_agent: cross_agent
routing_keywords:
  - action item
  - delta
  - trajectory
  - verification
  - task assignment
  - commitment
  - follow-up
---

# 🛠️ SKILL 5: ACTION ITEM & DELTA TRACKER

## Persona Alignment
- **Agent**: Cross-Agent / Shared Utility (Manager Agent & Mentor Agent)
- **Tone**: Verifiable, accountable, metric-driven.

## Required Output Schema
Markdown Table format:
| Owner | Task Description | Deadline | Binary Verification Criteria (Show X) | Status |
| :--- | :--- | :--- | :--- | :--- |

Followed by Delta Trajectory Summary:
- **Previous Session Baseline**: Initial state/progress.
- **Current Session Progress**: Key changes & milestone completions.
- **Trajectory Verdict**: On-track / At-Risk / Delayed.

## Execution Rules
1. **Binary Verification**: Tasks MUST specify tangible proof (e.g., "Show merged PR", "Run benchmark script", "Display table output") instead of subjective criteria.
2. **Owner Accountability**: Assign explicit single-owner responsibility for each item.
