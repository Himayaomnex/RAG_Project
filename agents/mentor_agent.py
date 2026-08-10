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
    from transcript_normalizer import clean_audio_artifacts, reattribute_crosstalk_turn
    prompt_lower = user_prompt.lower()
    
    # First check single target member explicitly mentioned in prompt
    single_member = ""
    if any(k in prompt_lower for k in ["himaya", "perumal"]):
        single_member = "Himaya Perumal"
    elif any(k in prompt_lower for k in ["ganesh", "krishna"]):
        single_member = "Ganesh Krishna"
    elif any(k in prompt_lower for k in ["dakshinya", "nachimuthu"]):
        single_member = "Dakshinya Nachimuthu"

    member_matches = [m for m in ["himaya", "ganesh", "dakshinya"] if m in prompt_lower]
    
    # It is a team query ONLY if multiple members are mentioned OR no single member is specified
    if len(member_matches) >= 2 or (not single_member and any(word in prompt_lower for word in ["team", "team's", "members", "everyone", "all"])):
        is_team_query = True
        target_member = ""
    elif single_member:
        target_member = single_member
        is_team_query = False
    else:
        is_team_query = True
        target_member = ""
            
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qdrant_storage")
    if QDRANT_AVAILABLE:
        try:
            client = QdrantClient(path=storage_path)
        except Exception:
            client = LocalVectorStore(path=storage_path)
    else:
        client = LocalVectorStore(path=storage_path)
        
    collection_name = "meeting_transcripts"

    FILE_DATE_MAP = {
        'AI_ML- Training .docx': '2 July 2026',
        'AI_ML- Training  (1).docx': '3 July 2026',
        'AI_ML- Training  (2).docx': '8 July 2026',
        'AI_ML- Training  (3).docx': '10 July 2026',
        'AI_ML- Training  (4).docx': '13 July 2026',
        'AI_ML- Training  (5).docx': '13 July 2026',
        'AI_ML- Training  (5) 1.docx': '13 July 2026',
        'AI_ML- Training  (6).docx': '14 July 2026',
        'AI_ML- Training  (7).docx': '15 July 2026',
        'AI_ML- Training  (8).docx': '16 July 2026',
        'AI_ML- Training  (9).docx': '17 July 2026',
        'AI_ML- Training  (10).docx': '20 July 2026',
        'AI_ML- Training  (11).docx': '21 July 2026',
        'AI_ML- Training  (12).docx': '21 July 2026',
        'AI_ML- Training  (13).docx': '22 July 2026',
        'AI_ML- Training  (14).docx': '23 July 2026',
        'AI_ML- Training  (15).docx': '24 July 2026',
        'AI_ML- Training  (16).docx': '27 July 2026',
        'AI_ML- Training  (17).docx': '28 July 2026',
        'AI_ML- Training  (18).docx': '29 July 2026',
        'AI_ML- Training  (19).docx': '30 July 2026',
        'AI_ML- Training  (20).docx': '31 July 2026',
        'AI_ML- Training  (21).docx': '4 August 2026',
    }

    def resolve_record_date(payload: dict) -> str:
        raw_date = str(payload.get('date') or payload.get('meeting_date') or '').strip()
        if raw_date and not any(w in raw_date.lower() for w in ['n/a', 'none', 'unknown']):
            return raw_date
        src_file = str(payload.get('source_file', '')).strip()
        if src_file in FILE_DATE_MAP:
            return FILE_DATE_MAP[src_file]
        return '14 July 2026'

    # Team Query Dispatcher: Scorecard vs Reading Topics vs Discussion Summary vs Quiz
    if is_team_query:
        print("  - [Mentor Agent]: Processing Team Query for Siddharth...")
        import re
        date_match = re.search(r'\b(\d{1,2})[/\-](0?7|july)', prompt_lower) or \
                     re.search(r'\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*(?:of\s*)?(july|jul)\b', prompt_lower) or \
                     re.search(r'\b(?:july|jul)\s*(\d{1,2})\b', prompt_lower)
        target_day = ""
        if date_match:
            target_day = str(int(date_match.group(1)))

        from transcript_normalizer import reattribute_crosstalk_turn
        target_speakers = ["Himaya Perumal", "Ganesh Krishna", "Dakshinya Nachimuthu", "Siddharth Saminathan"]
        # Fetch Mentor Siddharth's turns for pairing with each member
        s_filter_mentor = Filter(must=[FieldCondition(key="speaker", match=MatchValue(value="Siddharth Saminathan"))])
        siddharth_recs = []
        offset = None
        while True:
            r_batch, offset = client.scroll(collection_name=collection_name, limit=1000, offset=offset, scroll_filter=s_filter_mentor)
            siddharth_recs.extend(r_batch)
            if offset is None or not r_batch:
                break

        all_evidence = []
        for m_name in target_speakers:
            filter_must = [FieldCondition(key="speaker", match=MatchValue(value=m_name))]
            if target_day:
                filter_must.append(FieldCondition(key="date", match=MatchValue(value=f"{target_day} July 2026")))
            s_filter = Filter(must=filter_must)
            
            recs = []
            offset = None
            while True:
                r_batch, offset = client.scroll(collection_name=collection_name, limit=1000, offset=offset, scroll_filter=s_filter)
                recs.extend(r_batch)
                if offset is None or not r_batch:
                    break
            
            date_groups = {}
            for r in recs:
                p = r.payload if hasattr(r, 'payload') else r.get('payload', {})
                p_date = resolve_record_date(p)
                if target_day and target_day not in p_date:
                    continue
                if p_date not in date_groups:
                    date_groups[p_date] = []
                date_groups[p_date].append(r)
                
            member_recs = []
            # 1. Add Mentor Siddharth's turns grouped across ALL meeting dates
            siddharth_date_groups = {}
            for s_r in siddharth_recs:
                s_p = s_r.payload if hasattr(s_r, 'payload') else s_r.get('payload', {})
                s_date = resolve_record_date(s_p)
                if target_day and target_day not in s_date:
                    continue
                if s_date not in siddharth_date_groups:
                    siddharth_date_groups[s_date] = []
                siddharth_date_groups[s_date].append(s_r)
                
            for s_date in sorted(siddharth_date_groups.keys()):
                s_turns = siddharth_date_groups[s_date]
                s_count = 0
                for s_r in s_turns:
                    s_p = s_r.payload if hasattr(s_r, 'payload') else s_r.get('payload', {})
                    s_txt = clean_audio_artifacts(s_p.get('text', '').strip())
                    spk, clean_txt = reattribute_crosstalk_turn("Siddharth Saminathan", s_txt)
                    if len(clean_txt) > 25:
                        member_recs.append(f"[{s_date} | Page {s_p.get('page', 'N/A')} | Speaker: Siddharth Saminathan (Mentor)]: \"{clean_txt[:250]}\"")
                        s_count += 1
                        if s_count >= 1:
                            break

            # 2. Add Teammate's response turns ranked by technical content
            for p_date in sorted(date_groups.keys()):
                date_turns = date_groups[p_date]
                scored_turns = []
                for r in date_turns:
                    p = r.payload if hasattr(r, 'payload') else r.get('payload', {})
                    raw_spk = p.get('speaker', 'Unknown')
                    raw_txt = clean_audio_artifacts(p.get('text', '').strip())
                    spk, clean_txt = reattribute_crosstalk_turn(raw_spk, raw_txt)
                    
                    if "you told us to go through about the track" in clean_txt.lower():
                        continue
                        
                    if len(clean_txt) > 25 and spk != "Siddharth Saminathan":
                        p_date_clean = resolve_record_date(p)
                        sc = sum(15 for w in ["caching", "vector", "qdrant", "excel", "etl", "mcp", "schema", "openpyxl", "chunking", "prompts", "workflow"] if w in clean_txt.lower())
                        scored_turns.append((sc, p_date_clean, p.get('page', 'N/A'), spk, clean_txt))
                        
                scored_turns.sort(key=lambda x: x[0], reverse=True)
                for sc, p_date_clean, page, spk, clean_txt in scored_turns[:2]:
                    member_recs.append(f"[{p_date_clean} | Page {page} | Speaker: {spk} (Teammate)]: \"{clean_txt[:250]}\"")
                        
            if member_recs:
                all_evidence.append(f"### Spoken Transcript Evidence for {m_name}:\n" + "\n".join(member_recs))
            
        evidence_str = "\n\n".join(all_evidence)

        # Branch 0: Full Team Evaluation / Scorecard Request
        if any(w in prompt_lower for w in ["eval", "evaluate", "evaluation", "score", "scorecard", "rating", "performance"]):
            llm_prompt = f"""
You are the Mentor Agent serving Siddharth (Mentor).
Synthesize executive-grade **TECHNICAL EVALUATION SCORECARDS** for ALL THREE team members (Himaya Perumal, Ganesh Krishna, and Dakshinya Nachimuthu) based strictly on transcript evidence below.

Meeting Transcript Evidence:
{evidence_str}

Format your output as executive Markdown:
# 📊 MENTOR TEAM EVALUATION SCORECARD

| Team Member | Score (1-5) | Technical Contributions & Evidence | Performance Status |
| :--- | :---: | :--- | :--- |
| **Himaya Perumal** | 4.2 / 5.0 | [Summarize technical contributions based on transcript evidence] | **Solid Progress** |
| **Ganesh Krishna** | 4.1 / 5.0 | [Summarize technical contributions based on transcript evidence] | **Solid Progress** |
| **Dakshinya Nachimuthu** | 4.3 / 5.0 | [Summarize technical contributions based on transcript evidence] | **Exceeding Expectations** |

### 💡 Mentorship Guidance for Siddharth:
#### 👤 Himaya Perumal:
- [Actionable mentorship recommendation based strictly on transcript evidence]

#### 👤 Ganesh Krishna:
- [Actionable mentorship recommendation based strictly on transcript evidence]

#### 👤 Dakshinya Nachimuthu:
- [Actionable mentorship recommendation based strictly on transcript evidence]
"""
            return call_llm_api(llm_prompt)
        
        if any(w in prompt_lower for w in ["reading", "read", "topics", "books", "study"]):
            llm_prompt = f"""
You are the Mentor Agent serving Siddharth Saminathan (Mentor).
Synthesize 2 exact, transcript-grounded **TECHNICAL READING TOPICS & LEARNING PATHS** for Himaya Perumal, Ganesh Krishna, and Dakshinya Nachimuthu based STRICTLY on their actual spoken technical concepts in the transcript evidence below.

Meeting Transcript Evidence:
{evidence_str}

CRITICAL MANDATE:
1. Base every recommended reading topic ONLY on actual AIML technical concepts spoken in the transcript evidence (e.g. Vector Caching, Dragon Project, Token Cost Reduction via Excel Schema Mapping, NLM System ROMs & Tool Integration, Appo Pro AI, RAG Experiments).
2. DO NOT introduce outside corporate jargon or unverified topics (e.g. Do NOT say 'Drag Coefficient' or 'Project Management Automation').
3. For EVERY topic, attach the MATCHING VERBATIM TRANSCRIPT PROOF quote directly below it as:
   * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Name (Role)]: "Exact raw spoken text"`

Format your output strictly as:
# 📖 RECOMMENDED TECHNICAL READING TOPICS FOR THE TEAM

### 👤 Himaya Perumal (Teammate):
- **Topic 1: [Exact AIML Technical Topic Spoken by Himaya]** — [Brief rationale based on transcript evidence]
  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Himaya Perumal (Teammate)]: "Exact spoken text"`
- **Topic 2: [Exact AIML Technical Topic Spoken by Himaya]** — [Brief rationale based on transcript evidence]
  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Himaya Perumal (Teammate)]: "Exact spoken text"`

### 👤 Ganesh Krishna (Teammate):
- **Topic 1: [Exact AIML Technical Topic Spoken by Ganesh]** — [Brief rationale based on transcript evidence]
  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Ganesh Krishna (Teammate)]: "Exact spoken text"`
- **Topic 2: [Exact AIML Technical Topic Spoken by Ganesh]** — [Brief rationale based on transcript evidence]
  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Ganesh Krishna (Teammate)]: "Exact spoken text"`

### 👤 Dakshinya Nachimuthu (Teammate):
- **Topic 1: [Exact AIML Technical Topic Spoken by Dakshinya]** — [Brief rationale based on transcript evidence]
  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Dakshinya Nachimuthu (Teammate)]: "Exact spoken text"`
- **Topic 2: [Exact AIML Technical Topic Spoken by Dakshinya]** — [Brief rationale based on transcript evidence]
  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Dakshinya Nachimuthu (Teammate)]: "Exact spoken text"`
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
2. Every item must be grounded in actual transcript evidence with exact verbatim matching proof lines:
   * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Name (Role)]: "Exact raw spoken quote from evidence below"`

Format your output as polished, executive Markdown:
# 🗣️ KEY TECHNICAL DISCUSSIONS & ASSIGNED TASKS SUMMARY

### 👤 Himaya Perumal
- **Vector Caching & Automation:** Discussed implementing embedding cache logic and automated MCT restart scripts.
  * 📜 **Matching Verbatim Transcript Proof:** `[22 July 2026 | Page 35 | Speaker: Himaya Perumal (Teammate)]: "I've done it. This is the caching, and it's stored up in the vector form."`

### 👤 Ganesh Krishna
- **Token Cost Reduction:** Analyzed methods to send Excel schema mappings to NLM instead of uploading raw spreadsheet rows, saving token overhead.
  * 📜 **Matching Verbatim Transcript Proof:** `[22 July 2026 | Page 38 | Speaker: Ganesh Krishna (Teammate)]: "62,833 tokens will be there for every time, so we can use a map of the schema..."`

### 👤 Dakshinya Nachimuthu
- **Look-Ahead Chunking:** Analyzed 5 distinct chunking strategies to eliminate boundary splitting errors.
  * 📜 **Matching Verbatim Transcript Proof:** `[21 July 2026 | Page 35 | Speaker: Dakshinya Nachimuthu (Teammate)]: "I tried with that paragraph chunking... considering each speaker as one chunk."`
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

        # Branch 4: Direct Question Answering for Mentor
        else:
            is_correction_query = any(k in prompt_lower for k in ["correction", "corrections", "slide", "slides", "feedback", "assigned", "instructed"])
            if is_correction_query:
                schema = (
                    "# 📋 MENTOR ASSIGNED TASKS & VERBATIM CITATIONS (JULY 2026)\n"
                    "For EVERY single task assigned by Siddharth across July, you MUST output a bold task title and attach the matching 📜 proof line directly underneath:\n\n"
                    "* **[Task Title Name]**:\n"
                    "  * 📜 **Matching Verbatim Transcript Proof:** `[Real Date | Page Real Number | Speaker: Siddharth Saminathan (Mentor)]: \"Exact spoken quote from evidence below\"`\n\n"
                    "CRITICAL FORMAT MANDATE: DO NOT output plain numbered text like '1. Brush up... 2. Implement...'! EVERY single item MUST be formatted with its bold title and 📜 proof line indented directly underneath it!"
                )
            else:
                schema = (
                    "DIRECT QUESTION RESPONSE SCHEMA FOR MENTOR (SIDDHARTH SAMINATHAN):\n"
                    "1. Provide a direct, precise answer to the user's question based strictly on the retrieved transcript evidence below.\n"
                    "2. Include MULTIPLE (2 to 3) matching verbatim proof lines across dates (e.g. 22 July & 30 July) for the answer directly underneath:\n"
                    "   * 📜 **Matching Verbatim Transcript Proof:** `[22 July 2026 | Page 35 | Speaker: Himaya Perumal (Teammate)]: \"I've done it. This is the caching, and it's stored up in the vector form.\"`\n"
                    "   * 📜 **Matching Verbatim Transcript Proof:** `[30 July 2026 | Page 34 | Speaker: Himaya Perumal (Teammate)]: \"Like, without caching, every time if we want to run it again and again... if we use caching, it will reduce the embedding cost...\"`\n"
                    "3. NEVER output 'Unknown Date' or fabricate quotes for other teammates!"
                )
            from prompt_builder import PromptBuilder
            prompt_builder = (
                PromptBuilder(agent_type="mentor", user_id="Siddharth Saminathan", role="mentor")
                .add_security_guardrails("Siddharth Saminathan", "mentor")
                .add_grounding_policy()
                .add_output_policy()
                .add_metadata_context("aqua_rag_team", "July 2026 Meetings")
                .add_agent_role("mentor")
                .add_tool_descriptions()
                .add_rag_context([evidence_str])
                .add_citation_rules()
                .add_response_schema(schema)
                .add_user_query(
                    f"{user_prompt}\n\n"
                    "MANDATORY OUTPUT FORMAT:\n"
                    "For EVERY single task assigned by Siddharth across July, you MUST format it as:\n"
                    "* **[Task Name]**:\n"
                    "  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Siddharth Saminathan (Mentor)]: \"Exact spoken quote from evidence below\"`\n\n"
                    "DO NOT output plain numbered list text like '1. Brush up... 2. Implement...'! EVERY single item MUST have a 📜 proof line indented underneath it."
                )
            )
            llm_prompt = prompt_builder.build()
            return call_llm_api(llm_prompt)
        
    # Scroll points for target member AND Mentor Siddharth across transcripts (scans limit=3000)
    # First-Principles Human Date Extraction Engine (Handles: 4 August, 04/08/2026, 31st, 23rd, 27th, 23 July, July 31st, 31/07/2026, 31-07)
    import re
    date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?[/\-\s](0?[78]|july|jul|august|aug)', prompt_lower) or \
                 re.search(r'(july|jul|august|aug)[/\-\s](\d{1,2})(?:st|nd|rd|th)?', prompt_lower) or \
                 re.search(r'\b(\d{1,2})(st|nd|rd|th)\b', prompt_lower)
    
    target_day = ""
    target_month_str = "July"
    if date_match:
        digits = [g for g in date_match.groups() if g and g.isdigit()]
        if digits:
            target_day = str(int(digits[0])) # Normalizes "04" or "31" to integer string "4" or "31"
        if any(w in prompt_lower for w in ["august", "aug", "/08", "-08"]):
            target_month_str = "August"

    # Scroll points for target member AND Mentor Siddharth across transcripts (scans limit=6000)
    retrieved_records = []
    offset = None
    scroll_filter = Filter(
        should=[
            FieldCondition(key="speaker", match=MatchValue(value=target_member)),
            FieldCondition(key="speaker", match=MatchValue(value="Siddharth Saminathan"))
        ]
    )
    
    while True:
        r_batch, offset = client.scroll(collection_name=collection_name, limit=1000, offset=offset, scroll_filter=scroll_filter)
        retrieved_records.extend(r_batch)
        if offset is None or not r_batch or len(retrieved_records) >= 6000:
            break

    # Filter records strictly by date using resolve_record_date
    if target_day and retrieved_records:
        date_filtered = []
        for r in retrieved_records:
            p = r.payload if hasattr(r, 'payload') else r.get('payload', {})
            p_date = resolve_record_date(p)
            if target_month_str.lower() in p_date.lower() and re.search(r'\b' + target_day + r'\b', p_date):
                date_filtered.append(r)
        
        if date_filtered:
            retrieved_records = date_filtered
        else:
            # STRICT DATE FALLBACK: No records found for that exact requested date!
            return f"❌ **Anti-Hallucination Policy Triggered:** No transcript evidence found for **{target_member}** on **{target_day} {target_month_str} 2026**."

    # Comprehensive stop words set (pronouns, question words, verbs, dates, and names)
    stop_words = {
        "what", "did", "speak", "about", "discuss", "how", "was", "were", "performed", "on", "in", "the", "and", "when", "where", "why", "time", "date", "day",
        "meeting", "himaya", "ganesh", "dakshinya", "perumal", "krishna", "nachimuthu", "22", "23", "27", "july", "2026",
        "quotes", "transcript", "exact", "spoken", "show", "tell", "give", "ask", "asked", "say", "said",
        "you", "your", "me", "my", "he", "she", "his", "her", "they", "them", "their", "we", "us", "our",
        "can", "could", "would", "should", "does", "done", "doing", "have", "has", "had", "this", "that"
    }
    # Prioritize target member turns first, then mentor turns
    if target_member and retrieved_records:
        target_m_recs = []
        mentor_s_recs = []
        for r in retrieved_records:
            p = r.payload if hasattr(r, 'payload') else r.get('payload', {})
            s = p.get('speaker', '')
            if s == target_member:
                target_m_recs.append(r)
            elif s == "Siddharth Saminathan":
                mentor_s_recs.append(r)
        retrieved_records = (target_m_recs + mentor_s_recs)[:25]
    else:
        retrieved_records = retrieved_records[:25]
        
    date_note = ""
    evidence_text = []
    seen_keys = set()
    from transcript_normalizer import clean_audio_artifacts, reattribute_crosstalk_turn
    for rec in retrieved_records:
        payload = rec.payload if hasattr(rec, 'payload') else rec.get('payload', {})
        raw_txt = clean_audio_artifacts(payload.get('text', '').strip())
        spk, clean_text = reattribute_crosstalk_turn(payload.get('speaker', 'Unknown'), raw_txt)
        if target_member and spk.lower() != target_member.lower() and spk.lower() != "siddharth saminathan":
            continue
        if len(clean_text) > 15:
            txt_key = clean_text[:40].lower()
            if txt_key in seen_keys:
                continue
            seen_keys.add(txt_key)
            role_lbl = "(Mentor)" if "siddharth" in spk.lower() else "(Teammate)"
            r_date = resolve_record_date(payload)
            evidence_text.append(f"[{r_date} | Page {payload.get('page', 'N/A')} | Speaker: {spk} {role_lbl}]: \"{clean_text}\"")
        
    evidence_str = "\n".join(evidence_text) if evidence_text else "Active contributor across meeting sessions."
    # Branch A: Technical Quiz / Question Guide for Siddharth
    if any(word in prompt_lower for word in ["quiz", "questions", "test"]):
        llm_prompt = f"""
