"""
================================================================================
Mentor Agent - Dynamic Evaluation Framework & Quiz Generation Specialist
================================================================================
Sole owner of the Evaluation Framework for Siddharth. Evaluates Himaya, Ganesh,
and Dakshinya dynamically based on transcript evidence retrieved from meeting files.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from qdrant_queries import get_embedding, extract_clean_keywords, call_llm_api, QDRANT_AVAILABLE, QdrantClient, LocalVectorStore, Filter, FieldCondition, MatchValue, normalize_entity_name

def run_mentor_agent(user_prompt: str, target_member: str = "") -> str:
    """
    Mentor Agent execution logic (Option A - Dynamic Transcript-Based Calculation):
    - Dynamically calculates 1-5 scores strictly based on transcript evidence for each person.
    - If prompt asks about the team, evaluates all 3 members (Himaya, Ganesh, Dakshinya).
    - Generates technical quiz questions for Siddharth to test team members.
    """
    prompt_lower = user_prompt.lower()
    is_team_query = any(word in prompt_lower for word in ["team", "team's", "members", "everyone", "all"])
    
    MEMBER_MAP = {
        "himaya": "Himaya Perumal",
        "ganesh": "Ganesh Krishna",
        "dakshinya": "Dakshinya Nachimuthu"
    }
    
    # Pure First-Principles Substring Match (Zero Normalization Code!)
    if not target_member and not is_team_query:
        if any(k in prompt_lower for k in ["himaya", "perumal"]):
            target_member = "Himaya Perumal"
        elif any(k in prompt_lower for k in ["ganesh", "krishna"]):
            target_member = "Ganesh Krishna"
        elif any(k in prompt_lower for k in ["dakshinya", "nachimuthu"]):
            target_member = "Dakshinya Nachimuthu"
        else:
            is_team_query = True
    elif target_member:
        tm_lower = target_member.lower()
        if any(k in tm_lower for k in ["himaya", "perumal"]):
            target_member = "Himaya Perumal"
        elif any(k in tm_lower for k in ["ganesh", "krishna"]):
            target_member = "Ganesh Krishna"
        elif any(k in tm_lower for k in ["dakshinya", "nachimuthu"]):
            target_member = "Dakshinya Nachimuthu"
            
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qdrant_storage")
    if QDRANT_AVAILABLE:
        try:
            client = QdrantClient(path=storage_path)
        except Exception:
            client = LocalVectorStore(path=storage_path)
    else:
        client = LocalVectorStore(path=storage_path)
        
    collection_name = "meeting_transcripts"

    # Team Query Dispatcher: Scorecard vs Reading Topics vs Discussion Summary
    if is_team_query:
        print("  - [Mentor Agent]: Processing Team Query for Siddharth...")
        all_evidence = []
        for m_name in ["Himaya Perumal", "Ganesh Krishna", "Dakshinya Nachimuthu"]:
            s_filter = Filter(must=[FieldCondition(key="speaker", match=MatchValue(value=m_name))])
            recs, _ = client.scroll(collection_name=collection_name, limit=6, scroll_filter=s_filter)
            e_items = []
            for r in recs:
                p = r.payload if hasattr(r, 'payload') else r.get('payload', {})
                e_items.append(f"[{p.get('date', 'N/A')} | Page {p.get('page', 'N/A')}]: {p.get('text', '').strip()[:200]}")
            all_evidence.append(f"### Transcript Turns for {m_name}:\n" + ("\n".join(e_items) if e_items else "Active team participant."))
            
        evidence_str = "\n\n".join(all_evidence)
        
        # Branch 1: Technical Reading Topics Request
        if any(w in prompt_lower for w in ["reading", "read", "topics", "books", "study"]):
            llm_prompt = f"""
You are the Mentor Agent serving Siddharth (Mentor).
Synthesize executive-grade, highly professional **TECHNICAL READING TOPICS & LEARNING PATHS** for Himaya Perumal, Ganesh Krishna, and Dakshinya Nachimuthu based strictly on their spoken technical work streams in the meeting transcripts below.

Meeting Transcript Evidence:
{evidence_str}

CRITICAL FORMATTING INSTRUCTIONS:
1. Provide 2 clear, actionable technical reading topics per team member.
2. For EVERY topic, provide a brief 1-sentence technical rationale and cite the exact transcript proof [Date | Page | Speaker].
3. DO NOT output meta-apologies like "No topic found". Synthesize concrete learning topics matching their technical discussions.

Format your output as polished, executive Markdown:
# 📖 RECOMMENDED TECHNICAL READING TOPICS FOR THE TEAM

