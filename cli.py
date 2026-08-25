"""
================================================================================
Interactive Terminal CLI  (cli.py)
================================================================================
Multi-turn conversational terminal interface for the Multi-Agent RAG system.
Replaces the browser UI entirely.

Usage:
    python cli.py                           # Interactive session
    python cli.py --agent mentor            # Force mentor agent
    python cli.py --trainee Himaya          # Scope to trainee
    python cli.py --agent team --date "July 31"
    python cli.py --session my-session      # Named session (persists memory)

Commands during session:
    exit / quit / q     End session
    /reset              Clear conversation history for this session
    /history            Show conversation history
    /agent <name>       Switch forced agent (manager|mentor|team|auto)
    /trainee <name>     Set trainee scope
    /session <id>       Switch session
    /help               Show this help
================================================================================
"""

import sys
import os
import argparse
import textwrap

# Reconfigure standard output encoding for clean Windows terminal rendering
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph import run_graph, get_history, reset_session

# ── Terminal styling (plain ASCII, no unicode) ─────────────────────────────────
SEP      = "-" * 70
SEP_THIN = "." * 70


def _header(text: str) -> str:
    return f"\n{SEP}\n  {text}\n{SEP}"


def _dim(text: str) -> str:
    return text


def _wrap(text: str, width: int = 80, indent: int = 2) -> str:
    lines = text.split("\n")
    wrapped = []
    prefix = " " * indent
    for line in lines:
        if len(line) <= width:
            wrapped.append(prefix + line if line.strip() else line)
        else:
            for sub in textwrap.wrap(line, width=width - indent):
                wrapped.append(prefix + sub)
    return "\n".join(wrapped)


# ── Command handling ───────────────────────────────────────────────────────────

def handle_command(
    cmd: str,
    forced_agent: str,
    trainee: str,
    session_id: str
):
    """
    Handles slash-commands entered during the session.
    Returns (forced_agent, trainee, session_id) after applying changes.
    """
    parts = cmd.strip().split()
    command = parts[0].lower()

    if command == "/reset":
        reset_session(session_id)
        print(f"  [Memory cleared for session '{session_id}']")

    elif command == "/trace":
        if len(parts) < 2:
            print("  Usage: /trace <trace_id>   (e.g. /trace trc-12345)")
        else:
            trace_id = parts[1].strip()
            from agents.shared.logging import get_trace
            trace_data = get_trace(trace_id)
            if not trace_data:
                print(f"  [Error]: Trace '{trace_id}' not found in logs/traces/ directory.")
            else:
                print(_header(f"Trace Inspector: {trace_id}"))
                print(f"  Agent Model : {trace_data.get('llm_model', 'Unknown')}")
                print(f"  Dispatched  : {trace_data.get('agent', 'Unknown')} / {trace_data.get('skill', 'Unknown')}")
                print(f"  Final Status: {trace_data.get('final_status', 'Unknown')}")
                print(f"  Latency     : {trace_data.get('latency_seconds', 0.0)}s")
                print(f"  Tokens Used : Prompt={trace_data.get('token_usage', {}).get('prompt_tokens', 0)} | Completion={trace_data.get('token_usage', {}).get('completion_tokens', 0)}")
                print(f"  Qdrant Chunks: {len(trace_data.get('retrieved_chunk_ids', []))} retrieved points")
                if trace_data.get('retrieved_chunk_ids'):
                    print(f"  Point IDs   : {', '.join(trace_data.get('retrieved_chunk_ids')[:10])}...")
                print(SEP)

    elif command == "/history":
        history = get_history(session_id)
        if not history:
            print("  [No conversation history yet]")
        else:
            print(_header(f"Conversation History  (session: {session_id})"))
            for i, turn in enumerate(history, 1):
                role_label = "YOU  " if turn["role"] == "user" else "AGENT"
                content_preview = turn["content"][:200].replace("\n", " ")
                print(f"  [{i}] {role_label}: {content_preview}")
            print(SEP)

    elif command == "/agent":
        if len(parts) < 2:
            print("  Usage: /agent manager|mentor|team|auto")
        else:
            val = parts[1].lower()
            if val in ("manager", "mentor", "team", "auto", ""):
                forced_agent = None if val == "auto" else val
                print(f"  [Agent set to: {val}]")
            else:
                print(f"  Unknown agent '{val}'. Choose: manager | mentor | team | auto")

    elif command == "/trainee":
        if len(parts) < 2:
            print("  Usage: /trainee Himaya|Ganesh|Dakshinya|none")
        else:
            val = parts[1].strip()
            trainee = None if val.lower() in ("none", "all", "team") else val
            print(f"  [Trainee set to: {trainee or 'Auto-detect'}]")

    elif command == "/session":
        if len(parts) < 2:
            print("  Usage: /session <session-id>")
        else:
            session_id = parts[1].strip()
            print(f"  [Switched to session: {session_id}]")

    elif command == "/help":
        print(_header("Available Commands"))
        cmds = [
            ("/reset",           "Clear conversation history for this session"),
            ("/history",         "Show conversation history"),
            ("/agent <name>",    "Set agent: manager | mentor | team | auto"),
            ("/trainee <name>",  "Set trainee scope: Himaya | Ganesh | Dakshinya | none"),
            ("/session <id>",    "Switch to a named session (creates new memory)"),
            ("/trace <id>",      "Inspect execution metrics, latency, and point IDs"),
            ("/help",            "Show this help"),
            ("exit / q",         "End session"),
        ]
        for c, desc in cmds:
            print(f"  {c:<22}  {desc}")
        print(SEP)

    else:
        print(f"  Unknown command: '{cmd}'. Type /help for available commands.")

    return forced_agent, trainee, session_id


