"""Gemini implementation of LLMProvider (google-genai SDK)."""
from __future__ import annotations

import time

from google import genai
from google.genai import errors, types

from .base import LLMResult, RateLimitError

RETRYABLE = {429, 500, 503}


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def generate(self, prompt: str, system: str | None, model: str, json_mode: bool,
                 schema: type | None = None) -> LLMResult:
        """With `schema` (a Pydantic class) the API's structured output enforces the fields; if the API
        rejects the schema, the call falls back to plain JSON mode (the reply is still validated by code)."""
        def config(with_schema: bool):
            return types.GenerateContentConfig(
                system_instruction=system, temperature=0,
                response_mime_type="application/json" if json_mode else None,
                response_schema=schema if (with_schema and schema is not None) else None)

        start = time.perf_counter()
        try:
            try:
                resp = self.client.models.generate_content(model=model, contents=prompt, config=config(True))
            except (errors.ClientError, ValueError, TypeError) as e:
                if schema is None or getattr(e, "code", 400) in RETRYABLE:
                    raise
                resp = self.client.models.generate_content(model=model, contents=prompt, config=config(False))
        except errors.APIError as e:
            if getattr(e, "code", None) in RETRYABLE:
                raise RateLimitError(str(e)) from e
            raise
        latency = (time.perf_counter() - start) * 1000
        usage = resp.usage_metadata
        out_tokens = (getattr(usage, "candidates_token_count", 0) or 0) + (getattr(usage, "thoughts_token_count", 0) or 0)
        return LLMResult(
            text=resp.text or "",
            model=model,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=out_tokens,
            latency_ms=latency,
        )

    def embed(self, texts: list[str], model: str, task_type: str | None = None) -> list[list[float]]:
        config = types.EmbedContentConfig(task_type=task_type) if task_type else None
        try:
            resp = self.client.models.embed_content(model=model, contents=texts, config=config)
        except errors.APIError as e:
            if getattr(e, "code", None) in RETRYABLE:
                raise RateLimitError(str(e)) from e
            raise
        vecs = [list(e.values) for e in resp.embeddings]
        if len(vecs) != len(texts):
            raise ValueError(f"{model} returned {len(vecs)} embeddings for {len(texts)} inputs")
        return vecs
