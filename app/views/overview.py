import streamlit as st
from common import FOOTER, correct_counts, results

st.title("ClaimFlow")
st.markdown("#### Triage of insurance claim emails against the policy wording and the claims procedures")

st.markdown(
    "When a customer reports a loss, a claims handler has to read the email, pull out the facts, check the "
    "policy wording (including the exclusions and endorsements that clauses refer to), and check that the claim "
    "has been handled by the book. ClaimFlow does this first pass with a set of small AI agents and hands the "
    "handler a recommendation with the exact clauses and procedure sections it relies on. The handler approves "
    "or rejects it, and every decision is logged."
)

st.graphviz_chart("""
digraph {
  rankdir=LR; bgcolor="transparent";
  node [shape=box style="rounded,filled" fillcolor="#eef2f7" color="#8aa0b8" fontname="Helvetica" fontsize=11];
  edge [color="#8aa0b8"];
  email [label="Claim email\\n+ handling history"];
  intake [label="Intake agent\\nextracts the facts"];
  router [label="Router\\npicks the policy type"];
  cov [label="Coverage agent\\nchecks policy clauses"];
  proc [label="Process agent\\nchecks the procedures"];
  graph [label="Policy clause graph\\n(follows cross-references)" fillcolor="#fff6e5"];
  sup [label="Recommendation\\nwith citations"];
  human [label="Claims handler\\napproves or rejects" fillcolor="#e8f5e9"];
  log [label="Review log" shape=cylinder];
  email -> intake -> router; router -> cov; router -> proc; graph -> cov;
  cov -> sup; proc -> sup; sup -> human -> log;
}
""")

r = results()
if r:
    st.subheader("How well it works")
    g, n = correct_counts("graph")
    v, _ = correct_counts("vector")
    xr = [x for x in r["rows"]["graph"] if x["cross_reference"]]
    xg = sum(x["decision_ok"] for x in xr)
    xv = sum(x["decision_ok"] for x in r["rows"]["vector"] if x["cross_reference"])
    m = r["metrics"]["graph"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Coverage decisions correct", f"{g} of {n}", f"{g - v:+d} vs similarity search only")
    c2.metric("Claims that need a cross-reference", f"{xg} of {len(xr)}", f"{xg - xv:+d} vs similarity search only")
    c3.metric("Handling problems found", f"{m['process_flags_matched']} of {m['process_flags_gold']}",
              f"{m['process_flags_predicted'] - m['process_flags_matched']} false alarms", delta_color="off")
    st.caption(f"Measured on {n} test claims with known answers. The Evaluation page has the full results.")

st.subheader("Try it")
st.markdown(
    "1. Open **Triage a claim**, pick one of the 30 test claims and press **Run**.\n"
    "2. Read the recommendation, the policy clauses behind it and any handling problems found.\n"
    "3. Approve or reject it. Your decision appears in the **Review log**.\n\n"
    "Results are stored, so the claims open instantly. Switch on **Run live** to call the model again."
)

st.subheader("What it is built with")
st.markdown(
    "- **Model:** Google Gemini 3.5 Flash-Lite for the agents, Gemini embeddings for search (free tier).\n"
    "- **Retrieval:** Chroma vector store, plus a NetworkX graph of the cross-references between clauses.\n"
    "- **Checks:** every model answer is validated; a citation is kept only if its quote is really in the clause; "
    "if nothing supports a decision, the claim is referred to a handler.\n"
    "- **Service:** FastAPI, SQLite review log and call monitoring, Streamlit, pytest, GitHub Actions, Docker."
)
st.divider()
st.caption(FOOTER)
