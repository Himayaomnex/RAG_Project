"""
================================================================================
Observability & Execution Traces (agents/shared/logging.py)
================================================================================
Writes structured execution traces to logs/traces/{trace_id}.json
Answers boundary failures (Agent, Skill, Retrieval API, or LLM) without re-running.
"""

import os
import json
import time
from typing import Optional, Dict, Any, List
from .schemas import ExecutionTrace

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs", "traces")
os.makedirs(LOGS_DIR, exist_ok=True)


class TraceLogger:
    def __init__(self, agent: str, skill: str, input_query: str, input_params: Optional[Dict[str, Any]] = None):
        self.trace = ExecutionTrace(
            agent=agent,
            skill=skill,
            input_query=input_query,
            input_params=input_params or {}
        )
        self.start_time = time.time()

    def record_retrieval(self, chunk_ids: List[str]):
        self.trace.retrieval_requests += 1
        self.trace.retrieved_chunk_ids.extend(chunk_ids)

    def record_llm_call(self, model: str = "gemini-2.5-flash", prompt_tokens: int = 0, completion_tokens: int = 0):
        self.trace.llm_calls += 1
        self.trace.llm_model = model
        self.trace.token_usage["prompt_tokens"] = self.trace.token_usage.get("prompt_tokens", 0) + prompt_tokens
        self.trace.token_usage["completion_tokens"] = self.trace.token_usage.get("completion_tokens", 0) + completion_tokens
        self.trace.token_usage["total_tokens"] = self.trace.token_usage.get("total_tokens", 0) + prompt_tokens + completion_tokens

    def set_failure(self, failure_msg: str, status: str = "ERROR"):
        self.trace.failure = failure_msg
        self.trace.final_status = status

    def complete(self, output: str, status: str = "SUCCESS") -> ExecutionTrace:
        self.trace.latency_seconds = round(time.time() - self.start_time, 3)
        self.trace.output = output
        self.trace.final_status = status
        self.save()
        return self.trace

    def save(self):
        try:
            file_path = os.path.join(LOGS_DIR, f"{self.trace.trace_id}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.trace.model_dump(), f, indent=2)
            print(f"  - [Trace Logged]: {self.trace.trace_id} ({self.trace.agent}/{self.trace.skill} -> {self.trace.final_status})")
        except Exception as e:
            print(f"  - [Trace Log Error]: {e}")


def get_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    file_path = os.path.join(LOGS_DIR, f"{trace_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
