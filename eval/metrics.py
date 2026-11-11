"""Evaluation metrics. Pure functions over packets (dicts) and gold labels; no API calls."""
from __future__ import annotations

import re
from collections import Counter

import numpy as np

FIELDS = ["claimant_name", "policy_number", "line_of_business", "incident_date", "incident_type", "location",
          "severity", "documents_attached"]


def _n(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def field_correct(name: str, pred, gold) -> bool:
    if name == "documents_attached":
        return sorted(pred or []) == sorted(gold or [])
    if gold in (None, ""):
        return pred in (None, "", "unknown")
    if name == "policy_number":
        return _n(pred).replace(" ", "").upper() == _n(gold).replace(" ", "").upper()
    if name == "location":
        return _n(gold) in _n(pred)
    return _n(pred) == _n(gold)


def match_flags(pred: list[dict], gold: list[dict]) -> list[tuple[dict, dict]]:
    """Pair predicted and gold flaws on (type, document); document only compared when gold has one."""
    pairs, left = [], list(gold)
    for p in pred:
        for g in left:
            if p["type"] == g["type"] and (g.get("document") is None or p.get("document") == g.get("document")):
                pairs.append((p, g))
                left.remove(g)
                break
    return pairs


def claim_row(packet: dict | None, gold: dict) -> dict:
    """Per-claim scores. A missing packet (failure) scores as wrong everywhere."""
    row = {"claim_id": gold["claim_id"], "cross_reference": gold["cross_reference"],
           "should_refuse": gold["should_refuse"], "failed": packet is None}
    g = gold["fields"]
    intake = (packet or {}).get("intake") or {}
    route = (packet or {}).get("route") or {}
    cov = (packet or {}).get("coverage") or {}
    proc = (packet or {}).get("process") or {}
    row["route_ok"] = route.get("line_of_business") == gold["expected_route"]["line_of_business"] and \
        sorted(route.get("specialists", [])) == sorted(gold["expected_route"]["specialists"])
    row["fields"] = {f: bool(intake) and field_correct(f, intake.get(f), g[f]) for f in FIELDS}
    row["decision"] = cov.get("decision")
    row["gold_decision"] = gold["coverage"]["decision"]
    row["decision_ok"] = cov.get("decision") == gold["coverage"]["decision"]
    cited = {c["clause_id"] for c in cov.get("citations", [])}
    req, ok = set(gold["coverage"]["required_clause_ids"]), set(gold["coverage"]["acceptable_clause_ids"])
    row["cited"] = sorted(cited)
    row["citation_recall"] = len(cited & req) / len(req) if req else None
    row["citation_precision"] = len(cited & (req | ok)) / len(cited) if (req and cited) else None
    ctx = set(cov.get("retrieved_ids", [])) | set(cov.get("expanded_ids", []))
    row["context_recall"] = len(ctx & req) / len(req) if req else None
    row["context_size"] = len(ctx)
    pred_flags = proc.get("flags", [])
    pairs = match_flags(pred_flags, gold["process_flaws"])
    row["flags_pred"], row["flags_gold"], row["flags_matched"] = len(pred_flags), len(gold["process_flaws"]), len(pairs)
    row["flags_sop_ok"] = sum(p["sop_id"] == g["sop_id"] for p, g in pairs)
    row["needs_human_review"] = (packet or {}).get("needs_human_review")
    return row


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(float(np.mean(xs)), 3) if xs else None


def aggregate(rows: list[dict], usage: list[dict]) -> dict:
    """Mode-level metrics. `usage` has per-claim latency/token totals."""
    def acc(sub, key):
        return _mean([float(r[key]) for r in sub]) if sub else None
    xref = [r for r in rows if r["cross_reference"]]
    other = [r for r in rows if not r["cross_reference"] and not r["should_refuse"]]
    refuse = [r for r in rows if r["should_refuse"]]
    not_refuse = [r for r in rows if not r["should_refuse"]]
    per_field = {f: _mean([float(r["fields"][f]) for r in rows]) for f in FIELDS}
    fp = sum(r["flags_pred"] for r in rows)
    fg = sum(r["flags_gold"] for r in rows)
    fm = sum(r["flags_matched"] for r in rows)
    lat = [u["latency_ms"] for u in usage]
    tok = [u["input_tokens"] + u["output_tokens"] for u in usage]
    calls = [c for u in usage for c in u["calls"]]
    return {
        "n_claims": len(rows), "n_failed": sum(r["failed"] for r in rows),
        "routing_accuracy": acc(rows, "route_ok"),
        "field_accuracy_mean": _mean(list(per_field.values())), "field_accuracy": per_field,
        "coverage_accuracy": acc(rows, "decision_ok"),
        "coverage_accuracy_cross_reference": acc(xref, "decision_ok"), "n_cross_reference": len(xref),
        "coverage_accuracy_other_decidable": acc(other, "decision_ok"), "n_other_decidable": len(other),
        "citation_precision": _mean([r["citation_precision"] for r in rows]),
        "citation_recall": _mean([r["citation_recall"] for r in rows]),
        "citation_recall_cross_reference": _mean([r["citation_recall"] for r in xref]),
        "context_recall": _mean([r["context_recall"] for r in rows]),
        "context_recall_cross_reference": _mean([r["context_recall"] for r in xref]),
        "mean_context_size": _mean([r["context_size"] for r in rows]),
        "process_flag_precision": round(fm / fp, 3) if fp else None,
        "process_flag_recall": round(fm / fg, 3) if fg else None,
        "process_fix_sop_correct": round(sum(r["flags_sop_ok"] for r in rows) / fm, 3) if fm else None,
        "process_flags_predicted": fp, "process_flags_gold": fg, "process_flags_matched": fm,
        "false_flags_on_clean_claims": sum(r["flags_pred"] for r in rows if r["flags_gold"] == 0),
        "refusal_correct": f"{sum(r['decision_ok'] for r in refuse)}/{len(refuse)}",
        "false_refusals": f"{sum(r['decision'] == 'needs_review' for r in not_refuse)}/{len(not_refuse)}",
        "latency_ms_mean_per_claim": _mean(lat),
        "latency_ms_p95_per_claim": round(float(np.percentile(lat, 95)), 1) if lat else None,
        "tokens_mean_per_claim": _mean(tok),
        "model_calls_mean_per_claim": _mean([len(u["calls"]) for u in usage]),
        "cache_hit_rate_this_run": round(sum(c["cached"] for c in calls) / len(calls), 3) if calls else None,
        "decision_confusion_gold_to_pred": dict(Counter(f"{r['gold_decision']}->{r['decision']}" for r in rows)),
    }
