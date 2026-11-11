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