# ── Main interactive loop ──────────────────────────────────────────────────────

def run_cli(
    forced_agent: str = None,
    trainee: str = None,
    date: str = None,
    period: str = None,
    session_id: str = "default"
):
    print(_header("RAG_COMBINED  Multi-Agent Terminal  (LangGraph v2)"))
    print(f"  Session  : {session_id}")
    print(f"  Agent    : {forced_agent or 'Auto (LLM intent classifier)'}")
    print(f"  Trainee  : {trainee or 'Auto-detect from query'}")
    print(f"  Date     : {date or 'None'}")
    print(f"\n  Type your query and press Enter.")
    print(f"  Type /help for commands, exit to quit.")
    print(SEP)

    while True:
        try:
            raw = input("\n  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  [Session ended]")
            break

        if not raw:
            continue

        if raw.lower() in ("exit", "quit", "q"):
            print("\n  [Session ended]")
            break

        if raw.startswith("/"):
            forced_agent, trainee, session_id = handle_command(
                raw, forced_agent, trainee, session_id
            )
            continue

        # ── Run the LangGraph pipeline ─────────────────────────────────────────
        print(f"\n  [Routing query...  agent={forced_agent or 'auto'}  trainee={trainee or 'auto'}]")
        print(SEP_THIN)

        try:
            result = run_graph(
                query=raw,
                trainee=trainee,
                date=date,
                period=period,
                session_id=session_id,
                forced_agent=forced_agent,
            )

            # ── Print response ─────────────────────────────────────────────────
            print(_header(
                f"Agent: {result['dispatched_agent'].upper()}"
                f"  |  Latency: {result['latency_seconds']}s"
                f"  |  Trace: {result['trace_id']}"
            ))
            print(_wrap(result["final_response"]))
            print(SEP)

        except Exception as e:
            print(f"\n  [ERROR]: {e}")
            print(f"  The system encountered an error. Your conversation history is intact.")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RAG_COMBINED Multi-Agent Terminal CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples:
          python cli.py
          python cli.py --agent mentor --trainee Himaya
          python cli.py --agent team --date "July 31"
          python cli.py --agent manager --session review-session-aug25
        """)
    )
    parser.add_argument("--agent",   choices=["manager", "mentor", "team", "auto"],
                        default="auto", help="Force a specific agent (default: auto)")
    parser.add_argument("--trainee", type=str, default=None,
                        help="Scope queries to a trainee: Himaya | Ganesh | Dakshinya")
    parser.add_argument("--date",    type=str, default=None,
                        help="Session date for team catch-up (e.g. 'July 31')")
    parser.add_argument("--period",  type=str, default=None,
                        help="Date range for manager rollup (e.g. 'July 21 to July 28')")
    parser.add_argument("--session", type=str, default="default",
                        help="Session ID for conversation memory (default: 'default')")

    args = parser.parse_args()

    run_cli(
        forced_agent=None if args.agent == "auto" else args.agent,
        trainee=args.trainee,
        date=args.date,
        period=args.period,
        session_id=args.session,
    )


if __name__ == "__main__":
    main()