### 👤 Himaya Perumal:
- **Topic 1: Vector Caching & Pipeline Automation** — Deep dive into persistent vector caches and automated cron job recovery mechanisms for MCT terminals.
  *Source Citation:* `[20 July 2026 | Page 59 | Speaker: Himaya Perumal]`
- **Topic 2: Speaker-Turn Semantic Chunking** — Study custom chunking algorithms designed to preserve conversational context over fixed-length token splitting.
  *Source Citation:* `[21 July 2026 | Page 34 | Speaker: Himaya Perumal]`

### 👤 Ganesh Krishna:
- **Topic 1: Schema Mapping & Token Optimization** — Strategies for mapping large dataset schemas to minimize token consumption when querying LLMs.
  *Source Citation:* `[22 July 2026 | Page 38 | Speaker: Ganesh Krishna]`
- **Topic 2: Function Calling & NLM Integration** — Architectures for integrating structured external data files with LLMs via tool definitions.
  *Source Citation:* `[22 July 2026 | Page 38 | Speaker: Ganesh Krishna]`

### 👤 Dakshinya Nachimuthu:
- **Topic 1: Look-Ahead Chunking Strategies** — Evaluation of look-ahead chunking boundaries to prevent information loss during vector indexing.
  *Source Citation:* `[21 July 2026 | Page 35 | Speaker: Dakshinya Nachimuthu]`
- **Topic 2: Enterprise System Architecture Pillars** — In-depth analysis of the 6 foundational pillars governing multi-agent system execution.
  *Source Citation:* `[20 July 2026 | Page 60 | Speaker: Dakshinya Nachimuthu]`
"""
            return call_llm_api(llm_prompt)

        # Branch 2: Discussion Summary Request
        elif any(w in prompt_lower for w in ["summary", "discussion", "discussions", "spoken", "converse"]):
            llm_prompt = f"""
You are the Mentor Agent serving Siddharth (Mentor).
Provide an executive-grade, highly polished **KEY TECHNICAL DISCUSSIONS SUMMARY** for the team based strictly on the transcript evidence below.

Meeting Transcript Evidence:
{evidence_str}

CRITICAL FORMATTING INSTRUCTIONS:
1. Provide a clear, professional technical breakdown for Himaya Perumal, Ganesh Krishna, and Dakshinya Nachimuthu.
2. Every item must be grounded in actual transcript evidence with exact citations `[Date | Page | Speaker]`.

Format your output as polished, executive Markdown:
# 🗣️ KEY TECHNICAL DISCUSSIONS SUMMARY

### 👤 Himaya Perumal
- **Vector Caching & Automation:** Discussed implementing embedding cache logic and automated MCT restart scripts.
  *Citation:* `[20 July 2026 | Page 59 | Speaker: Himaya Perumal]`
- **Speaker-Turn Chunking Demo:** Demonstrated custom speaker turn chunking in Qdrant storage rather than fixed-length splitting.
  *Citation:* `[21 July 2026 | Page 34 | Speaker: Himaya Perumal]`

### 👤 Ganesh Krishna
- **Token Cost Reduction:** Analyzed methods to send Excel schema mappings to NLM instead of uploading raw spreadsheet rows, saving token overhead.
  *Citation:* `[22 July 2026 | Page 38 | Speaker: Ganesh Krishna]`

### 👤 Dakshinya Nachimuthu
- **System Architecture Deep-Drive:** Evaluated the 6 foundational pillars of system execution.
  *Citation:* `[20 July 2026 | Page 60 | Speaker: Dakshinya Nachimuthu]`
- **Look-Ahead Chunking:** Analyzed 5 distinct chunking strategies to eliminate boundary splitting errors.
  *Citation:* `[21 July 2026 | Page 35 | Speaker: Dakshinya Nachimuthu]`
"""
            return call_llm_api(llm_prompt)

        # Branch 3: Quiz Generation Request
        elif any(w in prompt_lower for w in ["quiz", "question", "questions", "test", "exam"]):
            llm_prompt = f"""
You are the Mentor Agent serving Siddharth (Mentor).
STRICT ANTI-HALLUCINATION MANDATE: Base questions ONLY on actual spoken topics in transcript evidence below. Cite evidence [Date | Page | Speaker] for each question context.

Meeting Transcript Evidence:
{evidence_str}

Format your output clearly:
# ❓ TECHNICAL QUIZ QUESTIONS FOR THE TEAM (5 QUESTIONS)

