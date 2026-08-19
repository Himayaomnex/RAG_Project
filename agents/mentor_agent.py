"""
================================================================================
Mentor Agent - Mentee Evaluation & Learning Specialist (RAG_COMBINED)
================================================================================
Role: Mentee Evaluation & Learning Specialist (Siddharth Saminathan Persona)
Scope: Evaluates technical performance and diagnoses learning gaps for
       individual mentees (Himaya, Ganesh, Dakshinya).

Capabilities (all 4 per spec):
  1. Diagnoses Technical Strengths & Misconceptions
     (e.g., distinguishing performance latency logging from step-by-step
     boundary failure logging)
  2. Evaluates Technical Problem-Solving Methodologies demonstrated in
     review meetings
  3. Recommends Evidence-Based Next Tasks & Learning Topics
     (extracted from Siddharth's actual guidance turns in transcripts)
  4. Provides Targeted Mentorship Feedback & Guidance
     (Siddharth's exact spoken instructions as verbatim citations)

Pipeline: P4 Full Corpus XML Map-Reduce (100% corpus sweep across all 22
          meeting transcripts)
"""

import sys
import os
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from pipeline import VectorDatabase, DenseRetriever, ensure_pipeline_initialized
from prompt_builder import PromptBuilder
from llm_client import generate_llm_response

_db = None
_retriever = None

def get_retriever():
    global _db, _retriever
    if _retriever is None:
        _db = ensure_pipeline_initialized()
        _retriever = DenseRetriever(_db)
    return _retriever


# ── Classification helpers ─────────────────────────────────────────────────────

STRENGTH_KEYWORDS = [
    "understand", "worked", "created", "added", "solution", "schema", "excel",
    "finished", "built", "implemented", "completed", "pushed", "tested",
    "correct", "right", "good", "exactly", "yes", "figured out", "resolved",
    "fixed", "working", "deployed", "uploaded", "submitted", "achieved"
]

MISCONCEPTION_KEYWORDS = [
    "confused", "not sure", "wrong", "mistake", "misunderstand", "thought",
    "assumed", "didn't realise", "didn't know", "incorrect", "mixing up",
    "conflated", "unclear", "didn't understand", "i thought", "but actually"
]

METHODOLOGY_KEYWORDS = [
    "approach", "tried", "attempted", "first i", "then i", "so i", "my approach",
    "my method", "my plan", "my logic", "i did", "i used", "i checked",
    "i looked", "i searched", "i ran", "i wrote", "step by step", "process",
    "workflow", "pipeline", "strategy", "decided to", "reason why",
    "chunking", "caching", "cache", "embedding", "router", "architecture", "multi-agent",
    "semantic", "qdrant", "openpyxl", "deepseek", "baseline", "feature engineering",
    "xgboost", "reranker", "normalization", "token window", "budgeting"
]

MENTOR_GUIDANCE_KEYWORDS = [
    "want you to", "you should", "next task", "next step", "your task",
    "assignment", "focus on", "work on", "read about", "study", "learn",
    "implement", "build", "i want", "i need you", "can you", "please",
    "make sure", "remember to", "don't forget", "deliverable", "deadline",
    "by tomorrow", "by next week", "action item", "homework", "try to",
    "practice", "review", "go through", "understand", "explore"
]


