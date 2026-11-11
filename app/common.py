"""Shared helpers for the Streamlit pages."""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODES = {
    "graph": "Policy graph",
    "vector": "Similarity search",
    "vector_wide": "Similarity search, same size as graph",
}
MODE_HELP = ("**Policy graph**: the 5 most similar clauses, plus the clauses they refer to (exclusions, endorsements, "
             "definitions). **Similarity search**: only the 5 most similar clauses. **Same size as graph**: as many "
             "similar clauses as the graph method would use, to check whether the graph helps beyond adding text.")
DECISION_TEXT = {"covered": "Covered", "not_covered": "Not covered", "needs_review": "Refer to a handler"}
LOB_TEXT = {"motor": "Motor", "property": "Home", "health": "Health", "unknown": "Unknown"}


def load_secrets() -> None:
    """On Streamlit Community Cloud the key comes from the app's Secrets; locally from .env."""
    try:
        import streamlit as st
        if "GEMINI_API_KEY" in st.secrets and not os.getenv("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass


@lru_cache(maxsize=1)
def claims() -> dict:
    return {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "data/claims").glob("*.json"))}


@lru_cache(maxsize=1)
def labels() -> dict:
    return {json.loads(x)["claim_id"]: json.loads(x) for x in (ROOT / "data/labels.jsonl").read_text().splitlines()}


@lru_cache(maxsize=1)
def results() -> dict | None:
    p = ROOT / "eval/results.json"
    return json.loads(p.read_text()) if p.exists() else None


def claim_title(cid: str) -> str:
    f = labels()[cid]["fields"]
    what = f["incident_type"].replace("_", " ") if f["incident_type"] != "other" else "unclear incident"
    where = f" · {f['location']}" if f["location"] else ""
    return f"{cid} · {LOB_TEXT[f['line_of_business']]} · {what}{where}"


def correct_counts(mode: str) -> tuple[int, int]:
    rows = results()["rows"][mode]
    return sum(r["decision_ok"] for r in rows), len(rows)


FOOTER = ("Claims, people, policies and the insurer (Northwind Mutual) are fictional. "
          "Source code: [github.com/ashashree2000/claimflow](https://github.com/ashashree2000/claimflow)")
