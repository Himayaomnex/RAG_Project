"""
================================================================================
Manager Agent - Project Status & Executive Summary Specialist (RAG_COMBINED)
================================================================================
Role: Executive Status & Decision Specialist (Iyappan Sir Persona)
Scope: Scans meeting transcripts to track progress, deliverables, and active
       bottlenecks across Himaya, Ganesh, and Dakshinya.

Capabilities (all 4 per spec):
  1. Summarizes Completed Accomplishments & Highlights
  2. Highlights Active Blockers & Risks
  3. Recommends Executive Decisions & Resource Allocation
  4. Tracks Milestone Progress & Task Timelines across team members

Pipeline: P4 Full Corpus XML Map-Reduce (100% corpus sweep, day-by-day coverage)
"""

import sys
import os
import re
from collections import defaultdict

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

ACCOMPLISHMENT_KEYWORDS = [
    "done", "completed", "created", "added", "solution", "schema", "code",
    "built", "implemented", "cache", "finished", "pushed", "merged", "fixed",
    "tested", "deployed", "working", "wrote", "uploaded", "submitted",
    "generated", "output", "result", "achieved", "delivered", "set up",
    "running", "passed", "integrated"
]

BLOCKER_KEYWORDS = [
    "stuck", "block", "problem", "taking long", "didn't start", "issue",
    "error", "delay", "timeout", "couldn't", "could not", "haven't started",
    "not done", "pending", "failing", "not able", "not working", "unable",
    "exception", "failed", "authentication failed", "access denied",
    "not completed", "haven't", "didn't", "not yet"
]

RISK_KEYWORDS = [
    "risk", "trade off", "hard", "difficult", "fail", "challenge",
    "concern", "slow", "bottleneck", "latency", "overloaded", "unclear",
    "ambiguous", "not sure about", "depends on"
]

DECISION_KEYWORDS = [
    "decide", "store", "table", "structure", "choose", "langgraph",
    "database", "deliverable", "want you to", "should we", "can you",
    "need to", "must", "plan to", "architecture", "approach", "strategy",
    "assign", "next step", "action item", "follow up", "target"
]

CONCEPTUAL_NOISE = [
    "why?", "how is that happening", "what is", "how does", "explain to"
]


MENTEE_NAMES_MAP = {
    "himaya": "Himaya Perumal",
    "ganesh": "Ganesh Krishna",
    "dakshinya": "Dakshinya Nachimuthu",
}


def _clean_chunk_text(raw_txt: str) -> str:
    """
    Strips XML document wrapper tags injected by P4 map-reduce
    (e.g. <document name="...">...</document>) and returns the plain
    transcript text, truncated to 300 chars for bullet readability.
    """
    # Strip <document ...> opening tag and </document> closing tag
    txt = re.sub(r'<document[^>]*>', '', raw_txt, flags=re.DOTALL)
    txt = re.sub(r'</document>', '', txt, flags=re.DOTALL)
    txt = txt.strip()
    return txt


def _primary_mentee(spk: str) -> str:
    """
    Extracts the first individual mentee name from a (possibly comma-joined)
    speaker field.  Returns the canonical full name, or the original string
    if no mentee is found.
    """
    for part in spk.split(","):
        part_lower = part.strip().lower()
        for key, full in MENTEE_NAMES_MAP.items():
            if key in part_lower:
                return full
    return spk.split(",")[0].strip()


def _classify_chunk(txt: str, spk: str, dt: str, doc: str, pg: str):
    """
    Classify a single transcript chunk into one of:
    accomplishment | blocker | risk | decision | milestone | skip
    Returns (category, formatted_bullet) or (None, None) if skipped.
    """
    txt_lower = txt.lower()
    cit = f"[{dt} | {doc} | Speaker: {spk} | Page {pg}]"
    # Show only a short summary — not the full raw chunk
    summary = txt[:150] + ("..." if len(txt) > 150 else "")
    bullet = f"- **{spk}** ({dt}): \"{summary}\"  \n  > 📌 Citation: `{cit}`"

    # Skip pure conceptual-learning noise
    if any(w in txt_lower for w in CONCEPTUAL_NOISE):
        return None, None
    # Skip bare questions
    if txt.strip().endswith("?") and len(txt.strip()) < 120:
        return None, None

    if not txt.strip().endswith("?") and any(w in txt_lower for w in ACCOMPLISHMENT_KEYWORDS):
        return "accomplishment", bullet
    if any(w in txt_lower for w in BLOCKER_KEYWORDS):
        return "blocker", bullet
    if any(w in txt_lower for w in RISK_KEYWORDS):
        return "risk", bullet
    if any(w in txt_lower for w in DECISION_KEYWORDS):
        return "decision", bullet

    return None, None


