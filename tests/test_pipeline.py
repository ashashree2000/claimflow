from claimflow.agents import triage
from claimflow.schemas import ClaimEmail, ClaimEvent


def run(llm, c, mode):
    return triage(llm, ClaimEmail(**c["email"]), [ClaimEvent(**e) for e in c["events"]], "C07", mode=mode, save=False)


def test_vector_mode_refuses_when_cited_clause_was_not_retrieved(make_llm, fake_search, claim_c07):
    p = run(make_llm(), claim_c07, "vector")
    assert p.coverage.decision == "needs_review" and not p.coverage.citations
    assert any("not in the retrieved clauses" in n for n in p.coverage.guardrail_notes)
    assert p.needs_human_review


def test_graph_mode_keeps_verified_citation(make_llm, fake_search, claim_c07):
    p = run(make_llm(), claim_c07, "graph")
    assert "MOTOR-EXC-4.2" in p.coverage.expanded_ids
    assert p.coverage.decision == "not_covered" and [c.clause_id for c in p.coverage.citations] == ["MOTOR-EXC-4.2"]
    assert p.confidence == "high" and not p.needs_human_review
    assert p.documents_missing == ["claim_form", "driving_licence", "registration_certificate"]


def test_wrong_quote_is_dropped(make_llm, fake_search, claim_c07):
    bad = {"decision": "covered", "reasoning": "x",
           "citations": [{"clause_id": "MOTOR-COV-2.1", "quote": "we always pay for everything"}]}
    p = run(make_llm({"coverage": [bad]}), claim_c07, "vector")
    assert p.coverage.decision == "needs_review"


def test_process_flags_with_unknown_sop_or_event_are_dropped(make_llm, fake_search, claim_c07):
    flags = {"flags": [{"type": "out_of_order", "event_ids": ["E99"], "sop_id": "SOP-VER-1.1", "fix": "x"},
                       {"type": "excessive_wait", "event_ids": ["E1"], "sop_id": "SOP-XXX-9.9", "fix": "x"},
                       {"type": "repeated_verification", "event_ids": ["E3", "E9"], "sop_id": "SOP-VER-1.2",
                        "fix": "Verify once."}]}
    p = run(make_llm({"process": [flags]}), claim_c07, "graph")
    assert [f.type for f in p.process.flags] == ["repeated_verification"]
    assert len(p.process.guardrail_notes) == 2


def test_intake_failure_is_safe(make_llm, fake_search, claim_c07):
    p = run(make_llm({"intake": ["bad", "bad"]}), claim_c07, "graph")
    assert p.intake is None and p.coverage is None and p.needs_human_review and p.confidence == "low"
    assert p.route.line_of_business == "motor"  # router still reads the policy number from the email


def test_second_run_is_served_from_cache(make_llm, fake_search, claim_c07):
    llm = make_llm()
    run(llm, claim_c07, "graph")
    n = len(llm.provider.calls)
    run(llm, claim_c07, "graph")
    assert len(llm.provider.calls) == n
