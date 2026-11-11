"""Provider-neutral interface for model calls. Every agent talks to this, never to an SDK."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False


class LLMProvider(Protocol):
    """A provider makes raw calls. Caching, retries, throttling and logging live in LLMClient."""

    name: str

    def generate(self, prompt: str, system: str | None, model: str, json_mode: bool,
                 schema: type | None = None) -> LLMResult: ...

    def embed(self, texts: list[str], model: str, task_type: str | None = None) -> list[list[float]]: ...


class RateLimitError(Exception):
    """Raised by a provider when the API says to slow down (HTTP 429) or is briefly unavailable."""
