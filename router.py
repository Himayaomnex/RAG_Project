"""
================================================================================
Central Prompt Router & Role Dispatcher (router.py)
================================================================================
Routes incoming user requests based on user role (Manager, Siddharth/Mentor, 
or Teammates: Himaya/Ganesh/Dakshinya) to the appropriate Agent module.
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))
from agents.manager_agent import run_manager_agent
from agents.mentor_agent import run_mentor_agent
from agents.teammates_agent import run_teammates_agent

def route_request(user_prompt: str, user_role: str = "auto", target_member: str = "") -> str:
    """
    Central router function:
    1. Inspects user_role or prompt intent.
    2. Dispatches to Manager Agent, Mentor Agent, or Teammates Agent.
    3. Handles Manager Agent -> Mentor Agent delegation for evaluation requests.
    """
    role_lower = user_role.lower()
    prompt_lower = user_prompt.lower()
    
    print(f"\n[Router.py Dispatching Request]: Role='{user_role}' | Prompt='{user_prompt}'")
    print("=" * 80)
    
    # Priority 1: Check Intent for Performance Evaluation & Quizzes -> Mentor Agent
    if any(word in prompt_lower for word in ["evaluate", "performance", "score", "rating", "quiz", "questions", "test"]):
        return run_mentor_agent(user_prompt, target_member=target_member or (role_lower if role_lower in ["himaya", "ganesh", "dakshinya"] else ""))

    # Priority 2: Check Intent for Manager Status & Action Items -> Manager Agent
    if any(word in prompt_lower for word in ["action item", "status", "summary", "project update", "roadblock"]):
        return run_manager_agent(user_prompt, target_member=target_member)

    # Priority 3: Role-Based Routing
    if role_lower in ["manager", "project_lead"]:
        return run_manager_agent(user_prompt, target_member=target_member)
    elif role_lower in ["siddharth", "mentor", "evaluator"]:
        return run_mentor_agent(user_prompt, target_member=target_member)
    else:
        return run_teammates_agent(user_prompt, user_name=user_role.capitalize())

if __name__ == "__main__":
    print(route_request("What are the action items for the team?", user_role="manager"))
