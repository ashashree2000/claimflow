"""Coverage agent (GraphRAG): retrieve clauses, optionally expand along the clause graph, decide with citations.

AI proposes, code decides: code drops citations to clauses that were not retrieved or whose quote is not in
the clause text, and turns any decision without a verified citation into "needs_review".
"""
from __future__ import annotations

from functools import lru_cache

from .. import config
from ..guardrails import call_validated, quote_in_text
from ..llm import LLMClient
from ..retrieval import graph, load_policies, load_sops, vector
from ..schemas import ClaimEmail, CoverageAnswer, CoverageResult, IntakeResult

SYSTEM = """You are the coverage agent for an insurer. You decide whether a claim is covered using ONLY the
policy clauses you are given. Reply with one JSON object only."""


@lru_cache(maxsize=1)
def _graph():
    return graph.build_graph()


def retrieve(llm: LLMClient, query: str, lob: str, mode: str, k: int = config.TOP_K) -> tuple[list[str], list[str]]:
    hits = [h[0] for h in vector.search(llm, query, lob, k=k, agent="coverage")]
    if mode == "vector":
        return hits, []
    extra = [a["id"] for a in graph.expand(_graph(), hits)]
    if mode == "graph":
        return hits, extra
    # vector_wide: plain vector search with as many clauses as graph mode would give this claim
    return [h[0] for h in vector.search(llm, query, lob, k=len(hits) + len(extra), agent="coverage")], []


def build_prompt(email: ClaimEmail, intake: IntakeResult, clause_ids: list[str]) -> str:
    pol = load_policies()
    esc = load_sops()
    clauses = "\n".join(pol[c].render() for c in clause_ids)
    return f"""Decide the coverage for this claim.

Rules:
1. Use only the clauses below. Follow cross-references between them: a coverage "subject to" an exclusion,
   an exclusion "amended by" an endorsement, and definitions used in a clause.
2. decision: "covered", "not_covered", or "needs_review".
3. Use "needs_review" when the clauses below do not address the event in the claim, or the facts are missing
   or conflicting. These are the insurer's rules:
   - {esc['SOP-ESC-1.1'].text}
   - {esc['SOP-ESC-1.2'].text}
4. citations: every clause your decision relies on, each with clause_id and a short quote copied word for
   word from that clause's text. For "needs_review", citations may be empty.
5. reasoning: 2-4 sentences linking the claim facts to the clauses.

Claim facts (extracted): {intake.model_dump_json()}
Claim email:
{email.body}

Policy clauses:
{clauses}
"""


def run(llm: LLMClient, email: ClaimEmail, intake: IntakeResult, lob: str,
        mode: str = config.RETRIEVAL_MODE) -> tuple[CoverageResult | None, dict]:
    query = f"{intake.incident_type.replace('_', ' ')}: {intake.description}"
    hits, extra = retrieve(llm, query, lob, mode)
    context = hits + extra
    ans, meta = call_validated(llm, build_prompt(email, intake, context), SYSTEM, CoverageAnswer, agent="coverage")
    if ans is None:
        return None, meta
    pol = load_policies()
    notes, kept = [], []
    for c in ans.citations:
        if c.clause_id not in context:
            notes.append(f"dropped citation {c.clause_id}: not in the retrieved clauses")
        elif not quote_in_text(c.quote, pol[c.clause_id].title + " " + pol[c.clause_id].text):
            notes.append(f"dropped citation {c.clause_id}: quote not found in the clause text")
        else:
            kept.append(c)
    decision = ans.decision
    if decision != "needs_review" and not kept:
        notes.append("no verified citation supports the decision: changed to needs_review")
        decision = "needs_review"
    return CoverageResult(decision=decision, citations=kept, reasoning=ans.reasoning, retrieval_mode=mode,
                          retrieved_ids=hits, expanded_ids=extra, guardrail_notes=notes), meta
