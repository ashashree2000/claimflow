from claimflow.agents.router import route
from claimflow.schemas import IntakeResult
from tests.conftest import DEFAULTS


def intake(**kw):
    return IntakeResult(**{**DEFAULTS["intake"], **kw})


def test_prefix_and_intake_agree():
    r = route(intake())
    assert r.line_of_business == "motor" and r.method == "rules" and r.specialists == ["coverage", "process"]
    assert "MTR-26-52318" in r.reason


def test_disagreement_goes_to_human():
    r = route(intake(line_of_business="health"))
    assert r.method == "needs_human" and r.line_of_business == "unknown" and "coverage" not in r.specialists


def test_policy_number_found_in_raw_text_when_intake_missing():
    r = route(None, "Claim for policy PRP-26-11834, kitchen fire")
    assert r.line_of_business == "property"


def test_unknown_everything_goes_to_human():
    r = route(intake(policy_number=None, line_of_business="unknown"))
    assert r.method == "needs_human"
