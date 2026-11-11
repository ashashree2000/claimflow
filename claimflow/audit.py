"""SQLite audit log: every packet (inputs, outputs, sources, model, time) and every reviewer action."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from . import config
from .guardrails import mask_pii
from .schemas import TriagePacket

SCHEMA = """
CREATE TABLE IF NOT EXISTS packets (
    packet_id TEXT PRIMARY KEY, claim_id TEXT, created_at TEXT, model TEXT, retrieval_mode TEXT,
    input_masked TEXT, packet_json TEXT, sources_json TEXT, needs_human_review INTEGER);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT, packet_id TEXT, action TEXT, note TEXT, reviewer TEXT, ts TEXT,
    FOREIGN KEY (packet_id) REFERENCES packets(packet_id));
"""


def _conn(db=None):
    c = sqlite3.connect(db or config.DB_PATH)
    c.executescript(SCHEMA)
    return c


def save_packet(packet: TriagePacket, raw_input: str, db=None) -> None:
    sources = {
        "policy_clauses": (packet.coverage.retrieved_ids + packet.coverage.expanded_ids) if packet.coverage else [],
        "cited": [c.clause_id for c in packet.coverage.citations] if packet.coverage else [],
        "sops_cited": [f.sop_id for f in packet.process.flags] if packet.process else [],
    }
    with _conn(db) as c:
        c.execute("INSERT OR REPLACE INTO packets VALUES (?,?,?,?,?,?,?,?,?)",
                  (packet.packet_id, packet.claim_id, packet.created_at, packet.model, packet.retrieval_mode,
                   mask_pii(raw_input), mask_pii(packet.model_dump_json()), json.dumps(sources),
                   int(packet.needs_human_review)))


def record_review(packet_id: str, action: str, note: str = "", reviewer: str = "reviewer", db=None) -> dict:
    if action not in ("approve", "reject"):
        raise ValueError("action must be 'approve' or 'reject'")
    with _conn(db) as c:
        if not c.execute("SELECT 1 FROM packets WHERE packet_id = ?", (packet_id,)).fetchone():
            raise KeyError(packet_id)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        c.execute("INSERT INTO reviews (packet_id, action, note, reviewer, ts) VALUES (?,?,?,?,?)",
                  (packet_id, action, mask_pii(note), reviewer, ts))
    return {"packet_id": packet_id, "action": action, "ts": ts}


def list_packets(db=None) -> list[dict]:
    with _conn(db) as c:
        rows = c.execute("""SELECT p.packet_id, p.claim_id, p.created_at, p.model, p.retrieval_mode,
                            p.needs_human_review, r.action, r.note, r.ts FROM packets p
                            LEFT JOIN reviews r ON r.id = (SELECT MAX(id) FROM reviews WHERE packet_id = p.packet_id)
                            ORDER BY p.created_at DESC, p.rowid DESC""").fetchall()
    keys = ["packet_id", "claim_id", "created_at", "model", "retrieval_mode", "needs_human_review",
            "review_action", "review_note", "review_ts"]
    return [dict(zip(keys, r)) for r in rows]


def get_packet(packet_id: str, db=None) -> dict | None:
    with _conn(db) as c:
        row = c.execute("SELECT packet_json, input_masked, sources_json FROM packets WHERE packet_id = ?",
                        (packet_id,)).fetchone()
    if not row:
        return None
    return {"packet": json.loads(row[0]), "input_masked": row[1], "sources": json.loads(row[2])}