def _build_milestone_timeline(results: list) -> list:
    """
    CAPABILITY 4 — Tracks Milestone Progress & Task Timelines.
    Groups evidence by (member, date) and builds a chronological per-member
    timeline of tasks, showing what was reported on each meeting date.
    Returns list of formatted markdown strings.
    """
    # member → { date → [text snippets] }
    timeline: dict = defaultdict(lambda: defaultdict(list))

    mentee_names = ["himaya", "ganesh", "dakshinya"]

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
            spk     = payload.get("speaker", "")
            from transcript_normalizer import clean_audio_artifacts
            txt = _clean_chunk_text(clean_audio_artifacts(raw_txt))
            if txt.endswith("..."):
                txt = txt.rstrip(".").rstrip() + "."
            spk_lower = spk.lower()
            if not any(m in spk_lower for m in mentee_names):
                continue
            if txt.strip().endswith("?") and len(txt.strip()) < 120:
                continue
            if any(w in txt.lower() for w in CONCEPTUAL_NOISE):
                continue
            if any(w in txt.lower() for w in ACCOMPLISHMENT_KEYWORDS + BLOCKER_KEYWORDS + DECISION_KEYWORDS):
                primary = _primary_mentee(spk)
                cit = f"[{dt} | {doc} | Speaker: {primary} | Page {pg}]"
                snippet = txt[:180] + ("..." if len(txt) > 180 else "")
                timeline[primary][dt].append(f"  - \"{snippet}\"  *(📌 `{cit}`)*")
        else:
            for turn_spk, turn_txt in matches:
                turn_spk = turn_spk.strip()
                turn_txt = turn_txt.strip()
                from transcript_normalizer import clean_audio_artifacts
                txt = _clean_chunk_text(clean_audio_artifacts(turn_txt))
                if not txt:
                    continue
                if txt.endswith("..."):
                    txt = txt.rstrip(".").rstrip() + "."
                spk_lower = turn_spk.lower()
                if not any(m in spk_lower for m in mentee_names):
                    continue
                if txt.strip().endswith("?") and len(txt.strip()) < 120:
                    continue
                if any(w in txt.lower() for w in CONCEPTUAL_NOISE):
                    continue
                if any(w in txt.lower() for w in ACCOMPLISHMENT_KEYWORDS + BLOCKER_KEYWORDS + DECISION_KEYWORDS):
                    primary = _primary_mentee(turn_spk)
                    cit = f"[{dt} | {doc} | Speaker: {primary} | Page {pg}]"
                    snippet = txt[:180] + ("..." if len(txt) > 180 else "")
                    timeline[primary][dt].append(f"  - \"{snippet}\"  *(📌 `{cit}`)*")

    if not timeline:
        return ["- No milestone timeline data found in retrieved transcript evidence."]

    lines = []
    # Sort by canonical mentee order
    ordered = ["Himaya Perumal", "Ganesh Krishna", "Dakshinya Nachimuthu"]
    sorted_members = [m for m in ordered if m in timeline] + \
                     [m for m in sorted(timeline.keys()) if m not in ordered]
    for member in sorted_members:
        lines.append(f"\n**👤 {member}**")
        for dt in sorted(timeline[member].keys()):
            lines.append(f"  - 📅 **{dt}**:")
            for entry in timeline[member][dt][:2]:   # max 2 entries per date
                lines.append(f"  {entry}")
    return lines


# ── Main agent function ────────────────────────────────────────────────────────

