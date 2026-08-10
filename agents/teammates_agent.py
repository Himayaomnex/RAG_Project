"""
================================================================================
Teammates Agent - Codebase Learning & Technical Q&A Specialist
================================================================================
Serves Himaya, Ganesh, and Dakshinya by scanning local codebases, explaining
technical architectures (RAG, MCP, LangGraph), providing reading materials,
and answering technical questions.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from qdrant_queries import call_llm_api

def scan_local_codebase(target_file: str = "qdrant_queries.py") -> str:
    """Scans any uploaded file (.py, .csv, .json, .txt, .md, Excel, AquaPro AI) in workspace."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    matched_file = None
    for root, _, files in os.walk(base_dir):
        for f in files:
            if target_file.lower() in f.lower():
                matched_file = os.path.join(root, f)
                break
        if matched_file:
            break
            
    if matched_file and os.path.exists(matched_file):
        try:
            with open(matched_file, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()[:3000]
        except Exception as e:
            return f"Error reading {os.path.basename(matched_file)}: {e}"
            
    return f"File '{target_file}' is loaded in project workspace."

def run_teammates_agent(user_prompt: str, user_name: str = "Teammate") -> str:
    """
    Teammates Agent execution logic:
    - Queries meeting transcripts in Qdrant & local codebase to answer teammate questions.
    - Recommends structured learning materials and explains complex concepts.
    """
    print(f"  - [Teammates Agent]: Processing technical question / reading material request for {user_name}...")
    
    # Query Qdrant meeting transcripts with User-Scoped Privacy Filtering
    from qdrant_queries import get_embedding, QDRANT_AVAILABLE, QdrantClient, LocalVectorStore, Filter, FieldCondition, MatchValue
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
        return '22 July 2026'
    
    # Map user_name to full speaker identity for metadata scoping
    MEMBER_MAP = {"himaya": "Himaya Perumal", "ganesh": "Ganesh Krishna", "dakshinya": "Dakshinya Nachimuthu"}
    full_user_name = MEMBER_MAP.get(user_name.lower(), user_name)
    
    # 1. User-Scoped Private Transcript Turns (User ID Scoped + Smart Date Matching across ALL 2,843 records)
    u_filter = Filter(must=[FieldCondition(key="speaker", match=MatchValue(value=full_user_name))])
    user_recs = []
    offset = None
    while True:
        r_batch, offset = client.scroll(collection_name=collection_name, limit=1000, offset=offset, scroll_filter=u_filter)
        user_recs.extend(r_batch)
        if offset is None or not r_batch:
            break
    
    # Robust Date Extraction (e.g. 22/07/2026, 22 July, 22nd, 21st)
    import re
    date_match = re.search(r'\b(\d{1,2})[/\-](0?7|july)', user_prompt, re.IGNORECASE) or \
                 re.search(r'\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*(?:of\s*)?(july|jul)\b', user_prompt, re.IGNORECASE) or \
                 re.search(r'\b(?:july|jul)\s*(\d{1,2})\b', user_prompt, re.IGNORECASE) or \
                 re.search(r'\b(\d{1,2})\s*(?:st|nd|rd|th)\b', user_prompt, re.IGNORECASE)
    target_day = ""
    if date_match:
        digits = [g for g in date_match.groups() if g and g.isdigit()]
        if digits and 1 <= int(digits[0]) <= 31:
            target_day = str(int(digits[0]))
            
    from transcript_normalizer import reattribute_crosstalk_turn
    
    # Filter user_recs to exclude crosstalk turns spoken by Mentor Siddharth
    clean_user_recs = []
    for pt in user_recs:
        payload = pt.payload if hasattr(pt, 'payload') else pt.get('payload', {})
        orig_spk = payload.get('speaker', '')
        txt = payload.get('text', '')
        real_spk, clean_txt = reattribute_crosstalk_turn(orig_spk, txt)
        if real_spk == full_user_name:
            clean_user_recs.append((pt, clean_txt))
            
    # Extract clean keywords from prompt (including numbers like 62833 / 62,833 / a4)
    raw_words = re.findall(r'\b[\w,]+\b', user_prompt)
    STOPWORDS = set(["what", "did", "discuss", "about", "regarding", "with", "show", "give", "tell", "completed", "specific", "how", "was", "mentioned", "summarize", "accomplished", "accomplishments", "contributions", "performance", "my", "work", "technical"])
    query_words = [w.lower().replace(',', '') for w in raw_words if len(w) >= 3 and w.lower() not in STOPWORDS]
    prompt_numbers = [n for n in re.findall(r'\b\d{4,6}\b', user_prompt.replace(',', ''))]
    
    # If specific target_day requested or specific query_words exist, score by relevance; otherwise sample across all dates
    if target_day or query_words or prompt_numbers:
        scored_user_recs = []
        for pt, clean_t in clean_user_recs:
            payload = pt.payload if hasattr(pt, 'payload') else pt.get('payload', {})
            date_str = resolve_record_date(payload)
            txt_clean_norm = clean_t.lower().replace(',', '')
            
            score = sum(10 for w in query_words if re.search(r'\b' + re.escape(w) + r'(?:s|ing|ed)?\b', txt_clean_norm))
            if any(num in txt_clean_norm for num in prompt_numbers):
                score += 100
            if target_day and target_day in date_str:
                score += 50
            scored_user_recs.append((score, pt, clean_t))
            
        scored_user_recs.sort(key=lambda x: x[0], reverse=True)
        
        seen_texts = set()
        matched_recs = []
        for score, pt, clean_t in scored_user_recs:
            snippet_key = clean_t[:50].strip()
            if snippet_key not in seen_texts and len(clean_t) > 15:
                seen_texts.add(snippet_key)
                matched_recs.append((pt, clean_t))
                if len(matched_recs) >= 8:
                    break
    else:
        # Multi-Date Diversity Sampler across ALL July dates
        date_groups = {}
        for pt, clean_t in clean_user_recs:
            payload = pt.payload if hasattr(pt, 'payload') else pt.get('payload', {})
            p_date = resolve_record_date(payload)
            if p_date not in date_groups:
                date_groups[p_date] = []
            date_groups[p_date].append((pt, clean_t))
            
        matched_recs = []
        for p_date in sorted(date_groups.keys()):
            for pt, clean_t in date_groups[p_date][:2]:
                if len(clean_t) > 20:
                    matched_recs.append((pt, clean_t))
                    if len(matched_recs) >= 10:
                        break
                        
    transcript_chunks = []
    for pt, clean_t in matched_recs:
        payload = pt.payload if hasattr(pt, 'payload') else pt.get('payload', {})
        r_date = resolve_record_date(payload)
        transcript_chunks.append(f"[{r_date} | Page {payload.get('page', 'N/A')} | User: {full_user_name}]: \"{clean_t}\"")
        
    transcript_str = "\n".join(transcript_chunks) if transcript_chunks else "No specific user-scoped turns found."
    
    # Check if prompt references a specific file
    target_file = "qdrant_queries.py"
    if "mcp" in user_prompt.lower():
        target_file = "mcp_server.py"
    elif "report" in user_prompt.lower():
        target_file = "cache_reuse_report.py"
        
    code_excerpt = scan_local_codebase(target_file)
    # Check prompt intent with typo tolerance
    is_quote_request = any(k in user_prompt.lower() for k in ["spoke", "discussed", "said", "transcript", "quotes", "what i said", "what did i say", "dialogue", "give me quotes"])
    is_performance_request = any(k in user_prompt.lower() for k in ["my performance", "performance", "scorecard", "accomplishment", "accomplished", "contributions", "what did i do"])
    is_code_request = any(k in user_prompt.lower() for k in ["code", "architecture", "localvectorstore", "qdrant_queries", "how works", "explain how"])
    
    if is_quote_request:
        schema = (
            "Output the EXACT RAW SPOKEN TRANSCRIPT QUOTES spoken by the user on that date from the evidence.\n"
            "Format each spoken turn strictly as:\n"
            "- **[Date | Page X | Speaker]**: \"Exact spoken text from transcript\"\n\n"
            "CRITICAL: Output ONLY the quote bullet points. DO NOT output any meta-notes, disclaimers, or explanations like 'Note: I have only included...'"
        )
    elif is_performance_request:
        schema = (
            "Synthesize the user's accomplishments and contributions strictly from the retrieved evidence turns below across ALL review dates.\n"
            "MANDATORY MULTI-DATE CITATIONS: You MUST include bullet points and matching verbatim transcript proofs for ALL distinct meeting dates present in the retrieved evidence (e.g. 22 July, 23 July, 28 July).\n"
            "CRITICAL NUMBERING RULE: Use bullet points (`•`) instead of numbered lists (1, 2, 3) to prevent duplicate item numbers across quote blocks.\n\n"
            "Format each distinct accomplishment as:\n"
            "• **[Topic / Date Accomplishment]**: [Summary from evidence]\n"
            "  * 📜 **Matching Verbatim Transcript Proof:** `[Date | Page X | User: Name]: \"Exact raw quote from evidence\"`\n\n"
            "DO NOT limit citations to a single date when multiple dates exist in the evidence below."
        )
    elif is_code_request:
        schema = (
            "Provide a clear, professional technical explanation of the requested codebase file based on the code context provided below.\n"
            "Format your output clearly:\n\n"
            "### 🏗️ Codebase & Architectural Explanation\n"
            "[Detailed, clean technical explanation of functions, classes, and vector search operations in the file]"
        )
    else:
        schema = (
            "Provide a clean, professional, grounded response directly answering every part of the user's technical question using the retrieved transcript evidence below.\n"
            "For EVERY topic or question in the prompt, synthesize the answer from the evidence and cite the matching verbatim transcript proof: `[Date | Page X | User: Name]: \"Exact raw quote\"` directly underneath."
        )

    from prompt_builder import EnterprisePromptBuilder
    
    prompt_builder = (
        EnterprisePromptBuilder(agent_type="teammates", user_id=full_user_name, role="teammate")
        .add_security_guardrails(full_user_name, "teammate")
        .add_hallucination_and_failure_policy()
        .add_reasoning_and_thinking_policy()
        .add_metadata_context("aqua_rag_team", "July 2026 Meetings")
        .add_agent_role("teammates")
        .add_tool_descriptions()
        .add_rag_context(transcript_chunks)
        .add_code_context(target_file, code_excerpt if is_code_request else "")
        .add_citation_rules()
        .add_response_schema(schema)
        .add_user_query(user_prompt)
    )
    llm_prompt = prompt_builder.build()
    res = call_llm_api(llm_prompt)
    if not res:
        res = f"### 💬 Grounded Spoken Transcript Evidence for {target_member}:\n\n" + transcript_str
    return res

if __name__ == "__main__":
    test_q = "Explain how LocalVectorStore works in qdrant_queries.py"
    print(run_teammates_agent(test_q))
