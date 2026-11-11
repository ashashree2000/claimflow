import pytest

from claimflow import audit
from claimflow.agents import triage
from claimflow.schemas import ClaimEmail, ClaimEvent


def test_packet_and_review_are_logged_and_masked(make_llm, fake_search, claim_c07):
    p = triage(make_llm(), ClaimEmail(**claim_c07["email"]), [ClaimEvent(**e) for e in claim_c07["events"]], "C07")
    rows = audit.list_packets()
    assert rows[0]["packet_id"] == p.packet_id and rows[0]["review_action"] is None
    rec = audit.get_packet(p.packet_id)
    assert "66778" not in rec["input_masked"] and "[PHONE]" in rec["input_masked"]
    assert rec["sources"]["policy_clauses"]
    audit.record_review(p.packet_id, "reject", "wrong clause, call 90000 66778")
    row = audit.list_packets()[0]
    assert row["review_action"] == "reject" and "66778" not in row["review_note"]


def test_review_validation():
    with pytest.raises(ValueError):
        audit.record_review("x", "maybe")
    with pytest.raises(KeyError):
        audit.record_review("does-not-exist", "approve")
