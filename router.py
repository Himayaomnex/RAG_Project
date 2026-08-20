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

def detect_agent_intent(user_prompt: str) -> str:
    prompt_lower = user_prompt.lower()
    mentor_keywords = [
        "evaluate", "mentor", "weakness", "strength", "quiz", "mentee", "score",
        "misconception", "methodology", "problem-solving", "next task", "grading",
        "next tasks", "learning topic", "feedback", "guidance", "diagnosis", "grade",
        "diagnose", "learning gap", "technical gap", "understanding", "coaching"
    ]
    teammate_keywords = [
        "code", "pipeline", "qdrant", "how works", "explain", "architecture",
        "semantic", "chunking", "embedding", "cachedembedding",
        "semantictranscriptparser", "vector", "retriever", "reranker",
        "transcript parser", "dense", "collection"
    ]
    if any(w in prompt_lower for w in mentor_keywords):
        return "mentor"
    elif any(w in prompt_lower for w in teammate_keywords):
        return "teammate"
    return "manager"


def route_request_with_role(user_prompt: str, user_role: str = "auto", target_member: str = "") -> tuple:
    """
    Central router function that returns (result_text, dispatched_role_name).
    """
    role_lower = user_role.lower()
    prompt_lower = user_prompt.lower()
    
    print(f"\n[Router Dispatching]: Role='{user_role}' | Prompt='{user_prompt}'")
    print("=" * 80)
    
    # 1. Manager Role Dispatch
    if role_lower in ["manager", "project_lead", "executive", "iyappan"]:
        return run_manager_agent(user_prompt, target_member=target_member), "manager"
        
    # 2. Mentor Role Dispatch
    elif role_lower in ["siddharth", "mentor", "evaluator"]:
        p_low = prompt_lower
        if target_member:
            mentee = target_member
        elif any(w in p_low for w in ["all", "everyone", "trainees", "mentees", "team"]):
            mentee = "All Team Members"
        elif "ganesh" in p_low and "himaya" not in p_low and "dakshinya" not in p_low:
            mentee = "Ganesh"
        elif "dakshinya" in p_low and "himaya" not in p_low and "ganesh" not in p_low:
            mentee = "Dakshinya"
        elif "himaya" in p_low and "ganesh" not in p_low and "dakshinya" not in p_low:
            mentee = "Himaya"
        else:
            mentee = "All Team Members"
        return run_mentor_agent(user_prompt, target_mentee=mentee), "mentor"
        
    # 3. Teammate Specific Role Dispatch (Himaya, Ganesh, Dakshinya)
    elif role_lower in ["himaya", "ganesh", "dakshinya", "teammate", "teammates"]:
        name_map = {"himaya": "Himaya", "ganesh": "Ganesh", "dakshinya": "Dakshinya"}
        t_name = name_map.get(role_lower, target_member if target_member else "Himaya")
        return run_teammates_agent(user_prompt, user_name=t_name), "teammate"
        
    # 4. Auto Intent Dispatch
    else:
        detected = detect_agent_intent(user_prompt)
        if detected == "mentor":
            p_low = prompt_lower
            if target_member:
                mentee = target_member
            elif any(w in p_low for w in ["all", "everyone", "trainees", "mentees", "team"]):
                mentee = "All Team Members"
            elif "ganesh" in p_low and "himaya" not in p_low and "dakshinya" not in p_low:
                mentee = "Ganesh"
            elif "dakshinya" in p_low and "himaya" not in p_low and "ganesh" not in p_low:
                mentee = "Dakshinya"
            elif "himaya" in p_low and "ganesh" not in p_low and "dakshinya" not in p_low:
                mentee = "Himaya"
            else:
                mentee = "All Team Members"
            return run_mentor_agent(user_prompt, target_mentee=mentee), "mentor"
        elif detected == "teammate":
            return run_teammates_agent(user_prompt, user_name=target_member if target_member else "Himaya"), "teammate"
        else:
            return run_manager_agent(user_prompt, target_member=target_member), "manager"


def route_request(user_prompt: str, user_role: str = "auto", target_member: str = "") -> str:
    result, _ = route_request_with_role(user_prompt, user_role=user_role, target_member=target_member)
    return result


if __name__ == "__main__":
    print(route_request("What completed work was reported by Ganesh?", user_role="manager"))
