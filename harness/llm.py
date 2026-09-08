"""LLM invoker with retry, backoff, and JSON parsing."""

import json
import re
import time
from typing import Tuple, Dict, Any, Optional
from agents.shared.llm_client import LLMClient

_llm_client = LLMClient()


def clean_json_response(raw_text: str) -> str:
    """Strip markdown fences (```json ... ```) or preamble."""
    text = raw_text.strip()
    if text.startswith("```"):
        # Strip opening fence
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def generate_with_retry(
    system_instruction: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    json_mode: bool = False,
    trace_id: Optional[str] = None,
    max_retries: int = 3,
    initial_backoff: float = 1.5,
) -> Tuple[str, str, int, int]:
    """Calls LLM with exponential backoff on transient errors (429, 503, connection timeouts).
    
    Returns:
        (response_text, model_name, prompt_tokens, completion_tokens)
    """
    last_error = None
    delay = initial_backoff

    for attempt in range(1, max_retries + 1):
        try:
            return _llm_client.generate(
                system_instruction=system_instruction,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                trace_id=trace_id,
            )
        except Exception as e:
            err_str = str(e).lower()
            last_error = e
            is_transient = any(code in err_str for code in ["429", "503", "500", "timeout", "rate limit", "overloaded"])
            if is_transient and attempt < max_retries:
                print(f"  [Harness LLM Retry] Attempt {attempt} failed ({e}). Backing off for {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2.0
            else:
                # If non-transient or retries exhausted, raise
                if attempt == max_retries:
                    break

    raise RuntimeError(f"Harness LLM generation failed after {max_retries} attempts: {last_error}") from last_error


def generate_json_object(
    system_instruction: str,
    user_prompt: str,
    temperature: float = 0.2,
    trace_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], str, int, int]:
    """Generate and parse a valid JSON dictionary from the model."""
    raw_text, model_name, pt, ct = generate_with_retry(
        system_instruction=system_instruction,
        user_prompt=user_prompt,
        temperature=temperature,
        json_mode=True,
        trace_id=trace_id,
    )

    cleaned = clean_json_response(raw_text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data, model_name, pt, ct
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")
    except Exception as e:
        # Try regex search for first outermost JSON block {...}
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict):
                    return data, model_name, pt, ct
            except Exception:
                pass
        raise ValueError(f"Failed to parse valid JSON from model output: {e}\nRaw output:\n{raw_text}") from e
