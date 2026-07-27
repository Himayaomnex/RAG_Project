"""
================================================================================
Teammates Agent - Codebase Learning & Technical Q&A Specialist
================================================================================
Serves Himaya, Ganesh, and Dakshinya by scanning local codebases, explaining
technical architectures (RAG, MCP, LangGraph), providing reading materials,
and answering technical questions.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from qdrant_queries import call_llm_api

def scan_local_codebase(target_file: str = "qdrant_queries.py") -> str:
    """Scans local python files to extract code snippets for explanation."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    file_path = os.path.join(base_dir, target_file)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content[:3000] # Return top 3,000 chars for context
        except Exception as e:
            return f"Error reading {target_file}: {e}"
    return f"File {target_file} not found."

def run_teammates_agent(user_prompt: str, user_name: str = "Teammate") -> str:
    """
    Teammates Agent execution logic:
    - Scans codebase files to answer technical questions.
    - Recommends structured learning materials and explains complex concepts.
    """
    print(f"  - [Teammates Agent]: Processing technical question / reading material request for {user_name}...")
    
    # Check if prompt references a specific file
    target_file = "qdrant_queries.py"
    if "mcp" in user_prompt.lower():
        target_file = "mcp_server.py"
    elif "report" in user_prompt.lower():
        target_file = "cache_reuse_report.py"
        
    code_excerpt = scan_local_codebase(target_file)
    
    llm_prompt = f"""
You are the Teammates Assistant Agent serving Himaya, Ganesh, and Dakshinya.
Answer the teammate's technical question by explaining the codebase, architecture, and recommending clear reading concepts:

Teammate Prompt: "{user_prompt}"

Code Excerpt from {target_file}:
```python
{code_excerpt[:1500]}
```

Provide a clear, educational, step-by-step technical explanation and recommended reading topics.
"""
    return call_llm_api(llm_prompt)

if __name__ == "__main__":
    test_q = "Explain how LocalVectorStore works in qdrant_queries.py"
    print(run_teammates_agent(test_q))
