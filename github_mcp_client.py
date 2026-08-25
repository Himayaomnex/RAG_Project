"""
================================================================================
GitHub Model Context Protocol (MCP) Integration Engine (RAG_COMBINED)
================================================================================
Connects Multi-Agent RAG system to GitHub MCP Server & REST API:
- Enables Teammate & Manager Agents to query GitHub repos, commits, issues, and code diffs.
- Supports GITHUB_TOKEN from .env or unauthenticated public repository access.
- Implements MCP tool schemas for GitHub context retrieval.
"""

import os
import requests
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"


class GitHubMCPClient:
    """
    Model Context Protocol (MCP) Client for GitHub Integration.
    Exposes structured MCP tool functions for agent invocation.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MultiAgent-RAG-System"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def get_headers(self) -> Dict[str, str]:
        return self.headers


    def list_repository_issues(self, owner: str, repo: str, state: str = "open", limit: int = 10) -> List[Dict[str, Any]]:
        """
        MCP Tool: github_list_issues
        Fetches open/closed issues and pull requests from a target GitHub repository.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
        params = {"state": state, "per_page": limit}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                issues = resp.json()
                results = []
                for issue in issues:
                    results.append({
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "user": issue.get("user", {}).get("login"),
                        "state": issue.get("state"),
                        "created_at": issue.get("created_at"),
                        "url": issue.get("html_url"),
                        "body": (issue.get("body") or "")[:300]
                    })
                return results
            else:
                print(f"  - [GitHub MCP Warning]: API returned status {resp.status_code}: {resp.text[:200]}")
                return []
        except Exception as e:
            print(f"  - [GitHub MCP Error]: Failed to fetch issues: {e}")
            return []

    def get_repository_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> Dict[str, Any]:
        """
        MCP Tool: github_get_file_contents
        Retrieves raw code file content from a GitHub repository path.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                import base64
                content_b64 = data.get("content", "")
                decoded = base64.b64decode(content_b64).decode("utf-8", errors="ignore") if content_b64 else ""
                return {
                    "name": data.get("name"),
                    "path": data.get("path"),
                    "sha": data.get("sha"),
                    "size": data.get("size"),
                    "content": decoded
                }
            else:
                return {"error": f"HTTP {resp.status_code}", "message": resp.text[:200]}
        except Exception as e:
            return {"error": "Exception", "message": str(e)}

    def list_recent_commits(self, owner: str, repo: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        MCP Tool: github_list_commits
        Fetches recent commit history for project milestone tracking.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
        params = {"per_page": limit}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            if resp.status_code == 200:
                commits = resp.json()
                results = []
                for c in commits:
                    commit_data = c.get("commit", {})
                    results.append({
                        "sha": c.get("sha")[:7],
                        "author": commit_data.get("author", {}).get("name"),
                        "date": commit_data.get("author", {}).get("date"),
                        "message": commit_data.get("message", "").split("\n")[0]
                    })
                return results
            else:
                return []
        except Exception as e:
            return []

    def _get_local_repo_details(self) -> Tuple[str, str]:
        import subprocess
        try:
            url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"]).decode("utf-8").strip()
            # Strip trailing .git
            url_clean = url.replace(".git", "")
            # Handle standard SSH formats like git@github.com:owner/repo
            # or HTTPS formats like https://github.com/owner/repo
            url_clean = url_clean.replace("git@github.com:", "https://github.com/")
            parts = url_clean.split("/")
            if len(parts) >= 2:
                owner = parts[-2].split(":")[-1].split("@")[-1]
                repo = parts[-1]
                if owner and repo:
                    return owner, repo
        except Exception:
            pass
        return "Himayaomnex", "RAG_Project"  # safe static fallback

    def format_github_context_for_llm(self, owner: Optional[str] = None, repo: Optional[str] = None) -> str:
        """Formats GitHub MCP context for injection into PromptBuilder Module 7 context."""
        if not owner or not repo:
            from typing import Tuple
            owner, repo = self._get_local_repo_details()

        issues = self.list_repository_issues(owner, repo, limit=5)
        commits = self.list_recent_commits(owner, repo, limit=5)

        lines = [f"--- GITHUB MCP LIVE CONTEXT ({owner}/{repo}) ---"]
        lines.append("Recent Repository Commits:")
        if commits:
            for c in commits:
                lines.append(f"  • [{c['sha']}] {c['author']} ({c['date'][:10]}): {c['message']}")
        else:
            lines.append("  • No recent commits retrieved or token unconfigured.")

        lines.append("\nOpen GitHub Issues & Tasks:")
        if issues:
            for i in issues:
                lines.append(f"  • Issue #{i['number']} ({i['user']}): {i['title']} - {i['url']}")
        else:
            lines.append("  • No open issues retrieved.")

        lines.append("--- END GITHUB MCP CONTEXT ---\n")
        return "\n".join(lines)


# Singleton Instance
github_mcp = GitHubMCPClient()

if __name__ == "__main__":
    print("Testing GitHub MCP Client...")
    test_context = github_mcp.format_github_context_for_llm("octocat", "Hello-World")
    print(test_context)
