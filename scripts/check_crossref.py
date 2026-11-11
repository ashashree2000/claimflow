"""Retrieval check (milestone 3): does vector top-k find the gold clauses, and does graph expansion add the missing ones?

Query = the claim email body (the pipeline later queries with the intake agent's description).
Writes eval/retrieval_check.json. Uses 1 embedding call for the 30 claims (cached afterwards).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from claimflow import config  # noqa: E402
from claimflow.llm import get_client  # noqa: E402
from claimflow.retrieval import graph, vector  # noqa: E402


def main() -> None:
    llm = get_client()
    labels = [json.loads(x) for x in (ROOT / "data/labels.jsonl").read_text().splitlines()]
    bodies = {lab["claim_id"]: json.loads((ROOT / f"data/claims/{lab['claim_id']}.json").read_text())["email"]["body"]
              for lab in labels}
    llm.embed(list(bodies.values()), agent="retrieval_check", task_type="RETRIEVAL_QUERY")  # one batched call; search() then hits the cache
    g = graph.build_graph()
    rows = []
    for lab in labels:
        gold = set(lab["coverage"]["required_clause_ids"])
        if not gold:
            continue
        hits = vector.search(llm, bodies[lab["claim_id"]], lab["line_of_business"], k=config.TOP_K)
        vec_ids = [h[0] for h in hits]
        graph_ids = vec_ids + [a["id"] for a in graph.expand(g, vec_ids)]
        wide_ids = [h[0] for h in vector.search(llm, bodies[lab["claim_id"]], lab["line_of_business"], k=len(graph_ids))]
        rows.append({
            "claim_id": lab["claim_id"], "cross_reference": lab["cross_reference"], "gold": sorted(gold),
            "vector_top_k": vec_ids,
            "vector_recall": round(len(gold & set(vec_ids)) / len(gold), 3),
            "graph_recall": round(len(gold & set(graph_ids)) / len(gold), 3),
            "vector_same_size_recall": round(len(gold & set(wide_ids)) / len(gold), 3),
            "graph_context_size": len(graph_ids),
            "missing_after_graph": sorted(gold - set(graph_ids)),
        })
    out = {"top_k": config.TOP_K, "hops": config.GRAPH_HOPS, "embed_model": llm.embed_model, "rows": rows}
    for name, sub in (("all", rows), ("cross_reference", [r for r in rows if r["cross_reference"]]),
                      ("other", [r for r in rows if not r["cross_reference"]])):
        if sub:
            out[f"mean_vector_recall_{name}"] = round(sum(r["vector_recall"] for r in sub) / len(sub), 3)
            out[f"mean_graph_recall_{name}"] = round(sum(r["graph_recall"] for r in sub) / len(sub), 3)
            out[f"full_recall_vector_{name}"] = sum(r["vector_recall"] == 1 for r in sub)
            out[f"full_recall_graph_{name}"] = sum(r["graph_recall"] == 1 for r in sub)
            out[f"mean_vector_same_size_recall_{name}"] = round(sum(r["vector_same_size_recall"] for r in sub) / len(sub), 3)
            out[f"full_recall_vector_same_size_{name}"] = sum(r["vector_same_size_recall"] == 1 for r in sub)
            out[f"n_{name}"] = len(sub)
    (ROOT / "eval").mkdir(exist_ok=True)
    (ROOT / "eval/retrieval_check.json").write_text(json.dumps(out, indent=2))
    print(f"{'claim':6} {'xref':5} {'vec':>5} {'graph':>6} {'vecN':>5} ctx  missing_after_graph")
    for r in rows:
        print(f"{r['claim_id']:6} {str(r['cross_reference']):5} {r['vector_recall']:>5} {r['graph_recall']:>6} {r['vector_same_size_recall']:>5} "
              f"{r['graph_context_size']:>3}  {','.join(r['missing_after_graph'])}")
    print({k: v for k, v in out.items() if k != "rows"})


if __name__ == "__main__":
    main()
