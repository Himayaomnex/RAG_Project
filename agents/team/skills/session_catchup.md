# Skill Specification: team_session_catchup

## Purpose
Enables a trainee who missed a training session to resume work immediately. Distills what happened into actionable requirements: technical concepts discussed, assignments given, decisions reached, important changes, and what the absent person must do.

## Inputs
- `date`: Requested meeting date string (e.g. "2026-07-24" or "24 July 2026") — required.
- `trainee`: Optional requesting trainee name ("Himaya", "Ganesh", or "Dakshinya") to filter items specifically relevant to them.

## Required Workflow
1. **Identify Requested Session**: Resolve the target date from query.
2. **Retrieve Session Evidence**: Query Dakshinya's retrieval service for all turns on that date.
3. **Identify Major Technical Discussions**: Isolate architecture and implementation topics explored in the session.
4. **Identify Assignments Given**: Extract specific tasks assigned by the mentor with binary verification criteria.
5. **Identify Decisions Made**: Note framework, tool, or design choices settled in the session.
6. **Identify Changes & Blockers**: Note bug fixes or architecture shifts that affect teammate code.
7. **Filter for Requesting Trainee**: Highlight items directly assigned to or impacting the requesting mentee.
8. **Produce Actionable Catch-Up**: Synthesize clear, prose sections following the locked output shape.
9. **Self-Check**: Verify every assignment and decision traces back to a dialogue turn on that date.

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
