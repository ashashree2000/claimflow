Run `20261111T224100Z_pilot` on 5 synthetic claims; text model `gemini-3.5-flash-lite`, embeddings `gemini-embedding-001`; top-k 5, graph hops 2, wide k 13.

| Metric | vector | vector_wide | graph |
|---|---|---|---|
| Routing accuracy | 100.0% | 100.0% | 100.0% |
| Field-extraction accuracy (mean of 8 fields) | 95.0% | 95.0% | 95.0% |
| Coverage-decision accuracy (all) | 60.0% | 60.0% | 40.0% |
| Coverage-decision accuracy (cross-reference subset) | 66.7% | 66.7% | 33.3% |
| Coverage-decision accuracy (other decidable claims) | 100.0% | 100.0% | 100.0% |
| Citation precision | 100.0% | 100.0% | 100.0% |
| Citation recall | 50.0% | 58.3% | 50.0% |
| Citation recall (cross-reference subset) | 33.3% | 44.4% | 33.3% |
| Gold clauses in context (recall) | 58.3% | 66.7% | 66.7% |
| Gold clauses in context (cross-reference subset) | 44.4% | 55.6% | 55.6% |
| Mean clauses in context | 5.0 | 13.0 | 10.0 |
| Process-flaw precision | 60.0% | 60.0% | 60.0% |
| Process-flaw recall | 60.0% | 60.0% | 60.0% |
| Fix cites the correct SOP section | 100.0% | 100.0% | 100.0% |
| False flags on the 6 clean claims | 0 | 0 | 0 |
| Refusal correct (should be needs_review) | 0/1 | 0/1 | 0/1 |
| False refusals (needs_review on decidable claims) | 1/4 | 1/4 | 1/4 |
| Model latency per claim, mean (s) | 8.40 | 4.95 | 5.63 |
| Model latency per claim, p95 (s) | 8.58 | 5.47 | 6.76 |
| Tokens per claim, mean (input+output) | 4972.2 | 5338.2 | 5968.6 |
| Model calls per claim, mean | 5.0 | 5.0 | 5.4 |
| Cache hit rate in this run | 0.0% | 80.0% | 74.1% |
| Failed claims | 0 | 0 | 0 |
