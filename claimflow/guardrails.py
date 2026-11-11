"""Guardrails: schema validation with one retry, citation checks, refusal, PII masking."""
from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .llm import LLMClient

T = TypeVar("T", bound=BaseModel)


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    return t


def parse_model(text: str, model: type[T]) -> tuple[T | None, str]:
    try:
        return model.model_validate(json.loads(_strip_fences(text))), ""
    except (json.JSONDecodeError, ValidationError) as e:
        return None, str(e)[:800]


def call_validated(llm: LLMClient, prompt: str, system: str, model: type[T], agent: str) -> tuple[T | None, dict]:
    """Call the model, validate against `model`; on failure retry once with the error; then fail safely (None)."""
    r = llm.generate(prompt, system=system, agent=agent, schema=model)
    obj, err = parse_model(r.text, model)
    meta = {"retried": False, "error": ""}
    if obj is not None:
        return obj, meta
    meta["retried"] = True
    retry = (f"{prompt}\n\nYour previous reply was not valid. Error:\n{err}\n"
             f"Reply again with only a JSON object that matches the required fields.")
    r = llm.generate(retry, system=system, agent=agent, schema=model)
    obj, err = parse_model(r.text, model)
    if obj is None:
        meta["error"] = f"schema validation failed twice: {err[:300]}"
    return obj, meta


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def quote_in_text(quote: str, text: str, min_words: int = 3) -> bool:
    """True if the quote appears (after normalising case and punctuation) in the clause text."""
    q = _norm(quote)
    return len(q.split()) >= min_words and q in _norm(text)


PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){9,12}\d")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
ID_RE = re.compile(r"\b[A-Z]{2,5}-\d{2}-\d{4,6}\b|\b[A-Z]{4,5}\d{4,}[A-Z]?\b")


def mask_pii(text: str) -> str:
    """Simple regex masking before anything is written to logs or the audit DB (SOP-COM-1.2)."""
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = ID_RE.sub("[ID]", text)
    return PHONE_RE.sub("[PHONE]", text)
