"""
================================================================================
Structured Schemas for Multi-Agent RAG Layer (agents/shared/schemas.py)
================================================================================
Production Pydantic contracts for:
- Retrieval chunks
- Manager Skill (manager_weekly_rollup)
- Mentor Skill (mentor_trainee_assessment)
- Team Intelligence Skill (team_session_catchup)
- Observability Execution Traces
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time
import uuid


class EvidenceChunk(BaseModel):
    chunk_id: str
    text: str
    speaker: str
    date: str
    page: str
    source_file: str
    score: float = 1.0


class ExecutionTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: f"trc-{uuid.uuid4().hex[:10]}")
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    agent: str
    skill: str
    input_query: str
    input_params: Dict[str, Any] = Field(default_factory=dict)
    retrieval_requests: int = 0
    retrieved_chunk_ids: List[str] = Field(default_factory=list)
    llm_calls: int = 0
    llm_model: str = "gemini-2.5-flash"
    latency_seconds: float = 0.0
    token_usage: Dict[str, int] = Field(default_factory=dict)
    failure: Optional[str] = None
    final_status: str = "SUCCESS"  # SUCCESS, INSUFFICIENT_EVIDENCE, ERROR
    output: Optional[str] = None


# ── Manager Skill Contracts ───────────────────────────────────────────────────

class ManagerRollupRequest(BaseModel):
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    trainee: Optional[str] = None
    query: str = "Give me the training status for this week."
    trace_id: Optional[str] = None


class CompletedItem(BaseModel):
    trainee: str
    item: str
    technical_significance: str
    supporting_quote: Optional[str] = None
    chunk_id: str


class InProgressItem(BaseModel):
    trainee: str
    item: str
    current_state: str
    chunk_id: str


class BlockedItem(BaseModel):
    trainee: str
    impediment: str
    resolution_state: str  # Agreed, Contested, Resolved, Pending Decision
    chunk_id: str


class ImportantChangeItem(BaseModel):
    topic: str
    change_description: str
    chunk_id: str


class RequiresAttentionItem(BaseModel):
    item: str
    recommended_intervention: str
    chunk_id: str


class ManagerWeeklyRollupOutput(BaseModel):
    executive_conclusion: str
    completed: List[CompletedItem] = Field(default_factory=list)
    in_progress: List[InProgressItem] = Field(default_factory=list)
    blocked_or_at_risk: List[BlockedItem] = Field(default_factory=list)
    important_changes: List[ImportantChangeItem] = Field(default_factory=list)
    requires_attention: List[RequiresAttentionItem] = Field(default_factory=list)


# ── Mentor Skill Contracts ────────────────────────────────────────────────────

class MentorAssessmentRequest(BaseModel):
    trainee: str
    period: Optional[str] = None
    focus_area: Optional[str] = None
    query: str = "Assess trainee technical progress."
    trace_id: Optional[str] = None


class DemonstratedCapabilityItem(BaseModel):
    concept: str
    demonstration_level: str  # Taught, Attempted, Demonstrated, Confused
    evidence_justification: str
    chunk_id: str


class MisconceptionItem(BaseModel):
    concept: str
    what_trainee_believed: str
    what_is_true: str
    mentor_correction: str
    chunk_id: str


class MentorTraineeAssessmentOutput(BaseModel):
    trainee: str
    overall_assessment: str
    current_work: List[str] = Field(default_factory=list)
    demonstrated_capabilities: List[DemonstratedCapabilityItem] = Field(default_factory=list)
    learning_progress: str
    knowledge_gaps: List[str] = Field(default_factory=list)
    recurring_misconceptions: List[MisconceptionItem] = Field(default_factory=list)
    feedback_signals: List[str] = Field(default_factory=list)
    change_from_previous_period: str
    evidence_backed_conclusion: str


# ── Team Intelligence Skill Contracts ─────────────────────────────────────────

class TeamCatchupRequest(BaseModel):
    date: Optional[str] = None
    trainee: Optional[str] = None
    query: str = "What did I miss in today's training session?"
    trace_id: Optional[str] = None


class ActionItem(BaseModel):
    assigned_to: str
    task_description: str
    acceptance_criteria: str
    chunk_id: str


class TeamSessionCatchupOutput(BaseModel):
    session_date: str
    what_happened: str
    technical_concepts_discussed: List[str] = Field(default_factory=list)
    assignments_and_actions: List[ActionItem] = Field(default_factory=list)
    decisions: List[str] = Field(default_factory=list)
    important_changes: List[str] = Field(default_factory=list)
    what_you_need_to_know_or_do: List[str] = Field(default_factory=list)
