"""Milestone 4 check: run the full pipeline on a few claims and save the packets to eval/samples/.

Usage: python scripts/run_samples.py C07 C14 C30 [--mode graph|vector]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from claimflow.agents import triage  # noqa: E402
from claimflow.llm import get_client  # noqa: E402
from claimflow.schemas import ClaimEmail, ClaimEvent  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("claims", nargs="+")
ap.add_argument("--mode", default="graph", choices=["graph", "vector"])
args = ap.parse_args()

llm = get_client()
out_dir = ROOT / "eval/samples"
out_dir.mkdir(parents=True, exist_ok=True)
labels = {json.loads(x)["claim_id"]: json.loads(x) for x in (ROOT / "data/labels.jsonl").read_text().splitlines()}
for cid in args.claims:
    c = json.loads((ROOT / f"data/claims/{cid}.json").read_text())
    p = triage(llm, ClaimEmail(**c["email"]), [ClaimEvent(**e) for e in c["events"]], cid, mode=args.mode)
    (out_dir / f"{cid}_{args.mode}.json").write_text(p.model_dump_json(indent=2))
    gold = labels[cid]
    print(f"\n== {cid} ({args.mode}) packet {p.packet_id}")
    print(" route:", p.route.line_of_business, "|", p.route.reason)
    print(" coverage:", p.coverage.decision if p.coverage else None, "| gold:", gold["coverage"]["decision"])
    print(" cited:", [x.clause_id for x in p.coverage.citations] if p.coverage else None,
          "| gold:", gold["coverage"]["required_clause_ids"])
    print(" flags:", [(f.type, f.document, f.sop_id) for f in p.process.flags] if p.process else None)
    print(" gold flags:", [(f["type"], f.get("document"), f["sop_id"]) for f in gold["process_flaws"]])
    print(" confidence:", p.confidence, "| needs_human_review:", p.needs_human_review, "| errors:", p.errors)
    print(" reasons:", p.reasons)
