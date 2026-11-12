"""Model-graded score (1-5) for how well each proposed process fix is written.

Scores every fix in the graph-mode evaluation packets that matched a planted problem. The judge sees the
problem, the handling history, the cited SOP section and the fix. This is MODEL-GRADED: the judge is the same
model family as the agents, so treat the scores as a rough signal, not ground truth.

Run after eval/run_eval.py:  python eval/judge_fixes.py      (about one API call per matched fix)
Writes eval/judge_results.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from claimflow.guardrails import call_validated  # noqa: E402
from claimflow.llm import get_client  # noqa: E402
from claimflow.retrieval import load_sops  # noqa: E402
from eval.metrics import match_flags  # noqa: E402

SYSTEM = "You grade proposed fixes for claims-handling problems. Be strict and consistent. Reply with JSON only."
RUBRIC = """Score the fix from 1 to 5:
5 = names the specific problem in this claim, says exactly what the handler should do, and is fully consistent
    with the cited procedure section.
4 = correct and consistent with the section, but slightly generic or missing one specific detail.
3 = broadly right but vague, or only partly follows the section.
2 = mostly generic advice that would fit any claim, or partly inconsistent with the section.
1 = wrong, irrelevant, or contradicts the section."""


class Grade(BaseModel):
    score: int = Field(ge=1, le=5)
    reason: str


def main() -> None:
    llm = get_client()
    sops = load_sops()
    labels = {json.loads(x)["claim_id"]: json.loads(x) for x in (ROOT / "data/labels.jsonl").read_text().splitlines()}
    rows = []
    for p in sorted((ROOT / "eval/packets/graph").glob("*.json")):
        packet = json.loads(p.read_text())
        cid = packet["claim_id"]
        events = {e["event_id"]: e for e in json.loads((ROOT / f"data/claims/{cid}.json").read_text())["events"]}
        flags = (packet.get("process") or {}).get("flags", [])
        for pred, gold in match_flags(flags, labels[cid]["process_flaws"]):
            history = "\n".join(f"{e['event_id']} | {e['timestamp']} | {e['step']}" for e in events.values())
            sop = sops.get(pred["sop_id"])
            prompt = (f"{RUBRIC}\n\nProblem type: {pred['type']}"
                      f"{' (document: ' + pred['document'] + ')' if pred.get('document') else ''}\n"
                      f"Handling history:\n{history}\n\nCited procedure section {pred['sop_id']}: "
                      f"{sop.text if sop else 'not found'}\n\nProposed fix: {pred['fix']}")
            grade, meta = call_validated(llm, prompt, SYSTEM, Grade, agent="judge")
            rows.append({"claim_id": cid, "type": pred["type"], "sop_id": pred["sop_id"],
                         "sop_correct": pred["sop_id"] == gold["sop_id"], "fix": pred["fix"],
                         "score": grade.score if grade else None, "reason": grade.reason if grade else meta["error"]})
            print(cid, pred["type"], grade.score if grade else "failed", flush=True)
    scored = [r["score"] for r in rows if r["score"] is not None]
    out = {"model_graded": True, "judge_model": llm.text_model, "n_fixes": len(rows), "n_scored": len(scored),
           "mean_score": round(mean(scored), 2) if scored else None,
           "score_counts": {s: scored.count(s) for s in range(1, 6)}, "rows": rows}
    (ROOT / "eval/judge_results.json").write_text(json.dumps(out, indent=2))
    print({k: v for k, v in out.items() if k != "rows"})


if __name__ == "__main__":
    main()
