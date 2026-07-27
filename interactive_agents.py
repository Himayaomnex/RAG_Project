"""
================================================================================
Interactive Multi-Agent Chat Interface (interactive_agents.py)
================================================================================
Allows users (Manager, Siddharth, Himaya, Ganesh, Dakshinya) to interactively
type questions in terminal and receive real-time answers from the 3 Agents.
"""

import sys
import os
from router import route_request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=" * 80)
    print("  ENTERPRISE MULTI-AGENT INTERACTIVE SYSTEM")
    print("=" * 80)
    print("Available Roles: manager, siddharth, himaya, ganesh, dakshinya")
    print("Type 'exit' or 'quit' to end session.\n")
    
    # Prompt for User Role
    user_role = input("Enter your role (e.g. 'siddharth', 'manager', 'himaya'): ").strip()
    if not user_role:
        user_role = "siddharth"
        
    print(f"\n[Session Started as Role: '{user_role}']\n")
    
    while True:
        try:
            user_prompt = input(f"[{user_role.capitalize()}] Ask a question > ").strip()
            if not user_prompt:
                continue
            if user_prompt.lower() in ["exit", "quit", "q"]:
                print("\nEnding session. Goodbye!")
                break
                
            response = route_request(user_prompt, user_role=user_role)
            print("\n" + response + "\n")
            print("-" * 80)
        except (KeyboardInterrupt, EOFError):
            print("\nEnding session. Goodbye!")
            break

if __name__ == "__main__":
    main()
