"""Monitoring: latency, tokens per agent, failure rate and cache hit rate of model calls."""
import json

import pandas as pd
import streamlit as st
from common import ROOT, SYNTHETIC_NOTE, load_secrets

load_secrets()
from claimflow import monitoring  # noqa: E402

st.set_page_config(page_title="ClaimFlow - Monitoring", layout="wide")
st.title("Monitoring")
st.caption(SYNTHETIC_NOTE + " Token counts come from the API's usage metadata. No cost figures are shown.")

df = monitoring.calls_df()
if df.empty:
    st.info("No model calls logged in this deployment yet. Live triage runs are logged here; "
            "the evaluation summary below comes from eval/results.json.")
else:
    df["ts"] = pd.to_datetime(df["ts"])
    gen = df[df.kind == "generate"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Model calls logged", len(df))
    c2.metric("Cache hit rate", f"{100 * df.cache_hit.mean():.1f}%")
    c3.metric("Failure rate", f"{100 * (1 - df.success.mean()):.1f}%")
    live = gen[(gen.cache_hit == 0) & (gen.success == 1)]
    c4.metric("Mean live generate latency", f"{live.latency_ms.mean() / 1000:.2f} s" if len(live) else "n/a")
    st.subheader("Latency of live calls over time (ms)")
    lv = df[(df.cache_hit == 0) & (df.success == 1)]
    if len(lv):
        st.line_chart(lv.pivot_table(index="ts", columns="agent", values="latency_ms", aggfunc="mean"))
    st.subheader("Tokens per agent")
    st.bar_chart(gen.groupby("agent")[["input_tokens", "output_tokens"]].sum())
    st.subheader("Cache hit rate and failure rate by hour")
    hourly = df.set_index("ts").resample("h").agg({"cache_hit": "mean", "success": "mean"}).dropna()
    hourly["failure_rate"] = 1 - hourly.pop("success")
    st.line_chart(hourly)

res = ROOT / "eval" / "results.md"
if res.exists():
    st.subheader("Latest evaluation (30 synthetic claims)")
    st.markdown(res.read_text())
    r = json.loads((ROOT / "eval" / "results.json").read_text())
    st.caption(f"Run {r['run_id']}; data fingerprint {r['data_fingerprint']}; code fingerprint {r['code_fingerprint']}.")