def run_manager_agent(user_prompt: str, target_member: str = "") -> str:
    """
    Manager Agent — All 4 capabilities fully implemented:
      1. Completed Accomplishments & Highlights
      2. Active Blockers & Risks
      3. Executive Decisions & Resource Allocation
      4. Milestone Progress & Task Timelines (date-ordered per-member timeline)

    Pipeline: P4 Full Corpus XML Map-Reduce across all 22 transcripts.
    """
    prompt_lower = user_prompt.lower()
    print("  - [Manager Agent]: Processing executive project status for Manager (Iyappan Sir)...")

    retriever = get_retriever()

    # Resolve target speakers from prompt or explicit argument
    target_speakers = []
    if "ganesh"    in prompt_lower or target_member.lower() == "ganesh":    target_speakers.append("Ganesh")
    if "himaya"    in prompt_lower or target_member.lower() == "himaya":    target_speakers.append("Himaya")
    if "dakshinya" in prompt_lower or target_member.lower() == "dakshinya": target_speakers.append("Dakshinya")

    if not target_speakers:
        target_speakers = ["Himaya", "Ganesh", "Dakshinya", "Siddharth"]

    # === PIPELINE 4 (P4): Full Corpus XML Map-Reduce ===
    print("  - [Manager Agent]: Using P4 Full Corpus Map-Reduce across all 22 transcripts...")
    p4_raw = retriever.retrieve_p4_full_corpus_mapreduce(user_prompt)

    # Filter to target speakers, text mentions, or mentor (Siddharth) turns
    results = []
    for chunk in p4_raw:
        spk = chunk.get("speaker", "").lower()
        txt = chunk.get("text", "").lower()
        
        # If no specific target, keep everything
        if len(target_speakers) == 4: # ["Himaya", "Ganesh", "Dakshinya", "Siddharth"]
            results.append(chunk)
            continue
            
        match = False
        for s in target_speakers:
            s_low = s.lower()
            if s_low in spk:
                match = True
            elif s_low in txt:
                match = True
            elif "siddharth" in spk and any(s.lower() in txt for s in target_speakers):
                # Keep mentor feedback/queries specifically about the target speaker(s)
                match = True
        if match:
            results.append(chunk)

    if not results:
        return "### 👔 Executive Manager Report\n\nNo matching transcript evidence found in Qdrant database."

    # Rank results by keyword relevance to user query to prioritize matching content
    query_words = [w.lower() for w in user_prompt.split() if len(w) > 3]
    
    # Balanced selection per target speaker to prevent one mentee starving out another
    selected_chunks = []
    seen_ids = set()
    
    mentees_to_cover = [s for s in target_speakers if s.lower() in ["himaya", "ganesh", "dakshinya"]]
    if not mentees_to_cover:
        mentees_to_cover = ["Himaya", "Ganesh", "Dakshinya"]
        
    completion_indicators = ["completed", "finished", "done", "integrated", "tested", "working", "we have collection", "i have done", "reduced", "cache", "qdrant", "deepseek", "langgraph"]
    
    for m in mentees_to_cover:
        m_low = m.lower()
        m_chunks = []
        for chunk in results:
            txt = chunk.get("text", "").lower()
            spk = chunk.get("speaker", "").lower()
            dt = chunk.get("date", "").lower()
            if m_low in spk or m_low in txt:
                score = sum(1 for w in query_words if w in txt) + 3
                # Boost completion evidence over initial early drafts
                if any(ci in txt for ci in completion_indicators):
                    score += 4
                # Recency bonus prioritizing August 4 final wrap-up & late July
                if any(rd in dt for rd in ["4 august", "august", "aug", "31 july"]):
                    score += 6
                elif any(rd in dt for rd in ["28 july", "29 july", "30 july"]):
                    score += 3
                m_chunks.append((score, chunk))
        m_chunks.sort(key=lambda x: x[0], reverse=True)
        for _, c in m_chunks[:4]:
            c_key = f"{c.get('date')}_{c.get('page')}_{c.get('text', '')[:40]}"
            if c_key not in seen_ids:
                seen_ids.add(c_key)
                selected_chunks.append(c)
                
    # Also add top global decision/accomplishment chunks with recency bonus
    scored_all = []
    for chunk in results:
        txt = chunk.get("text", "").lower()
        dt = chunk.get("date", "").lower()
        score = sum(1 for w in query_words if w in txt)
        if any(ci in txt for ci in completion_indicators):
            score += 3
        if any(rd in dt for rd in ["4 august", "august", "31 july"]):
            score += 4
        elif any(rd in dt for rd in ["28 july", "29 july", "30 july"]):
            score += 2
        scored_all.append((score, chunk))
    scored_all.sort(key=lambda x: x[0], reverse=True)
    for _, c in scored_all[:3]:
        c_key = f"{c.get('date')}_{c.get('page')}_{c.get('text', '')[:40]}"
        if c_key not in seen_ids:
            seen_ids.add(c_key)
            selected_chunks.append(c)
            
    results = selected_chunks if selected_chunks else results[:8]

    # ── Classify every chunk into the 4 capability buckets ────────────────────
    completed  = []
    blockers   = []
    risks      = []
    decisions  = []
    raw_chunks = []

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
            spk     = payload.get("speaker", "Team Member")
            from transcript_normalizer import clean_audio_artifacts
            txt = _clean_chunk_text(clean_audio_artifacts(raw_txt))
            if txt.endswith("..."):
                txt = txt.rstrip(".").rstrip() + "."
            display_spk = _primary_mentee(spk) if any(
                m in spk.lower() for m in ["himaya", "ganesh", "dakshinya"]
            ) else spk

            raw_chunks.append(f"[{dt} | {doc} | Page {pg}]\n{display_spk}: {txt}\n")

            category, bullet = _classify_chunk(txt, display_spk, dt, doc, pg)
            if category == "accomplishment": completed.append(bullet)
            elif category == "blocker":      blockers.append(bullet)
            elif category == "risk":         risks.append(bullet)
            elif category == "decision":     decisions.append(bullet)
        else:
            for turn_spk, turn_txt in matches:
                turn_spk = turn_spk.strip()
                turn_txt = turn_txt.strip()
                
                from transcript_normalizer import clean_audio_artifacts
                txt = _clean_chunk_text(clean_audio_artifacts(turn_txt))
                if not txt:
                    continue
                if txt.endswith("..."):
                    txt = txt.rstrip(".").rstrip() + "."
                
                display_spk = _primary_mentee(turn_spk) if any(
                    m in turn_spk.lower() for m in ["himaya", "ganesh", "dakshinya"]
                ) else turn_spk

                raw_chunks.append(f"[{dt} | {doc} | Page {pg}]\n{display_spk}: {txt}\n")

                category, bullet = _classify_chunk(txt, display_spk, dt, doc, pg)
                if category == "accomplishment": completed.append(bullet)
                elif category == "blocker":      blockers.append(bullet)
                elif category == "risk":         risks.append(bullet)
                elif category == "decision":     decisions.append(bullet)

    # ── CAPABILITY 4: Milestone Progress & Task Timelines ─────────────────────
    milestone_timeline = _build_milestone_timeline(results)

    # ── Build fallback structured report ──────────────────────────────────────
    report_lines = ["### 👔 Executive Manager Status Report (Iyappan Sir Mode)\n"]

    # CAPABILITY 1 — Completed Accomplishments & Highlights
    report_lines.append("#### ✅ Completed Accomplishments & Highlights")
    if completed:
        report_lines.extend(completed[:6])
    else:
        report_lines.append(
            "- Team progressed chunking & vector search experiments across July meeting reviews. "
            "No explicit delivery confirmation found in current retrieved window."
        )

    # CAPABILITY 2 — Active Blockers & Risks
    report_lines.append("\n#### ⚠️ Active Blockers & Risks")
    if blockers:
        report_lines.extend(blockers[:5])
    else:
        report_lines.append("- No critical blockers flagged in current retrieved window.")
    if risks:
        report_lines.extend(risks[:3])
    else:
        report_lines.append("- Monitor model latency and context limit for dense vector retrieval.")

    # CAPABILITY 3 — Executive Decisions & Resource Allocation
    report_lines.append("\n#### 🎯 Recommended Executive Decisions & Resource Allocation")
    if decisions:
        report_lines.extend(decisions[:4])
    else:
        report_lines.append(
            "- Review teammate milestone delivery status across Himaya, Ganesh, and Dakshinya "
            "and confirm deliverable readiness for upcoming demo."
        )

    # CAPABILITY 4 — Milestone Progress & Task Timelines
    report_lines.append("\n#### 📅 Milestone Progress & Task Timelines")
    report_lines.append(
        "> *Chronological task progression per team member extracted from transcript evidence.*"
    )
    report_lines.extend(milestone_timeline)

    # === Direct Context Build (no batching needed — Groq handles 128k tokens) ===
    sorted_results = []
    for r in results:
        payload = r if isinstance(r, dict) else (r.payload if hasattr(r, "payload") else {})
        dt = payload.get("date", "Unknown Date")
        sorted_results.append((dt, r))
    sorted_results.sort(key=lambda x: x[0])

    doc_context = ""
    for c in sorted_results:
        p = c[1] if isinstance(c, dict) else c[1]
        p = p if isinstance(p, dict) else (p.payload if hasattr(p, "payload") else {})
        doc_context += f"[{p.get('date', 'Unknown')} | {p.get('source_file', 'doc')} | Page {p.get('page', '1')}]\n{p.get('speaker', 'Unknown')}: {p.get('text', '')}\n\n"

    final_rag_context = [{"text": doc_context, "speaker": "Team", "date": "", "source_file": "transcripts", "page": "1", "score": 1.0}]
    print(f"  - [Manager]: Sending {len(sorted_results)} chunks directly to LLM (no batching)...")

    fallback_report = "\n".join(report_lines)


    # ── Construct 8-Module System Prompt via PromptBuilder → Groq LLM ─────────
    builder = PromptBuilder(user_id="Iyappan Sir", role="Manager")
    builder.add_security_guardrails()
    # Note: add_security_guardrails already calls add_speaker_attribution_policy()
    # internally, so we do NOT call it again here to avoid duplication.
    builder.add_grounding_policy()
    builder.add_output_policy()
    builder.add_agent_role("manager", manager_name="Iyappan Sir")
    builder.add_rag_context(final_rag_context)
    builder.add_user_query(user_prompt)
    system_prompt = builder.build()

    return generate_llm_response(system_prompt, user_prompt, fallback_response=fallback_report, agent_type="manager")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    test_q = "What are the project updates, milestones, and action items for Himaya, Ganesh, and Dakshinya?"
    print(run_manager_agent(test_q))
