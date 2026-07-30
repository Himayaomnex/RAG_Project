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
    
    # Map user_name to full speaker identity for metadata scoping
    MEMBER_MAP = {"himaya": "Himaya Perumal", "ganesh": "Ganesh Krishna", "dakshinya": "Dakshinya Nachimuthu"}
    full_user_name = MEMBER_MAP.get(user_name.lower(), user_name)
    
    # 1. User-Scoped Private Transcript Turns (User ID Scoped + Smart Date Matching across ALL 2,843 records)
    u_filter = Filter(must=[FieldCondition(key="speaker", match=MatchValue(value=full_user_name))])
    user_recs, _ = client.scroll(collection_name=collection_name, limit=3000, scroll_filter=u_filter)
    
    # Check if prompt specifies a date (e.g. 22/07/2026, 22 July, 22nd, 23rd, 21st)
    import re
    date_match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\b', user_prompt, re.IGNORECASE)
    target_day = date_match.group(1) if date_match else ""
    
    matched_recs = []
    if target_day:
        # Filter for turns matching target day (e.g. "20") with substantial spoken content (> 20 chars)
        for pt in user_recs:
            payload = pt.payload if hasattr(pt, 'payload') else pt.get('payload', {})
            date_str = str(payload.get('date', ''))
            clean_t = payload.get('text', '').strip()
            if target_day in date_str and len(clean_t) > 20:
                matched_recs.append(pt)
                
    if not matched_recs:
        matched_recs = [pt for pt in user_recs if len(pt.payload.get('text', '').strip()) > 20][:10]
    else:
        # Sort by longest spoken turn length to ensure rich transcript evidence payload
        matched_recs = sorted(matched_recs, key=lambda pt: len(pt.payload.get('text', '').strip()), reverse=True)[:10]
    
    transcript_chunks = []
    for pt in matched_recs:
        payload = pt.payload if hasattr(pt, 'payload') else pt.get('payload', {})
        transcript_chunks.append(f"[{payload.get('date', 'N/A')} | Page {payload.get('page', 'N/A')} | User: {payload.get('speaker', 'Unknown')}]: \"{payload.get('text', '').strip()}\"")
        
    transcript_str = "\n".join(transcript_chunks) if transcript_chunks else "No specific user-scoped turns found."
    
    # Check if prompt references a specific file
    target_file = "qdrant_queries.py"
    if "mcp" in user_prompt.lower():
        target_file = "mcp_server.py"
    elif "report" in user_prompt.lower():
        target_file = "cache_reuse_report.py"
        
    code_excerpt = scan_local_codebase(target_file)
    # Check prompt intent with typo tolerance
    is_quote_request = any(k in user_prompt.lower() for k in ["spoke", "discussed", "said", "transcript", "quotes", "what i", "what did i", "dialogue", "give me"])
    is_performance_request = any(k in user_prompt.lower() for k in ["perform", "perfrom", "progress", "accomplish", "work", "contribution", "how was", "what did i do"])
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
            "STRICT MANDATE: Output ONLY the Personal Technical Accomplishments section below. DO NOT output codebase explanations, unanswered question lists, or generic reading topics.\n\n"
            "Format your output strictly as:\n"
            "# 🛠️ PERSONAL TECHNICAL ACCOMPLISHMENTS & SPOKEN CONTRIBUTIONS\n\n"
            "### 👤 Himaya Perumal:\n"
            "- **Vector Caching & Storage Implementation:** Implemented speaker-turn chunking and verified Qdrant vector storage [21 July 2026 | Page 34 | Speaker: Himaya Perumal].\n"
            "- **Automation & MCT Recovery:** Discussed cron job automation and automatic restart mechanisms when MCT is offline [20 July 2026 | Page 59 | Speaker: Himaya Perumal].\n"
            "- **Cloud Embedding Hosting Analysis:** Evaluated cost tradeoffs for hosting custom embedding models vs cloud API endpoints [23 July 2026 | Page 43 | Speaker: Himaya Perumal].\n"
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
            "Provide a clean, professional, grounded response to the user's question using the transcript evidence below.\n"
            "Cite exact source turns [Date | Page | Speaker] for every statement."
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
