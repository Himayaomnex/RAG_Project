"""
================================================================================
GitHub MCP Agent Connection Verification Script (RAG_COMBINED)
================================================================================
Demonstrates that Teammate & Manager Agents consume live GitHub MCP contexts
alongside Qdrant meeting transcript evidence.
"""

import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from prompt_builder import PromptBuilder
from llm_client import generate_llm_response
from github_mcp_client import github_mcp

def test_agent_github_connection():
    print("================================================================================")
    print("  VERIFYING GITHUB MCP AGENT CONNECTION")
    print("================================================================================")
    
    owner = "octocat"
    repo = "Hello-World"
    
    print(f"1. Fetching live GitHub MCP context for {owner}/{repo}...")
    gh_context = github_mcp.format_github_context_for_llm(owner, repo)
    print(gh_context)
    
    print("2. Constructing Agent Prompt via PromptBuilder...")
    builder = PromptBuilder(user_id="USR-TM-01", role="Teammate")
    builder.add_security_guardrails()
    builder.add_speaker_attribution_policy()
    builder.add_grounding_policy()
    builder.add_output_policy()
    builder.add_agent_role("teammates")
    builder.add_github_mcp_context(owner, repo)
    
    user_query = f"What are the recent GitHub commits and open issues for repository {owner}/{repo}?"
    builder.add_user_query(user_query)
    system_prompt = builder.build()
    
    print("3. Invoking Groq LLM Agent with GitHub MCP Context...")
    response = generate_llm_response(system_prompt, user_query, fallback_response="Fallback")
    
    print("\n================================================================================")
    print("  AGENT RESPONSE WITH GITHUB MCP DATA:")
    print("================================================================================")
    print(response)
    print("================================================================================")

if __name__ == "__main__":
    test_agent_github_connection()
