"""Interactive CLI and query runner for the Agent Harness."""

import sys
import json
import argparse

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from harness.runner import run_agent
from harness.capabilities.loader import capability_registry


def main():
    parser = argparse.ArgumentParser(description="Omnex Training-Program Agent Harness Runner")
    parser.add_argument("query", nargs="*", help="The task or question for the agent")
    parser.add_argument("--capability", "-c", choices=capability_registry.list_names(), default=None,
                        help="Pin a specific capability (default: auto/ad_hoc)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive session")

    args = parser.parse_args()

    if args.interactive or not args.query:
        print("=" * 70)
        print("OMNEX AGENT HARNESS - INTERACTIVE RUNNER")
        print(f"Available Capabilities: {', '.join(capability_registry.list_names())}")
        print("Type 'exit' or 'quit' to stop.")
        print("=" * 70)

        while True:
            try:
                task = input("\n[?] Enter your task / question (or 'q' to exit): ").strip()
                if task.lower() in ("exit", "quit", "q"):
                    break
                if not task:
                    continue

                print(f"\n[*] Auto-routing query & executing LangGraph Dual-Loop agent...")
                inferred = capability_registry.infer_capability(task)
                print(f"[*] Inferred Capability: {inferred}")
                result = run_agent(task=task, capability=inferred)
                print_result(result)
            except KeyboardInterrupt:
                print("\nExiting.")
                break
    else:
        task = " ".join(args.query)
        inferred = args.capability or capability_registry.infer_capability(task)
        print(f"Running task: {task} (Capability: {inferred})")
        result = run_agent(task=task, capability=inferred)
        print_result(result)


def print_result(result):
    print("\n" + "=" * 70)
    print(f"RESULT SUMMARY [Trace ID: {result['trace_id']}]")
    print(f"Status:      {result['status']}")
    print(f"Capability:  {result['capability']}")
    print(f"Tool Calls:  {result['tool_calls_used']}")
    print("=" * 70)

    if result.get("plan_history"):
        print("\nPLAN HISTORY (Decisions made by Model):")
        for idx, p in enumerate(result["plan_history"], 1):
            action = p.get("action")
            tool = p.get("tool")
            thought = p.get("thought", "")
            print(f"  Turn {idx}: [{action}] {f'tool={tool}' if tool else ''}")
            print(f"          Thought: {thought}")

    if result.get("observations"):
        print("\nOBSERVATIONS (Evidence Collected):")
        for o in result["observations"]:
            tool = o.get("tool")
            res_cnt = o.get("result_count", 0)
            toks = o.get("tokens_added", 0)
            summary = o.get("summary", "")
            print(f"  - {tool}: {summary} ({toks} tokens)")

    if result.get("violations"):
        print("\nVERIFIER VIOLATIONS:")
        for v in result["violations"]:
            print(f"  - Field '{v.get('field')}': {v.get('why')} (Rule: {v.get('rule')})")

    if result.get("output"):
        print("\nVERIFIED OUTPUT (JSON):")
        print(json.dumps(result["output"], indent=2))
    elif result.get("error"):
        print(f"\nERROR: {result.get('error')}")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
