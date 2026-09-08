# Repair prompt — one per failed verification

Template. Called only when the verifier returns violations. Bounded by `max_repair_attempts`.

---

Your previous output failed verification. Fix **only** what is listed. Do not rewrite parts
that passed, do not add new claims, do not remove valid content.

## Violations

{{violations}}

Each violation is:
```
field: <json path>
rule:  <which rule failed>
found: <what you produced>
why:   <the specific reason>
```

## Your previous output

{{previous_draft}}

## Evidence available (unchanged)

{{assembled_evidence}}

## Produce

Return the **complete corrected JSON object**, not a diff and not only the changed fields.

If a violation cannot be fixed with the evidence you have — for example, a claim whose
supporting evidence does not exist — **remove that claim and use the abstention value**.
Removing an unsupported claim is always the correct fix. Never invent an evidence id to
satisfy a citation rule; that converts a caught error into an uncatchable one.
