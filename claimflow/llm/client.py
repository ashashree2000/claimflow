"""LLMClient: the single entry point for model calls.

Adds, around any LLMProvider: disk cache, a minimum delay between calls (free tier),
retry with exponential backoff on rate limits, and a monitoring row per call.
"""
from __future__ import annotations

import time

from .. import config, monitoring
from .base import LLMProvider, LLMResult, RateLimitError
from .cache import DiskCache


class QuotaExhausted(Exception):
    """Raised when retries run out; callers show a clear message instead of crashing."""


class LLMClient:
    def __init__(self, provider: LLMProvider | None, text_model: str = config.TEXT_MODEL,
                 embed_model: str = config.EMBED_MODEL, cache: DiskCache | None = None,
                 delay_s: float = config.CALL_DELAY_S, max_retries: int = config.MAX_RETRIES,
                 log_calls: bool = True):
        self.provider = provider
        self.text_model = text_model
        self.embed_model = embed_model
        self.cache = cache or DiskCache(config.CACHE_DIR)
        self.delay_s = delay_s
        self.max_retries = max_retries
        self.log_calls = log_calls
        self._last_call = 0.0
        self.trace: list[dict] = []  # every call this client made (the evaluation reads and resets it)

    # -- internals ---------------------------------------------------------
    def _throttle(self) -> None:
        wait = self.delay_s - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def _with_retry(self, fn):
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                return fn()
            except RateLimitError:
                if attempt == self.max_retries:
                    raise QuotaExhausted("Model API rate limit or quota reached; try again later.")
                time.sleep(min(60, 2 ** (attempt + 2)))  # 4, 8, 16, 32, 60 s

    def _log(self, agent: str, kind: str, model: str, r: LLMResult | None, ok: bool, err: str = "") -> None:
        self.trace.append({"agent": agent, "kind": kind, "ok": ok, "cached": bool(r and r.cached),
                           "latency_ms": r.latency_ms if r else 0.0, "input_tokens": r.input_tokens if r else 0,
                           "output_tokens": r.output_tokens if r else 0})
        if self.log_calls:
            monitoring.log_call(agent=agent, kind=kind, model=model,
                                latency_ms=r.latency_ms if r else 0.0,
                                input_tokens=r.input_tokens if r else 0,
                                output_tokens=r.output_tokens if r else 0,
                                cache_hit=bool(r and r.cached), success=ok, error=err)

    # -- public API --------------------------------------------------------
    def generate(self, prompt: str, system: str | None = None, agent: str = "unknown",
                 json_mode: bool = True, schema: type | None = None) -> LLMResult:
        key = self.cache.key("generate", self.text_model, {"system": system, "prompt": prompt, "json": json_mode,
                                                           "schema": schema.__name__ if schema else None})
        hit = self.cache.get(key)
        if hit is not None:
            r = LLMResult(**{**hit, "cached": True})
            self._log(agent, "generate", self.text_model, r, True)
            return r
        if self.provider is None:
            self._log(agent, "generate", self.text_model, None, False, "no provider (offline, cache miss)")
            raise QuotaExhausted("No API key configured and this input is not in the cache.")
        try:
            r = self._with_retry(lambda: self.provider.generate(prompt, system, self.text_model, json_mode, schema))
        except Exception as e:
            self._log(agent, "generate", self.text_model, None, False, type(e).__name__)
            raise
        self.cache.set(key, {**r.__dict__, "cached": False})
        self._log(agent, "generate", self.text_model, r, True)
        return r

    def embed(self, texts: list[str], agent: str = "retrieval", batch_size: int = 50,
              task_type: str | None = None) -> list[list[float]]:
        """Embed texts; each text is cached on its own, misses are sent in batches."""
        out: list[list[float] | None] = [None] * len(texts)
        todo, cached_ms = [], 0.0
        for i, t in enumerate(texts):
            hit = self.cache.get(self.cache.key("embed", self.embed_model, {"text": t, "task": task_type}))
            if hit is not None:
                vec, ms = (hit["v"], hit.get("ms", 0.0)) if isinstance(hit, dict) else (hit, 0.0)
                out[i] = vec
                cached_ms += ms
            else:
                todo.append(i)
        if todo and self.provider is None:
            raise QuotaExhausted("No API key configured and some embeddings are not in the cache.")
        for s in range(0, len(todo), batch_size):
            idx = todo[s:s + batch_size]
            start = time.perf_counter()
            try:
                vecs = self._with_retry(lambda: self.provider.embed([texts[i] for i in idx], self.embed_model, task_type))
            except Exception as e:
                self._log(agent, "embed", self.embed_model, None, False, type(e).__name__)
                raise
            ms = (time.perf_counter() - start) * 1000
            self._log(agent, "embed", self.embed_model, LLMResult(text="", model=self.embed_model, latency_ms=ms), True)
            for i, v in zip(idx, vecs):
                out[i] = v
                self.cache.set(self.cache.key("embed", self.embed_model, {"text": texts[i], "task": task_type}),
                               {"v": v, "ms": ms / len(idx)})
        if todo == [] and texts:  # all from cache: replay the original latency
            self._log(agent, "embed", self.embed_model,
                      LLMResult(text="", model=self.embed_model, latency_ms=cached_ms, cached=True), True)
        return out  # type: ignore[return-value]


def get_client(**kwargs) -> LLMClient:
    """Gemini client if a key is set; otherwise a cache-only client (works offline from cached results)."""
    key = config.api_key()
    provider = None
    if key:
        from .gemini import GeminiProvider
        provider = GeminiProvider(key)
    return LLMClient(provider, **kwargs)
