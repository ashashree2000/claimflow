import pandas as pd
import streamlit as st
from common import FOOTER, ROOT

from claimflow import monitoring

st.title("Monitoring")
st.markdown("Every model call is logged with the agent that made it, its latency, the tokens it used (from the API's "
            "usage data), whether it was answered from the cache, and whether it succeeded.")

live = monitoring.calls_df()
saved = ROOT / "eval/model_calls.csv"
options = []
if not live.empty:
    options.append("Calls made by this app")
if saved.exists():
    options.append("Calls made during the evaluation run")
if not options:
    st.info("No calls logged yet.")
    st.stop()
choice = st.radio("Show", options, horizontal=True)
df = live if choice.startswith("Calls made by") else pd.read_csv(saved)
df["ts"] = pd.to_datetime(df["ts"])
df["time"] = df["ts"].dt.floor("min")

gen = df[df.kind == "generate"]
real = df[(df.cache_hit == 0) & (df.success == 1)]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Calls", f"{len(df):,}", f"{len(df) - int(df.cache_hit.sum())} sent to the API", delta_color="off")
c2.metric("Answered from cache", f"{100 * df.cache_hit.mean():.0f}%")
c3.metric("Failed", f"{100 * (1 - df.success.mean()):.1f}%")
rg = real[real.kind == "generate"]
c4.metric("Model latency, median", f"{rg.latency_ms.median() / 1000:.1f} s" if len(rg) else "n/a")

left, right = st.columns(2)
with left:
    st.markdown("**Latency of calls sent to the API (seconds)**")
    if len(real):
        st.line_chart(real.assign(s=real.latency_ms / 1000).pivot_table(index="time", columns="agent", values="s",
                                                                        aggfunc="mean"))
    st.markdown("**Cache hits and failures per minute (share of calls)**")
    per_min = df.groupby("time").agg(cache_hit=("cache_hit", "mean"), success=("success", "mean"))
    per_min["failed"] = 1 - per_min.pop("success")
    st.line_chart(per_min)
with right:
    st.markdown("**Tokens by agent**")
    st.bar_chart(gen.groupby("agent")[["input_tokens", "output_tokens"]].sum(), stack=True)
    st.markdown("**Calls by agent**")
    st.dataframe(df.groupby(["agent", "kind"]).agg(calls=("ts", "count"), cached=("cache_hit", "sum"),
                                                   tokens_in=("input_tokens", "sum"),
                                                   tokens_out=("output_tokens", "sum")).reset_index(),
                 hide_index=True, width="stretch")
st.caption("No costs are shown: the free tier was used, and tokens are reported instead.")
st.divider()
st.caption(FOOTER)
