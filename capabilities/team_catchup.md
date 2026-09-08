# Capability: team_catchup

Amended from `agents/team/skills/session_catchup.md`. Purpose and "not a summary" framing
KEPT. The per-person filter moves from a prompt request to verifier rule V3.

## Consumer

A trainee who missed a session and needs to keep working.

## Purpose

Answer: **I missed it — what do I need to know, and what is mine to do?** A chronological
retelling of the meeting is a failed output.

## Inputs

- `date` (required)
- `person` (optional; when present, `assignments_for_you` must be filtered to them)

## Tool hints

`get_session_digest(date)` first — it is one cheap call that often answers most of it. Then
`get_assignments`/`get_decisions` scoped to the date, and `search_transcripts` only for
technical detail the digest lacks.

## Default budget

25,000 tokens · 4 tool calls

## Output schema

```json
{
  "session_date": "string",
  "what_happened": "string",
  "technical_topics":     [{"topic": "string", "summary": "string", "evidence_ids": ["string"]}],
  "decisions":            [{"decision": "string", "evidence_ids": ["string"]}],
  "assignments_for_you":  [{"task": "string", "due": "string|null", "evidence_ids": ["string"]}],
  "assignments_for_others": [{"owner": "string", "task": "string", "evidence_ids": ["string"]}],
  "what_to_do_next": "string"
}
```

## Abstention

Any list may be empty. An empty list is a valid, honest answer — never pad one.

## Verification rules

| # | Rule | Failure |
|---|---|---|
| V1 | Every `evidence_ids` entry exists in the assembled evidence | invented citation |
| V2 | Every cited evidence item's date matches `session_date` | evidence from the wrong session |
| V3 | When `person` is set, every `assignments_for_you` item cites evidence naming that person as owner | someone else's work handed to them |
| V4 | `what_to_do_next` is non-empty only if `assignments_for_you` is non-empty, or it explicitly states there is nothing assigned | invented homework |

V2 exists because the date filter silently failed in the previous implementation — the KB
was queried with an unnormalised date string, returned nothing, and nobody noticed.
