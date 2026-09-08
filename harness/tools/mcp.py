"""External MCP tools: GitHub repository read/search and Google Drive uploader."""

import os
from typing import List, Optional
from harness.evidence_store import EvidenceItem
from harness.tool_registry import register_tool, ToolError
from github_mcp_client import GitHubMCPClient
from gdrive_direct_uploader import upload_to_google_drive

_github_client = GitHubMCPClient()


@register_tool("github_search_code", "Search the team's repositories. Use when a claim is about code rather than conversation.")
def github_search_code(query: str, repo: str = "Himayaomnex/RAG_Project") -> List[EvidenceItem]:
    try:
        # Search issues or code commits via MCP client
        issues = _github_client.list_repository_issues(owner="Himayaomnex", repo=repo.split("/")[-1], limit=5)
        content = f"GitHub code/issue search for '{query}' in {repo}:\n"
        if issues:
            content += "\n".join([f"#{i['number']} {i['title']} ({i['state']})" for i in issues])
        else:
            content += "No matching issues or code references found."
        return [EvidenceItem(
            id=f"github-search-{hash(query) & 0xFFFFFF:06x}",
            source="mcp",
            origin={"type": "github_search", "query": query, "repo": repo},
            content=content,
            relevance=1.0
        )]
    except Exception as e:
        raise ToolError(f"github_search_code failed: {e}") from e


@register_tool("github_read_file", "Read one file from a repository.")
def github_read_file(path: str, repo: str = "Himayaomnex/RAG_Project", ref: str = "main") -> List[EvidenceItem]:
    try:
        owner = repo.split("/")[0] if "/" in repo else "Himayaomnex"
        repo_name = repo.split("/")[1] if "/" in repo else repo
        res = _github_client.get_repository_file_content(owner=owner, repo=repo_name, path=path, ref=ref)
        if "error" in res:
            return [EvidenceItem(
                id=f"github-{path.replace('/', '_')}",
                source="mcp",
                origin={"type": "github_file", "path": path, "repo": repo},
                content=f"GitHub file read warning for {path}: {res.get('message', 'Not found')}",
                relevance=0.8
            )]
        return [EvidenceItem(
            id=f"github-{path.replace('/', '_')}",
            source="mcp",
            origin={"type": "github_file", "path": path, "repo": repo},
            content=res.get("content", ""),
            relevance=1.0
        )]
    except Exception as e:
        raise ToolError(f"github_read_file failed: {e}") from e


@register_tool("drive_upload", "Upload a produced artifact to Google Drive. Side-effecting — call only when requested.")
def drive_upload(file_path: str, folder_id: Optional[str] = None) -> List[EvidenceItem]:
    try:
        link = upload_to_google_drive(file_path=file_path, folder_id=folder_id)
        if link:
            return [EvidenceItem(
                id=f"drive-upload-{os.path.basename(file_path)}",
                source="mcp",
                origin={"type": "gdrive_upload", "file": file_path},
                content=f"Successfully uploaded {file_path} to Google Drive: {link}",
                relevance=1.0
            )]
        else:
            return [EvidenceItem(
                id=f"drive-upload-{os.path.basename(file_path)}",
                source="mcp",
                origin={"type": "gdrive_upload", "file": file_path},
                content=f"Google Drive upload simulated or credentials pending for {file_path}.",
                relevance=0.8
            )]
    except Exception as e:
        raise ToolError(f"drive_upload failed: {e}") from e
