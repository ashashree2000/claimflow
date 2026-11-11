"""Typed contracts between agents. Every model output is validated against one of these."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LOB = Literal["motor", "property", "health"]
DocName = Literal["claim_form", "driving_licence", "registration_certificate", "damage_photos", "repair_estimate",
                  "police_report", "proof_of_ownership", "discharge_summary", "itemised_bill", "id_proof"]
Decision = Literal["covered", "not_covered", "needs_review"]
FlawType = Literal["missing_document", "duplicate_request", "repeated_verification", "out_of_order", "excessive_wait"]


class ClaimEmail(BaseModel):
    from_name: str = ""
    from_email: str = ""
    sent_at: str = ""
    subject: str = ""
    attachments: list[str] = []
    body: str


class ClaimEvent(BaseModel):
    event_id: str
    timestamp: str
    step: str
    document: str | None = None


# ---- agent outputs (model-produced, validated) ----
class IntakeResult(BaseModel):
    claimant_name: str | None
    policy_number: str | None
    line_of_business: Literal["motor", "property", "health", "unknown"]
    incident_date: str | None = Field(description="YYYY-MM-DD, or null if not stated")
    incident_type: str
    description: str
    location: str | None
    documents_attached: list[DocName]
    severity: Literal["low", "medium", "high"]
    severity_reason: str


class Citation(BaseModel):
    clause_id: str
    quote: str


class CoverageAnswer(BaseModel):
    decision: Decision
    citations: list[Citation]
    reasoning: str


class ProcessFlag(BaseModel):
    type: FlawType
    document: DocName | None = None
    event_ids: list[str]
    sop_id: str
    fix: str


class ProcessAnswer(BaseModel):
    flags: list[ProcessFlag]


# ---- code-assembled results ----
class RouteDecision(BaseModel):
    line_of_business: LOB | Literal["unknown"]
    specialists: list[str]
    reason: str
    method: Literal["rules", "needs_human"]


class CoverageResult(BaseModel):
    decision: Decision
    citations: list[Citation]
    reasoning: str
    retrieval_mode: str
    retrieved_ids: list[str]
    expanded_ids: list[str] = []
    guardrail_notes: list[str] = []


class ProcessResult(BaseModel):
    flags: list[ProcessFlag]
    guardrail_notes: list[str] = []


class TriagePacket(BaseModel):
    packet_id: str
    claim_id: str | None
    synthetic: bool = True
    created_at: str
    model: str
    retrieval_mode: str
    intake: IntakeResult | None
    documents_missing: list[str]
    route: RouteDecision
    coverage: CoverageResult | None
    process: ProcessResult | None
    confidence: Literal["high", "medium", "low"]
    reasons: list[str]
    needs_human_review: bool
    errors: list[str] = []
