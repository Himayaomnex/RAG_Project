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
import importlib
import agents.manager_agent
import agents.mentor_agent
import agents.teammates_agent

def route_request(user_prompt: str, user_role: str = "auto", target_member: str = "") -> str:
    """
    Central router function:
    1. Inspects user_role or prompt intent.
    2. Dispatches to Manager Agent, Mentor Agent, or Teammates Agent.
    3. Reloads agent modules dynamically from disk on every invocation.
    """
    importlib.reload(agents.manager_agent)
    importlib.reload(agents.mentor_agent)
    importlib.reload(agents.teammates_agent)
    
    from agents.manager_agent import run_manager_agent
    from agents.mentor_agent import run_mentor_agent
    from agents.teammates_agent import run_teammates_agent

    role_lower = user_role.lower()
    prompt_lower = user_prompt.lower()
    
    print(f"\n[Router.py Dispatching Request]: Role='{user_role}' | Prompt='{user_prompt}'")
    print("=" * 80)
    
    # Explicit Role Routing
    if role_lower in ["manager", "project_lead"]:
        return run_manager_agent(user_prompt, target_member=target_member)
        
    elif role_lower in ["siddharth", "mentor", "evaluator"]:
        return run_mentor_agent(user_prompt, target_member=target_member)
        
    elif role_lower in ["himaya", "ganesh", "dakshinya", "teammate", "intern"]:
        # Intent Override for Teammates/Mentor: Evaluation & Quiz requests
        if any(word in prompt_lower for word in ["evaluate", "performance", "score", "quiz"]):
            target = target_member if target_member else user_role.capitalize()
            return run_mentor_agent(user_prompt, target_member=target)
        return run_teammates_agent(user_prompt, user_name=user_role.capitalize())
        
    # Auto Role Detection based on Prompt Intent
    else:
        if any(word in prompt_lower for word in ["evaluate", "performance", "score", "quiz"]):
            return run_mentor_agent(user_prompt, target_member=target_member)
        elif any(word in prompt_lower for word in ["code", "explain", "how does", "reading"]):
            return run_teammates_agent(user_prompt, user_name="Teammate")
        else:
            return run_manager_agent(user_prompt, target_member=target_member)

if __name__ == "__main__":
    print(route_request("What are the action items for the team?", user_role="manager"))
