import pandas as pd
import streamlit as st
from common import DECISION_TEXT, FOOTER, MODES, claim_title, labels, results

st.title("Evaluation")
r = results()
if not r:
    st.info("No evaluation results found. Run `python eval/run_eval.py`.")
    st.stop()

st.markdown(
    "Every claim in the test set has a known answer: the right recommendation, the clauses that support it, and "
    "the handling problems hidden in its history. Each claim was run through the full system once with each way "
    "of finding policy clauses, and the answers were scored automatically."
)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Test claims", "30", "10 motor, 10 home, 10 health", delta_color="off")
c2.metric("Need a cross-reference", "8", "e.g. an exclusion changed by an endorsement", delta_color="off")
c3.metric("Should go to a handler", "3", "unclear or conflicting facts", delta_color="off")
c4.metric("Hidden handling problems", "28", "6 claims have none", delta_color="off")

modes = [m for m in ("graph", "vector_wide", "vector") if m in r["metrics"]]
M = r["metrics"]


def pct(x):
    return "n/a" if x is None else f"{100 * x:.0f}%"


rows = [
    ("Coverage recommendation correct (30 claims)", lambda m: pct(M[m]["coverage_accuracy"])),
    ("... on the 8 claims that need a cross-reference", lambda m: pct(M[m]["coverage_accuracy_cross_reference"])),
    ("... on the other 19 decidable claims", lambda m: pct(M[m]["coverage_accuracy_other_decidable"])),
    ("Required clauses cited (recall)", lambda m: pct(M[m]["citation_recall"])),
    ("Cited clauses that are relevant (precision)", lambda m: pct(M[m]["citation_precision"])),
    ("Required clauses shown to the agent", lambda m: pct(M[m]["context_recall"])),
    ("Clauses shown to the agent, average", lambda m: f"{M[m]['mean_context_size']:.1f}"),
    ("Decidable claims wrongly referred to a handler", lambda m: M[m]["false_refusals"]),
    ("Claims correctly referred to a handler", lambda m: M[m]["refusal_correct"]),
    ("Model time per claim, average / 95th percentile",
     lambda m: f"{M[m]['latency_ms_mean_per_claim'] / 1000:.1f} s / {M[m]['latency_ms_p95_per_claim'] / 1000:.1f} s"),
    ("Tokens per claim, average", lambda m: f"{M[m]['tokens_mean_per_claim']:,.0f}"),
]
st.subheader("Policy coverage: three ways of finding clauses")
st.dataframe(pd.DataFrame({"": [x[0] for x in rows]} | {MODES[m]: [x[1](m) for x in rows] for m in modes}),
             hide_index=True, width="stretch")

g = M["graph"]
st.subheader("Parts that do not depend on clause search")
st.dataframe(pd.DataFrame({"": ["Policy type routed correctly", "Claim details extracted correctly (8 fields)",
                                "Handling problems found (recall)", "Flags that were real problems (precision)",
                                "Fix cites the right procedure section", "False alarms on the 6 clean claims"],
                           "Result": [pct(g["routing_accuracy"]), pct(g["field_accuracy_mean"]),
                                      f"{g['process_flags_matched']} of {g['process_flags_gold']}",
                                      f"{g['process_flags_matched']} of {g['process_flags_predicted']}",
                                      pct(g["process_fix_sop_correct"]), str(g["false_flags_on_clean_claims"])]}),
             hide_index=True, width="stretch")

st.subheader("What the numbers say")
st.markdown(
    "- Following cross-references helped most where it was designed to: 7 of the 8 cross-reference claims were "
    "right with the policy graph, against 5 when plain search was given the same number of clauses, and 4 with "
    "5 clauses. The test set is small, so this is a difference of two or three claims.\n"
    "- Most mistakes are cautious ones: a decidable claim sent to a handler rather than a wrong approval. "
    "The system refers a claim whenever it cannot back its answer with a verified quote.\n"
    "- One claim that should have been referred (wall cracks after a neighbour's excavation) was answered "
    "'not covered' by every method."
)

st.subheader("Claim by claim")
lab = labels()
table = []
for cid in r["claims"]:
    row = {"Claim": claim_title(cid), "Expected": DECISION_TEXT[lab[cid]["coverage"]["decision"]]}
    for m in modes:
        x = next(y for y in r["rows"][m] if y["claim_id"] == cid)
        row[MODES[m]] = ("✓ " if x["decision_ok"] else "✗ ") + DECISION_TEXT.get(x["decision"], "failed")
    row["Needs cross-reference"] = "yes" if lab[cid]["cross_reference"] else ""
    table.append(row)
st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch", height=600)
st.caption(f"Run {r['run_id']} · model {r['text_model']} · embeddings {r['embed_model']} · "
           f"{r['config']['top_k']} similar clauses, graph followed up to {r['config']['graph_hops']} references deep.")
st.divider()
st.caption(FOOTER)
