Run `20261111T225615Z` on 30 synthetic claims; text model `gemini-3.5-flash-lite`, embeddings `gemini-embedding-001`; top-k 5, graph hops 2, vector_wide uses the same number of clauses as graph mode for each claim.

| Metric | vector | vector_wide | graph |
|---|---|---|---|
| Routing accuracy | 100.0% | 100.0% | 100.0% |
| Field-extraction accuracy (mean of 8 fields) | 97.1% | 97.1% | 97.1% |
| Coverage-decision accuracy (all) | 66.7% | 76.7% | 83.3% |
| Coverage-decision accuracy (cross-reference subset) | 50.0% | 62.5% | 87.5% |
| Coverage-decision accuracy (other decidable claims) | 73.7% | 84.2% | 84.2% |
| Citation precision | 77.3% | 90.9% | 83.7% |
| Citation recall | 63.6% | 76.5% | 80.2% |
| Citation recall (cross-reference subset) | 45.8% | 58.3% | 83.3% |
| Gold clauses in context (recall) | 78.4% | 87.0% | 92.6% |
| Gold clauses in context (cross-reference subset) | 58.3% | 75.0% | 100.0% |
| Mean clauses in context | 5.0 | 12.5 | 12.5 |
| Process-flaw precision | 88.5% | 88.5% | 88.5% |
| Process-flaw recall | 82.1% | 82.1% | 82.1% |
| Fix cites the correct SOP section | 82.6% | 82.6% | 82.6% |
| False flags on the 6 clean claims | 1 | 1 | 1 |
| Refusal correct (should be needs_review) | 2/3 | 2/3 | 2/3 |
| False refusals (needs_review on decidable claims) | 5/27 | 6/27 | 3/27 |
| Model latency per claim, mean (s) | 8.07 | 11.66 | 8.16 |
| Model latency per claim, p95 (s) | 11.23 | 14.82 | 9.52 |
| Tokens per claim, mean (input+output) | 3785.167 | 4073.6 | 4123.567 |
| Model calls per claim, mean | 4.0 | 5.0 | 4.0 |
| Cache hit rate in this run | 16.7% | 83.3% | 79.2% |
| Failed claims | 0 | 0 | 0 |
