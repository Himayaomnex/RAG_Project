import sys
sys.stdout.reconfigure(encoding="utf-8")

print("=" * 70)
print("MANAGER AGENT DEMO — Iyappan Sir View")
print("=" * 70)
from agents.manager_agent import run_manager_agent
r1 = run_manager_agent("What are the tasks and status completed by Himaya, Ganesh, and Dakshinya?")
print(r1)

print()
print("=" * 70)
print("MENTOR AGENT DEMO — Siddharth Saminathan View")  
print("=" * 70)
from agents.mentor_agent import run_mentor_agent
r2 = run_mentor_agent("Evaluate technical strengths, misconceptions and next tasks for Himaya, Ganesh, and Dakshinya.", "Himaya")
print(r2)
