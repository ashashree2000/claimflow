"""Shared fixtures. All tests use a fake model: no API key, no network, no Chroma."""
import json
from pathlib import Path

import pytest

from claimflow import config
from claimflow.llm import LLMClient, LLMResult
from claimflow.llm.cache import DiskCache

ROOT = Path(__file__).resolve().parent.parent


class FakeProvider:
    """Answers by agent (read from the system prompt). `replies` can override per agent with a list."""

    name = "fake"

    def __init__(self, replies: dict | None = None):
        self.replies = replies or {}
        self.calls = []

    def generate(self, prompt, system, model, json_mode, schema=None):
        agent = "intake" if "intake agent" in system else "coverage" if "coverage agent" in system else "process"
        self.calls.append(agent)
        queue = self.replies.get(agent)
        if queue:
            out = queue.pop(0)
        else:
            out = DEFAULTS[agent]
        text = out if isinstance(out, str) else json.dumps(out)
        return LLMResult(text=text, model=model, input_tokens=100, output_tokens=20, latency_ms=10)

    def embed(self, texts, model, task_type=None):
        return [[float(len(t) % 7), 1.0] for t in texts]


DEFAULTS = {
    "intake": dict(claimant_name="Vikram Singh", policy_number="MTR-26-52318", line_of_business="motor",
                   incident_date="2026-10-26", incident_type="collision", description="Hit at a junction.",
                   location="Jaipur", documents_attached=["damage_photos", "repair_estimate"], severity="medium",
                   severity_reason="estimate Rs 70,000"),
    "coverage": {"decision": "not_covered", "reasoning": "Commercial use.",
                 "citations": [{"clause_id": "MOTOR-EXC-4.2", "quote": "being used for commercial use"}]},
    "process": {"flags": [{"type": "repeated_verification", "document": None, "event_ids": ["E3", "E9"],
                           "sop_id": "SOP-VER-1.2", "fix": "Verify once."}]},
}


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    return tmp_path / "test.db"


@pytest.fixture
def make_llm(tmp_path):
    def _make(replies=None):
        return LLMClient(FakeProvider(replies), cache=DiskCache(tmp_path / "cache"), delay_s=0, max_retries=1)
    return _make


@pytest.fixture
def fake_search(monkeypatch):
    """Replace Chroma vector search with a fixed result."""
    from claimflow.retrieval import vector
    hits = [("MOTOR-COV-2.1", 0.9), ("MOTOR-CON-5.1", 0.8)]
    monkeypatch.setattr(vector, "search", lambda llm, q, lob, k=5, agent="", collection="": hits[:k])
    monkeypatch.setattr(vector, "ensure_index", lambda llm: True)
    return hits


@pytest.fixture
def claim_c07():
    return json.loads((ROOT / "data/claims/C07.json").read_text())