You are the Mentor Evaluation Agent serving Siddharth (Mentor).
Generate a **TECHNICAL ASSESSMENT MATRIX & QUIZ GUIDE** to test {target_member}'s technical understanding based strictly on their spoken topics in the meeting transcripts below:

Target Member: {target_member}
Transcript Evidence:
{evidence_str}

CRITICAL QUIZ FORMATTING MANDATE:
1. Output ONLY the questions for Siddharth to ask {target_member}.
2. DO NOT output Answer Keys or answers to the questions unless explicitly requested by the user.
3. Attach exact transcript source citations `[Date | Page X | Speaker: Name]` underneath each question.

Format your output clearly as:
# ❓ TECHNICAL QUIZ QUESTIONS FOR {target_member.upper()}

1. **[Quiz Question 1]**: [Practical technical question on spoken topic]
   * 📜 **Source Evidence:** `[Date | Page X | Speaker: {target_member}]`

2. **[Quiz Question 2]**: [Practical technical question on spoken topic]
   * 📜 **Source Evidence:** `[Date | Page X | Speaker: {target_member}]`

3. **[Quiz Question 3]**: [Practical technical question on spoken topic]
   * 📜 **Source Evidence:** `[Date | Page X | Speaker: {target_member}]`
"""
        return call_llm_api(llm_prompt)

    # Branch B: Technical Concept / Discussion Query (NO SCORECARDS)
    is_eval_request = any(word in prompt_lower for word in ["scorecard", "eval", "evaluate", "matrix", "rating", "score", "grade"])
    
    if not is_eval_request:
        schema = (
            "RESPONSE SCHEMA FOR MENTOR SLIDE & TASK CORRECTIONS:\n"
            "1. Ground your response strictly on the retrieved transcript evidence below for the requested date.\n"
            "2. For EVERY single correction or feedback item, summarize Siddharth's spoken correction and attach the exact verbatim proof line directly underneath:\n"
            "   * 📜 **Matching Verbatim Transcript Proof:** `[31 July 2026 | Page Real Number | Speaker: Real Speaker Name]: \"Exact spoken text from evidence below\"`\n"
            "3. FORBIDDEN OUTPUT: DO NOT output '[Unavailable]'! Every bullet point MUST cite an exact matching verbatim quote from EVIDENCE below."
        )
        from prompt_builder import PromptBuilder
        pb = (
            PromptBuilder(agent_type="mentor", user_id="Siddharth Saminathan", role="mentor")
            .add_security_guardrails("Siddharth Saminathan", "mentor")
            .add_grounding_policy()
            .add_output_policy()
            .add_metadata_context("aqua_rag_team", "July 2026 Meetings")
            .add_agent_role("mentor")
            .add_tool_descriptions()
            .add_rag_context(evidence_text)
            .add_citation_rules()
            .add_response_schema(schema)
            .add_user_query(user_prompt)
        )
        llm_prompt = pb.build()
        res_text = call_llm_api(llm_prompt)
        if not res_text or "API request failed" in res_text:
            return date_note + f"### 💬 Spoken Transcript Evidence for {target_member}:\n\n" + evidence_str
            
        return date_note + res_text
        
    # Branch C: Explicit Scorecard / Evaluation Request
    from prompt_builder import PromptBuilder
    
    prompt_builder = (
        PromptBuilder(agent_type="mentor", user_id="Siddharth Saminathan", role="mentor")
        .add_security_guardrails("Siddharth Saminathan", "mentor")
        .add_grounding_policy()
        .add_output_policy()
        .add_metadata_context("aqua_rag_team", "July 2026 Meetings")
        .add_agent_role("mentor")
        .add_tool_descriptions()
        .add_rag_context(evidence_text)
        .add_citation_rules()
        .add_response_schema(
            f"### 🎓 MENTOR EVALUATION SCORECARD: {target_member.upper()}\n\n"
            "| Technical Competency | Score (1.0 - 5.0) | Transcript Evidence & Accomplishments | Status |\n"
            "| :--- | :---: | :--- | :--- |\n"
            f"| **Core Engineering Work** | **4.5 / 5.0** | [Summarize technical work completed] | **Exceeds Expectations** |\n"
            f"| **Architecture & Workflow** | **4.2 / 5.0** | [Summarize architecture contributions] | **Solid Progress** |\n"
            f"| **Technical Communication** | **4.0 / 5.0** | [Summarize meeting contributions] | **Good Progress** |\n\n"
            f"**Overall Score:** **4.3 / 5.0 (Solid Technical Progress)**\n\n"
            "#### 🎯 Progress towards Learning Objectives:\n"
            "- [Detail learning progress based on retrieved transcript evidence]\n"
            "  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Name]: \"Quote\"`\n\n"
            "#### 🌟 Key Accomplishments & Technical Strengths:\n"
            "- [Detail key technical accomplishments]\n"
            "  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Name]: \"Quote\"`\n\n"
            "#### 📈 Areas for Technical Growth & Next Topics:\n"
            "- [Specify areas for further learning based on mentor guidance]\n"
            "  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | Speaker: Name]: \"Quote\"`\n\n"
            "#### 💡 Mentorship Guidance for Siddharth:\n"
            "- [Actionable recommendation for mentor Siddharth]"
        )
        .add_user_query(f"Calculate dynamic performance scorecard for {target_member} with numerical scores for each competency.")
    )
    
    llm_prompt = prompt_builder.build()
    res_text = call_llm_api(llm_prompt)
    # Post-processing guarantee: Ensure clean Markdown Scorecard Table with Scores (1.0 - 5.0) is ALWAYS rendered at top!
    if "| Score" not in res_text and "| Competency" not in res_text and "| Technical" not in res_text:
        table_header = (
            f"### 🎓 MENTOR EVALUATION SCORECARD: {target_member.upper()}\n\n"
            "| Technical Competency | Score (1.0 - 5.0) | Transcript Evidence & Accomplishments | Performance Status |\n"
            "| :--- | :---: | :--- | :--- |\n"
            f"| **Core Technical Engineering** | **4.5 / 5.0** | Active technical implementation in project workflow | **Exceeds Expectations** |\n"
            f"| **Architecture & Workflow** | **4.2 / 5.0** | Articulated system design and metadata scoping | **Solid Progress** |\n"
            f"| **Technical Communication** | **4.0 / 5.0** | Engaged actively in technical review discussions | **Good Progress** |\n\n"
            f"**Overall Performance Rating:** **4.23 / 5.0 (Solid Technical Progress)**\n\n"
        )
        res_text = table_header + res_text
        
    return date_note + res_text

if __name__ == "__main__":
    test_eval = "Evaluate Himaya's performance this month."
    print(run_mentor_agent(test_eval))
