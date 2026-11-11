"""Router: decides the line of business and which specialists to call. Rules only, with a logged reason.

Signals: the policy-number prefix (MTR/PRP/HLT) and the intake agent's line of business.
If they disagree or neither is known, the claim goes to a human (SOP-INT-1.4) instead of guessing.
"""
from __future__ import annotations

import re

from ..schemas import IntakeResult, RouteDecision
from ..sop_rules import POLICY_PREFIX

SPECIALISTS = ["coverage", "process"]


def route(intake: IntakeResult | None, raw_text: str = "") -> RouteDecision:
    policy = (intake.policy_number if intake else None) or ""
    if not policy:
        m = re.search(r"\b(MTR|PRP|HLT)-\d{2}-\d{4,6}\b", raw_text)
        policy = m.group(0) if m else ""
    prefix_lob = POLICY_PREFIX.get(policy.split("-")[0]) if policy else None
    intake_lob = intake.line_of_business if intake and intake.line_of_business != "unknown" else None

    if prefix_lob and intake_lob and prefix_lob != intake_lob:
        return RouteDecision(line_of_business="unknown", specialists=["process"], method="needs_human",
                             reason=f"policy prefix says {prefix_lob} but the email reads as {intake_lob} (SOP-INT-1.4)")
    lob = prefix_lob or intake_lob
    if not lob:
        return RouteDecision(line_of_business="unknown", specialists=["process"], method="needs_human",
                             reason="line of business could not be determined (SOP-INT-1.4)")
    parts = []
    if prefix_lob:
        parts.append(f"policy number {policy} has prefix for {prefix_lob}")
    if intake_lob:
        parts.append(f"intake agent read the email as {intake_lob}")
    return RouteDecision(line_of_business=lob, specialists=SPECIALISTS, method="rules", reason="; ".join(parts))
