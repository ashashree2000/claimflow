# ClaimFlow build notes (handoff)

Running record so any session (Claude chat, Claude Code) can pick up the work. Newest entries at the bottom.

## Setup (2026-11-12)
- Repo: https://github.com/ashashree2000/claimflow (local folder `claim flow`). `ProcessDNA/` is a separate reference project, git-ignored, never copied.
- All Gemini calls run in the user's Mac Terminal (`conda activate claimflow`, Python 3.11). Claude's shells cannot reach the Gemini API. Git commands also run in the user's Terminal.
- Models (from `client.models.list()`, saved in `scripts/models.json`): text `gemini-3.5-flash-lite`, embeddings `gemini-embedding-2`.
- Free-tier limits seen in AI Studio on 2026-11-12: 3.5 Flash-Lite 15 RPM / 250K TPM / 500 RPD; Embedding 2 100 RPM / 30K TPM / 1K RPD. Fallback text model: `gemini-3.1-flash-lite` (separate 500 RPD).

## Method borrowed from ProcessDNA (ideas only, no code)
- One spec generates emails, event logs and labels (`data/build_dataset.py`), so they cannot disagree.
- Grid designed first: 10 claims per line; 8 cross-reference cases; 3 refusal cases; 6 claims with no process flaw.
- Leakage checks and an independent flaw detector in `data/check_dataset.py` (no API calls).
- AI proposes, code decides: code verifies citations/quotes and forces "needs human review" when unsupported.
- Pilot (5 claims) before the full evaluation; cache keyed on prompt+model; failures recorded, run resumable.

## Milestone 2: dataset (2026-11-12)
- 3 policies (20 numbered clauses each, 60 total, 49 explicit cross-references), 8 SOPs (25 sections), 30 claims, 28 planted process flaws.
- `python data/build_dataset.py && python data/check_dataset.py` -> all checks pass.
- Emails written by Claude (no Gemini quota used). Human review by Ashashree: see below.
- Human review so far: Ashashree read C07, C10 and C14 against their labels and found them correct (2026-11-12). C18, C28, C30 not yet reviewed by her.

## Milestone 3: retrieval (2026-11-12)
- First index build failed: `gemini-embedding-2` merges a list of inputs into one embedding (confirmed in the google-genai SDK test `test_gemini_embedding_2_content_combination`). The retrieval check that ran after it used an empty index, so its zeros were discarded.
- Switched to `gemini-embedding-001` (one embedding per input; same free limits in AI Studio), with task types RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY and guards that fail loudly on a count mismatch or empty index.
- Graph: 78 nodes, 109 edges (references + parent). Expansion walks reference edges both ways up to 2 hops (cap 8), then adds the seed clauses' section headers.

## Milestone 4: agents (2026-11-12)
- Intake (LLM) -> router (rules: policy prefix + intake line; disagreement -> human) -> coverage (LLM, cited) + process (LLM, all 25 SOP sections) -> supervisor (code).
- Guardrails: Pydantic validation with one retry then safe failure; citations dropped unless retrieved and quoted verbatim; decision with no verified citation -> needs_review; process flags with unknown SOP/event dropped; regex PII masking before audit writes.
- Confidence is rule-based (errors/forced review -> low; any guardrail note or retry -> medium; else high), not a model self-report.
- Offline smoke test with a fake model passed (retry path, citation drop, forced needs_review, flag drop, masking, audit review).

## Milestone 5: pilot (2026-11-12)
- Retrieval check (no LLM): mean gold-clause recall, cross-reference subset (8 claims): vector top-5 0.333, graph 0.75, vector with the same number of clauses as graph 0.833. Other 19 claims: 0.789 / 1.0 / 1.0. So on retrieval alone, graph expansion did not beat simply retrieving more clauses. (eval/retrieval_check.json)
- C30 relabel: the first version (hospitalised abroad) was labelled needs_review, but the health wording does address hospitalisation and is silent on territory, so "covered" was defensible. Rewritten as conflicting admission/discharge dates (SOP-ESC-1.2) before the full evaluation.
- Pilot 1 (5 claims: C09 C12 C18 C20 C28, run 20261111T224100Z_pilot) found: C18/graph schema failure twice (quote field missing); C09/graph END-6.1 cut by the expansion cap; vector_wide k fixed at 13 instead of graph's size; process agent read same-time document requests as a problem; cached query embeddings replayed 0 ms latency.
- Changes after pilot 1: Gemini structured output with the Pydantic schema (falls back to JSON mode if rejected); graph expansion follows outgoing references first, cap 10; vector_wide uses graph's per-claim context size; process prompt states that same-time requests are one message; embedding latency stored in the cache. These are pilot-driven changes; the full 30-claim run is made once, after pilot 2, with no further tuning.
- Pilot 2 (run 20261111T224911Z_pilot): no failures; no further changes.

## Milestone 5: full evaluation (2026-11-12)
- Run 20261111T225615Z, 30 claims x 3 modes, 0 failures. Coverage accuracy vector 66.7% / vector_wide 76.7% / graph 83.3%; cross-reference subset 4/8, 5/8, 7/8. Process: 23 of 28 planted flaws matched, 26 predicted, SOP correct 19/23. 390 model calls in the run, 150 live, cache hit 61.5%.

## Milestone 6 (2026-11-12)
- FastAPI (api/main.py), Streamlit (app/), pytest 29 tests with a fake model (pass), ruff clean, CI workflow, manual smoke-eval workflow, Dockerfile (API only, requirements-api.txt). Docker build not yet verified.
