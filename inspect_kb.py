"""
================================================================================
Interactive Knowledge Base Explorer (inspect_kb.py)
================================================================================
Interactive terminal tool to inspect Ganesh's Supabase PostgreSQL Knowledge Base.
================================================================================
"""

import os
import sys

# Ensure workspace root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.shared.kb_client import kb_client

SEP = "=" * 80
SEP_THIN = "-" * 80


def print_table(title: str, headers: list, rows: list, max_col_widths: list = None):
    print(f"\n{SEP}\n  📊 {title.upper()}\n{SEP}")
    if not rows:
        print("  [No data returned]")
        print(SEP)
        return

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            str_val = str(val if val is not None else "-")
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str_val))

    if max_col_widths:
        for i, max_w in enumerate(max_col_widths):
            if i < len(col_widths) and max_w:
                col_widths[i] = min(col_widths[i], max_w)

    # Format header
    header_str = " | ".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers)))
    divider_str = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(f"  {header_str}")
    print(f"  {divider_str}")

    # Format rows
    for row in rows:
        row_str = " | ".join(f"{str(row[i] if row[i] is not None else '-')[:col_widths[i]]:<{col_widths[i]}}" for i in range(len(headers)))
        print(f"  {row_str}")
    print(f"{SEP}\n  Total rows: {len(rows)}\n{SEP}\n")


def menu():
    while True:
        print(f"\n{SEP}")
        print("  🔍 GANESH'S SUPABASE KNOWLEDGE BASE EXPLORER")
        print(f"{SEP}")
        print("  [1] Trainee Scoreboard & State (kb.v_person_state)")
        print("  [2] Active Deliverables & Deadlines (kb.v_assignments_current)")
        print("  [3] Concept Gaps & Confusions (kb.v_concepts)")
        print("  [4] Q&A Quality & Exam Performance (kb.v_qa)")
        print("  [5] Mentor Feedback History (kb.v_feedback)")
        print("  [6] Architectural Decisions Register (kb.v_decisions)")
        print("  [7] Session Digests & Daily Deltas (kb.v_digests)")
        print("  [8] Run Custom SQL Query")
        print("  [0] Exit")
        print(SEP)

        choice = input("Enter choice [0-8]: ").strip()

        if choice == "0" or choice.lower() in ("exit", "q", "quit"):
            print("Exiting KB Explorer. Goodbye!")
            break

        elif choice == "1":
            states = kb_client.get_person_state()
            headers = ["Person", "Open Tasks", "Delivered", "Late", "Concepts Demo'd", "Confused", "Partial", "Feedback"]
            rows = [
                [s.get("person"), s.get("assignments_open"), s.get("assignments_delivered"), s.get("assignments_late"),
                 s.get("concepts_demonstrated"), s.get("concepts_confused"), s.get("concepts_partial"), s.get("feedback_received")]
                for s in states
            ]
            print_table("Trainee Scoreboard (kb.v_person_state)", headers, rows)

        elif choice == "2":
            assignments = kb_client.get_current_assignments()
            headers = ["Trainee", "Status", "Due Date", "Delivered", "Late?", "Task Description"]
            rows = [
                [a.get("person"), a.get("status"), a.get("due_date"), a.get("delivered_date"), "YES" if a.get("was_late") else "NO", a.get("task_description")]
                for a in assignments
            ]
            print_table("Current Deliverables (kb.v_assignments_current)", headers, rows, [20, 12, 12, 12, 6, 50])

        elif choice == "3":
            gaps = kb_client.get_concept_gaps()
            headers = ["Trainee", "Concept", "State", "Session Date", "Observation"]
            rows = [
                [cg.get("person"), cg.get("concept"), cg.get("understanding_state"), cg.get("session_date"), cg.get("observation")]
                for cg in gaps
            ]
            print_table("Concept Gaps (kb.v_concepts)", headers, rows, [20, 25, 10, 12, 50])

        elif choice == "4":
            qas = kb_client.get_qa_history()
            headers = ["Answered By", "Topic", "Quality", "Date", "Question", "Answer Summary"]
            rows = [
                [q.get("answered_by"), q.get("topic"), q.get("answer_quality"), q.get("session_date"), q.get("question_text"), q.get("answer_summary")]
                for q in qas
            ]
            print_table("Q&A Evaluations (kb.v_qa)", headers, rows, [20, 15, 12, 12, 30, 40])

        elif choice == "5":
            fb = kb_client.get_feedback_history()
            headers = ["To Person", "From", "Topic", "Sentiment", "Date", "Verbatim Feedback"]
            rows = [
                [f.get("to_person"), f.get("from_person"), f.get("topic"), f.get("sentiment"), f.get("session_date"), f.get("verbatim_feedback")]
                for f in fb
            ]
            print_table("Mentor Feedback (kb.v_feedback)", headers, rows, [20, 20, 15, 10, 12, 50])

        elif choice == "6":
            decisions = kb_client.get_decisions()
            headers = ["Date", "Owner", "Scope", "Decision Text", "Rationale"]
            rows = [
                [d.get("session_date"), d.get("owner"), d.get("scope"), d.get("decision_text"), d.get("rationale")]
                for d in decisions
            ]
            print_table("Decisions Register (kb.v_decisions)", headers, rows, [12, 20, 10, 40, 40])

        elif choice == "7":
            digests = kb_client.get_session_digest()
            headers = ["Date", "Key Topics", "Summary", "Unresolved Items"]
            rows = [
                [d.get("session_date"), d.get("key_topics"), d.get("summary"), d.get("unresolved_items")]
                for d in digests
            ]
            print_table("Session Digests (kb.v_digests)", headers, rows, [12, 25, 45, 30])

        elif choice == "8":
            sql = input("\nEnter SQL query (e.g. SELECT * FROM kb.v_person_state LIMIT 5): ").strip()
            if sql:
                try:
                    res = kb_client._query(sql)
                    if res:
                        headers = list(res[0].keys())
                        rows = [[r.get(h) for h in headers] for r in res]
                        print_table("Custom Query Results", headers, rows)
                    else:
                        print("  [0 rows returned]")
                except Exception as e:
                    print(f"  [Query Error]: {e}")
        else:
            print("Invalid choice, please select 0-8.")


if __name__ == "__main__":
    menu()
