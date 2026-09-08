# Capability: mentor_assessment

Amended from `agents/mentor/skills/trainee_assessment.md`. The cognitive ladder, the
abstention wording and the section names are KEPT — they were the strongest content in the
original. What changed: the ten prose workflow stages are gone (the agent plans its own
retrieval), citations became `evidence_ids`, and the markdown schema became JSON so the
verifier can parse it.

## Consumer

The technical mentor. Decides what to teach next and how to score each trainee.

## Purpose

Show a trainee's **demonstrated** progress — not their claimed progress, and not what they
were merely present for.

## Inputs

- `person` (required)
- `period` (optional; defaults to all available)
- `focus_area` (optional)

## Tool hints

Not constraints. `get_concepts`, `get_qa_events`, `get_feedback` for state; then
`search_transcripts` filtered to the person for the language behind a specific claim.

## Default budget

40,000 tokens · 6 tool calls

## Output schema

```json
{
  "person": "string",
  "period": "string",
  "overall": "string",
  "dimensions": [
    {"name": "Preparation|Conceptual depth|Code quality|Engagement",
     "score": "integer 1-10 | \"not_observed\"",
     "reason": "string",
     "evidence_ids": ["string"]}
  ],
  "current_work": [{"item": "string", "evidence_ids": ["string"]}],
  "demonstrated_capabilities": [{"concept": "string", "how_shown": "string", "evidence_ids": ["string"]}],
  "knowledge_gaps": [{"gap": "string", "evidence_ids": ["string"]}],
  "recurring_misconceptions": [{"misconception": "string", "corrected_on": "string|null", "evidence_ids": ["string"]}],
  "feedback_signals": [{"feedback": "string", "evidence_ids": ["string"]}],
  "change_from_previous": "string | \"not_observed\"",
  "next_teaching_action": "string"
}
```

## Abstention value

`"not_observed"` — the schema equivalent of her original *"Not demonstrated from available
evidence."* Valid in any scored or narrative field. **Never penalised.**

## Verification rules

| # | Rule | Failure |
|---|---|---|
| V1 | Every `evidence_ids` entry exists in the assembled evidence | invented citation |
| V2 | Every dimension has a score in 1-10 **or** `not_observed` | out of range / free text |
| V3 | Every dimension with a numeric score has >= 1 evidence id | scored without evidence |
| V4 | **Taught != understood** — every item in `demonstrated_capabilities` cites evidence in which the *person* speaks or acts, not evidence in which they were taught | inferred demonstration |
| V5 | Every `recurring_misconceptions` item cites >= 2 evidence items from different sessions | "recurring" claimed once |
| V6 | If `change_from_previous` is not `not_observed`, it cites evidence from >= 2 distinct dates | trajectory without a baseline |

V4 and V5 are the ones that will actually fire. They are also the two the original prompt
merely asked for.
