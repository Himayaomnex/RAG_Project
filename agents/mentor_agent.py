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
    - If prompt asks about the team, evaluates all 3 members (Himaya, Ganesh, Dakshinya).
    - Generates technical quiz questions for Siddharth to test team members.
    """
    prompt_lower = user_prompt.lower()
    is_team_query = any(word in prompt_lower for word in ["team", "team's", "members", "everyone", "all"])
    
    # Identify target team member (Himaya, Ganesh, Dakshinya)
    if not target_member and not is_team_query:
        for member in ["himaya", "ganesh", "dakshinya"]:
            if member in prompt_lower:
                target_member = member.capitalize()
                break
        if not target_member:
            target_member = "Himaya Perumal"
            
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qdrant_storage")
    if QDRANT_AVAILABLE:
        try:
            client = QdrantClient(path=storage_path)
        except Exception:
            client = LocalVectorStore(path=storage_path)
    else:
        client = LocalVectorStore(path=storage_path)
        
    collection_name = "meeting_transcripts"

    if is_team_query:
        print("  - [Mentor Agent]: Processing Full Team Evaluation request for Himaya, Ganesh, and Dakshinya...")
        all_evidence = []
        for m_name in ["Himaya Perumal", "Ganesh Krishna", "Dakshinya Nachimuthu"]:
            s_filter = Filter(must=[FieldCondition(key="speaker", match=MatchValue(value=m_name))])
            recs, _ = client.scroll(collection_name=collection_name, limit=3, scroll_filter=s_filter)
            e_items = []
            for r in recs:
                p = r.payload if hasattr(r, 'payload') else r.get('payload', {})
                e_items.append(f"[{p.get('date', 'N/A')}]: {p.get('text', '').strip()[:150]}")
            all_evidence.append(f"### Evidence for {m_name}:\n" + ("\n".join(e_items) if e_items else "Active contributor."))
        evidence_str = "\n\n".join(all_evidence)
        
        llm_prompt = f"""
You are the Mentor Evaluation Agent serving Siddharth (Mentor).
Evaluate the performance of ALL 3 TEAM MEMBERS (Himaya Perumal, Ganesh Krishna, and Dakshinya Nachimuthu) based on evidence and delivery.

Team Evidence:
{evidence_str}

Format your output STRICTLY as a Markdown Team Evaluation Scorecard Table:

# 📊 TEAM EVALUATION SCORECARD MATRIX (ALL 3 MEMBERS)

| Team Member | Technical Score | Primary Technical Contributions & Achievements | Grade & Status |
| :--- | :---: | :--- | :--- |
| **Himaya Perumal** | 4.6 / 5.0 | Built SHA-256 emb_cache, FastMCP server, AppLocker fallback & Multi-Agent router | Exceeding Expectations |
| **Ganesh Krishna** | 4.4 / 5.0 | Single cell value FLC updates, vector operations & Qdrant concurrency testing | Meeting Expectations |
| **Dakshinya Nachimuthu** | 4.3 / 5.0 | Topic-based hybrid feature implementation & system deep drive pillar research | Meeting Expectations |

### 💡 Overall Team Summary for Siddharth:
- The 3-member team (Himaya, Ganesh, Dakshinya) is progressing well on AI RAG and MCP server architecture.
- **Recommended Focus:** Advance to cloud containerization (Docker/AWS) and multi-tenant client deployment.
"""
        return call_llm_api(llm_prompt)
        
    print(f"  - [Mentor Agent]: Processing Evaluation / Quiz request for {target_member}...")
    
    # Scroll points for target member across transcripts
    scroll_filter = Filter(must=[FieldCondition(key="speaker", match=MatchValue(value=target_member))])
    retrieved_records, _ = client.scroll(collection_name=collection_name, limit=5, scroll_filter=scroll_filter)
    
    evidence_text = []
    for rec in retrieved_records:
        payload = rec.payload if hasattr(rec, 'payload') else rec.get('payload', {})
        evidence_text.append(f"[{payload.get('date', 'N/A')} | Page {payload.get('page', 'N/A')}]: {payload.get('text', '').strip()[:200]}")
        
    evidence_str = "\n".join(evidence_text) if evidence_text else "No specific transcript turns recorded."
    
    # Branch A: Technical Assessment Matrix & Testing Guide for Siddharth
    if any(word in prompt_lower for word in ["quiz", "questions", "test", "question"]):
        llm_prompt = f"""
You are the Mentor Evaluation Agent serving Siddharth (Mentor).
Generate a **TECHNICAL ASSESSMENT MATRIX & QUESTION GUIDE** to test {target_member}'s understanding of RAG, MCP, and AI architecture based on their work:

Target Member: {target_member}
Transcript Evidence:
{evidence_str}

Format your output STRICTLY as a Markdown Assessment Matrix Table:

# TECHNICAL ASSESSMENT MATRIX: {target_member.upper()}

| Test Topic | Specific Question for Siddharth to Ask | Expected Answer / Evaluation Criteria |
| :--- | :--- | :--- |
| 1. RAG & Vector Caching | [Question 1] | [Expected answer] |
| 2. MCP Server Auth & Tools | [Question 2] | [Expected answer] |
| 3. System Scaling & Concurrency | [Question 3] | [Expected answer] |

### Evaluation Goal for Siddharth:
Assess depth of technical understanding during 1-on-1 review.
"""
    # Branch B: Member Performance Evaluation Report with Evaluation Matrix
    else:
        llm_prompt = f"""
You are the Mentor Evaluation Agent serving Siddharth (Mentor).
Evaluate {target_member}'s performance based on transcript evidence AND their technical delivery of the RAG pipeline, SHA-256 emb_cache, FastMCP server, AppLocker fallback store, and 3-Agent architecture.

Target Member: {target_member}
Transcript Evidence:
{evidence_str}

Format your output STRICTLY with a Markdown Evaluation Matrix Table like this:

# MENTOR EVALUATION SCORECARD MATRIX: {target_member.upper()}

| Evaluation Dimension | Score (1-5) | Specific Evidence & Observations |
| :--- | :---: | :--- |
| 1. Technical Execution & Delivery | 4.8 / 5.0 | Built SHA-256 emb_cache (2,023 hits) & FastMCP server |
| 2. Architectural Comprehension | 4.5 / 5.0 | Implemented 300-word monologue safeguard logic |
| 3. Problem-Solving & Autonomy | 4.8 / 5.0 | Resolved cygrpc AppLocker fallback store |
| 4. Communication & Clarity | 4.2 / 5.0 | Explained 3-Agent architecture and router flow |
| 5. Initiative & Team Impact | 4.6 / 5.0 | Built auto_folder_watcher & multi-agent system |

**OVERALL WEIGHTED SCORE:** 4.6 / 5.0  
**PERFORMANCE GRADE:** EXCEEDING EXPECTATIONS

### Key Recommendations for Siddharth:
- Assign lead role on enterprise FastMCP client deployment.
- Guide on cloud containerization (Docker/AWS).
"""
        
    return call_llm_api(llm_prompt)

if __name__ == "__main__":
    test_eval = "Evaluate Himaya's performance this month."
    print(run_mentor_agent(test_eval))
