"""Supervisor: runs intake -> router -> coverage + process, and assembles one triage packet.

Flow:  email --> intake --> router --+--> coverage (vector | graph retrieval)
                                     +--> process (event log vs SOPs)
                                     +--> supervisor: packet, confidence, needs_human_review --> audit log
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .. import audit, config
from ..llm import LLMClient, QuotaExhausted
from ..schemas import ClaimEmail, ClaimEvent, TriagePacket
from ..sop_rules import required_docs
from . import coverage, intake, process, router


def triage(llm: LLMClient, email: ClaimEmail, events: list[ClaimEvent] | None = None, claim_id: str | None = None,
           mode: str = config.RETRIEVAL_MODE, save: bool = True) -> TriagePacket:
    events = events or []
    errors, reasons = [], []
    raw = f"{email.subject}\n{email.body}"

    try:
        intake_res, meta = intake.run(llm, email)
    except QuotaExhausted:
        raise
    except Exception as e:  # safe failure: the packet still goes to a human
        intake_res, meta = None, {"error": f"intake failed: {type(e).__name__}: {e}"}
    if meta.get("error"):
        errors.append(meta["error"])
    if meta.get("retried"):
        reasons.append("intake output needed one retry to pass validation")

    route = router.route(intake_res, raw)
    lob = route.line_of_business
    attached = list(intake_res.documents_attached) if intake_res else []
    required = required_docs(lob, intake_res.incident_type if intake_res else "other")
    missing = [d for d in required if d not in attached]

    cov = None
    if "coverage" in route.specialists and intake_res is not None:
        try:
            cov, cmeta = coverage.run(llm, email, intake_res, lob, mode=mode)
        except QuotaExhausted:
            raise
        except Exception as e:
            cov, cmeta = None, {"error": f"coverage failed: {type(e).__name__}: {e}"}
        if cmeta.get("error"):
            errors.append(cmeta["error"])
        if cmeta.get("retried"):
            reasons.append("coverage output needed one retry to pass validation")

    proc = None
    if "process" in route.specialists:
        try:
            proc, pmeta = process.run(llm, lob, intake_res, attached, required, events)
        except QuotaExhausted:
            raise
        except Exception as e:
            proc, pmeta = None, {"error": f"process failed: {type(e).__name__}: {e}"}
        if pmeta.get("error"):
            errors.append(pmeta["error"])

    # rule-based confidence (not a model self-report)
    needs_human = route.method == "needs_human" or cov is None or cov.decision == "needs_review" or bool(errors)
    if route.method == "needs_human":
        reasons.append(f"routing: {route.reason}")
    if cov is not None:
        reasons += cov.guardrail_notes
        if cov.decision == "needs_review":
            reasons.append("coverage could not be decided from the policy clauses")
    if proc is not None:
        reasons += proc.guardrail_notes
    if errors or cov is None:
        confidence = "low"
    elif needs_human or (cov.guardrail_notes) or any("retry" in r for r in reasons):
        confidence = "medium"
    else:
        confidence = "high"
        reasons.append("all citations verified against the clause text; outputs passed validation first time")

    packet = TriagePacket(
        packet_id=uuid.uuid4().hex[:12], claim_id=claim_id,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), model=llm.text_model,
        retrieval_mode=mode, intake=intake_res, documents_missing=missing, route=route, coverage=cov,
        process=proc, confidence=confidence, reasons=reasons, needs_human_review=needs_human, errors=errors)
    if save:
        audit.save_packet(packet, raw)
    return packet
