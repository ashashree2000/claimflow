"""ClaimFlow Streamlit app. Run: streamlit run app/streamlit_app.py"""
import streamlit as st
from common import load_secrets

load_secrets()
st.set_page_config(page_title="ClaimFlow", page_icon=":material/fact_check:", layout="wide")

pages = [
    st.Page("views/overview.py", title="Overview", icon=":material/home:", default=True),
    st.Page("views/triage.py", title="Triage a claim", icon=":material/fact_check:"),
    st.Page("views/evaluation.py", title="Evaluation", icon=":material/analytics:"),
    st.Page("views/review_log.py", title="Review log", icon=":material/history:"),
    st.Page("views/monitoring.py", title="Monitoring", icon=":material/monitoring:"),
]
st.navigation(pages).run()
