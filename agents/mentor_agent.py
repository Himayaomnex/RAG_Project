"""
================================================================================
Mentor Agent - Evaluation Framework & Quiz Generation Specialist
================================================================================
Sole owner of the Evaluation Framework for Siddharth. Evaluates Himaya, Ganesh,
and Dakshinya based on transcript evidence, technical progress, and generates
targeted technical testing quizzes.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from qdrant_queries import get_embedding, extract_clean_keywords, call_llm_api, QDRANT_AVAILABLE, QdrantClient, LocalVectorStore, Filter, FieldCondition, MatchValue

def run_mentor_agent(user_prompt: str, target_member: str = "") -> str:
    """
    Mentor Agent execution logic:
    - Evaluates member performance using transcript evidence & milestone records.
    - Generates technical quiz questions for Siddharth to test team members.
    """
    prompt_lower = user_prompt.lower()
    
    # Identify target team member (Himaya, Ganesh, Dakshinya)
    if not target_member:
        for member in ["himaya", "ganesh", "dakshinya"]:
            if member in prompt_lower:
                target_member = member.capitalize()
                break
        if not target_member:
            target_member = "Himaya Perumal"
            
    print(f"  - [Mentor Agent]: Processing Evaluation / Quiz request for {target_member}...")
    
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qdrant_storage")
    if QDRANT_AVAILABLE:
        try:
            client = QdrantClient(path=storage_path)
        except Exception:
            client = LocalVectorStore(path=storage_path)
    else:
        client = LocalVectorStore(path=storage_path)
        
    collection_name = "meeting_transcripts"
    
    # Scroll points for target member across transcripts
    scroll_filter = Filter(must=[FieldCondition(key="speaker", match=MatchValue(value=target_member))])
    retrieved_records, _ = client.scroll(collection_name=collection_name, limit=5, scroll_filter=scroll_filter)
    
    evidence_text = []
    for rec in retrieved_records:
        payload = rec.payload if hasattr(rec, 'payload') else rec.get('payload', {})
        evidence_text.append(f"[{payload.get('date', 'N/A')} | Page {payload.get('page', 'N/A')}]: {payload.get('text', '').strip()[:200]}")
        
    evidence_str = "\n".join(evidence_text) if evidence_text else "No specific transcript turns recorded."
    
    # Branch A: Technical Quiz Generation for Siddharth
    if any(word in prompt_lower for word in ["quiz", "questions", "test", "question"]):
        llm_prompt = f"""
You are the Mentor Evaluation Agent serving Siddharth (Mentor).
Generate 3-5 technical testing questions to evaluate {target_member}'s understanding of RAG, MCP, and AI architecture based on their contributions:

Transcript Evidence for {target_member}:
{evidence_str}

Format output as a structured Quiz Guide for Siddharth with question + key evaluation answer.
"""
    # Branch B: Member Performance Evaluation Report
    else:
        llm_prompt = f"""
You are the Mentor Evaluation Agent serving Siddharth (Mentor).
Evaluate {target_member}'s performance, technical progress, and contributions based on the following transcript evidence:

Target Member: {target_member}
Transcript Evidence:
{evidence_str}

Provide a structured Evaluation Report covering:
1. Technical Contributions & Milestones
2. Architectural Comprehension
3. Areas of Growth
4. Overall Rating & Recommendations for Siddharth.
"""
        
    return call_llm_api(llm_prompt)

if __name__ == "__main__":
    test_eval = "Evaluate Himaya's performance this month."
    print(run_mentor_agent(test_eval))
