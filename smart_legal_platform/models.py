from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Role(str, Enum):
    admin = "admin"
    lawyer = "lawyer"
    paralegal = "paralegal"
    client = "client"


class User(BaseModel):
    username: str
    full_name: str
    role: Role
    disabled: bool = False


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SearchRequest(BaseModel):
    query: str = Field(min_length=3)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    source_id: str
    title: str
    summary: str
    score: float
    citations: list[str]


class SearchResponse(BaseModel):
    question: str
    synthesized_answer: str
    results: list[SearchResult]


class PrecedentLink(BaseModel):
    case_id: str
    related_case_id: str
    relationship_score: float
    reason: str


class OutcomePrediction(BaseModel):
    case_id: str
    predicted_outcome: str
    confidence: float
    feature_contributions: dict[str, float]


class ContractReviewRequest(BaseModel):
    contract_text: str = Field(min_length=30)


class ContractGenerateRequest(BaseModel):
    template_name: str
    fields: dict[str, str] = Field(default_factory=dict)


class ContractRisk(BaseModel):
    clause_type: str
    severity: str
    details: str


class ContractAnalysisResponse(BaseModel):
    extracted_clauses: dict[str, str]
    unusual_clauses: list[str]
    risks: list[ContractRisk]


class CaseStatus(str, Enum):
    intake = "intake"
    active = "active"
    negotiation = "negotiation"
    trial = "trial"
    closed = "closed"


class LegalCaseCreate(BaseModel):
    title: str
    client_name: str
    judge: str
    strategy: str
    value_at_risk: float = 0.0


class LegalCase(BaseModel):
    id: str
    title: str
    client_name: str
    judge: str
    strategy: str
    value_at_risk: float
    status: CaseStatus = CaseStatus.intake
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskCreate(BaseModel):
    title: str
    assignee: str
    due_date: datetime


class Task(BaseModel):
    id: str
    case_id: str
    title: str
    assignee: str
    due_date: datetime
    status: str = "open"


class AppointmentCreate(BaseModel):
    title: str
    starts_at: datetime
    ends_at: datetime
    participants: list[str]


class Appointment(BaseModel):
    id: str
    case_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    participants: list[str]


class TimeEntryCreate(BaseModel):
    user: str
    hours: float = Field(gt=0, le=24)
    rate: float = Field(gt=0)
    description: str


class TimeEntry(BaseModel):
    id: str
    case_id: str
    user: str
    hours: float
    rate: float
    description: str
    created_at: datetime


class InvoiceCreate(BaseModel):
    issued_to: str
    tax_percent: float = Field(default=0.0, ge=0, le=100)


class Invoice(BaseModel):
    id: str
    case_id: str
    issued_to: str
    subtotal: float
    tax_percent: float
    total: float
    created_at: datetime


class SecureMessageCreate(BaseModel):
    sender: str
    recipient: str
    subject: str
    body: str
    case_id: str | None = None


class SecureMessage(BaseModel):
    id: str
    sender: str
    recipient: str
    subject: str
    encrypted_body: str
    case_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SecureMessageView(BaseModel):
    id: str
    sender: str
    recipient: str
    subject: str
    body: str
    case_id: str | None = None
    created_at: datetime


class ESignatureRequest(BaseModel):
    case_id: str
    signer: str
    document_hash: str = Field(min_length=16)
    signed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ESignatureRecord(BaseModel):
    id: str
    case_id: str
    signer: str
    document_hash: str
    signed_at: datetime
    verification_code: str


class DashboardMetrics(BaseModel):
    total_cases: int
    active_cases: int
    avg_hours_per_case: float
    revenue_estimate: float
    lawyer_success_rate: dict[str, float]
    judge_trend_score: dict[str, float]


class StrategyPrediction(BaseModel):
    strategy: str
    probability_of_success: float
    sample_size: int


class RiskOpportunitySignal(BaseModel):
    case_id: str
    risk_score: float
    opportunity_score: float
    drivers: list[str]
