"""Intake agent: FNOL email -> structured facts (IntakeResult). Severity follows SOP-INT-1.3."""
from __future__ import annotations

import json

from ..guardrails import call_validated
from ..llm import LLMClient
from ..retrieval import load_sops
from ..schemas import ClaimEmail, IntakeResult
from ..sop_rules import DOC_HINTS, INCIDENT_TYPES

SYSTEM = """You are the intake agent for an insurer's claims team. You read a first notice of loss (FNOL)
email and extract facts. Extract only what the email states; use null when a fact is not stated.
Reply with one JSON object only."""


def build_prompt(email: ClaimEmail) -> str:
    sops = load_sops()
    return f"""Extract these fields from the claim email below.

- claimant_name: the sender's full name
- policy_number: exactly as written
- line_of_business: one of "motor", "property", "health", or "unknown"
- incident_date: the date of the incident (for health: the admission or treatment date; for a loss found
  later: the date it was discovered), as YYYY-MM-DD, or null if no date is given
- incident_type: one value from this list for the line of business: {json.dumps(INCIDENT_TYPES)}
  Use "other" if none fits or the email does not say what happened.
- description: 1-2 neutral sentences on what happened, keeping facts that may matter for coverage
- location: the town or city where the incident happened (one place name), or null
- documents_attached: documents the email says are attached or that the attachment names show, using only
  these keys (key: what it covers): {json.dumps(DOC_HINTS)}. A document that "will follow" is not attached.
- severity and severity_reason: apply this rule exactly:
  "{sops['SOP-INT-1.3'].text}"

Email sent at: {email.sent_at}
Subject: {email.subject}
Attachments: {", ".join(email.attachments) or "none"}
Body:
{email.body}
"""


def run(llm: LLMClient, email: ClaimEmail) -> tuple[IntakeResult | None, dict]:
    return call_validated(llm, build_prompt(email), SYSTEM, IntakeResult, agent="intake")
