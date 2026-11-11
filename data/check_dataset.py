"""Consistency checks for the synthetic ClaimFlow dataset. No API calls.

Checks:
  1. Policy and SOP documents: IDs unique, every cross-reference points to a real clause.
  2. Labels: every gold clause / SOP ID exists, in the right policy.
  3. Emails: no leakage (no clause/SOP IDs, no decision or policy-term words),
     and the gold fields (policy number, date, location) are actually in the email.
  4. Notice periods in the policies are met (so no claim fails by accident).
  5. Event logs: a flaw detector written independently of the generator must find
     exactly the planted flaws, and nothing else.
  6. Grid counts: claims per line, cross-reference, refusal and no-flaw cases.

Run: python data/check_dataset.py     (exits 1 if any check fails)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent
ID_RE = re.compile(r"\b(?:MOTOR|PROP|HLTH)-[A-Z]{3}-\d+(?:\.\d+)?\b")
SOP_RE = re.compile(r"\bSOP-[A-Z]{3}-\d+\.\d+\b")
HEAD_RE = re.compile(r"^#{2,3} ((?:MOTOR|PROP|HLTH|SOP)-[A-Z]{3}-\d+(?:\.\d+)?) ", re.M)
BANNED = ["not covered", "excluded", "exclusion", "endorsement", "commercial use", "pre-existing",
          "unoccupied", "day-care", "hypertension", "sop", "clause", "policy wording"]
NOTICE_DAYS = {"motor": 7, "property": 14, "health": 7}
REQUIRED = {
    "motor": ["claim_form", "driving_licence", "registration_certificate", "damage_photos", "repair_estimate"],
    "motor_theft": ["claim_form", "driving_licence", "registration_certificate", "police_report"],
    "property": ["claim_form", "damage_photos", "repair_estimate", "proof_of_ownership"],
    "health": ["claim_form", "discharge_summary", "itemised_bill", "id_proof"],
}

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def parse_ids(folder: Path) -> tuple[dict, dict]:
    """Return {id: text} and {id: file} for every heading in the folder."""
    ids, where = {}, {}
    for f in sorted(folder.glob("*.md")):
        text = f.read_text()
        parts = HEAD_RE.split(text)
        for i in range(1, len(parts), 2):
            cid, body = parts[i], parts[i + 1]
            if cid in ids:
                fail(f"duplicate ID {cid} in {f.name}")
            ids[cid], where[cid] = body, f.name
    return ids, where


def detect_flaws(lob: str, itype: str, attached: list[str], events: list[dict]) -> list[tuple]:
    """Independent re-implementation of the SOP rules over an event log."""
    t = lambda e: datetime.fromisoformat(e["timestamp"])  # noqa: E731
    found = []
    steps = [e["step"] for e in events]
    fnol = next(e for e in events if e["step"] == "FNOL received")
    ack = next((e for e in events if e["step"] == "Acknowledgement sent"), None)
    if ack is None or t(ack) - t(fnol) > timedelta(hours=24):
        found.append(("excessive_wait", None))
    key = "motor_theft" if (lob == "motor" and itype == "theft") else lob
    req = REQUIRED[key] + (["police_report"] if lob == "property" and itype == "burglary_theft" else [])
    requested = Counter(e["document"] for e in events if e["step"].startswith("Document requested"))
    for d in req:
        if d not in attached and requested[d] == 0:
            found.append(("missing_document", d))
    for d, n in requested.items():
        if n > 1 or d in attached:
            found.append(("duplicate_request", d))
    if steps.count("Policy status verified") > 1 or steps.count("Coverage check completed") > 1:
        found.append(("repeated_verification", None))
    assign = [e for e in events if e["step"] in ("Surveyor assigned", "Medical reviewer assigned")]
    checks = [e for e in events if e["step"] in ("Policy status verified", "Coverage check completed")]
    if assign and checks and t(assign[0]) < max(t(e) for e in checks[:2]):
        found.append(("out_of_order", None))
    for e in events:
        if e["step"].startswith("Document requested"):
            d = e["document"]
            got = [x for x in events if x["step"].startswith("Document received") and x["document"] == d and t(x) >= t(e)]
            rem = [x for x in events if x["step"].startswith("Reminder sent") and x.get("document") == d]
            if got and t(got[0]) - t(e) > timedelta(days=3) and not rem:
                found.append(("excessive_wait", d))
    return found


def main() -> None:
    clauses, cwhere = parse_ids(DATA / "policies")
    sops, _ = parse_ids(DATA / "sops")
    print(f"Policies: {len(set(cwhere.values()))} files, {len(clauses)} headings "
          f"({sum(1 for c in clauses if '.' in c)} numbered clauses)")
    print(f"SOPs: {len(list((DATA / 'sops').glob('*.md')))} files, {len(sops)} sections")

    # 1. cross-references resolve
    for cid, text in clauses.items():
        for ref in ID_RE.findall(text):
            if ref not in clauses:
                fail(f"{cid} references missing clause {ref}")
    xref_edges = sum(len(set(ID_RE.findall(t)) - {c}) for c, t in clauses.items())
    print(f"Explicit cross-references in policy text: {xref_edges}")

    labels = [json.loads(line) for line in (DATA / "labels.jsonl").read_text().splitlines()]
    prefix = {"motor": "MOTOR", "property": "PROP", "health": "HLTH"}
    for lab in labels:
        cid, lob = lab["claim_id"], lab["line_of_business"]
        claim = json.loads((DATA / "claims" / f"{cid}.json").read_text())
        email, events = claim["email"], claim["events"]
        text = email["subject"] + "\n" + email["body"]
        f = lab["fields"]

        # 2. gold IDs exist and belong to the right policy
        cov = lab["coverage"]
        for x in cov["required_clause_ids"] + cov["acceptable_clause_ids"]:
            if x not in clauses:
                fail(f"{cid}: gold clause {x} does not exist")
            elif not x.startswith(prefix[lob]):
                fail(f"{cid}: gold clause {x} is from another policy")
        if set(cov["required_clause_ids"]) & set(cov["acceptable_clause_ids"]):
            fail(f"{cid}: clause in both required and acceptable")
        if (cov["decision"] == "needs_review") != lab["should_refuse"]:
            fail(f"{cid}: refusal flag does not match decision")
        if cov["decision"] != "needs_review" and not cov["required_clause_ids"]:
            fail(f"{cid}: decision without supporting clauses")
        for fl in lab["process_flaws"]:
            if fl["sop_id"] not in sops:
                fail(f"{cid}: SOP {fl['sop_id']} does not exist")
            for eid in fl["event_ids"]:
                if eid not in {e["event_id"] for e in events}:
                    fail(f"{cid}: flaw cites missing event {eid}")

        # 3. leakage and field presence
        low = text.lower()
        if ID_RE.search(text) or SOP_RE.search(text):
            fail(f"{cid}: email contains a clause or SOP ID")
        for w in BANNED:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                fail(f"{cid}: email contains banned term '{w}'")
        if f["policy_number"] not in text:
            fail(f"{cid}: policy number not in email")
        if f["incident_date"]:
            d = datetime.fromisoformat(f["incident_date"])
            if f"{d.day} {d.strftime('%B')}" not in email["body"]:
                fail(f"{cid}: incident date not written in the email")
        if f["location"] and f["location"] not in email["body"]:
            fail(f"{cid}: location not in email")
        if not email["synthetic"] if "synthetic" in email else not claim.get("synthetic"):
            fail(f"{cid}: not labelled synthetic")
        if len(email["attachments"]) != len(f["documents_attached"]):
            fail(f"{cid}: attachment count differs from gold")

        # 4. notice period
        if f["incident_date"]:
            gap = datetime.fromisoformat(email["sent_at"]) - datetime.fromisoformat(f["incident_date"])
            if gap > timedelta(days=NOTICE_DAYS[lob]) or gap < timedelta(0):
                fail(f"{cid}: notice period broken ({gap.days} days)")

        # 5. flaws: independent detector == planted
        ts = [e["timestamp"] for e in events]
        if ts != sorted(ts):
            fail(f"{cid}: events not in time order")
        got = Counter(detect_flaws(lob, f["incident_type"], f["documents_attached"], events))
        want = Counter((x["type"], x.get("document")) for x in lab["process_flaws"])
        if got != want:
            fail(f"{cid}: detector found {dict(got)} but labels plant {dict(want)}")

    # 6. grid
    by_lob = Counter(lab["line_of_business"] for lab in labels)
    dec = Counter((lab["line_of_business"], lab["coverage"]["decision"]) for lab in labels)
    n_xref = sum(lab["cross_reference"] for lab in labels)
    n_ref = sum(lab["should_refuse"] for lab in labels)
    n_clean = sum(not lab["process_flaws"] for lab in labels)
    n_flaws = Counter(x["type"] for lab in labels for x in lab["process_flaws"])
    sev = Counter(lab["fields"]["severity"] for lab in labels)
    print(f"Claims: {len(labels)} {dict(by_lob)}")
    print(f"Decisions: {dict(sorted(dec.items()))}")
    print(f"Cross-reference cases: {n_xref}; refusal cases: {n_ref}; claims with no process flaw: {n_clean}")
    print(f"Planted process flaws: {sum(n_flaws.values())} {dict(n_flaws)}")
    print(f"Severity: {dict(sev)}")
    if len(labels) != 30 or set(by_lob.values()) != {10}:
        fail("expected 10 claims per line of business")
    if not 7 <= n_xref <= 9:
        fail("expected about 8 cross-reference cases")

    if errors:
        print(f"\nFAILED: {len(errors)} problem(s)")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("\nAll dataset checks passed.")


if __name__ == "__main__":
    main()
