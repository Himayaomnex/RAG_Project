# Capability: manager_rollup

Amended from `agents/manager/prompt.md` + `agents/manager/skills/weekly_rollup.md`. Persona
and consumer KEPT. `Routing & Activation Conditions` deleted — there is no router.

## Consumer

The executive manager. Reads for sixty seconds and decides where to intervene. A transcript
summary or an undifferentiated wall of text is a failed output.

## Purpose

Answer: **what do I need to know about the state of the training programme, and where do I
need to step in?**

## Inputs

- `period_start`, `period_end` (optional; default = last 7 days with sessions)
- `person` (optional; default = everyone)

## Tool hints

`get_assignments`, `get_decisions`, `get_session_digest` for state; `search_transcripts`
only to substantiate a blocker or a decision that the KB records without explanation.

## Default budget

35,000 tokens · 6 tool calls

## Output schema

```json
{
  "period": "string",
  "headline": "string",
  "completed":        [{"owner": "string", "item": "string", "evidence_ids": ["string"]}],
  "in_progress":      [{"owner": "string", "item": "string", "evidence_ids": ["string"]}],
  "blocked":          [{"owner": "string", "item": "string", "impact": "string",
                        "agreed_resolution": "string | \"none_agreed\"", "evidence_ids": ["string"]}],
  "decisions":        [{"decision": "string", "owner": "string|null", "evidence_ids": ["string"]}],
  "needs_your_call":  [{"question": "string", "why_now": "string", "evidence_ids": ["string"]}],
  "coverage_note": "string | null"
}
```

## Abstention values

`"none_agreed"` for an unresolved blocker. `coverage_note` states what the report could not
cover and why — set it whenever the assembler dropped evidence or a tool failed.

## Verification rules

| # | Rule | Failure |
|---|---|---|
| V1 | Every `evidence_ids` entry exists in the assembled evidence | invented citation |
| V2 | Every `completed` item cites evidence stating completion — not merely absence of a contradiction | inferred completion |
| V3 | Every `blocked` item has `agreed_resolution` set, using `none_agreed` where none was reached | invented mitigation |
| V4 | Every item's `owner` is a person returned by `list_people` | invented owner |
| V5 | If any evidence was dropped or any tool failed, `coverage_note` is non-null | silent incompleteness |

V2 is the direct replacement for the status-falsification incident. The old system forced
every status to "Completed"; here, a completed claim that cannot cite completion is rejected
by code.
