"""Process agent: checks the claim's event log against the claims-handling SOPs and proposes SOP-cited fixes.

The SOP corpus is small (25 sections), so the agent receives all of it rather than a retrieved subset.
Code drops flags that cite an unknown SOP section or event ID.
"""
from __future__ import annotations

import json

from ..guardrails import call_validated
from ..llm import LLMClient
from ..retrieval import load_sops
from ..schemas import ClaimEvent, IntakeResult, ProcessAnswer, ProcessResult

SYSTEM = """You are the process-compliance agent for an insurer's claims team. You compare a claim's event log
with the claims-handling SOPs and report only real departures from them. Reply with one JSON object only."""

FLAW_TYPES = {
    "missing_document": "a document on the SOP checklist was neither attached nor ever requested",
    "duplicate_request": "the same document was requested more than once, or requested although already received or attached",
    "repeated_verification": "a verification step was performed more than once without a recorded reason",
    "out_of_order": "a step happened before a step the SOP says must come first",
    "excessive_wait": "a wait longer than an SOP time limit (acknowledgement, document follow-up, assignment)",
}


def build_prompt(lob: str, intake: IntakeResult | None, attached: list[str], required: list[str],
                 events: list[ClaimEvent]) -> str:
    sops = "\n".join(c.render() for c in load_sops().values())
    log = "\n".join(f"{e.event_id} | {e.timestamp} | {e.step}" for e in events)
    itype = intake.incident_type if intake else "unknown"
    return f"""Check this claim's handling against the SOPs.

Line of business: {lob}; incident type: {itype}
Documents attached to the first notice: {json.dumps(attached)}
Documents required by the checklist for this claim: {json.dumps(required)}

Event log (event_id | time | step). Several "Document requested" events with the same time are one
consolidated request message.
{log}

Report each departure from the SOPs as a flag with:
- type: one of {json.dumps(FLAW_TYPES)}
- document: the document key if the flag is about one document (else null)
- event_ids: the events that show the problem
- sop_id: the one SOP section the fix relies on
- fix: one or two sentences saying what the handler should do, grounded in that SOP section
Return {{"flags": []}} if the handling follows the SOPs.

SOPs:
{sops}
"""


def run(llm: LLMClient, lob: str, intake: IntakeResult | None, attached: list[str], required: list[str],
        events: list[ClaimEvent]) -> tuple[ProcessResult | None, dict]:
    ans, meta = call_validated(llm, build_prompt(lob, intake, attached, required, events), SYSTEM,
                               ProcessAnswer, agent="process")
    if ans is None:
        return None, meta
    sops, ids = load_sops(), {e.event_id for e in events}
    kept, notes = [], []
    for f in ans.flags:
        if f.sop_id not in sops:
            notes.append(f"dropped {f.type} flag: unknown SOP section {f.sop_id}")
        elif any(e not in ids for e in f.event_ids):
            notes.append(f"dropped {f.type} flag: cites an event that is not in the log")
        else:
            kept.append(f)
    return ProcessResult(flags=kept, guardrail_notes=notes), meta
