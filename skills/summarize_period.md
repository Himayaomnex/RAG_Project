# Skill: summarize_period

Derived from her `weekly_rollup.md` workflow, steps 1-3 (the parts that were real code).

## Signature

`summarize_period(period_start: str, period_end: str, person: str | None = None) -> EvidenceItem[]`

## When the agent should call it

The request is about the state of work across a window — a rollup, a status, "what happened
this week", "where are we".

## Procedure

1. `list_sessions(period_start, period_end)` — establish which sessions exist in the window.
   **This step matters:** it is how the agent learns whether the window is empty, rather than
   inferring emptiness from a search that returned nothing.
2. `get_session_digest(date)` for each session in the window (cheap, high signal)
3. `get_assignments(person, period)` — all states, not only open
4. `get_decisions(period)`

## Returns

Evidence items, each carrying its session date so the composer can order chronologically.

## Cost

2 + N calls where N = sessions in the window. For a week, typically 5-7 calls, ~15-25k tokens.
For a month, the agent should narrow the window or accept that the assembler will drop the
oldest, lowest-relevance items.

## Failure

If step 1 returns no sessions, return empty with `found_nothing=true` and `reason="no sessions
in window"`. This is the difference between *"nothing happened"* and *"we could not see"* —
the composer needs it to write an honest `coverage_note`.
