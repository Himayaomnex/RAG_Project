"""Compute and execution tools: sandboxed run_python, write_artifact, and gated run_shell."""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from harness.evidence_store import EvidenceItem
from harness.tool_registry import register_tool, ToolError
from harness.budget import count_tokens
from daily_excel_generator import generate_daily_rollup_excel

_ALLOWLIST_MODULES = {"json", "csv", "re", "math", "statistics", "datetime", "collections", "itertools", "pathlib", "openpyxl", "pandas"}
_SCRATCH_DIR = Path(__file__).parent.parent.parent / "scratch" / "compute"
_SCRATCH_DIR.mkdir(parents=True, exist_ok=True)


@register_tool(
    "generate_daily_excel",
    "Generate the multi-tab executive Excel (.xlsx) report from KB facts (assignments, concepts, decisions, QA, feedback)."
)
def generate_daily_excel(output_dir: Optional[str] = None) -> List[EvidenceItem]:
    """Generates the multi-tab Excel workbook using openpyxl and returns evidence of the generated file."""
    try:
        target_dir = output_dir or str(Path(__file__).parent.parent.parent / "deliverables")
        file_path = generate_daily_rollup_excel(output_dir=target_dir)
        size_bytes = os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
        return [EvidenceItem(
            id=f"excel-report-{os.path.basename(file_path)}",
            source="tool",
            origin={"type": "excel_generator", "file_path": file_path, "size_bytes": size_bytes},
            content=f"Successfully generated multi-tab Excel report at: {file_path} ({size_bytes} bytes).",
            relevance=1.0
        )]
    except Exception as e:
        raise ToolError(f"generate_daily_excel failed: {e}") from e


@register_tool(
    "run_python",
    "Run Python to compute over evidence, aggregate data, or generate spreadsheet files. Not for fetching data."
)
def run_python(code: str, inputs: Optional[Dict[str, Any]] = None) -> List[EvidenceItem]:
    """Execute Python in a sandboxed subprocess with timeout."""
    with tempfile.TemporaryDirectory(dir=str(_SCRATCH_DIR)) as run_dir:
        script_path = Path(run_dir) / "compute_script.py"
        inputs_path = Path(run_dir) / "inputs.json"

        # Write inputs
        with open(inputs_path, "w", encoding="utf-8") as f:
            json.dump(inputs or {}, f)

        # Wrap user code to inject data dict and capture result
        wrapped_code = f"""
import sys, json, os
from pathlib import Path

with open({repr(str(inputs_path))}, 'r', encoding='utf-8') as f:
    data = json.load(f)

result = None
output_files = []

# --- User Code ---
{code}
# --- End User Code ---

# Find any created files
for root, dirs, files in os.walk({repr(run_dir)}):
    for f in files:
        if f not in ("compute_script.py", "inputs.json"):
            output_files.append(os.path.join(root, f))

out_dict = {{
    "result": result,
    "output_files": output_files
}}
with open(os.path.join({repr(run_dir)}, "output.json"), "w", encoding="utf-8") as f:
    try:
        json.dump(out_dict, f, default=str)
    except Exception:
        json.dump({{"result": str(result), "output_files": output_files}}, f)
"""
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(wrapped_code)

        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=run_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            out_json_path = Path(run_dir) / "output.json"
            result_val = None
            out_files = []
            if out_json_path.exists():
                try:
                    with open(out_json_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        result_val = meta.get("result")
                        out_files = meta.get("output_files", [])
                except Exception:
                    pass

            if proc.returncode != 0:
                raise ToolError(f"run_python execution failed with exit code {proc.returncode}:\n{stderr}\n{stdout}")

            content_parts = []
            if stdout:
                content_parts.append(f"stdout: {stdout[:3000]}")
            if result_val is not None:
                content_parts.append(f"result: {result_val}")
            if out_files:
                content_parts.append(f"files: {', '.join(out_files)}")

            content = "\n".join(content_parts) or "Execution completed successfully with no output."
            return [EvidenceItem(
                id=f"compute-{hash(code) & 0xFFFFFF:06x}",
                source="tool",
                origin={"type": "run_python", "files": out_files},
                content=content,
                relevance=1.0
            )]
        except subprocess.TimeoutExpired as te:
            raise ToolError("run_python timed out after 30 seconds.") from te
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(f"run_python failed: {e}") from e


@register_tool("write_artifact", "Save a produced file or spreadsheet artifact so a human can collect it.")
def write_artifact(path: str, content: str) -> List[EvidenceItem]:
    """Save an artifact to disk deterministically."""
    out_path = Path(path)
    if not out_path.is_absolute():
        out_path = Path(__file__).parent.parent.parent / "scratch" / "artifacts" / path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if isinstance(content, bytes):
            out_path.write_bytes(content)
        else:
            out_path.write_text(str(content), encoding="utf-8")

        size_bytes = out_path.stat().st_size
        return [EvidenceItem(
            id=f"artifact-{out_path.name}",
            source="tool",
            origin={"type": "artifact", "path": str(out_path), "bytes": size_bytes},
            content=f"Saved artifact to {out_path} ({size_bytes} bytes).",
            relevance=1.0
        )]
    except Exception as e:
        raise ToolError(f"write_artifact failed: {e}") from e


@register_tool("run_shell", "Run a gated shell command (when ALLOW_SHELL=true is set in environment).")
def run_shell(command: str) -> List[EvidenceItem]:
    """Gated shell tool for system inspection."""
    allow_shell = os.getenv("ALLOW_SHELL", "false").lower() == "true"
    if not allow_shell:
        raise ToolError("run_shell is disabled by default. Enable with ALLOW_SHELL=true in environment.")

    # Token check
    tokens = command.strip().split()
    if not tokens:
        raise ToolError("Empty command provided to run_shell.")

    allowed_first_tokens = {"git", "ls", "cat", "head", "tail", "wc", "grep", "find", "python", "pytest"}
    if tokens[0] not in allowed_first_tokens:
        raise ToolError(f"Command '{tokens[0]}' is not in the shell allowlist: {allowed_first_tokens}")

    blocked_substrings = ["rm ", "mv ", "curl", "wget", "ssh", "pip install", ">", ".env", "credentials"]
    if any(b in command for b in blocked_substrings):
        raise ToolError(f"Command contains prohibited operation or sensitive target.")

    repo_dir = Path(__file__).parent.parent.parent
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        return [EvidenceItem(
            id=f"shell-{hash(command) & 0xFFFFFF:06x}",
            source="tool",
            origin={"command": command, "exit_code": proc.returncode},
            content=f"exit_code: {proc.returncode}\nstdout: {proc.stdout[:2000]}\nstderr: {proc.stderr[:1000]}",
            relevance=1.0
        )]
    except Exception as e:
        raise ToolError(f"run_shell failed: {e}") from e
