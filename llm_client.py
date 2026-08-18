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
        "| Trainee | Assigned Task / Learning Topic | Meeting Date | Verbatim Citation Proof |\n"
        "| :--- | :--- | :--- | :--- |"
    ),
    "mentor_feedback": (
        "| Trainee | Mentorship Guidance / Feedback Topic | Meeting Date | Verbatim Citation Proof |\n"
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
        if any(w in q for w in ["feedback","guidance","mentorship","coach","advice","targeted"]):
            return "mentor_feedback"
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


def ensure_single_table_header(content: str, table_header: str) -> str:
    """
    Ensures that a Markdown table has exactly ONE header block.
    If the content already starts with a valid header + separator row, it is returned as-is
    to prevent duplicate stacked table headers.
    """
    if not table_header:
        return content
    content_clean = content.strip()
    lines = [line.strip() for line in content_clean.splitlines() if line.strip()]
    if not lines:
        return table_header
    
    # If the content already starts with a table header (row 1 is '| ... |' and row 2 is '| :--- ... |')
    if len(lines) >= 2 and lines[0].startswith("|") and re.match(r"^\|[\s|:\-]+\|$", lines[1]):
        return content_clean
    
    # If it starts with data rows directly without a header
    return table_header.strip() + "\n" + content_clean


def sanitize_markdown_table_pipes(text: str) -> str:
    """
    Replaces unescaped pipe characters '|' inside brackets [...] or citations within table lines
    so they don't break markdown table column alignment.
    """
    lines = text.splitlines()
    out_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            # Replace '|' inside [...] with ' — '
            def replace_bracket_pipes(match):
                inside = match.group(1)
                inside_cleaned = inside.replace("|", " — ").replace("\t", " ")
                return f"[{inside_cleaned}]"
            line = re.sub(r"\[(.*?)\]", replace_bracket_pipes, line)
            
            # Also replace '|' inside `...` with ' — '
            def replace_backtick_pipes(match):
                inside = match.group(1)
                inside_cleaned = inside.replace("|", " — ").replace("\t", " ")
                return f"`{inside_cleaned}`"
            line = re.sub(r"`(.*?)`", replace_backtick_pipes, line)
            
            # Replace any stray tabs with space
            line = line.replace("\t", " ")
        out_lines.append(line)
    return "\n".join(out_lines)


def clean_reasoning_and_thinking(content: str, is_table_query: bool = False) -> str:
    content_stripped = content.strip()
    # Strip <think>...</think> blocks (Qwen, DeepSeek)
    content_stripped = re.sub(r"<think>.*?</think>", "", content_stripped, flags=re.DOTALL).strip()
    # Strip **Reasoning...** preamble blocks emitted by groq/compound model
    content_stripped = re.sub(
        r"\*\*[Rr]easoning[^*]*\*\*.*?(\n\n\*\*[A-Z]|\Z)",
        lambda m: m.group(1).lstrip("\n") if m.group(1) else "",
        content_stripped, flags=re.DOTALL
    ).strip()
    # Strip any remaining "Exact phrase" / "Final Answer" heading wrappers
    content_stripped = re.sub(r"^\*\*[^*]{1,50}\*\*\s*\n+", "", content_stripped).strip()

    # Sanitize any raw pipes inside citations to prevent table column shifting
    content_stripped = sanitize_markdown_table_pipes(content_stripped)

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
    table_key = _detect_table_key(user_query, agent_type)
    is_table_query = bool(table_key)
    table_header = TABLE_HEADERS.get(table_key, "")

    truncated_prompt = system_prompt
    if len(system_prompt) > 15000:
        truncated_prompt = (
            system_prompt[:12000]
            + "\n... [Evidence truncated to fit context limits] ...\n</transcript_evidence>\n"
            + system_prompt[-2500:]
        )

    # ── Build messages once (valid for both Groq and OpenRouter APIs) ──
    if is_table_query and table_header:
        user_content = (
            f"SYSTEM INSTRUCTIONS & TRANSCRIPT GROUNDING POLICY:\n{truncated_prompt}\n\n"
            f"USER QUERY:\n{user_query}\n\n"
            "== STRICT OUTPUT RULE ==\n"
            "Format your ENTIRE answer as a standard Markdown Pipe Table using this header:\n"
            f"{table_header}\n"
            "Populate rows based on transcript evidence for Himaya Perumal, Ganesh Krishna, and Dakshinya Nachimuthu.\n"
            "Do NOT output thinking steps, reasoning preambles, or conversational commentary. Output the Markdown table."
        )
        messages = [
            {"role": "user", "content": user_content}
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

    # ── #1 PRIMARY: Google Gemini API (Mentor Preferred Provider) ──
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        configured_model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash").strip()
        gemini_models = [configured_model, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-pro"]
        # Deduplicate while preserving order
        seen_g = set()
        gemini_models = [m for m in gemini_models if m and not (m in seen_g or seen_g.add(m))]
        
        temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
        top_p = float(os.getenv("GEMINI_TOP_P", "0.9"))
        max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))
        timeout = int(os.getenv("GEMINI_TIMEOUT", "300"))
        max_retries = int(os.getenv("GEMINI_MAX_RETRIES", "3"))

        print(f"  - [LLM Client]: Agent={agent_type or 'auto'} | Table={table_key or 'none'} | Primary=Google Gemini ({gemini_models[0]})")
        
        for g_model in gemini_models:
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={gemini_key}"
            gemini_payload = {
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{
                            "text": (
                                user_query + ("\n\n== STRICT RULE ==\nFormat output strictly as a Markdown Pipe Table:\n" + table_header if is_table_query else "")
                            )
                        }]
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "topP": top_p,
                    "maxOutputTokens": max_tokens
                }
            }
            
            for attempt in range(max_retries):
                try:
                    import time as _time
                    t0 = _time.time()
                    resp = requests.post(gemini_url, json=gemini_payload, timeout=min(timeout, 30))
                    t1 = _time.time()
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
                            g_text = candidates[0]["content"]["parts"][0].get("text", "").strip()
                            g_text = clean_reasoning_and_thinking(g_text, is_table_query=is_table_query)
                            if is_table_query and table_header:
                                g_text = ensure_single_table_header(g_text, table_header)
                            if is_table_query and not _has_valid_table_rows(g_text):
                                print(f"  - [Gemini Guard]: {g_model} produced no table rows. Trying next...")
                                break
                            print(f"  - [Gemini {g_model}]: Success! [{round(t1-t0, 2)}s]")
                            return g_text
                    elif resp.status_code == 429:
                        print(f"  - [Gemini {g_model}]: Rate-limited (429). Attempt {attempt+1}/{max_retries}...")
                        _time.sleep(1.5)
                        continue
                    else:
                        print(f"  - [Gemini {g_model}]: HTTP {resp.status_code}. Trying next model...")
                        break
                except Exception as e_gem:
                    print(f"  - [Gemini Warning]: {e_gem}. Trying next...")
                    break

    # ── #2 SECONDARY: Groq API (High quota, fast, 128k context) ──
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        groq_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
        print(f"  - [LLM Client]: Agent={agent_type or 'auto'} | Table={table_key or 'none'} | Prompt={len(truncated_prompt)} chars | Provider=Groq ({groq_models[0]})")
        groq_headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        for g_model in groq_models:
            groq_payload = {
                "model": g_model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 4000,
            }
            try:
                import time as _time
                t0 = _time.time()
                g_resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=groq_headers, json=groq_payload, timeout=30
                )
                t1 = _time.time()
                if g_resp.status_code == 200:
                    g_content = g_resp.json()["choices"][0]["message"]["content"].strip()
                    g_content = clean_reasoning_and_thinking(g_content, is_table_query=is_table_query)
                    if is_table_query and table_header:
                        g_content = ensure_single_table_header(g_content, table_header)
                    if is_table_query and not _has_valid_table_rows(g_content):
                        print(f"  - [Groq Guard]: {g_model} produced no table rows. Trying next...")
                        continue
                    print(f"  - [Groq {g_model}]: Success! [{round(t1-t0, 2)}s]")
                    return g_content
                elif g_resp.status_code == 429:
                    print(f"  - [Groq {g_model}]: Rate-limited. Trying next...")
                    continue
                else:
                    print(f"  - [Groq {g_model}]: HTTP {g_resp.status_code}. Trying next...")
                    continue
            except Exception as g_err:
                print(f"  - [Groq Warning]: {g_err}. Trying next...")
                continue

    # ── #3 TERTIARY: OpenRouter free models ──
    api_key = os.getenv("OPENROUTER_API_KEY") or OPENROUTER_API_KEY
    if not api_key:
        if fallback_response:
            return fallback_response
        return "[LLM ERROR]: No API keys configured in .env."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "RAG Combined Multi-Agent",
        "Connection": "close"
    }

    models_to_try = [
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3.5-lightning:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "openai/gpt-oss-20b:free",
    ]

    print(f"  - [LLM Client OpenRouter]: Agent={agent_type or 'auto'} | Table={table_key or 'none'} | Trying {len(models_to_try)} free models...")

    for model_name in models_to_try:
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
                content = clean_reasoning_and_thinking(content, is_table_query=is_table_query)
                if is_table_query and table_header:
                    content = ensure_single_table_header(content, table_header)

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
                for attempt in range(1, 3):
                    print(f"  - [OpenRouter 429]: {model_name} rate-limited. Retry #{attempt} in 1.5s...")
                    time.sleep(1.5)
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

    print("  - [LLM Client]: All OpenRouter free models exhausted.")

    if fallback_response and len(fallback_response.strip()) > 20:
        print("  - [LLM Client]: All live LLM APIs rate-limited. Returning structured ground-truth transcript report.")
        return fallback_response

    error_msg = "[LLM ERROR]: OpenRouter daily free quota exhausted. Please update OPENROUTER_API_KEY or add GROQ_API_KEY in .env."
    print(f"  - {error_msg}")
    return error_msg
