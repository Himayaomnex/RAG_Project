"""Agent state, status enumeration, and trace representations."""

from enum import Enum
from typing import TypedDict, List, Dict, Any, Optional
from harness.budget import Budget
from harness.evidence_store import EvidenceStore


class Status(str, Enum):
    SUCCESS = "SUCCESS"
    DEGRADED = "DEGRADED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    RETRIEVAL_UNAVAILABLE = "RETRIEVAL_UNAVAILABLE"
    KB_UNAVAILABLE = "KB_UNAVAILABLE"
    BUDGET_EXHAUSTED_TOKENS = "BUDGET_EXHAUSTED_TOKENS"
    BUDGET_EXHAUSTED_CALLS = "BUDGET_EXHAUSTED_CALLS"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    TIMEOUT = "TIMEOUT"


class Violation(TypedDict):
    field: str
    rule: str
    found: Any
    why: str


class AgentState(TypedDict, total=False):
    # request
    task: str
    capability: Optional[str]
    session_id: str
    trace_id: str

    # agency
    plan_history: List[Dict[str, Any]]
    observations: List[Dict[str, Any]]
    tool_calls_used: int
    tool_calls_remaining: int
    tool_calls_total: int

    # context
    evidence: EvidenceStore
    budget: Budget
    assembled_evidence: List[Any]
    dropped_evidence: List[Dict[str, Any]]

    # output
    draft: Optional[Dict[str, Any]]
    violations: List[Dict[str, Any]]
    repair_attempts: int
    max_repair_attempts: int

    # termination
    status: str
    error_message: Optional[str]
    response: Optional[Dict[str, Any]]
