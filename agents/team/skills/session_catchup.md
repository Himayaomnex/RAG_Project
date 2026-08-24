# Skill Specification: team_session_catchup

## Purpose
Enables a trainee who missed a training session to continue working immediately. Serves the request: "I missed the session. Tell me what I need to know to keep going." A chronological retelling of the meeting fails review; the output is what the absent person must know and do — nothing more.

## Inputs
- `date`: Requested session date string (e.g. "2026-07-31" or "31 July 2026")
- `trainee`: Optional requesting trainee name (to filter for what concerns them)

## Required Workflow
1. **Identify the requested session**: Resolve the target date from query.
2. **Retrieve the session's evidence**: Query the retrieval service for all turns on that date.
3. **Identify the major technical discussions**: Isolate architecture and implementation topics explored in the session.
4. **Identify assignments given**: Extract specific tasks assigned by the mentor with binary verification criteria.
5. **Identify decisions made**: Note framework, tool, or design choices settled in the session.
6. **Identify changes and blockers**: Note bug fixes or architecture shifts that affect teammate code.
7. **Filter for the requesting trainee**: Highlight items directly assigned to or impacting the requesting trainee.
8. **Produce the actionable catch-up**: Synthesize clear, prose sections following the defined output schema.
9. **Self-check against evidence**: Verify every assignment and decision traces back to a dialogue turn on that date.

## Evidence Requirements
- Discard chronological storytelling, mic checks, and conversational chatter.
- Focus 100% on actionable knowledge: what was built, what broke, what was decided, what to code next.
- Cite `[Date, Page — Speaker]` for every point.

## Failure Behavior
- If no transcript chunks exist for the specified date, output `INSUFFICIENT_EVIDENCE`.
- If an assignment has no explicit owner, label it `Team-Wide Action`.

## Output Schema
```
Session · What happened
- 1-2 sentence core objective and takeaway of the session.

Technical concepts discussed
- Key technical topics and architectural mechanics explored [Date, Page — Speaker].

Assignments and actions
- [Owner]: [Task description and binary acceptance criteria] [Date, Page — Speaker].

Decisions
- [Settled technical choices and tool commitments] [Date, Page — Speaker].

Important changes
- [Codebase or system modifications that affect teammates] [Date, Page — Speaker].

What you need to know or do
- Immediate concrete next steps for the requesting trainee to resume work.
```
