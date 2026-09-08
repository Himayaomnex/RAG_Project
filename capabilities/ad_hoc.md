# Capability: ad_hoc

New. No equivalent in the original system — and it is the point of the redesign.

## Consumer

Whoever asked. Anyone.

## Purpose

Answer a question nobody designed a capability for, using the same tools, budget and
verification as every other capability. This is the capability that makes the claim *"the
agent can do whatever we want"* true rather than aspirational.

## When the agent should choose it

When the request does not fit `mentor_assessment`, `manager_rollup` or `team_catchup`.
Prefer a specific capability when one fits — its verifier is stricter and its output is more
useful. `ad_hoc` is the fallback, not the default.

## Inputs

- `task` (the raw request)

## Tool hints

None. The whole action space is available.

## Default budget

30,000 tokens · 6 tool calls

## Output schema

```json
{
  "question": "string",
  "answer": "string",
  "claims": [{"claim": "string", "evidence_ids": ["string"]}],
  "uncertainty": "string | null",
  "coverage_note": "string | null"
}
```

## Abstention

`uncertainty` states what could not be established. `answer` may legitimately be *"the
evidence does not answer this"* — that is a success, not a failure.

## Verification rules

| # | Rule | Failure |
|---|---|---|
| V1 | Every `evidence_ids` entry exists in the assembled evidence | invented citation |
| V2 | Every factual assertion in `answer` appears as an entry in `claims` | unevidenced prose |
| V3 | If evidence was dropped or a tool failed, `coverage_note` is non-null | silent incompleteness |

V2 is what keeps the permissive schema honest: the prose may be free-form, but every fact
inside it has to be enumerated and cited.
