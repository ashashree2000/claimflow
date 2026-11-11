"""Audit log: every packet shown in the app and every reviewer decision."""
import pandas as pd
import streamlit as st
from common import SYNTHETIC_NOTE, load_secrets

load_secrets()
from claimflow import audit  # noqa: E402

st.set_page_config(page_title="ClaimFlow - Audit log", layout="wide")
st.title("Audit log")
st.caption(SYNTHETIC_NOTE + " Inputs are stored with phone numbers, emails and ID-like strings masked.")
rows = audit.list_packets()
if not rows:
    st.info("No packets yet. Run a triage first.")
else:
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    pid = st.selectbox("Open packet", [r["packet_id"] for r in rows])
    rec = audit.get_packet(pid)
    st.subheader("Masked input")
    st.code(rec["input_masked"])
    st.subheader("Sources")
    st.json(rec["sources"])
    with st.expander("Full packet (masked)"):
        st.json(rec["packet"])