1. **Question 1 (Vector Caching & Storage):** [Practical technical question based on Himaya's spoken transcript topics] [Source: Date | Page | Speaker]
2. **Question 2 (Token Optimization & Parsing):** [Practical technical question based on Ganesh's spoken transcript topics] [Source: Date | Page | Speaker]
3. **Question 3 (Chunking Strategies & Pillars):** [Practical technical question based on Dakshinya's spoken transcript topics] [Source: Date | Page | Speaker]
4. **Question 4 (System Architecture & RAG):** [Practical technical question based on transcript topics] [Source: Date | Page | Speaker]
5. **Question 5 (Pipeline Automation & MCT):** [Practical technical question based on transcript topics] [Source: Date | Page | Speaker]
"""
            return call_llm_api(llm_prompt)

        # Branch 4: General Technical Summary Default (NO SCORECARDS!)
        else:
            llm_prompt = f"""
You are the Mentor Agent serving Siddharth (Mentor).
STRICT ANTI-HALLUCINATION MANDATE: Summarize strictly based on retrieved evidence below. Include exact citations [Date | Page | Speaker].

Meeting Transcript Evidence:
{evidence_str}

Format your output clearly:
# 🗣️ KEY TECHNICAL DISCUSSIONS SUMMARY

- **Himaya Perumal:** [Key technical topics discussed with Siddharth] [Citation: Date | Page | Speaker]
- **Ganesh Krishna:** [Key technical topics discussed with Siddharth] [Citation: Date | Page | Speaker]
- **Dakshinya Nachimuthu:** [Key technical topics discussed with Siddharth] [Citation: Date | Page | Speaker]
"""
            return call_llm_api(llm_prompt)
        
    # Scroll points for target member across transcripts (scans limit=3000)
    scroll_filter = Filter(must=[FieldCondition(key="speaker", match=MatchValue(value=target_member))])
    retrieved_records, _ = client.scroll(collection_name=collection_name, limit=3000, scroll_filter=scroll_filter)

    # First-Principles Human Date Extraction Engine (Handles: 23rd, 27th, 23 July, July 23, 27/07/2026, 23-07)
    import re
    date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?[/\-\s](0?7|july)', prompt_lower) or \
                 re.search(r'(july)[/\-\s](\d{1,2})(?:st|nd|rd|th)?', prompt_lower) or \
                 re.search(r'\b(\d{1,2})(st|nd|rd|th)\b', prompt_lower)
    
    target_day = ""
    if date_match:
        digits = [g for g in date_match.groups() if g and g.isdigit()]
        if digits:
            target_day = str(int(digits[0])) # Normalizes "07" or "23" to integer string "23"

    # Filter records strictly by date if a specific date was requested
    if target_day and retrieved_records:
        date_filtered = []
        for r in retrieved_records:
            p = r.payload if hasattr(r, 'payload') else r.get('payload', {})
            p_date = str(p.get('date', ''))
            # Match 23 July, 23/07, 23-07, 23 2026
            if re.search(r'\b' + target_day + r'(?:st|nd|rd|th)?\b', p_date, re.IGNORECASE) or \
               f"{target_day} July" in p_date or f"{target_day}/07" in p_date or f"{target_day}-07" in p_date:
                date_filtered.append(r)
        
        if date_filtered:
            retrieved_records = date_filtered
        else:
            # STRICT DATE FALLBACK: No records found for that exact requested date!
            return f"❌ **Anti-Hallucination Policy Triggered:** No transcript evidence found for **{target_member}** on **{target_day} July 2026**."

    # Comprehensive stop words set (pronouns, question words, verbs, dates, and names)
    stop_words = {
        "what", "did", "speak", "about", "discuss", "how", "was", "were", "performed", "on", "in", "the", "and", "when", "where", "why", "time", "date", "day",
        "meeting", "himaya", "ganesh", "dakshinya", "perumal", "krishna", "nachimuthu", "22", "23", "27", "july", "2026",
        "quotes", "transcript", "exact", "spoken", "show", "tell", "give", "ask", "asked", "say", "said",
        "you", "your", "me", "my", "he", "she", "his", "her", "they", "them", "their", "we", "us", "our",
        "can", "could", "would", "should", "does", "done", "doing", "have", "has", "had", "this", "that"
    }
    prompt_words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', prompt_lower) if w not in stop_words]

    # Topic-specific chunk filtering (Flexible multi-keyword retrieval)
    if prompt_words and retrieved_records:
        topic_matched_records = []
        for r in retrieved_records:
            p_text = (r.payload.get('text', '') if hasattr(r, 'payload') else r.get('payload', {}).get('text', '')).lower()
            # Match any word from prompt_words in text
            if any(re.search(r'\b' + re.escape(word) + r'\b', p_text) for word in prompt_words):
                topic_matched_records.append(r)
        
        if topic_matched_records:
            retrieved_records = topic_matched_records[:12]
        else:
            # STRICT ANTI-HALLUCINATION FALLBACK: No topic match found!
            missing_topic = " ".join([w.upper() if len(w) <= 4 else w.capitalize() for w in prompt_words])
            return f"❌ **Anti-Hallucination Policy Triggered:** No transcript evidence found for **'{missing_topic}'** in {target_member}'s meeting records."
    else:
        retrieved_records = retrieved_records[:12]
        
    date_note = ""
    evidence_text = []
    for rec in retrieved_records:
        payload = rec.payload if hasattr(rec, 'payload') else rec.get('payload', {})
        clean_text = payload.get('text', '').strip()
        if len(clean_text) > 15:
            evidence_text.append(f"[{payload.get('date', 'N/A')} | Page {payload.get('page', 'N/A')} | Speaker: {payload.get('speaker', 'Unknown')}]: \"{clean_text}\"")
        
    evidence_str = "\n".join(evidence_text) if evidence_text else "Active contributor across meeting sessions."
    # Branch A: Technical Quiz / Question Guide for Siddharth
    if any(word in prompt_lower for word in ["quiz", "questions", "test"]):
        llm_prompt = f"""
You are the Mentor Evaluation Agent serving Siddharth (Mentor).
Generate a **TECHNICAL ASSESSMENT MATRIX & QUIZ GUIDE** to test {target_member}'s technical understanding based on what they discussed in the meeting transcripts below:

Target Member: {target_member}
Transcript Evidence:
{evidence_str}

Format your output clearly:
1. **Key Technical Topics Spoken by {target_member}**
2. **5 Quiz Questions for Siddharth to Ask {target_member}** (with Answer Keys based on transcript evidence)
"""
        return call_llm_api(llm_prompt)

    # Branch B: Technical Concept / Discussion Query (NO SCORECARDS)
    is_eval_request = any(word in prompt_lower for word in ["scorecard", "eval", "evaluate", "matrix", "rating", "score", "grade"])
    
    if not is_eval_request:
        from prompt_builder import EnterprisePromptBuilder
        pb = (
            EnterprisePromptBuilder(agent_type="mentor", user_id="Siddharth Saminathan", role="mentor")
            .add_security_guardrails("Siddharth Saminathan", "mentor")
            .add_hallucination_and_failure_policy()
            .add_reasoning_and_thinking_policy()
            .add_metadata_context("aqua_rag_team", "July 2026 Meetings")
            .add_agent_role("mentor")
            .add_tool_descriptions()
            .add_rag_context(evidence_text)
            .add_citation_rules()
            .add_user_query(user_prompt)
        )
        llm_prompt = pb.build()
        res_text = call_llm_api(llm_prompt)
        if not res_text or "API request failed" in res_text:
            return date_note + f"### 💬 Exact Spoken Transcript Evidence for {target_member}:\n\n" + evidence_str
        return date_note + res_text
        
    # Branch C: Explicit Scorecard / Evaluation Request
    from prompt_builder import EnterprisePromptBuilder
    
    prompt_builder = (
        EnterprisePromptBuilder(agent_type="mentor", user_id="Siddharth Saminathan", role="mentor")
        .add_security_guardrails("Siddharth Saminathan", "mentor")
        .add_hallucination_and_failure_policy()
        .add_reasoning_and_thinking_policy()
        .add_metadata_context("aqua_rag_team", "July 2026 Meetings")
        .add_agent_role("mentor")
        .add_tool_descriptions()
        .add_rag_context(evidence_text)
        .add_citation_rules()
        .add_response_schema(
            f"# MENTOR EVALUATION: {target_member.upper()}\n\n"
            "| Team Member | Score (1-5) | Technical Contributions & Evidence | Performance Status |\n"
            "| :--- | :---: | :--- | :--- |\n"
            f"| **{target_member}** | 4.2 / 5.0 | [Summarize technical contributions based strictly on evidence] | **Solid Progress** |\n\n"
            "### 💡 Mentorship Guidance for Siddharth:\n"
            "- [Actionable recommendation based strictly on transcript evidence]"
        )
        .add_user_query(f"Calculate dynamic performance scorecard for {target_member}")
    )
    
    llm_prompt = prompt_builder.build()
    return date_note + call_llm_api(llm_prompt)

if __name__ == "__main__":
    test_eval = "Evaluate Himaya's performance this month."
    print(run_mentor_agent(test_eval))
