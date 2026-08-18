"""
================================================================================
Central Prompt Router & Agent Dispatcher (RAG_COMBINED)
================================================================================
Routes user prompts to Manager Agent, Mentor Agent, or Teammates Agent
(Himaya, Ganesh, Dakshinya) using RAG_Training chunking & Qdrant retriever.
"""

import sys
import os
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from agents.manager_agent import run_manager_agent
from agents.mentor_agent import run_mentor_agent
from agents.teammates_agent import run_teammates_agent
from agents.production_agents import SharedRAGRetriever, ManagerAgent, MentorAgent, TeamIntelligenceAgent

_shared_retriever = None

def get_shared_retriever():
    global _shared_retriever
    if _shared_retriever is None:
        _shared_retriever = SharedRAGRetriever()
    return _shared_retriever

def route_request(user_prompt: str, user_role: str = "auto", target_member: str = "") -> str:
    """
    Central router function:
    1. Inspects user_role or prompt intent.
    2. Dispatches to Manager Agent, Mentor Agent, or Teammates Agent.
    3. Uses RAG_Training semantic topic-shift chunking & Qdrant dense vector retriever.
    """
    role_lower = user_role.lower()
    prompt_lower = user_prompt.lower()
    
    print(f"\n[Router Dispatching]: Role='{user_role}' | Prompt='{user_prompt}'")
    print("=" * 80)
    
    retriever = get_shared_retriever()
    
    # 1. Manager Role Dispatch
    if role_lower in ["manager", "project_lead", "executive", "iyappan"]:
        return run_manager_agent(user_prompt, target_member=target_member)
        
    # 2. Mentor Role Dispatch
    elif role_lower in ["siddharth", "mentor", "evaluator"]:
        mentee = target_member if target_member else ("Ganesh" if "ganesh" in prompt_lower else ("Dakshinya" if "dakshinya" in prompt_lower else "Himaya"))
        return run_mentor_agent(user_prompt, target_mentee=mentee)
        
    # 3. Teammate Specific Role Dispatch (Himaya, Ganesh, Dakshinya)
    elif role_lower in ["himaya", "ganesh", "dakshinya", "teammate", "teammates"]:
        name_map = {"himaya": "Himaya", "ganesh": "Ganesh", "dakshinya": "Dakshinya"}
        t_name = name_map.get(role_lower, target_member if target_member else "Himaya")
        return run_teammates_agent(user_prompt, user_name=t_name)
        
    # 4. Auto Intent Dispatch
    else:
        # Mentor Agent keywords — evaluation, learning, feedback
        mentor_keywords = [
            "evaluate", "mentor", "weakness", "strength", "quiz", "mentee",
            "misconception", "methodology", "problem-solving", "next task",
            "next tasks", "learning topic", "feedback", "guidance", "diagnosis",
            "diagnose", "learning gap", "technical gap", "understanding"
        ]
        # Manager Agent keywords — executive status, progress, blockers
        manager_keywords = [
            "accomplishment", "milestone", "blocker", "risk", "decision",
            "resource allocation", "executive", "progress", "status",
            "timeline", "delay", "action item", "deliverable", "pending",
            "completed", "what did", "project update", "team update"
        ]
        # Teammates / Codebase keywords
        teammate_keywords = [
            "code", "pipeline", "qdrant", "how works", "explain", "architecture",
            "semantic", "chunking", "embedding", "cachedembedding",
            "semantictranscriptparser", "vector", "retriever", "reranker",
            "transcript parser", "dense", "collection"
        ]

        if any(w in prompt_lower for w in mentor_keywords):
            return run_mentor_agent(user_prompt, target_mentee=target_member if target_member else "Himaya")
        elif any(w in prompt_lower for w in teammate_keywords):
            return run_teammates_agent(user_prompt, user_name=target_member if target_member else "Himaya")
        else:
            return run_manager_agent(user_prompt, target_member=target_member)

if __name__ == "__main__":
    print(route_request("What completed work was reported by Ganesh?", user_role="manager"))
