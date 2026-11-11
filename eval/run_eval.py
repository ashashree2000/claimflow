"""Run every claim through the pipeline in each retrieval mode and score it against data/labels.jsonl.

  python eval/run_eval.py --pilot                 # 5 claims, all modes (check prompts before the full run)
  python eval/run_eval.py                         # all 30 claims, modes: vector, vector_wide, graph
  python eval/run_eval.py --claims C01 C02 --modes graph

Free-tier friendly: every model call goes through the disk cache, so re-running (or resuming after a quota
stop) only calls the API for what is missing. Intake and process prompts do not depend on the retrieval
mode, so they are called once per claim and replayed from the cache for the other modes.

Latency = the sum of model-call latencies for one claim, as measured when each call was made live
(a cached replay reports the latency of its original call). Throttling sleeps are excluded.
Outputs: eval/results.json, eval/results.md, eval/packets/<mode>/<claim>.json, a line in eval/runs.jsonl.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from claimflow import config, monitoring  # noqa: E402
from claimflow.agents import triage  # noqa: E402
from claimflow.llm import QuotaExhausted, get_client  # noqa: E402
from claimflow.schemas import ClaimEmail, ClaimEvent  # noqa: E402
from eval.metrics import aggregate, claim_row  # noqa: E402

PILOT = ["C09", "C12", "C18", "C20", "C28"]
MODES = ["vector", "vector_wide", "graph"]
TABLE = [  # (label, key, format)
    ("Routing accuracy", "routing_accuracy", "pct"),
    ("Field-extraction accuracy (mean of 8 fields)", "field_accuracy_mean", "pct"),
    ("Coverage-decision accuracy (all)", "coverage_accuracy", "pct"),
    ("Coverage-decision accuracy (cross-reference subset)", "coverage_accuracy_cross_reference", "pct"),
    ("Coverage-decision accuracy (other decidable claims)", "coverage_accuracy_other_decidable", "pct"),
    ("Citation precision", "citation_precision", "pct"),
    ("Citation recall", "citation_recall", "pct"),
    ("Citation recall (cross-reference subset)", "citation_recall_cross_reference", "pct"),
    ("Gold clauses in context (recall)", "context_recall", "pct"),
    ("Gold clauses in context (cross-reference subset)", "context_recall_cross_reference", "pct"),
    ("Mean clauses in context", "mean_context_size", "num"),
    ("Process-flaw precision", "process_flag_precision", "pct"),
    ("Process-flaw recall", "process_flag_recall", "pct"),
    ("Fix cites the correct SOP section", "process_fix_sop_correct", "pct"),
    ("False flags on the 6 clean claims", "false_flags_on_clean_claims", "num"),
    ("Refusal correct (should be needs_review)", "refusal_correct", "str"),
    ("False refusals (needs_review on decidable claims)", "false_refusals", "str"),
    ("Model latency per claim, mean (s)", "latency_ms_mean_per_claim", "sec"),
    ("Model latency per claim, p95 (s)", "latency_ms_p95_per_claim", "sec"),
    ("Tokens per claim, mean (input+output)", "tokens_mean_per_claim", "num"),
    ("Model calls per claim, mean", "model_calls_mean_per_claim", "num"),
    ("Cache hit rate in this run", "cache_hit_rate_this_run", "pct"),
    ("Failed claims", "n_failed", "num"),
]


def _fmt(v, kind):
    if v is None:
        return "n/a"
    if kind == "pct":
        return f"{100 * v:.1f}%"
    if kind == "sec":
        return f"{v / 1000:.2f}"
    return str(v)


def _sha(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", nargs="*")
    ap.add_argument("--modes", nargs="*", default=MODES)
    ap.add_argument("--pilot", action="store_true")
    args = ap.parse_args()

    labels = {json.loads(x)["claim_id"]: json.loads(x) for x in (ROOT / "data/labels.jsonl").read_text().splitlines()}
    claim_ids = PILOT if args.pilot else (args.claims or sorted(labels))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ("_pilot" if args.pilot else "")
    monitoring.RUN_ID = run_id
    llm = get_client()

    rows = {m: [] for m in args.modes}
    usage = {m: [] for m in args.modes}
    failures, stopped = [], None
    for cid in claim_ids:
        c = json.loads((ROOT / f"data/claims/{cid}.json").read_text())
        email, events = ClaimEmail(**c["email"]), [ClaimEvent(**e) for e in c["events"]]
        for mode in args.modes:
            if stopped:
                break
            llm.trace = []
            packet = None
            try:
                p = triage(llm, email, events, cid, mode=mode, save=False)
                packet = json.loads(p.model_dump_json())
                out = ROOT / f"eval/packets/{mode}/{cid}.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(p.model_dump_json(indent=2))
            except QuotaExhausted as e:
                stopped = f"stopped at {cid}/{mode}: {e}"
                failures.append({"claim_id": cid, "mode": mode, "error": str(e)})
            except Exception as e:  # record and continue
                failures.append({"claim_id": cid, "mode": mode, "error": f"{type(e).__name__}: {e}"})
            if stopped:
                break
            rows[mode].append(claim_row(packet, labels[cid]))
            usage[mode].append({"claim_id": cid, "calls": llm.trace,
                                "latency_ms": sum(t["latency_ms"] for t in llm.trace),
                                "input_tokens": sum(t["input_tokens"] for t in llm.trace),
                                "output_tokens": sum(t["output_tokens"] for t in llm.trace)})
            live = sum(not t["cached"] for t in llm.trace)
            r = rows[mode][-1]
            print(f"{cid} {mode:11} decision={r['decision']} (gold {labels[cid]['coverage']['decision']}) "
                  f"cited={r['cited']} flags={r['flags_matched']}/{r['flags_gold']} pred={r['flags_pred']} "
                  f"live_calls={live}", flush=True)
        if stopped:
            print("QUOTA:", stopped)
            break

    results = {
        "run_id": run_id, "synthetic_data": True, "incomplete": stopped,
        "claims": claim_ids, "modes": args.modes,
        "text_model": llm.text_model, "embed_model": llm.embed_model,
        "config": {"top_k": config.TOP_K, "graph_hops": config.GRAPH_HOPS,
                   "call_delay_s": config.CALL_DELAY_S},
        "data_fingerprint": _sha([ROOT / "data/labels.jsonl", *(ROOT / "data/policies").glob("*.md"),
                                  *(ROOT / "data/sops").glob("*.md"), *(ROOT / "data/claims").glob("*.json")]),
        "code_fingerprint": _sha(list((ROOT / "claimflow").rglob("*.py"))),
        "metrics": {m: aggregate(rows[m], usage[m]) for m in args.modes if rows[m]},
        "failures": failures,
        "rows": rows,
    }
    name = "results_pilot" if args.pilot else "results"
    (ROOT / f"eval/{name}.json").write_text(json.dumps(results, indent=2))
    modes = [m for m in args.modes if rows[m]]
    md = [f"Run `{run_id}` on {len(claim_ids)} synthetic claims; text model `{llm.text_model}`, "
          f"embeddings `{llm.embed_model}`; top-k {config.TOP_K}, graph hops {config.GRAPH_HOPS}, "
          "vector_wide uses the same number of clauses as graph mode for each claim.", "",
          "| Metric | " + " | ".join(modes) + " |", "|---|" + "---|" * len(modes)]
    for label, key, kind in TABLE:
        md.append(f"| {label} | " + " | ".join(_fmt(results["metrics"][m][key], kind) for m in modes) + " |")
    if stopped:
        md.append(f"\n**Incomplete run:** {stopped}")
    (ROOT / f"eval/{name}.md").write_text("\n".join(md) + "\n")
    with open(ROOT / "eval/runs.jsonl", "a") as f:
        f.write(json.dumps({k: results[k] for k in ("run_id", "incomplete", "text_model", "embed_model", "config",
                                                    "data_fingerprint", "code_fingerprint")}
                           | {"n_claims": len(claim_ids), "metrics": results["metrics"]}) + "\n")
    print("\n" + "\n".join(md))
    if failures:
        print("\nFailures:", json.dumps(failures, indent=1))


if __name__ == "__main__":
    main()
