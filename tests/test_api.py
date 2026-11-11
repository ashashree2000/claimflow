from fastapi.testclient import TestClient

import api.main as main


def test_health():
    r = TestClient(main.app).get("/health")
    assert r.status_code == 200 and r.json()["synthetic_data_only"] is True


def test_triage_review_and_metrics(make_llm, fake_search, claim_c07, monkeypatch):
    monkeypatch.setattr(main, "_llm", make_llm())
    c = TestClient(main.app)
    r = c.post("/triage", json={"email": claim_c07["email"], "events": claim_c07["events"], "claim_id": "C07"})
    assert r.status_code == 200
    pid = r.json()["packet_id"]
    assert r.json()["coverage"]["decision"] == "not_covered"
    assert c.post(f"/review/{pid}", json={"action": "approve"}).json()["action"] == "approve"
    assert c.post("/review/nope", json={"action": "approve"}).status_code == 404
    m = c.get("/metrics/summary").json()
    assert m["model_calls"]["calls"] > 0
