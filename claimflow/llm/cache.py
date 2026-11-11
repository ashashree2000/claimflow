"""Disk cache keyed on (kind, model, exact input). Repeated runs and evaluations never re-call the API."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class DiskCache:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(kind: str, model: str, payload: object) -> str:
        raw = json.dumps({"kind": kind, "model": model, "payload": payload}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self.folder / key[:2] / f"{key}.json"

    def get(self, key: str):
        p = self._path(key)
        return json.loads(p.read_text()) if p.exists() else None

    def set(self, key: str, value: object) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, ensure_ascii=False))
