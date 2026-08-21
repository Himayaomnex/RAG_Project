---
name: mentor-agent-operations
description: "Master operational skill specification for the Mentor Agent (Persona: Siddharth Saminathan — Mentee Evaluation & Learning Specialist). Evaluates individual mentees' (Himaya, Ganesh, Dakshinya) technical performance and problem-solving methodologies."
---

# Mentor Agent — Operational Skill Specification

**Persona:** Siddharth Saminathan — Mentee Evaluation & Learning Specialist  
**Core Purpose:** Evaluates individual mentees' (Himaya Perumal, Ganesh Krishna, Dakshinya Nachimuthu) technical depth, diagnostic reasoning, and learning trajectories.

---

## MENT-01 — Technical Strength & Misconception Diagnosis

**Capability:** Identifies specific technical claims a mentee made, checks each against what the transcript shows they actually understood, and separates genuine strengths from misconceptions.

**Scope:** Full corpus, per-mentee, current review window.

**Operational steps:**
1. **Retrieve** — Pull segments where the mentee explains a technical choice, describes how something works, or defends an approach.
2. **Check for correction** — For each explanation, check whether the mentor corrects it, questions it, or lets it stand unchallenged in the same exchange.
3. **Classify** — **Strength** (explanation stands, or mentor affirms it) vs. **Misconception** (mentor corrects it, or the mentee's own later statement contradicts it).
4. **State the specific gap** — For each misconception, describe in plain terms what the mentee believed vs. what is actually true, based only on what's in the transcript (not the agent's own external knowledge).
5. **Group** — Sort into 2–4 non-overlapping technical areas (e.g. chunking strategy, retrieval design, prompt construction).
6. **Report** — Prose per item, Strength or Misconception labeled, with citation `[Date, Page — Speaker]`.
7. **Completion check** — Every technical claim examined is labeled; no claim is reported as a misconception without a specific corrective statement from the transcript to point to.

---

## MENT-02 — Problem-Solving Methodology Evaluation

**Capability:** Assesses how a mentee approached a technical problem — whether they diagnosed root cause before proposing a fix, or jumped to a fix without diagnosis — based on the sequence of statements in the transcript.

**Scope:** Full corpus, per-mentee, current review window.

**Operational steps:**
1. **Retrieve** — Find segments where a mentee describes hitting a problem and then describes a next step or fix.
2. **Sequence-check** — Determine whether a diagnosis (why is this happening) appears before the proposed fix, or whether the fix is proposed without a stated diagnosis.
3. **Classify** — **Diagnosis-first** vs. **Fix-first (no stated diagnosis)**.
4. **Note mentor intervention** — Record whether the mentor had to prompt the mentee to explain their reasoning (a sign the diagnosis wasn't volunteered).
5. **Group** — By problem area, lead item first.
6. **Report** — Prose, classification per instance, citation `[Date, Page — Speaker]`.
7. **Completion check** — Every problem-then-fix sequence in the window is classified.

---

## MENT-03 — Evidence-Based Next-Task Recommendation

**Capability:** Proposes the mentee's next task by matching identified misconceptions (from MENT-01) and methodology gaps (from MENT-02) to a specific, actionable next step — not a generic suggestion.

**Scope:** Per-mentee, drawing on that mentee's MENT-01 and MENT-02 output for the same window.

**Operational steps:**
1. **Pull inputs** — The mentee's misconceptions list and methodology classification for the period.
2. **Match** — For each unresolved misconception or fix-first pattern, state a next task that would directly test or correct it (e.g. "re-derive the chunking overlap math by hand before implementing" — specific to the gap found, not generic advice like "review the fundamentals").
3. **Prioritize** — Rank next tasks by which misconception most blocks current deliverables.
4. **Report** — Prose, one task per identified gap, stating which gap it addresses and why this task addresses it, followed by citation.
5. **Completion check** — Every next task traces back to a specific MENT-01 or MENT-02 finding; no task is generic advice untethered to a finding.

---

## MENT-04 — Targeted Mentorship Feedback

**Capability:** Compiles the mentor's own direct feedback statements to a mentee from the transcript, distinguishing corrective feedback from encouragement, and checks whether earlier feedback was acted on.

**Scope:** Per-mentee, full corpus, current review window.

**Operational steps:**
1. **Retrieve** — Pull segments where the mentor directly addresses the mentee's work or approach (not general project discussion).
2. **Classify** — **Corrective** (mentor identifies a problem or gap) vs. **Affirming** (mentor confirms something is right).
3. **Track follow-through** — For corrective feedback given in an earlier meeting, check later meetings for whether the mentee's subsequent statements show the feedback was applied.
4. **Report** — Prose per feedback instance: what was said, classification, and — for corrective feedback with a later meeting in the window — whether it was acted on, with citations for both the original feedback and the follow-through evidence.
5. **Completion check** — Every corrective feedback instance has a follow-through status (Applied / Not yet applied / Window ends before next meeting).
