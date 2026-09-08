# Tool registry

The agent's action space. Rendered into the plan prompt every turn. The agent does not know
or care which entries are HTTP calls, SQL queries, sandboxed code, composite skills, or MCP
tools — it sees one uniform list of actions.

**Two hard rules for every tool in this file:**

1. **No tool returns an empty result to mean it failed.** A tool that fails raises. A tool
   that legitimately found nothing returns empty *with* `found_nothing=true` and a `reason`.
   This distinction is what lets the harness emit `KB_UNAVAILABLE` instead of silently
   answering as if the knowledge base were merely empty.
2. **Every tool reports its token cost.** The wrapper measures the serialised result with the
   tokenizer and returns `tokens` alongside the data, so the budget stays truthful.

---

## 1 · Retrieval — Dakshinya's service (System 2)

**Base URL:** `RETRIEVAL_API_URL`, default `http://127.0.0.1:8000`
**Local run:** `python -m uvicorn rag_platform.api.app:app --host 127.0.0.1 --port 8000`
from her repo (branch `feature/my-updates`).

### 1.1 `search_transcripts`

Model-facing description:
> Search meeting dialogue for what was actually said. Use for exact language, quotations, and
> detail the knowledge base does not hold. Filter by speaker or date when you know them.

Signature: `search_transcripts(query, speaker=None, date=None, strategy="exp1", k=None, collection="teams_dense_collection_normalized")`

Wire call — `POST {base}/retrieve`:

```json
{
  "query": "what did Ganesh say about the KB schema",
  "collection": "teams_dense_collection_normalized",
  "strategy": "exp1",
  "use_reranker": true,
  "top_k": 15,
  "speaker": "Ganesh Krishna",
  "date": "14 July 2026"
}
```

`query` and `collection` are **required**. The rest are optional.

**Strategies** — pass through from her service, choose by intent:

| value | what it does | when the agent should pick it |
|---|---|---|
| `exp1` | scroll + custom reranker, precision-first | a specific claim, a named person, a known date |
| `exp2` | expanded scroll, completeness-first | "everything about X", broad sweeps |
| `exp3` | document-balanced, one-ish chunk per session | "across the whole programme", coverage over depth |
| `exp4` | single-pass full corpus | whole-corpus questions; expensive, use last |

**Response** — note the key names, they are *not* what you would guess:

```json
{"trace_id": "...", "strategy": "exp1", "total_chunks": 15,
 "documents_covered": ["AI_ML- Training  (28).docx"],
 "chunks": [{"id": "...", "score": 0.81, "file": "...", "speaker": "...",
             "date": "14 July 2026", "page": "3-4", "text": "..."}]}
```

**Mapping into `EvidenceItem` — do this in the tool wrapper, not in the agent:**

| her key | our field | note |
|---|---|---|
| `id` / `point_id` | `id` | the citable identity; **never invent one** |
| `score` | `relevance` | the assembler orders by this — the previous implementation fetched it and threw it away |
| `file` | `origin.source_file` | her key is `file`, not `source_file` |
| `speaker`, `date`, `page` | `origin.*` | |
| `text` | `content` | |

**Do not send `top_k: null`.** Her handler does `payload.top_k or 15`, so an explicit null
silently collapses every strategy to 15 chunks. Omit the key entirely, or send a real number.

### 1.2 `list_speakers` / `list_sessions`

> List everyone who appears in the corpus. / List session dates, optionally within a window.
> Use before assuming a window is empty.

`GET {base}/filters/metadata?collection=<collection>` returns available speakers and dates.
**Always pass `collection`** — it defaults server-side to the *raw* collection, so omitting it
means you discover names from one corpus and then filter against another.

### 1.3 `POST /query` — deliberately not exposed

Her `/query` runs retrieval *and* her own LLM. We only want evidence; we compose ourselves.
Calling it would mean paying for a second generation we throw away. Use `/retrieve`.

### 1.4 Known contract hazards

