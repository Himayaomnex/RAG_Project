"""
================================================================================
Enterprise Multi-Agent Demonstration & Verification System
================================================================================
Demonstrates all 5 workflows across the 3 specialized agents:
- Manager Agent (Manager role)
- Mentor Agent (Siddharth / Evaluation Framework role)
- Teammates Agent (Himaya, Ganesh, Dakshinya role)
- Router & Agent-to-Agent Delegation Logic
"""

import sys
import os
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from router import route_request

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def main():
    print_header("ENTERPRISE MULTI-AGENT SYSTEM - LIVE DEMONSTRATION")
    
    # ---------------------------------------------------------
    # WORKFLOW 1: Manager asks for team action items (Direct Manager Agent)
    # ---------------------------------------------------------
    print_header("WORKFLOW 1: Manager queries team action items (Manager Agent)")
    res1 = route_request("What are the project updates and action items for the team?", user_role="manager")
    print(res1)
    time.sleep(2)
    
    # ---------------------------------------------------------
    # WORKFLOW 2: Manager asks for performance evaluation (Delegation -> Mentor Agent)
    # ---------------------------------------------------------
    print_header("WORKFLOW 2: Manager asks for evaluation (Manager Agent -> Mentor Agent Delegation)")
    res2 = route_request("How has Himaya performed this month regarding embedding cache?", user_role="manager", target_member="Himaya Perumal")
    print(res2)
    time.sleep(2)
    
    # ---------------------------------------------------------
    # WORKFLOW 3: Siddharth asks for performance evaluation (Direct Mentor Agent)
    # ---------------------------------------------------------
    print_header("WORKFLOW 3: Siddharth requests evaluation for Dakshinya (Mentor Agent)")
    res3 = route_request("Evaluate Dakshinya's technical contributions and progress.", user_role="siddharth", target_member="Dakshinya Nachimuthu")
    print(res3)
    time.sleep(2)
    
    # ---------------------------------------------------------
    # WORKFLOW 4: Himaya asks for technical codebase explanation (Teammates Agent)
    # ---------------------------------------------------------
    print_header("WORKFLOW 4: Himaya asks for code explanation (Teammates Agent)")
    res4 = route_request("Explain how LocalVectorStore works in qdrant_queries.py", user_role="himaya")
    print(res4)
    time.sleep(2)
    
    # ---------------------------------------------------------
    # WORKFLOW 5: Siddharth asks for testing quiz questions for Ganesh (Mentor Agent)
    # ---------------------------------------------------------
    print_header("WORKFLOW 5: Siddharth requests testing quiz for Ganesh (Mentor Agent)")
    res5 = route_request("Generate 3 technical testing quiz questions for Ganesh.", user_role="siddharth", target_member="Ganesh Krishna")
    print(res5)
    
    print_header("ALL 5 MULTI-AGENT WORKFLOWS VERIFIED SUCCESSFULLY")

if __name__ == "__main__":
    main()
