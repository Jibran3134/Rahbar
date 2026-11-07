# Personal-value policy regression (in progress)

Reported question: **My gpa is 3.6. Am i on academic warning**. Request ID: `7aef3e3a365dc69fefbb2dfddf20027d`.

The original request retrieved the relevant 2.00 minimum (handbook section 5.4, physical page 24). Logs reported invalid_citation on both attempts, not a timeout. A host-side reproduction showed citation triples and inline labels matching, but contradictory refusal/groundedness fields; one attempt also reversed the 3.6 versus 2.00 comparison. `before-diagnostic.json` preserves public fields only.

`prompt-experiment.json` and `concise-prompt-experiment.json` are **failed** llama3.2:3b experiments, not passing acceptance evidence. One emitted a bare, wrong yes with valid citation syntax. This demonstrates why citation validity alone cannot certify correctness. No policy answer or model reasoning was hardcoded into production.

New regression tests first failed for supported conditionals rejected by a blanket cannot-determine substring check, misleading citation-only retry advice, and unsafe reuse between CGPA and semester GPA with identical embeddings. The implementation distinguishes global refusals from a cited conditional limitation, classifies contradictory output as inconsistent_answer, supplies bounded static retry advice, and guards GPA interpretation in cache signatures. Source/page matching and every-sentence citation checks remain intact. The cache namespace changed.

Initial focused tests: 5 expected failures then 32 passed; GPA cache guard: 1 expected failure then all 8 cache tests passed. Broad regression initially found the exhaustive enum contract needed the new typed category (208 passed, 1 failed); after updating that contract and testing the same two-attempt limit for the category, all **210 API/evaluator/script cases** passed. Ruff, API mypy, Node UI tests and actionlint passed. The new model/prompt and real acceptance are still being measured; this checkpoint is not a claim that the reported question is fixed.

`supplemental-cases.json` contains source-reviewed criteria separate from the frozen assignment golden set. `supplemental-retrieval.json` records actual bounded retrieval for all six cases; each clears the existing .74 query floor. Neither relevance/cache thresholds nor source snapshots, index data, golden truth or baselines were changed.

Delivery follows Jibran's new topic -> dev -> main instruction, with automated gates and no teammate approval. The topic also carries the four previously verified, unpublished local-main commits. Remote promotion results will be recorded after they actually occur.
