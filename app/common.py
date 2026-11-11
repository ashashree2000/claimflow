"""Shared setup for the Streamlit pages."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_secrets() -> None:
    """On Streamlit Community Cloud the key comes from the app's Secrets; locally from .env."""
    try:
        import streamlit as st
        if "GEMINI_API_KEY" in st.secrets and not os.getenv("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass


SYNTHETIC_NOTE = ("All data in this app is **synthetic**: invented claimants, policies, insurer (Northwind Mutual) "
                  "and events. Built for a portfolio demonstration.")
