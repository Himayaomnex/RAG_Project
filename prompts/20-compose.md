# Compose prompt — one per request

Template. Called once, when the agent declares `ready_to_compose`.

---

## Task

{{task}}

## Contract

{{capability_contract}}

*(purpose, consumer, and the full output schema with field descriptions)*

## Evidence

{{assembled_evidence}}

Each item appears as:
```
[id] source=rag|kb  origin={date, speaker, page, file | table, row}  relevance=0.00
<content>
```

{{dropped_notice}}

*(Present only if the assembler dropped items: "N items were dropped to fit the budget.
The lowest relevance admitted was X." Take this into account — do not claim completeness
you cannot support.)*

## Style directives from the request

{{style_directives}}

*(KEPT from her original: adapt depth and structure to what the user actually asked for —
a pyramid-principle breakdown, a two-line summary, a table — while keeping every schema
field present.)*

## Produce

Return **only** a JSON object matching the schema in the contract. No preamble, no markdown
fence, no commentary.

Requirements the verifier will check:

- Every item that makes a claim includes `evidence_ids`, and every id in it appears in the
  evidence above.
- Fields with no supporting evidence use the contract's abstention value. Do not omit the
  field and do not guess.
- Numeric fields fall inside the range the schema declares, or use the abstention value.
- Do not paraphrase a quotation. If you quote, it must be a character-exact substring of an
  evidence item.
