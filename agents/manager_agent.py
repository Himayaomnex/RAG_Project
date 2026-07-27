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
from qdrant_queries import get_embedding, extract_clean_keywords, call_llm_api, QDRANT_AVAILABLE, QdrantClient, LocalVectorStore

def run_manager_agent(user_prompt: str, target_member: str = "") -> str:
    """
    Manager Agent execution logic:
    - Analyzes manager requests for meeting summaries, team status, and action items.
    - If request requires performance evaluation, delegates to Mentor Agent.
    """
    prompt_lower = user_prompt.lower()
    
    # Delegate evaluation requests to Mentor Agent
    if any(word in prompt_lower for word in ["evaluate", "performance", "how has", "performing", "score", "rating"]):
        from agents.mentor_agent import run_mentor_agent
        print("  - [Manager Agent]: Evaluation request detected. Delegating to Mentor Agent...")
        return run_mentor_agent(user_prompt, target_member=target_member)
        
    print("  - [Manager Agent]: Processing meeting status / action item request...")
    
    storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qdrant_storage")
    if QDRANT_AVAILABLE:
        try:
            client = QdrantClient(path=storage_path)
        except Exception:
            client = LocalVectorStore(path=storage_path)
    else:
        client = LocalVectorStore(path=storage_path)
        
    collection_name = "meeting_transcripts"
    
    # Query Qdrant vector index for project updates and action items
    query_vec = get_embedding(user_prompt)
    search_res = client.query_points(collection_name=collection_name, query=query_vec, limit=4)
    
    context_chunks = []
    for pt in search_res.points:
        payload = pt.payload
        context_chunks.append(f"[{payload.get('date', 'N/A')} | Page {payload.get('page', 'N/A')} | {payload.get('speaker', 'Unknown')}]: {payload.get('text', '').strip()}")
        
    context_str = "\n\n".join(context_chunks)
    
    llm_prompt = f"""
You are the Manager Agent for an enterprise software team.
Based on the following meeting transcript context, summarize the team project status, completed milestones, and action items.

User Question: "{user_prompt}"

Meeting Evidence:
{context_str}

Provide a concise, professional summary for the Manager.
"""
    return call_llm_api(llm_prompt)

if __name__ == "__main__":
    test_query = "What are the action items and project updates for the team?"
    print(run_manager_agent(test_query))
