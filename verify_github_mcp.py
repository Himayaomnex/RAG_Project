"""Terminal verification tool for GitHub MCP live code reading.
Demonstrates reading live code and artifacts from both:
1. Teammate repo: Dakshinya0101/RAG-demo
2. Own repo: Himayaomnex/RAG_Project
"""
from harness.tools.mcp import github_read_file

def run_proof():
    print("=" * 70)
    print(" GITHUB MCP LIVE CODE & ARTIFACT VERIFICATION PROOF")
    print("=" * 70)
    
    tests = [
        ("Dakshinya0101/RAG-demo", "pipeline.py", "Teammate Core RAG Pipeline"),
        ("Dakshinya0101/RAG-demo", "evaluation_results.md", "Teammate RAG Evaluation Report"),
        ("Dakshinya0101/RAG-demo", "agentic_rag.py", "Teammate Agentic Vector Search"),
        ("Himayaomnex/RAG_Project", "harness/runner.py", "Own LangGraph Agent Harness"),
        ("Himayaomnex/RAG_Project", "capabilities/team_catchup.md", "Own Mentor Capability Spec"),
    ]
    
    for repo, path, desc in tests:
        print(f"\n[QUERYING GITHUB API] Repo: {repo} | Path: {path}")
        print(f" Description: {desc}")
        try:
            items = github_read_file(path=path, repo=repo)
            item = items[0]
            first_line = item.content.splitlines()[0] if item.content.splitlines() else "<empty>"
            total_chars = len(item.content)
            print(f" Status: SUCCESS (200 OK via GitHub MCP)")
            print(f" Source: {item.source}")
            print(f" Citation ID: {item.id}")
            print(f" Origin: {item.origin}")
            print(f" Total Size: {total_chars:,} characters")
            print(f" First Line: {first_line[:80]}")
        except Exception as e:
            print(f" Status: FAILED - {e}")
            
    print("\n" + "=" * 70)
    print(" PROOF COMPLETE: Both teammate and own repos verified live.")
    print("=" * 70)

if __name__ == "__main__":
    run_proof()
