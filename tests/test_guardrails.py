import pytest

from claimflow.guardrails import call_validated, mask_pii, parse_model, quote_in_text
from claimflow.schemas import CoverageAnswer, IntakeResult


def test_parse_model_accepts_valid_json_and_fences():
    obj, err = parse_model('```json\n{"decision": "covered", "citations": [], "reasoning": "x"}\n```', CoverageAnswer)
    assert obj is not None and obj.decision == "covered" and err == ""


@pytest.mark.parametrize("text", ["not json", '{"decision": "maybe", "citations": [], "reasoning": "x"}',
                                  '{"decision": "covered"}'])
def test_parse_model_rejects_invalid(text):
    obj, err = parse_model(text, CoverageAnswer)
    assert obj is None and err


def test_call_validated_retries_once_then_succeeds(make_llm):
    from tests.conftest import DEFAULTS
    llm = make_llm({"intake": ["garbage", DEFAULTS["intake"]]})
    obj, meta = call_validated(llm, "p", "You are the intake agent", IntakeResult, agent="intake")
    assert obj is not None and meta["retried"] and not meta["error"]
    assert llm.provider.calls == ["intake", "intake"]


def test_call_validated_fails_safely_after_two_bad_replies(make_llm):
    llm = make_llm({"intake": ["garbage", "{}"]})
    obj, meta = call_validated(llm, "p", "You are the intake agent", IntakeResult, agent="intake")
    assert obj is None and "failed twice" in meta["error"]


def test_quote_check_is_verbatim_but_ignores_case_and_punctuation():
    text = "We do not pay for any loss while the insured vehicle is being used for commercial use (MOTOR-DEF-1.3)."
    assert quote_in_text("Being used for commercial use", text)
    assert not quote_in_text("used for private use", text)
    assert not quote_in_text("loss", text)  # too short to count as a quote


def test_mask_pii():
    s = "Call +91 90000 66778 or mail vikram.singh@example.com about MTR-26-52318 on 2026-10-26."
    m = mask_pii(s)
    assert "[PHONE]" in m and "[EMAIL]" in m and "[ID]" in m
    assert "90000" not in m and "example.com" not in m and "2026-10-26" in m
