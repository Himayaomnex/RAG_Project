# Skill: assess_person

A skill is a **recipe** — a fixed sequence of tool calls the agent can invoke as a single
action instead of planning the sequence itself. Registered in the tool registry.

Derived from her `trainee_assessment.md` workflow. The steps that were genuine data-gathering
are KEPT and become this recipe. The steps that were reasoning instructions are gone — they
belong to the compose prompt. The steps that were checks are gone — they belong to the
verifier.

## Signature

`assess_person(person: str, period: str | None = None) -> EvidenceItem[]`

## When the agent should call it

The request is about one person's progress, capability or learning over a period. Cheaper and
more consistent than planning four separate KB calls.

## Procedure

1. `get_concepts(person)` — concept coverage and understanding state
2. `get_qa_events(person, period)` — questions asked, answered, deflected
3. `get_feedback(person, period)` — coaching received
4. `get_assignments(person)` — what was given and what state it reached
5. If any of 1-4 returns a state worth substantiating, one `search_transcripts` filtered to
   that person and the relevant date — for the language behind the fact

## Returns

Evidence items only. **A skill never composes an answer** — it gathers, and the agent
composes. This is what keeps a skill reusable across capabilities.

## Cost

Typically 4-5 tool calls, ~12-18k tokens. Counted against the request budget like any other
call.

## Failure

If steps 1-4 all return empty, return empty with `found_nothing=true`. Do not fall back to a
broad transcript search — that decision belongs to the agent, which can see the budget.
