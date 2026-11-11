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

FLOW = """
<style>
.cf{display:flex;align-items:stretch;gap:6px;flex-wrap:wrap;font-family:inherit;font-size:13px;margin:8px 0 4px}
.cf .b{border:1px solid rgba(128,128,128,.45);border-radius:8px;padding:8px 10px;background:rgba(128,128,128,.08);
       display:flex;flex-direction:column;justify-content:center;min-width:110px}
.cf .b b{font-size:13px}.cf .b span{opacity:.75;font-size:12px}
.cf .a{align-self:center;opacity:.6;font-size:18px}
.cf .col{display:flex;flex-direction:column;gap:6px}
.cf .g{border-style:dashed}.cf .h{background:rgba(46,160,67,.15);border-color:rgba(46,160,67,.6)}
</style>
<div class="cf">
 <div class="b"><b>Claim email</b><span>+ handling history</span></div><div class="a">&rarr;</div>
 <div class="b"><b>Intake agent</b><span>extracts the facts</span></div><div class="a">&rarr;</div>
 <div class="b"><b>Router</b><span>picks the policy type</span></div><div class="a">&rarr;</div>
 <div class="col">
   <div class="b"><b>Coverage agent</b><span>checks policy clauses, using the<br>clause graph to follow references</span></div>
   <div class="b"><b>Process agent</b><span>checks the handling history<br>against the procedures</span></div>
 </div><div class="a">&rarr;</div>
 <div class="b"><b>Recommendation</b><span>with cited clauses</span></div><div class="a">&rarr;</div>
 <div class="b h"><b>Claims handler</b><span>approves or rejects;<br>logged</span></div>
</div>
"""
st.html(FLOW)


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
              help=f"{m['process_flags_predicted'] - m['process_flags_matched']} of the "
                   f"{m['process_flags_predicted']} problems it reported were false alarms.")
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
