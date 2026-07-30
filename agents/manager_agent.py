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
    if QDRANT_AVAILABLE:
        try:
            client = QdrantClient(path=storage_path)
        except Exception:
            client = LocalVectorStore(path=storage_path)
    else:
        client = LocalVectorStore(path=storage_path)
        
    collection_name = "meeting_transcripts"
    
    # Retrieve transcript evidence for ALL team members across collection
    context_chunks = []
    for member_name in ["Himaya Perumal", "Ganesh Krishna", "Dakshinya Nachimuthu", "Siddharth Saminathan"]:
        s_filter = Filter(must=[FieldCondition(key="speaker", match=MatchValue(value=member_name))])
        recs, _ = client.scroll(collection_name=collection_name, limit=10, scroll_filter=s_filter)
        for pt in recs:
            payload = pt.payload if hasattr(pt, 'payload') else pt.get('payload', {})
            clean_text = payload.get('text', '').strip()
            if len(clean_text) > 20:
                context_chunks.append(f"[{payload.get('date', 'N/A')} | Page {payload.get('page', 'N/A')} | Speaker: {payload.get('speaker', 'Unknown')}]: {clean_text[:250]}")
        
    from prompt_builder import EnterprisePromptBuilder
    
    prompt_builder = (
        EnterprisePromptBuilder(agent_type="manager", user_id="Iyappan Sir", role="manager")
        .add_security_guardrails("Iyappan Sir", "manager")
        .add_hallucination_and_failure_policy()
        .add_reasoning_and_thinking_policy()
        .add_metadata_context("aqua_rag_team", "July 2026 Meetings")
        .add_agent_role("manager")
        .add_tool_descriptions()
        .add_rag_context(context_chunks[:25])
        .add_citation_rules()
        .add_response_schema(
            "Format your executive status summary for Iyappan Sir clearly:\n\n"
            "### 📈 Executive Project Status Summary\n"
            "[High-level overview of active team projects, pipeline developments, and overall progress]\n\n"
            "### ✅ Completed Milestones & Accomplishments\n"
            "- **Himaya Perumal**: [Key technical tasks and project contributions from transcripts]\n"
            "- **Ganesh Krishna**: [Key technical tasks and project contributions from transcripts]\n"
            "- **Dakshinya Nachimuthu**: [Key technical tasks and project contributions from transcripts]\n\n"
            "### 📌 Next Steps & Action Items\n"
            "- [Specific, constructive action item assigned per member based on transcript evidence]\n"
            "- [Specific, constructive action item assigned per member based on transcript evidence]\n\n"
            "Do NOT include harsh numerical scorecard ratings or negative labels. Focus strictly on constructive deliverables and milestone progress."
        )
        .add_user_query(user_prompt)
    )
    llm_prompt = prompt_builder.build()
    res = call_llm_api(llm_prompt)
    if not res:
        res = "### 📈 Executive Status Summary & Team Deliverables\n\n" + "\n\n".join(context_chunks[:15])
    return res

if __name__ == "__main__":
    test_query = "What are the action items and project updates for the team?"
    print(run_manager_agent(test_query))