- **Two collections, drifted.** `teams_dense_collection` (raw) and
  `teams_dense_collection_normalized` (speaker-corrected). Default to **normalized**. The raw
  one carries Teams' ~25% speaker mis-attribution.
- **Filename conventions differ between them** — raw stores `AI_ML- Training  (28).docx`
  (two spaces), normalized stores one space. A `source_file` filter written for one silently
  matches nothing in the other.
- **Normalized lags.** It may be missing the most recent sessions. If a recent date returns
  nothing there, retry against raw before concluding the session does not exist — and say so
  in `coverage_note`.

---

## 2 · Knowledge base — Ganesh's Supabase (System 3)

**Connection:** `KB_DSN` from `.env`. Read-only role. **Never hardcode it in source.**
Access is direct SQL over `psycopg` — there is no HTTP API for the KB.

Query the **views**, not the base tables. Ganesh's views do the joins.

| Tool | View | Model-facing description |
|---|---|---|
| `get_person_state(person)` | `kb.v_person_state` | Current rolled-up state for one person: open and completed work, concept counts, feedback counts. One cheap call — start here for "how is X doing". |
| `get_assignments(person?, status?, period?)` | `kb.v_assignments`, `kb.v_assignments_current` | Assignments with owner, due date, and current state. |
| `get_qa_events(person?, period?)` | `kb.v_qa` | Questions asked and answered, with answer quality and who resolved them. |
| `get_concepts(person?)` | `kb.v_concepts` | Concepts covered and each person's demonstrated understanding state. |
| `get_feedback(person?, period?)` | `kb.v_feedback` | Coaching feedback given, with topic and sentiment. |
| `get_decisions(period?)` | `kb.v_decisions` | Decisions recorded, with owner and rationale. |
| `get_session_digest(date)` | `kb.v_digests` | Per-session summary and per-person delta. The cheapest way to answer "what happened on X". |
| `get_patterns(person?)` | `kb.v_patterns` | Observed behavioural patterns per person. |
| `list_people()` | `kb.person` | Canonical names the KB knows. Use to validate an owner before naming one. |

### 2.1 Non-negotiable query rules

- **Always filter `extractor_version = 'taxonomy-v3'`.** The table may hold facts from more
  than one extractor generation. Without this filter a query can return two contradictory
  versions of the same fact with no way to tell them apart.
- **Normalise dates to ISO (`YYYY-MM-DD`) before the query.** Passing a natural-language date
  like `"July 28"` throws an invalid-datetime cast, which the previous implementation caught
  and turned into an empty list — so every date-scoped KB lookup silently returned nothing
  and nobody noticed for a week.
- **Parameterise everything.** `cur.execute(sql, params)`. Never f-string a value into SQL.
- **`evidence_line_ids` do not resolve inside Postgres.** They are pointers of the form
  `AI_ML- Training  (1)|t0000|l000` into the normalisation output (`transcript.jsonl`). If a
  capability needs the underlying line, fetch it through `search_transcripts`, not the KB.

### 2.2 Failure

A connection error, a bad DSN, or a schema error must **raise**, producing status
`KB_UNAVAILABLE`. It must never return `[]`. "The database is down" and "this person has no
assignments" are different answers and the report must be able to say which one it got.

---

## 3 · Compute — the execution tools

This is how the agent does arithmetic, aggregation, and artifact generation instead of asking
a language model to do maths. Anything countable should be counted here.

### 3.1 `run_python` — the primary execution tool

> Run Python to compute over evidence you have already gathered, or to produce a file.
> Use this for any counting, aggregation, sorting, date arithmetic, or spreadsheet output.
> Do not use it to fetch data — use the retrieval and knowledge-base tools for that.

Signature: `run_python(code: str, inputs: dict | None = None) -> {stdout, result, files, tokens}`

- Runs in a **subprocess with a timeout** (default 30 s) and a memory cap.
- **No network.** Data comes from tools, not from the code.
- Import allowlist: `json, csv, re, math, statistics, datetime, collections, itertools,
  pathlib, openpyxl, pandas`. Anything else raises.
