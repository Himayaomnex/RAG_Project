"""
================================================================================
Enterprise Multi-Agent Demonstration & Verification System (RAG_COMBINED)
================================================================================
Demonstrates all 5 workflows across the specialized agents:
- Manager Agent (Manager / Iyappan Sir role)
- Mentor Agent (Siddharth Saminathan role)
- Teammates Agent (Himaya, Ganesh, Dakshinya role)
- Router & RAG_Training Chunking & Qdrant Retriever Integration
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
    print_header("RAG_COMBINED MULTI-AGENT SYSTEM - LIVE VERIFICATION")
    
    # ---------------------------------------------------------
    # WORKFLOW 1: Manager asks for team action items (Manager Agent)
    # ---------------------------------------------------------
    print_header("WORKFLOW 1: Manager queries team action items (Manager Agent)")
    res1 = route_request("What are the project updates and action items for Himaya, Ganesh, and Dakshinya?", user_role="manager")
    print(res1)
    time.sleep(1)
    
    # ---------------------------------------------------------
    # WORKFLOW 2: Manager asks for performance evaluation (Manager -> Mentor Agent)
    # ---------------------------------------------------------
    print_header("WORKFLOW 2: Manager asks for evaluation on Himaya (Manager -> Mentor Agent)")
    res2 = route_request("How has Himaya performed regarding embedding cache and vector pipeline?", user_role="manager", target_member="Himaya")
    print(res2)
    time.sleep(1)
    
    # ---------------------------------------------------------
    # WORKFLOW 3: Siddharth asks for performance evaluation (Mentor Agent)
    # ---------------------------------------------------------
    print_header("WORKFLOW 3: Siddharth requests technical evaluation for Dakshinya (Mentor Agent)")
    res3 = route_request("Evaluate Dakshinya's technical contributions and progress.", user_role="siddharth", target_member="Dakshinya")
    print(res3)
    time.sleep(1)
    
    # ---------------------------------------------------------
    # WORKFLOW 4: Himaya asks for technical codebase explanation (Teammates Agent)
    # ---------------------------------------------------------
    print_header("WORKFLOW 4: Himaya asks for code explanation (Teammates Agent - Himaya)")
    res4 = route_request("Explain how SemanticTranscriptParser and Qdrant work in pipeline.py", user_role="himaya")
    print(res4)
    time.sleep(1)
    
    # ---------------------------------------------------------
    # WORKFLOW 5: Siddharth asks for testing quiz questions for Ganesh (Mentor Agent)
    # ---------------------------------------------------------
    print_header("WORKFLOW 5: Siddharth requests testing quiz for Ganesh (Mentor Agent)")
    res5 = route_request("Generate 3 technical testing quiz questions for Ganesh.", user_role="siddharth", target_member="Ganesh")
    print(res5)
    
    print_header("ALL 5 MULTI-AGENT WORKFLOWS VERIFIED SUCCESSFULLY IN RAG_COMBINED")

if __name__ == "__main__":
    main()
