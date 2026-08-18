"""
================================================================================
OpenRouter LLM Client (RAG_COMBINED)
================================================================================
Securely connects PromptBuilder system prompts with OpenRouter Free API
without hardcoding API keys in codebase. Key is loaded securely from .env.

Agent-aware table injection:
  - manager + accomplishments  -> Trainee | Task | Status | Citation
  - manager + blockers         -> Trainee | Situation | Complication | Question | Answer
  - manager + decisions        -> Owner | Decision | Rationale | Citation
  - manager + milestones       -> Owner | Task | Date | Status | Citation
  - mentor  + scores           -> Trainee | Prep | Depth | Code | Engagement | Overall | Verdict
  - mentor  + strengths        -> Trainee | Strength/Misconception | Evidence | Citation
  - mentor  + tasks            -> Trainee | Task | Date | Verification
  - teammates / general        -> no table injection, standard markdown output
"""

import os
import re
import time
import requests
import threading
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


TABLE_HEADERS = {
    "manager_accomplishments": (
        "| Trainee | Task / Deliverable | Status (Completed / In Progress) | Verbatim Citation Proof |\n"
        "| :--- | :--- | :--- | :--- |"
    ),
    "manager_blockers": (
        "| Trainee | Situation | Complication (Blocker) | Question (Impact) | Answer (Mitigation) |\n"
        "| :--- | :--- | :--- | :--- | :--- |"
    ),
    "manager_decisions": (
        "| Owner | Recommended Decision | Rationale | Verbatim Citation Proof |\n"
        "| :--- | :--- | :--- | :--- |"
    ),
    "manager_milestones": (
        "| Owner | Task / Milestone | Meeting Date | Status | Verbatim Citation Proof |\n"
        "| :--- | :--- | :--- | :--- | :--- |"
    ),
    "mentor_scores": (
        "| Trainee | Preparation (1-10) | Conceptual Depth (1-10) | Code Quality (1-10) | Engagement (1-10) | Overall (1-10) | One-Line Verdict |\n"
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- |"
    ),
    "mentor_strengths": (
        "| Trainee | Strength / Misconception | Evidence Type | Verbatim Citation Proof |\n"
        "| :--- | :--- | :--- | :--- |"
    ),
    "mentor_tasks": (
        "| Trainee | Assigned Task / Learning Topic | Meeting Date | Binary Verification |\n"
        "| :--- | :--- | :--- | :--- |"
    ),
}


def _detect_table_key(user_query: str, agent_type: str = "") -> str:
    q = user_query.lower()
    a = agent_type.lower()
    if "manager" in a:
        if any(w in q for w in ["block","risk","delay","stuck","issue","problem","barrier","challenge","concern"]):
            return "manager_blockers"
        if any(w in q for w in ["milestone","timeline","schedule","deadline"]):
            return "manager_milestones"
        if any(w in q for w in ["decision","executive","resource","allocat","recommend"]):
            return "manager_decisions"
        if any(w in q for w in ["accomplish","task","status","progress","done","complete","deliverable","himaya","ganesh","dakshinya","finish","built","implemented","created","what did","update"]):
            return "manager_accomplishments"
    elif "mentor" in a or "siddharth" in a:
        if any(w in q for w in ["strength","gap","misconception","weak","good at","diagnos","technical performance"]):
            return "mentor_strengths"
        if any(w in q for w in ["task","assign","next","topic","learn","homework","deliverable","action item","next step"]):
            return "mentor_tasks"
        if any(w in q for w in ["score","evaluat","grade","rating","verdict","preparation","conceptual","engagement","scorecard"]):
            return "mentor_scores"
    return ""


def _has_valid_table_rows(content: str) -> bool:
    HEADER_WORDS = {
        "trainee","task","deliverable","status","citation","proof","situation",
        "complication","blocker","question","impact","answer","mitigation","owner",
        "rationale","meeting","date","preparation","conceptual","depth","code",
        "quality","engagement","overall","verdict","strength","misconception",
        "evidence","binary","verification","topic","milestone","recommended",
        "decision","assigned","learning"
    }
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r"^\|[\s|:\-]+\|$", stripped):
            continue
        cells = [c.strip() for c in stripped.split("|") if c.strip()]
        if len(cells) < 2:
            continue
        data_cells = [c for c in cells if c.lower().strip("/: ") not in HEADER_WORDS and len(c) > 4]
        if data_cells:
            return True
    return False


def clean_reasoning_and_thinking(content: str, is_table_query: bool = False) -> str:
    content_stripped = content.strip()
    content_stripped = re.sub(r"<think>.*?</think>", "", content_stripped, flags=re.DOTALL).strip()
    if is_table_query:
        first_pipe = content_stripped.find("|")
        if first_pipe != -1:
            return content_stripped[first_pipe:].strip()
    else:
        lower_content = content_stripped.lower()
        if any(phrase in lower_content for phrase in [
            "thinking process","thought process","analyze user input",
            "here's my analysis","let me think","step 1:","step 2:","here's a thinking"
        ]):
            markers = ["###","##","**","🌟","✅","🎯","🔬","💬","👔","🎓","👥","⚠️","📅"]
            best_index = -1
            for marker in markers:
                idx = content_stripped.find(marker)
                if idx != -1 and (best_index == -1 or idx < best_index):
                    best_index = idx
            if best_index != -1:
                content_stripped = content_stripped[best_index:].strip()
    return content_stripped


def _post_with_hard_timeout(headers, payload, timeout=8):
    result = []
    def worker():
        try:
            r = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=timeout)
            result.append(r)
        except Exception as e:
            result.append(e)

    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        raise TimeoutError(f"HTTP request stalled and failed to complete within {timeout}s.")

    if not result:
        raise RuntimeError("HTTP thread completed with no output or exception.")

    res = result[0]
    if isinstance(res, Exception):
        raise res
    return res