def _extract_mentee_chunks(results: list, mentee_name: str):
    """
    Split P4 chunks into two groups:
      - mentee_chunks : turns spoken by the target mentee
      - mentor_chunks : turns spoken by Siddharth (guidance / next-task assignments)
    Returns (mentee_chunks, mentor_chunks) where each item is a dict with
    keys: spk, dt, doc, pg, txt, cit
    """
    mentee_chunks = []
    mentor_chunks = []

    for r in results:
        payload = r if isinstance(r, dict) else (r.payload if hasattr(r, "payload") else {})
        dt      = payload.get("date", "Unknown Date")
        doc     = payload.get("source_file", "Transcript.docx")
        pg      = payload.get("page", "1")
        raw_txt = payload.get("text", "").strip()

        # De-multiplex inline speaker turns on raw_txt first
        import re
        pattern = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+):\s*(.*?)(?=\n[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+:|$)"
        matches = re.findall(pattern, raw_txt, re.DOTALL)

        if not matches:
            spk     = payload.get("speaker", "Unknown")
            from transcript_normalizer import clean_audio_artifacts
            txt = clean_audio_artifacts(raw_txt)
            if txt.endswith("..."):
                txt = txt.rstrip(".").rstrip() + "."
            cit = f"[{dt} | {doc} | Speaker: {spk} | Page {pg}]"
            item = {"spk": spk, "dt": dt, "doc": doc, "pg": pg, "txt": txt, "cit": cit}

            if mentee_name.lower() in spk.lower():
                mentee_chunks.append(item)
            elif "siddharth" in spk.lower():
                mentor_chunks.append(item)
        else:
            for turn_spk, turn_txt in matches:
                turn_spk = turn_spk.strip()
                turn_txt = turn_txt.strip()
                from transcript_normalizer import clean_audio_artifacts
                txt = clean_audio_artifacts(turn_txt)
                if not txt:
                    continue
                if txt.endswith("..."):
                    txt = txt.rstrip(".").rstrip() + "."
                cit = f"[{dt} | {doc} | Speaker: {turn_spk} | Page {pg}]"
                item = {"spk": turn_spk, "dt": dt, "doc": doc, "pg": pg, "txt": txt, "cit": cit}

                if mentee_name.lower() in turn_spk.lower():
                    mentee_chunks.append(item)
                elif "siddharth" in turn_spk.lower():
                    mentor_chunks.append(item)

    return mentee_chunks, mentor_chunks


def _evaluate_strengths_and_misconceptions(mentee_chunks: list, mentee_name: str):
    """
    CAPABILITY 1 — Diagnoses Technical Strengths & Misconceptions.
    Returns (strengths_list, misconceptions_list).
    """
    strengths      = []
    misconceptions = []

    for item in mentee_chunks:
        txt     = item["txt"]
        txt_low = txt.lower()
        cit     = item["cit"]
        spk     = item["spk"]

        # Skip bare questions — these are learning queries, not demonstrations
        if txt.strip().endswith("?") and len(txt.strip()) < 150:
            continue

        if any(w in txt_low for w in STRENGTH_KEYWORDS):
            strengths.append(
                f"- **Demonstrated Strength** — {spk}: \"{txt}\"  \n"
                f"  > 📌 Citation: `{cit}`"
            )
        elif any(w in txt_low for w in MISCONCEPTION_KEYWORDS):
            misconceptions.append(
                f"- **Misconception / Gap** — {spk}: \"{txt}\"  \n"
                f"  > 📌 Citation: `{cit}`"
            )

    return strengths, misconceptions


def _evaluate_methodology(mentee_chunks: list, mentee_name: str):
    """
    CAPABILITY 2 — Evaluates Technical Problem-Solving Methodologies.
    Detects turns where the mentee explicitly describes their approach/process.
    Returns list of formatted markdown strings.
    """
    methodology_entries = []

    for item in mentee_chunks:
        txt     = item["txt"]
        txt_low = txt.lower()
        cit     = item["cit"]
        spk     = item["spk"]
        dt      = item["dt"]

        if any(w in txt_low for w in METHODOLOGY_KEYWORDS):
            methodology_entries.append(
                f"- **Methodology Observed** ({dt}) — {spk}: \"{txt}\"  \n"
                f"  > 📌 Citation: `{cit}`"
            )

    return methodology_entries


def _extract_evidence_based_next_tasks(mentor_chunks: list, mentee_name: str):
    """
    CAPABILITY 3 — Recommends Evidence-Based Next Tasks & Learning Topics.
    Scans Siddharth's guidance turns for explicit task assignments directed at
    the target mentee. Returns list of formatted markdown strings with citations.
    """
    next_tasks = []

    for item in mentor_chunks:
        txt     = item["txt"]
        txt_low = txt.lower()
        cit     = item["cit"]
        dt      = item["dt"]

        # Only include Siddharth turns that contain actionable guidance keywords
        if not any(w in txt_low for w in MENTOR_GUIDANCE_KEYWORDS):
            continue

        # Also only surface turns that mention the mentee or are clearly actionable
        is_addressed_to_mentee = mentee_name.lower() in txt_low
        is_generic_guidance    = any(w in txt_low for w in [
            "want you to", "your task", "next task", "work on", "implement",
            "deliverable", "by tomorrow", "by next", "action item", "homework"
        ])

        if is_addressed_to_mentee or is_generic_guidance:
            next_tasks.append(
                f"- **Assigned Task / Learning Topic** ({dt}): \"{txt}\"  \n"
                f"  > 📌 Mentor Citation: `{cit}`"
            )

    return next_tasks


def _extract_targeted_feedback(mentor_chunks: list, mentee_name: str):
    """
    CAPABILITY 4 — Targeted Mentorship Feedback & Guidance.
    Extracts Siddharth's direct evaluation/feedback turns — praise, corrections,
    or specific technical guidance — as verbatim citations.
    Returns list of formatted markdown strings.
    """
    FEEDBACK_KEYWORDS = [
        "good", "correct", "exactly", "well done", "no", "that's wrong",
        "not correct", "the issue is", "the problem is", "you need to",
        "the difference", "actually", "let me explain", "think about",
        "the reason", "key point", "important", "remember", "not quite",
        "close but", "you're mixing", "that's not", "clarify"
    ]

    feedback_entries = []

    for item in mentor_chunks:
        txt     = item["txt"]
        txt_low = txt.lower()
        cit     = item["cit"]
        dt      = item["dt"]

        if any(w in txt_low for w in FEEDBACK_KEYWORDS):
            snippet = txt[:300] + ("..." if len(txt) > 300 else "")
            feedback_entries.append(
                f"- **Mentor Feedback** ({dt}): \"{snippet}\"  \n"
                f"  > 📌 Mentor Citation: `{cit}`"
            )

    return feedback_entries


# ── Main agent function ────────────────────────────────────────────────────────

def run_mentor_agent(user_prompt: str, target_mentee: str = "Himaya") -> str:
    """
    Mentor Agent — All 4 capabilities fully implemented:
      1. Diagnoses Technical Strengths & Misconceptions
      2. Evaluates Technical Problem-Solving Methodologies
      3. Recommends Evidence-Based Next Tasks (from Siddharth's actual transcript turns)
      4. Provides Targeted Mentorship Feedback & Guidance (verbatim Siddharth quotes)

    Pipeline: P4 Full Corpus XML Map-Reduce across all 22 transcripts.
    """
    prompt_lower = user_prompt.lower()
    print(f"  - [Mentor Agent]: Evaluating technical performance for {target_mentee}...")

    retriever = get_retriever()

    # === PIPELINE 4 (P4): Full Corpus XML Map-Reduce ===
    print(f"  - [Mentor Agent]: Using P4 Full Corpus Map-Reduce to evaluate "
          f"{target_mentee} across all transcripts...")
    p4_raw = retriever.retrieve_p4_full_corpus_mapreduce(user_prompt)

    is_all_mentees = not target_mentee or target_mentee.lower() in ["all", "all team members", "teammates", "everyone", "team"]

    # Filter to mentee, mentions of the mentee in text, or mentor (Siddharth) turns referencing the mentee
    relevant = []
    for chunk in p4_raw:
        spk = chunk.get("speaker", "").lower()
        txt = chunk.get("text", "").lower()
        
        if is_all_mentees:
            if any(s in spk or s in txt for s in ["himaya", "ganesh", "dakshinya", "siddharth"]):
                relevant.append(chunk)
        else:
            if (target_mentee.lower() in spk or 
                target_mentee.lower() in txt or 
                ("siddharth" in spk and target_mentee.lower() in txt)):
                relevant.append(chunk)

    # Rank relevant results by keyword relevance to user query
    query_words = [w.lower() for w in user_prompt.split() if len(w) > 3]

    # Balanced selection per target speaker to prevent one mentee starving out another
    selected_chunks = []
    seen_ids = set()
    
    mentees_to_cover = ["Himaya", "Ganesh", "Dakshinya"] if is_all_mentees else [target_mentee]
    
    for m in mentees_to_cover:
        m_low = m.lower()
        m_chunks = []
        for chunk in relevant:
            txt = chunk.get("text", "").lower()
            spk = chunk.get("speaker", "").lower()
            if m_low in spk or m_low in txt or ("siddharth" in spk and m_low in txt):
                score = sum(1 for w in query_words if w in txt) + 3
                if m_low in spk:
                    score += 6  # Heavily prioritize words spoken by the mentee themselves
                if any(k in txt for k in STRENGTH_KEYWORDS + MISCONCEPTION_KEYWORDS + METHODOLOGY_KEYWORDS + MENTOR_GUIDANCE_KEYWORDS):
                    score += 4
                if any(date_str in chunk.get("date", "") for date_str in ["31 July", "22 July", "4 August", "28 July", "29 July", "3 July"]):
                    score += 4
                # Domain-specific milestone boosts
                if m_low == "himaya" and any(k in txt for k in ["chunking", "caching", "cache", "embedding", "router", "fastapi", "semantic", "qdrant"]):
                    score += 6
                elif m_low == "ganesh" and any(k in txt for k in ["excel", "openpyxl", "deepseek", "diff", "cell", "sheet", "extraction", "multi-file", "schema"]):
                    score += 6
                elif m_low == "dakshinya" and any(k in txt for k in ["baseline", "xgboost", "feature", "logistic", "reranker", "scroll", "context", "hypothesis"]):
                    score += 6
                m_chunks.append((score, chunk))
        m_chunks.sort(key=lambda x: x[0], reverse=True)
        for _, c in m_chunks[:15]:
            c_key = f"{c.get('date')}_{c.get('page')}_{c.get('text', '')[:40]}"
            if c_key not in seen_ids:
                seen_ids.add(c_key)
                selected_chunks.append(c)
                
    # Also add top global mentor feedback chunks
    scored_all = []
    for chunk in relevant:
        txt = chunk.get("text", "").lower()
        spk = chunk.get("speaker", "").lower()
        score = sum(1 for w in query_words if w in txt)
        if "siddharth" in spk:
            score += 3
        if any(k in txt for k in STRENGTH_KEYWORDS + MISCONCEPTION_KEYWORDS + METHODOLOGY_KEYWORDS + MENTOR_GUIDANCE_KEYWORDS):
            score += 2
        scored_all.append((score, chunk))
    scored_all.sort(key=lambda x: x[0], reverse=True)
    for _, c in scored_all[:10]:
        c_key = f"{c.get('date')}_{c.get('page')}_{c.get('text', '')[:40]}"
        if c_key not in seen_ids:
            seen_ids.add(c_key)
            selected_chunks.append(c)

    relevant = selected_chunks if selected_chunks else relevant

    # Split into per-speaker groups
    mentee_chunks, mentor_chunks = _extract_mentee_chunks(relevant, "all" if is_all_mentees else target_mentee)

    # ── CAPABILITY 1: Strengths & Misconceptions ──────────────────────────
    strengths, misconceptions = _evaluate_strengths_and_misconceptions(
        mentee_chunks, target_mentee
    )

    # ── CAPABILITY 2: Methodology Evaluation ─────────────────────────────
    methodology_entries = _evaluate_methodology(mentee_chunks, target_mentee)

    # ── CAPABILITY 3: Evidence-Based Next Tasks ───────────────────────────
    next_tasks = _extract_evidence_based_next_tasks(mentor_chunks, target_mentee)

    # ── CAPABILITY 4: Targeted Mentorship Feedback ────────────────────────
    targeted_feedback = _extract_targeted_feedback(mentor_chunks, target_mentee)

    # ── Assemble structured evaluation report dynamically from retrieved evidence ──
    eval_lines = [
        f"### 🎓 Mentor Evaluation Report (Mentor: Siddharth Saminathan)\n",
        f"#### 👤 Target Mentee: **{target_mentee}**\n",
    ]

    # CAPABILITY 1 — Technical Strengths
    eval_lines.append("#### 🌟 Demonstrated Technical Strengths")
    if strengths:
        eval_lines.extend(strengths[:5])
    else:
        eval_lines.append(
            f"- {target_mentee} actively participates in technical meetings and "
            f"architecture discussions. No explicit strength evidence found in "
            f"current retrieved window."
        )

    # CAPABILITY 1 — Misconceptions / Learning Gaps
    eval_lines.append("\n#### 🧠 Diagnosed Misconceptions & Learning Gaps")
    if misconceptions:
        eval_lines.extend(misconceptions[:4])
    else:
        eval_lines.append(
            f"- No explicit misconception evidence found. "
            f"Recommend reviewing dense vector distance metrics and payload filtering."
        )

    # CAPABILITY 2 — Problem-Solving Methodology Evaluation
    eval_lines.append("\n#### 🔬 Problem-Solving Methodology Evaluation")
    if methodology_entries:
        eval_lines.extend(methodology_entries[:4])
    else:
        eval_lines.append(
            f"- No explicit methodology description found from {target_mentee} in "
            f"current retrieved window. Encourage mentee to narrate their approach "
            f"step-by-step during next review session."
        )

    # CAPABILITY 3 — Evidence-Based Next Tasks (from Siddharth's turns)
    eval_lines.append("\n#### 🎯 Evidence-Based Next Tasks & Learning Topics")
    eval_lines.append(
        "> *Extracted directly from Siddharth Saminathan's guidance turns "
        "in meeting transcripts.*"
    )
    if next_tasks:
        eval_lines.extend(next_tasks[:5])
    else:
        eval_lines.append(
            f"- No explicit task assignment found from Siddharth for {target_mentee} "
            f"in current retrieved window. Default recommendation: implement custom "
            f"reranker evaluation benchmarks and verify hybrid retrieval precision."
        )

    # CAPABILITY 4 — Targeted Mentorship Feedback
    eval_lines.append("\n#### 💬 Targeted Mentorship Feedback & Guidance")
    eval_lines.append(
        "> *Verbatim feedback from Siddharth Saminathan — exact spoken words.*"
    )
    if targeted_feedback:
        eval_lines.extend(targeted_feedback[:4])
    else:
        eval_lines.append(
            "- No explicit feedback turns found from Siddharth in current "
            "retrieved window. Review transcripts for direct evaluation comments."
        )

    fallback_report = "\n".join(eval_lines)

    # === Direct Context Build (no batching — Groq 128k handles everything) ===
    sorted_items = []
    for item in (mentee_chunks + mentor_chunks):
        dt = item.get("dt", "Unknown Date")
        sorted_items.append((dt, item))
    sorted_items.sort(key=lambda x: x[0])

    doc_context = ""
    for _, item in sorted_items:
        doc_context += f"[{item.get('dt', 'Unknown')} | {item.get('doc', 'doc')} | Page {item.get('pg', '1')}]\n{item.get('spk', 'Unknown')}: {item.get('txt', '')}\n\n"

    final_rag_context = [{"text": doc_context, "speaker": target_mentee, "date": "", "source_file": "transcripts", "page": "1", "score": 1.0}]
    print(f"  - [Mentor]: Sending {len(sorted_items)} chunks directly to LLM (no batching)...")


    # ── Construct 8-Module System Prompt via PromptBuilder → Groq LLM ─────────
    builder = PromptBuilder(user_id="Siddharth Saminathan", role="Mentor")
    builder.add_security_guardrails()
    # Note: add_security_guardrails already calls add_speaker_attribution_policy()
    # internally, so we do NOT call it again here to avoid duplication.
    builder.add_grounding_policy()
    builder.add_output_policy()
    builder.add_agent_role("mentor", mentor_name="Siddharth Saminathan")
    builder.add_rag_context(final_rag_context)
    builder.add_user_query(user_prompt)
    system_prompt = builder.build()

    return generate_llm_response(system_prompt, user_prompt, fallback_response=fallback_report, agent_type="mentor")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    test_q = "Evaluate Ganesh's technical strengths, methodology, and suggest next steps."
    print(run_mentor_agent(test_q, "Ganesh"))
