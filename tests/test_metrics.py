from eval.metrics import aggregate, claim_row, field_correct, match_flags


def test_field_matching_rules():
    assert field_correct("policy_number", "mtr-26-52318 ", "MTR-26-52318")
    assert field_correct("location", "Malviya Nagar, Jaipur", "Jaipur")
    assert field_correct("incident_date", None, None)
    assert not field_correct("incident_date", "2026-10-01", None)
    assert field_correct("documents_attached", ["b", "a"], ["a", "b"])


def test_flag_matching_uses_type_and_document():
    gold = [{"type": "missing_document", "document": "id_proof"}, {"type": "excessive_wait"}]
    pred = [{"type": "missing_document", "document": "claim_form"}, {"type": "excessive_wait", "document": None}]
    assert len(match_flags(pred, gold)) == 1


def test_failed_packet_scores_as_wrong_and_aggregates():
    gold = {"claim_id": "C1", "cross_reference": True, "should_refuse": False,
            "expected_route": {"line_of_business": "motor", "specialists": ["coverage", "process"]},
            "fields": {k: None for k in ["claimant_name", "policy_number", "line_of_business", "incident_date",
                                         "incident_type", "location", "severity"]} | {"documents_attached": []},
            "coverage": {"decision": "covered", "required_clause_ids": ["A"], "acceptable_clause_ids": []},
            "process_flaws": [{"type": "out_of_order", "sop_id": "S"}]}
    row = claim_row(None, gold)
    assert row["failed"] and not row["decision_ok"] and row["citation_recall"] == 0
    agg = aggregate([row], [{"calls": [], "latency_ms": 0, "input_tokens": 0, "output_tokens": 0}])
    assert agg["coverage_accuracy"] == 0 and agg["n_failed"] == 1 and agg["process_flag_recall"] == 0
