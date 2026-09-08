"""Base dataclasses and Pydantic schemas for agent capabilities."""

from dataclasses import dataclass, field
from typing import List, Optional, Union, Literal, Dict, Any, Callable, Type
from pydantic import BaseModel, Field
from harness.evidence_store import EvidenceItem
from harness.state import Violation


# ── Schemas ──────────────────────────────────────────────────────────────────

class EvidenceClaim(BaseModel):
    claim: str
    evidence_ids: List[str] = Field(default_factory=list)


class AdHocOutput(BaseModel):
    question: str
    answer: str
    claims: List[EvidenceClaim] = Field(default_factory=list)
    uncertainty: Optional[str] = None
    coverage_note: Optional[str] = None


class CompletedItem(BaseModel):
    owner: str
    item: str
    evidence_ids: List[str] = Field(default_factory=list)


class InProgressItem(BaseModel):
    owner: str
    item: str
    evidence_ids: List[str] = Field(default_factory=list)


class BlockedItem(BaseModel):
    owner: str
    item: str
    impact: str
    agreed_resolution: Union[str, Literal["none_agreed"]]
    evidence_ids: List[str] = Field(default_factory=list)


class DecisionItem(BaseModel):
    decision: str
    owner: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class NeedsCallItem(BaseModel):
    question: str
    why_now: str
    evidence_ids: List[str] = Field(default_factory=list)


class ManagerRollupOutput(BaseModel):
    period: str
    headline: str
    completed: List[CompletedItem] = Field(default_factory=list)
    in_progress: List[InProgressItem] = Field(default_factory=list)
    blocked: List[BlockedItem] = Field(default_factory=list)
    decisions: List[DecisionItem] = Field(default_factory=list)
    needs_your_call: List[NeedsCallItem] = Field(default_factory=list)
    coverage_note: Optional[str] = None


class DimensionItem(BaseModel):
    name: str
    score: Union[int, Literal["not_observed"]]
    reason: str
    evidence_ids: List[str] = Field(default_factory=list)


class WorkItem(BaseModel):
    item: str
    evidence_ids: List[str] = Field(default_factory=list)


class DemonstratedItem(BaseModel):
    concept: str
    how_shown: str
    evidence_ids: List[str] = Field(default_factory=list)


class GapItem(BaseModel):
    gap: str
    evidence_ids: List[str] = Field(default_factory=list)


class MisconceptionItem(BaseModel):
    misconception: str
    corrected_on: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class FeedbackSignalItem(BaseModel):
    feedback: str
    evidence_ids: List[str] = Field(default_factory=list)


class MentorAssessmentOutput(BaseModel):
    person: str
    period: str
    overall: str
    dimensions: List[DimensionItem] = Field(default_factory=list)
    current_work: List[WorkItem] = Field(default_factory=list)
    demonstrated_capabilities: List[DemonstratedItem] = Field(default_factory=list)
    knowledge_gaps: List[GapItem] = Field(default_factory=list)
    recurring_misconceptions: List[MisconceptionItem] = Field(default_factory=list)
    feedback_signals: List[FeedbackSignalItem] = Field(default_factory=list)
    change_from_previous: Union[str, Literal["not_observed"]] = "not_observed"
    next_teaching_action: str


class TopicItem(BaseModel):
    topic: str
    summary: str
    evidence_ids: List[str] = Field(default_factory=list)


class TeamDecisionItem(BaseModel):
    decision: str
    evidence_ids: List[str] = Field(default_factory=list)


class AssignmentForYouItem(BaseModel):
    task: str
    due: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class AssignmentForOtherItem(BaseModel):
    owner: str
    task: str
    evidence_ids: List[str] = Field(default_factory=list)


class TeamCatchupOutput(BaseModel):
    session_date: str
    what_happened: str
    technical_topics: List[TopicItem] = Field(default_factory=list)
    decisions: List[TeamDecisionItem] = Field(default_factory=list)
    assignments_for_you: List[AssignmentForYouItem] = Field(default_factory=list)
    assignments_for_others: List[AssignmentForOtherItem] = Field(default_factory=list)
    what_to_do_next: str


# ── Capability Dataclass ─────────────────────────────────────────────────────

RuleFunc = Callable[[Dict[str, Any], List[EvidenceItem], Dict[str, Any]], List[Violation]]


@dataclass
class Rule:
    id: str
    description: str
    check_fn: RuleFunc


@dataclass
class Capability:
    name: str
    consumer: str
    purpose: str
    output_schema: Type[BaseModel]
    verification_rules: List[Rule]
    tool_hints: List[str] = field(default_factory=list)
    default_budget: int = 35000
    max_tool_calls: int = 6
    raw_content: str = ""  # Full markdown text — read-only, never modified
