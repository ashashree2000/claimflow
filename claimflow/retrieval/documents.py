"""Parse the policy and SOP Markdown files into clauses with stable IDs."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .. import config

HEAD_RE = re.compile(r"^#{2,3} ((?:MOTOR|PROP|HLTH|SOP)-[A-Z]{3}-\d+(?:\.\d+)?) (.+)$", re.M)
REF_RE = re.compile(r"\b(?:MOTOR|PROP|HLTH)-[A-Z]{3}-\d+(?:\.\d+)?\b")
LOB_PREFIX = {"MOTOR": "motor", "PROP": "property", "HLTH": "health"}


@dataclass
class Clause:
    id: str
    title: str
    text: str
    source: str
    lob: str | None  # None for SOP sections
    parent: str | None = None
    refs: list[str] = field(default_factory=list)

    @property
    def is_section(self) -> bool:
        return "." not in self.id.rsplit("-", 1)[-1]

    def render(self) -> str:
        return f"[{self.id}] {self.title}: {self.text}"


def _parse(path: Path) -> list[Clause]:
    text = path.read_text()
    parts = HEAD_RE.split(text)
    out = []
    for i in range(1, len(parts), 3):
        cid, title, body = parts[i], parts[i + 1].strip(), parts[i + 2].strip()
        lob = LOB_PREFIX.get(cid.split("-")[0])
        last = cid.rsplit("-", 1)[-1]
        parent = cid.rsplit(".", 1)[0] if "." in last and lob else None
        refs = sorted(set(REF_RE.findall(body)) - {cid})
        out.append(Clause(cid, title, " ".join(body.split()), path.name, lob, parent, refs))
    return out


@lru_cache(maxsize=1)
def load_policies() -> dict[str, Clause]:
    return {c.id: c for f in sorted((config.DATA_DIR / "policies").glob("*.md")) for c in _parse(f)}


@lru_cache(maxsize=1)
def load_sops() -> dict[str, Clause]:
    return {c.id: c for f in sorted((config.DATA_DIR / "sops").glob("*.md")) for c in _parse(f)}
