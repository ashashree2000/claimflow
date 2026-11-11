"""ClaimFlow REST API.

  POST /triage            email (+ optional event log) -> triage packet (saved to the audit log)
  POST /review/{id}       record a reviewer's approve / reject with an optional note
  GET  /health            liveness and readiness (API key present, index built)
  GET  /metrics/summary   model-call monitoring summary and the latest evaluation metrics
"""
from __future__ import annotations

import json
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from claimflow import audit, config, monitoring
from claimflow.agents import triage
from claimflow.llm import QuotaExhausted, get_client
from claimflow.retrieval import vector
from claimflow.schemas import ClaimEmail, ClaimEvent, TriagePacket

app = FastAPI(title="ClaimFlow", version="0.1.0",
              description="Multi-agent claims-intake copilot (synthetic data only).")
_llm = None


def llm():
    global _llm
    if _llm is None:
        _llm = get_client()
    return _llm


class TriageRequest(BaseModel):
    email: ClaimEmail
    events: list[ClaimEvent] = []
    claim_id: str | None = None
    mode: Literal["vector", "vector_wide", "graph"] = config.RETRIEVAL_MODE


class ReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    note: str = ""
    reviewer: str = "reviewer"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "api_key": bool(config.api_key()), "index_ready": vector.index_ready(),
            "text_model": config.TEXT_MODEL, "embed_model": config.EMBED_MODEL, "synthetic_data_only": True}


@app.post("/triage", response_model=TriagePacket)
def post_triage(req: TriageRequest) -> TriagePacket:
    if not vector.ensure_index(llm()):
        raise HTTPException(503, "Retrieval index is not built and cannot be built (no API key?).")
    try:
        return triage(llm(), req.email, req.events, req.claim_id, mode=req.mode)
    except QuotaExhausted as e:
        raise HTTPException(503, f"Model quota or rate limit reached: {e}") from e


@app.post("/review/{packet_id}")
def post_review(packet_id: str, req: ReviewRequest) -> dict:
    try:
        return audit.record_review(packet_id, req.action, req.note, req.reviewer)
    except KeyError:
        raise HTTPException(404, f"packet {packet_id} not found") from None


@app.get("/metrics/summary")
def metrics_summary() -> dict:
    out = {"model_calls": monitoring.summary()}
    res = config.ROOT / "eval" / "results.json"
    if res.exists():
        r = json.loads(res.read_text())
        out["latest_evaluation"] = {"run_id": r["run_id"], "n_claims": len(r["claims"]), "metrics": r["metrics"]}
    return out