- Writes are confined to a per-run scratch directory. Files it creates are returned as paths
  in `files` and can be passed to `write_artifact` or `drive_upload`.
- `inputs` is injected as a dict named `data` — normally the evidence items the agent wants
  to compute over, so it never has to paste them into the code as a literal.
- Only `stdout` and an explicitly assigned `result` variable come back. A 400-row DataFrame
  printed in full will blow the budget; the wrapper truncates and says so.

Typical use: the `evaluation_filler` capability computing six weighted dimension scores from
KB rows and writing the spreadsheet — arithmetic that must be exact and reproducible, which
is precisely what an LLM should not be doing in its head.

### 3.2 `run_shell` — gated, off by default

> Run a shell command. Available only when the task requires it and the harness was started
> with shell access enabled.

Signature: `run_shell(command: str) -> {stdout, stderr, exit_code}`

**Enabled by `ALLOW_SHELL=true` only. Default is off.** When enabled:

- Allowlist of first tokens: `git`, `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `find`,
  `python`, `pytest`. Anything else is refused before execution.
- Hard-blocked regardless of allowlist: `rm`, `mv`, `curl`, `wget`, `ssh`, `pip install`,
  anything containing `>` redirection, anything touching `.env` or `credentials`.
- Runs in the repository directory with a 30 s timeout.
- **Every invocation is written to the trace in full, before it runs.**

**Why it is gated and `run_python` is not.** Everything this system actually needs — compute,
aggregation, spreadsheets — `run_python` does in a sandbox with no network. `run_shell` adds
reach over a machine holding live database credentials and cloud keys, and adds essentially
no capability for the real use cases. Turn it on for a task that genuinely needs git or a
test run; leave it off the rest of the time.

### 3.3 `write_artifact`

> Save a produced file so a human can collect it.

Signature: `write_artifact(path: str, content: bytes | str) -> {path, bytes}`
Confined to the configured output directory. Overwrites deterministically — the same run
producing the same artifact twice must not mint a timestamped duplicate.

---

## 4 · Skills — composite recipes (see `skills/`)

| Tool | Model-facing description |
|---|---|
| `assess_person(person, period?)` | Gather everything needed to assess one person's progress. Cheaper than planning the four knowledge-base calls yourself. |
| `summarize_period(start, end, person?)` | Gather everything needed for a state-of-work report over a window. |
| `catch_up(date, person?)` | Gather everything needed to brief someone who missed one session. |

Skills gather evidence. **A skill never composes an answer** — that is what keeps it reusable
across capabilities.

---

## 5 · External — MCP

| Tool | Model-facing description |
|---|---|
| `github_search_code(query, repo?)` | Search the team's repositories. Use when a claim is about code rather than conversation. |
| `github_read_file(repo, path, ref?)` | Read one file from a repository. |
| `drive_upload(file_path, folder_id?)` | Upload a produced artifact. **Side-effecting** — call only when the task explicitly asks for delivery, and never speculatively. |

MCP is a transport, not a category. These appear in the same list as everything else.

---

## 6 · What the agent sees

Only the name, signature, and one-line description — never this document. Write those
descriptions for a reader choosing between fifteen options under a budget:

```
search_transcripts(query, speaker?, date?, strategy?, k?)
    Search meeting dialogue for what was actually said. Use for exact language and
    quotations. Filter by speaker or date when you know them.

get_person_state(person)
    Current rolled-up state for one person. One cheap call — start here for
    "how is X doing".

run_python(code, inputs?)
    Compute over evidence you already have, or produce a file. Use for any counting,
    aggregation or spreadsheet output. Not for fetching data.
```

---

## 7 · Maintenance

**Adding a tool:** implement it with a typed signature and a raising failure mode; add a row
here with the description the model will see. Nothing else — no routing change, no capability
change, no prompt change. That is the test of whether this architecture is holding.

**Retiring:** a skill the agent has not chosen in a month gets deleted. A tool sequence the
agent repeats often becomes a skill. Keep the list small enough to choose from — every extra
tool costs tokens on every planning turn and makes the choice harder.
