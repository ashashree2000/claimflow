Run `20261111T224911Z_pilot` on 5 synthetic claims; text model `gemini-3.5-flash-lite`, embeddings `gemini-embedding-001`; top-k 5, graph hops 2, vector_wide uses the same number of clauses as graph mode for each claim.

| Metric | vector | vector_wide | graph |
|---|---|---|---|
| Routing accuracy | 100.0% | 100.0% | 100.0% |
| Field-extraction accuracy (mean of 8 fields) | 97.5% | 97.5% | 97.5% |
| Coverage-decision accuracy (all) | 40.0% | 40.0% | 60.0% |
| Coverage-decision accuracy (cross-reference subset) | 33.3% | 33.3% | 66.7% |
| Coverage-decision accuracy (other decidable claims) | 100.0% | 100.0% | 100.0% |
| Citation precision | 50.0% | 83.3% | 83.3% |
| Citation recall | 33.3% | 50.0% | 75.0% |
| Citation recall (cross-reference subset) | 11.1% | 33.3% | 66.7% |
| Gold clauses in context (recall) | 58.3% | 75.0% | 100.0% |
| Gold clauses in context (cross-reference subset) | 44.4% | 66.7% | 100.0% |
| Mean clauses in context | 5.0 | 11.8 | 11.8 |
| Process-flaw precision | 75.0% | 75.0% | 75.0% |
| Process-flaw recall | 60.0% | 60.0% | 60.0% |
| Fix cites the correct SOP section | 66.7% | 66.7% | 66.7% |
| False flags on the 6 clean claims | 0 | 0 | 0 |
| Refusal correct (should be needs_review) | 0/1 | 0/1 | 0/1 |
| False refusals (needs_review on decidable claims) | 2/4 | 2/4 | 1/4 |
| Model latency per claim, mean (s) | 7.30 | 11.18 | 7.74 |
| Model latency per claim, p95 (s) | 7.74 | 11.94 | 8.81 |
| Tokens per claim, mean (input+output) | 3743.0 | 4031.6 | 4064.0 |
| Model calls per claim, mean | 4.0 | 5.0 | 4.0 |
| Cache hit rate in this run | 0.0% | 80.0% | 75.0% |
| Failed claims | 0 | 0 | 0 |
