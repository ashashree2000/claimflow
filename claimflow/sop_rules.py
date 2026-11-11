"""Deterministic pieces of the SOPs that code applies directly (no model)."""
from __future__ import annotations

DOC_LABELS = {
    "claim_form": "claim form", "driving_licence": "driving licence",
    "registration_certificate": "registration certificate", "damage_photos": "damage photos",
    "repair_estimate": "repair estimate", "police_report": "police report",
    "proof_of_ownership": "proof of ownership", "discharge_summary": "discharge summary",
    "itemised_bill": "itemised hospital bill", "id_proof": "ID proof",
}
DOC_HINTS = {
    "claim_form": "the insurer's filled claim form", "driving_licence": "driving licence / DL",
    "registration_certificate": "vehicle registration certificate / RC",
    "damage_photos": "photos of the damage or of the scene", "repair_estimate": "estimate or quote for repairs",
    "police_report": "FIR, police complaint or police report copy",
    "proof_of_ownership": "purchase bills, invoices or receipts for damaged or stolen items",
    "discharge_summary": "hospital discharge summary or discharge note",
    "itemised_bill": "hospital, clinic or lab bill / invoice", "id_proof": "ID card, passport or other identity proof",
}
INCIDENT_TYPES = {
    "motor": ["collision", "theft", "windscreen", "fire_natural_peril", "third_party", "breakdown", "other"],
    "property": ["fire", "escape_of_water", "storm_flood", "burglary_theft", "gradual_damage", "other"],
    "health": ["hospitalisation", "day_care", "outpatient", "other"],
}
POLICY_PREFIX = {"MTR": "motor", "PRP": "property", "HLT": "health"}


def required_docs(lob: str, incident_type: str) -> list[str]:
    """Checklist from SOP-DOC-2.1 / 2.2 / 2.3."""
    if lob == "motor":
        if incident_type == "theft":
            return ["claim_form", "driving_licence", "registration_certificate", "police_report"]
        return ["claim_form", "driving_licence", "registration_certificate", "damage_photos", "repair_estimate"]
    if lob == "property":
        docs = ["claim_form", "damage_photos", "repair_estimate", "proof_of_ownership"]
        return docs + ["police_report"] if incident_type == "burglary_theft" else docs
    if lob == "health":
        return ["claim_form", "discharge_summary", "itemised_bill", "id_proof"]
    return []
