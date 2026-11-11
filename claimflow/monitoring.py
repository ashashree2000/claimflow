"""Per-call monitoring log in SQLite: agent, model, latency, tokens, cache hit, success."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pandas as pd

from . import config

SCHEMA = """CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL, run_id TEXT, agent TEXT, kind TEXT, model TEXT,
    latency_ms REAL, input_tokens INTEGER, output_tokens INTEGER,
    cache_hit INTEGER, success INTEGER, error TEXT)"""

RUN_ID: str | None = None  # set by the evaluation so calls can be grouped per run


def _conn():
    c = sqlite3.connect(config.DB_PATH)
    c.execute(SCHEMA)
    return c


def log_call(agent: str, kind: str, model: str, latency_ms: float, input_tokens: int, output_tokens: int,
             cache_hit: bool, success: bool, error: str = "") -> None:
    with _conn() as c:
        c.execute("INSERT INTO llm_calls (ts, run_id, agent, kind, model, latency_ms, input_tokens, output_tokens,"
                  " cache_hit, success, error) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  (datetime.now(timezone.utc).isoformat(timespec="seconds"), RUN_ID, agent, kind, model,
                   latency_ms, input_tokens, output_tokens, int(cache_hit), int(success), error))


def calls_df(run_id: str | None = None) -> pd.DataFrame:
    with _conn() as c:
        q, args = "SELECT * FROM llm_calls", ()
        if run_id:
            q, args = q + " WHERE run_id = ?", (run_id,)
        return pd.read_sql_query(q, c, params=args)


def summary(run_id: str | None = None) -> dict:
    df = calls_df(run_id)
    if df.empty:
        return {"calls": 0}
    live = df[(df.cache_hit == 0) & (df.success == 1)]
    return {
        "calls": int(len(df)),
        "api_calls": int(len(df[df.cache_hit == 0])),
        "cache_hit_rate": round(float(df.cache_hit.mean()), 3),
        "failure_rate": round(float(1 - df.success.mean()), 3),
        "latency_ms_mean_live": round(float(live.latency_ms.mean()), 1) if len(live) else None,
        "input_tokens": int(df.input_tokens.sum()),
        "output_tokens": int(df.output_tokens.sum()),
        "by_agent": df.groupby("agent").agg(calls=("id", "count"), input_tokens=("input_tokens", "sum"),
                                            output_tokens=("output_tokens", "sum")).to_dict("index"),
    }
