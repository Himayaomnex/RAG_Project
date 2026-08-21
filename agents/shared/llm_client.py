"""
================================================================================
Provider LLM Client (agents/shared/llm_client.py)
================================================================================
Owns provider calls, retries, fallback (Google Gemini 2.5 Flash -> Groq)
Contains NOTHING that edits, regex-replaces, or manipulates model output.
"""

import os
import time
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Tuple


class LLMClient:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash").strip()

    def generate(
        self,
        system_instruction: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        json_mode: bool = False
    ) -> Tuple[str, str, int, int]:
        """
        Executes generation with automatic failover.
        Returns: (response_text, model_name, prompt_tokens, completion_tokens)
        """
        # Primary Tier: Google Gemini
        if self.gemini_key:
            try:
                res, pt, ct = self._call_gemini(system_instruction, user_prompt, temperature, max_tokens, json_mode)
                return res, self.gemini_model, pt, ct
            except Exception as e:
                print(f"  - [LLM Warning] Gemini failed: {e}. Attempting Groq failover...")

        # Secondary Tier: Groq
        if self.groq_key:
            try:
                res, pt, ct = self._call_groq(system_instruction, user_prompt, temperature, max_tokens, json_mode)
                return res, "groq/llama-3.3-70b-versatile", pt, ct
            except Exception as e:
                print(f"  - [LLM Warning] Groq failed: {e}")

        raise RuntimeError("All configured LLM providers failed or API keys are missing.")

    def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> Tuple[str, int, int]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        payload: Dict[str, Any] = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [{
                "role": "user",
                "parts": [{"text": user_prompt}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            candidates = body.get("candidates", [])
            if not candidates:
                raise ValueError("Gemini returned empty candidates.")
            
            content_parts = candidates[0].get("content", {}).get("parts", [])
            text_out = "".join(p.get("text", "") for p in content_parts)
            
            usage = body.get("usageMetadata", {})
            pt = usage.get("promptTokenCount", len(user_prompt) // 4)
            ct = usage.get("candidatesTokenCount", len(text_out) // 4)
            return text_out, pt, ct

    def _call_groq(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> Tuple[str, int, int]:
        url = "https://api.groq.com/openai/v1/chat/completions"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        payload: Dict[str, Any] = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.groq_key}"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            choice = body.get("choices", [{}])[0]
            text_out = choice.get("message", {}).get("content", "")
            usage = body.get("usage", {})
            return text_out, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


# Global singleton client
llm_client = LLMClient()