def generate_llm_response(
    system_prompt: str,
    user_query: str,
    fallback_response: str = "",
    agent_type: str = ""
) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY") or OPENROUTER_API_KEY
    if not api_key:
        print("  - [LLM Client]: No OPENROUTER_API_KEY found. Using local fallback.")
        return fallback_response

    truncated_prompt = system_prompt
    if len(system_prompt) > 50000:
        truncated_prompt = (
            system_prompt[:40000]
            + "\n... [Evidence truncated to fit context limits] ...\n</transcript_evidence>\n"
            + system_prompt[-8000:]
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "RAG Combined Multi-Agent",
        "Connection": "close"
    }

    # ── Model list: active free models on OpenRouter (Gemma-4 preferred for table format compliance) ──
    models_to_try = [
        "openai/gpt-oss-20b:free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3.5-lightning:free",
    ]

    table_key = _detect_table_key(user_query, agent_type)
    is_table_query = bool(table_key)
    table_header = TABLE_HEADERS.get(table_key, "")

    print(
        f"  - [LLM Client]: Agent={agent_type or 'auto'} | "
        f"Table={table_key or 'none'} | "
        f"Prompt={len(truncated_prompt)} chars | "
        f"Primary model={models_to_try[0]}"
    )

    for model_name in models_to_try:
        if is_table_query and table_header:
            header_line = table_header.splitlines()[0]
            num_cols = header_line.count("|") - 1
            row_cells = " | ".join(["Value"] * num_cols)
            row_format_str = f"| {row_cells} |"

            user_content = (
                f"SYSTEM INSTRUCTIONS & TRANSCRIPT GROUNDING POLICY:\n{truncated_prompt}\n\n"
                f"USER QUERY:\n{user_query}\n\n"
                "== STRICT OUTPUT RULE ==\n"
                "The assistant turn starts with the Markdown table header already written.\n"
                "Output ONLY the data rows. One row per trainee or item.\n"
                f"Row format: {row_format_str}\n"
                "NO intro. NO reasoning. NO explanation. NO preamble. Data rows ONLY."
            )
            messages = [
                {"role": "user",      "content": user_content},
                {"role": "assistant", "content": table_header},
            ]
        else:
            messages = [
                {
                    "role": "user",
                    "content": (
                        f"SYSTEM INSTRUCTIONS & TRANSCRIPT GROUNDING POLICY:\n{truncated_prompt}\n\n"
                        f"USER QUERY:\n{user_query}"
                    )
                }
            ]

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4000,
            "include_reasoning": False,
        }

        try:
            t_start = time.time()
            resp = _post_with_hard_timeout(headers, payload, timeout=8)
            t_end = time.time()
            total_duration = t_end - t_start

            if resp.status_code == 200:
                resp_json = resp.json()
                content = resp_json["choices"][0]["message"]["content"].strip()

                if is_table_query and table_header:
                    content = content.lstrip()
                    header_first_line = table_header.splitlines()[0].strip()
                    if not content.startswith(header_first_line):
                        content = table_header + "\n" + content

                content = clean_reasoning_and_thinking(content, is_table_query=is_table_query)

                if is_table_query and not _has_valid_table_rows(content):
                    print(
                        f"  - [LLM Guard]: {model_name} produced no valid table rows. "
                        f"Returning local structured fallback."
                    )
                    return fallback_response if fallback_response else content

                usage = resp_json.get("usage", {})
                completion_tokens = usage.get("completion_tokens", len(content.split()))
                ttft = round(total_duration * 0.25, 3)
                gen_time = max(0.001, total_duration - ttft)
                tps = round(completion_tokens / gen_time, 1) if gen_time > 0 else 0.0

                print(f"  - [OpenRouter {model_name}]: [TPS: {tps} tok/s | Total: {round(total_duration, 3)}s]")
                return content

            elif resp.status_code == 429:
                succeeded = False
                for attempt in range(1, 4):
                    print(f"  - [OpenRouter 429]: {model_name} rate-limited. Retry #{attempt} in 4.0s...")
                    time.sleep(4.0)
                    try:
                        resp_retry = _post_with_hard_timeout(headers, payload, timeout=8)
                        if resp_retry.status_code == 200:
                            resp_json = resp_retry.json()
                            content = resp_json["choices"][0]["message"]["content"].strip()
                            if is_table_query and table_header:
                                content = content.lstrip()
                                header_first_line = table_header.splitlines()[0].strip()
                                if not content.startswith(header_first_line):
                                    content = table_header + "\n" + content
                            content = clean_reasoning_and_thinking(content, is_table_query=is_table_query)
                            if is_table_query and not _has_valid_table_rows(content):
                                return fallback_response if fallback_response else content
                            print(f"  - [OpenRouter {model_name}]: Retry #{attempt} succeeded!")
                            succeeded = True
                            return content
                        elif resp_retry.status_code != 429:
                            print(f"  - [OpenRouter]: {model_name} -> HTTP {resp_retry.status_code} on retry. Trying next model...")
                            break
                    except Exception as retry_err:
                        print(f"  - [OpenRouter Retry Warning]: {retry_err}")
                if not succeeded:
                    print(f"  - [OpenRouter]: {model_name} exhausted all retries. Trying next model...")
                    continue
            else:
                print(f"  - [OpenRouter]: {model_name} -> HTTP {resp.status_code}. Trying next model...")
                continue

        except Exception as e:
            print(f"  - [OpenRouter Error]: {model_name} failed: {e}. Trying next model...")
            continue

    print("  - [OpenRouter LLM Notice]: All models exhausted. Using local fallback response.")
    return fallback_response
