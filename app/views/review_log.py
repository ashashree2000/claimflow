import pandas as pd
import streamlit as st
from common import DECISION_TEXT, FOOTER, MODES

from claimflow import audit

st.title("Review log")
st.markdown("Every recommendation opened on the Triage page is recorded here, with the handler's decision. "
            "Phone numbers, email addresses and ID numbers are masked before anything is stored.")

rows = audit.list_packets()
if not rows:
    st.info("Nothing recorded yet. Open **Triage a claim**, run a claim and save a decision; it will appear here.")
    st.caption("This demo keeps the log in a small SQLite file, which is cleared when the hosted app restarts.")
else:
    df = pd.DataFrame([{
        "Time (UTC)": x["created_at"].replace("T", " ")[:16], "Claim": x["claim_id"] or "pasted email",
        "Clause search": MODES.get(x["retrieval_mode"], x["retrieval_mode"]),
        "Needs review": "yes" if x["needs_human_review"] else "no",
        "Handler decision": (x["review_action"] or "pending").capitalize(), "Note": x["review_note"] or "",
        "Record": x["packet_id"]} for x in rows])
    st.dataframe(df, hide_index=True, width="stretch")
    pid = st.selectbox("Open a record", [x["packet_id"] for x in rows],
                       format_func=lambda p: next(f"{x['claim_id'] or 'pasted email'} · {x['created_at'][:16]}"
                                                  for x in rows if x["packet_id"] == p))
    rec = audit.get_packet(pid)
    p = rec["packet"]
    cov = p.get("coverage") or {}
    st.markdown(f"**Recommendation:** {DECISION_TEXT.get(cov.get('decision'), 'none')} · "
                f"**Model:** {p['model']} · **Clauses cited:** {', '.join(rec['sources']['cited']) or 'none'}")
    with st.expander("Stored input (masked)"):
        st.text(rec["input_masked"])
    with st.expander("Full stored record"):
        st.json(p)
st.divider()
st.caption(FOOTER)
