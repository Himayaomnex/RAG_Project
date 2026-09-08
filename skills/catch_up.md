# Skill: catch_up

Derived from her `session_catchup.md` workflow, steps 1-2.

## Signature

`catch_up(date: str, person: str | None = None) -> EvidenceItem[]`

## When the agent should call it

The request is about one specific session — "what did I miss on X", "what happened in
Tuesday's meeting".

## Procedure

1. **Normalise the date to ISO before any call.** Every downstream source requires it. The
   previous implementation passed a natural-language date straight to the database, which
   silently returned nothing on every date-scoped request.
2. `get_session_digest(date)` — usually answers most of the request in one call
3. `get_assignments(period=date)` and `get_decisions(period=date)`
4. Only if the digest is missing or thin: one `search_transcripts(date=date)` for technical
   detail

## Returns

Evidence items scoped to the single session date.

## Cost

Typically 3-4 calls, ~8-14k tokens. The cheapest of the three skills.

## Failure

If the date does not resolve to a session, return empty with `found_nothing=true` and
`reason="no session on that date"`. Do not silently widen the window — if the agent wants a
neighbouring session it must ask for it explicitly.
