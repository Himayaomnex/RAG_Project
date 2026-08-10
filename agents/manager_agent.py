"""
================================================================================
Manager Agent - Project Status & Meeting Summary Specialist
================================================================================
Handles meeting summaries, project updates, action items, and status tracking
for Himaya, Ganesh, and Dakshinya across Microsoft Teams transcripts.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from qdrant_queries import get_embedding, extract_clean_keywords, call_llm_api, QDRANT_AVAILABLE, QdrantClient, LocalVectorStore, Filter, FieldCondition, MatchValue

def run_manager_agent(user_prompt: str, target_member: str = "") -> str:
    """
    Manager Agent execution logic:
    - Analyzes manager requests for meeting summaries, team status, milestones, and action items.
    - Formats output for Iyappan Sir focusing on Completed Accomplishments, Active Workstreams, and Action Items.
    """
    prompt_lower = user_prompt.lower()
    
    print("  - [Manager Agent]: Processing project status & team action items for Manager...")
    
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qdrant_storage")
    client = LocalVectorStore(path=storage_path)
        
    collection_name = "meeting_transcripts"
    
    # Smart Date Extraction (e.g. 22/07/2026, 22 July)
    import re
    date_match = re.search(r'\b(\d{1,2})[/\-](0?7|july)', prompt_lower) or \
                 re.search(r'\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*(?:of\s*)?(july|jul)\b', prompt_lower) or \
                 re.search(r'\b(?:july|jul)\s*(\d{1,2})\b', prompt_lower)
    target_day = ""
    if date_match:
        digits = [g for g in date_match.groups() if g and g.isdigit()]
        if digits:
            target_day = str(int(digits[0]))
    # Speaker-Targeted Query Scoping (Multi-Speaker Aware)
    target_speakers = []
    if "ganesh" in prompt_lower: target_speakers.append("Ganesh Krishna")
    if "himaya" in prompt_lower: target_speakers.append("Himaya Perumal")
    if "dakshinya" in prompt_lower: target_speakers.append("Dakshinya Nachimuthu")
    if "siddharth" in prompt_lower: target_speakers.append("Siddharth Saminathan")
    
    if not target_speakers:
        target_speakers = ["Himaya Perumal", "Ganesh Krishna", "Dakshinya Nachimuthu", "Siddharth Saminathan"]

    from transcript_normalizer import reattribute_crosstalk_turn
    work_keywords = ["workflow", "strategy", "chunking", "look ahead", "appo", "mvp", "test", "experiment", "excel", "schema", "openpyxl", "ocr", "etl", "mcp", "dashboard", "caching", "vector", "qdrant", "code", "done", "created", "added", "tried", "solution", "highlighted", "provenance", "track", "skills", "components", "prompts", "instructions", "system", "deep drive", "pillars", "docker", "hybrid", "schematic"]
    
    STOPWORDS = set(["what", "did", "discuss", "about", "regarding", "with", "show", "give", "gives", "given", "giving", "tell", "completed", "specific", "how", "was", "mentioned", "summarize", "proposed", "team", "during", "july", "review", "meetings", "solutions", "were", "the", "and", "for", "from", "they", "this", "that", "there", "have", "has", "had", "will", "would", "could", "should", "your", "their", "our", "are", "you", "me", "who", "which", "when", "where", "why", "action", "items", "deliverables", "committed", "regard", "regarding", "full", "technical", "progress", "summary", "statement", "accomplishments", "executive", "report", "reports", "overview", "breakdown", "status", "update", "updates", "item", "deliverable", "task", "tasks", "work", "accomplished", "done", "achieved", "mentor", "manager", "teammate", "teammates", "iyappan", "sir", "please", "can"])
    
    raw_words = re.findall(r'\b[\w,]+\b', user_prompt)
    prompt_query_words = [w.lower().replace(',', '') for w in raw_words if len(w) >= 3 and w.lower() not in STOPWORDS]
    topic_query_words = [w for w in prompt_query_words if w not in ["himaya", "ganesh", "dakshinya", "siddharth"]]
    
    context_chunks = []
    # Retrieve clean speaker-isolated context for ALL requested target speakers
    for member_name in target_speakers:
        filter_must = [FieldCondition(key="speaker", match=MatchValue(value=member_name))]
        s_filter = Filter(must=filter_must)
        
        recs = []
        offset = None
        while True:
            r_batch, offset = client.scroll(collection_name=collection_name, limit=1000, offset=offset, scroll_filter=s_filter)
            recs.extend(r_batch)
            if offset is None or not r_batch:
                break
        
        scored = []
        for pt in recs:
            payload = pt.payload if hasattr(pt, 'payload') else pt.get('payload', {})
            clean_text = payload.get('text', '').strip()
            raw_spk = payload.get('speaker', 'Unknown')
            spk, clean_text = reattribute_crosstalk_turn(raw_spk, clean_text)
            if spk.lower() != member_name.lower():
                continue
            txt_lower = clean_text.lower()
            
            # If topic_query_words exist, require at least ONE topic query word match; otherwise match work_keywords
            if topic_query_words:
                q_matches = sum(50 for w in topic_query_words if re.search(r'\b' + re.escape(w) + r'(?:s|ing|ed)?\b', txt_lower))
                if q_matches == 0:
                    score = 0
                else:
                    score = q_matches + sum(5 for w in work_keywords if re.search(r'\b' + re.escape(w) + r'\b', txt_lower))
            else:
                score = 10 + sum(15 for w in work_keywords if re.search(r'\b' + re.escape(w) + r'\b', txt_lower))
                
            if "didn't start" in txt_lower or "taking very long" in txt_lower:
                score -= 30
                
            if score > 0:
                scored.append((score, payload, spk, clean_text))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        
        member_lines = []
        seen_texts = set()
        for score, payload, spk, clean_text in scored:
            snippet_key = clean_text[:50].strip()
            if snippet_key not in seen_texts and len(clean_text) > 15:
                seen_texts.add(snippet_key)
                p_date = str(payload.get('date', 'N/A'))
                p_page = payload.get('page', 'N/A')
                member_lines.append(f"• [{p_date} | Page {p_page} | Speaker: {spk}]: \"{clean_text[:250]}\"")
                if len(member_lines) >= 6:
                    break
                
        if member_lines:
            context_chunks.append(f"=== EVIDENCE FOR {member_name.upper()} ===\n" + "\n".join(member_lines))

    # Determine response schema based on prompt intent (Direct Q&A vs Executive Report)
    is_direct_question = any(prompt_lower.startswith(w) for w in ["did", "does", "is", "who", "which", "was", "has", "can", "what", "where", "why", "how"]) or "?" in user_prompt
    if is_direct_question or topic_query_words:
        schema = (
            "TOPIC & QUESTION RESPONSE SCHEMA FOR MANAGER (IYAPPAN SIR):\n"
            "1. Ground your response strictly on the retrieved evidence turns below.\n"
            "2. Output sections ONLY for speakers who have explicit matching evidence under RETRIEVED EVIDENCE below.\n"
            "3. If only Ganesh Krishna and Siddharth Saminathan spoke about the requested topic (e.g. Excel schema mapping and token costs), summarize ONLY Ganesh Krishna and Siddharth Saminathan.\n"
            "4. DO NOT create sections, disclaimers, or notes for teammates (like Dakshinya or Himaya) who have no evidence under RETRIEVED EVIDENCE below."
        )
    else:
        schema = (
            "EXECUTIVE PROJECT REPORT FOR IYAPPAN SIR:\n"
            "1. Ground your report strictly on the retrieved evidence turns below across all review dates for ALL 3 TEAMMATES (Himaya, Ganesh, Dakshinya).\n"
            "2. For EVERY team member (Himaya Perumal, Ganesh Krishna, Dakshinya Nachimuthu), summarize their actual technical deliverables based ONLY on their matching evidence block below.\n"
            "3. STRICT SPEAKER ISOLATION MANDATE: Under Himaya Perumal, ONLY cite proof quotes where Speaker is Himaya Perumal. Under Ganesh Krishna, ONLY cite proof quotes where Speaker is Ganesh Krishna. Under Dakshinya Nachimuthu, ONLY cite proof quotes where Speaker is Dakshinya Nachimuthu. NEVER copy or cite another teammate's quote under a different person's name!\n"
            "4. NEVER output literal string placeholders like '[Date | Page X]' or 'No specific task assigned'. Only output real dates, real page numbers, real speaker names, and real quotes from EVIDENCE below!"
        )

    from prompt_builder import PromptBuilder
    
    prompt_builder = (
        PromptBuilder(agent_type="manager", user_id="Iyappan Sir", role="manager")
        .add_security_guardrails("Iyappan Sir", "manager")
        .add_grounding_policy()
        .add_output_policy()
        .add_metadata_context("aqua_rag_team", "July 2026 Meetings")
        .add_agent_role("manager")
        .add_tool_descriptions()
        .add_rag_context(context_chunks[:25])
        .add_citation_rules()
        .add_response_schema(schema)
        .add_user_query(user_prompt)
    )
    llm_prompt = prompt_builder.build()
    res = call_llm_api(llm_prompt)
    if not res:
        res = "### 🎓 AIML Training & Skill Learning Overview\n\n" + "\n\n".join(context_chunks[:15])
            
    return res

if __name__ == "__main__":
    test_query = "What are the action items and project updates for the team?"
    print(run_manager_agent(test_query))

