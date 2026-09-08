# Plan prompt — one per planning turn

Template. The harness fills every `{{slot}}`.

---

## Task

{{task}}

## Contract you are fulfilling

{{capability_name}} — {{capability_purpose}}

## Actions available

{{tool_registry}}

## What you have gathered so far

{{observations}}

*(turn, tool called, arguments, how many items returned, tokens added — empty on the first turn)*

## Evidence currently held

{{evidence_summary}}

*(id, source, origin, relevance, tokens — one line each)*

## Your budget

- Tokens remaining: **{{budget_remaining}}** of {{budget_total}}
- Tool calls remaining: **{{calls_remaining}}** of {{calls_total}}

## Decide

Return exactly one JSON object. No prose outside it.

To call a tool:
```json
{"thought": "why this call, in one sentence", "action": "tool_call",
 "tool": "<name>", "args": {}}
```

To finish gathering:
```json
{"thought": "why the evidence is now sufficient", "action": "ready_to_compose"}
```

To stop because you cannot proceed:
```json
{"thought": "what is missing and why more searching will not help",
 "action": "abort", "status": "INSUFFICIENT_EVIDENCE"}
```

### How to decide well

- If you have not looked at the KB yet and the question is about state, look there first.
- Do not repeat a search you have already run. Change a parameter or change source.
- If two calls in a row returned nothing useful, the evidence probably does not exist —
  abort rather than burning the budget.
- Stop gathering when more evidence would not change your answer, not when the budget runs
  out. Leaving budget unspent is a good outcome.
