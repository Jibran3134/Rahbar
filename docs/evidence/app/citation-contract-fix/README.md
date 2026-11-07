# Personal-value policy regression (in progress)

Reported question: **My gpa is 3.6. Am i on academic warning**. Request ID: `7aef3e3a365dc69fefbb2dfddf20027d`.

The original request retrieved the relevant 2.00 minimum (handbook section 5.4, physical page 24). Logs reported invalid_citation on both attempts, not a timeout. A host-side reproduction showed citation triples and inline labels matching, but contradictory refusal/groundedness fields; one attempt also reversed the 3.6 versus 2.00 comparison. `before-diagnostic.json` preserves public fields only.

`prompt-experiment.json` and `concise-prompt-experiment.json` are **failed** llama3.2:3b experiments, not passing acceptance evidence. One emitted a bare, wrong yes with valid citation syntax. This demonstrates why citation validity alone cannot certify correctness. No policy answer or model reasoning was hardcoded into production.

New regression tests first failed for supported conditionals rejected by a blanket cannot-determine substring check, misleading citation-only retry advice, and unsafe reuse between CGPA and semester GPA with identical embeddings. The implementation distinguishes global refusals from a cited conditional limitation, classifies contradictory output as inconsistent_answer, supplies bounded static retry advice, and guards GPA interpretation in cache signatures. Source/page matching and every-sentence citation checks remain intact. The cache namespace changed.

Initial focused tests: 5 expected failures then 32 passed; GPA cache guard: 1 expected failure then all 8 cache tests passed. Broad regression initially found the exhaustive enum contract needed the new typed category (208 passed, 1 failed); after updating that contract and testing the same two-attempt limit for the category, all **210 API/evaluator/script cases** passed. Ruff, API mypy, Node UI tests and actionlint passed. The new model/prompt and real acceptance are still being measured; this checkpoint is not a claim that the reported question is fixed.

`supplemental-cases.json` contains source-reviewed criteria separate from the frozen assignment golden set. `supplemental-retrieval.json` records actual bounded retrieval for all six cases; each clears the existing .74 query floor. Neither relevance/cache thresholds nor source snapshots, index data, golden truth or baselines were changed.

Delivery follows Jibran's new topic -> dev -> main instruction, with automated gates and no teammate approval. The topic also carries the four previously verified, unpublished local-main commits. Remote promotion results will be recorded after they actually occur.


## Bounded arithmetic increment

The Decimal helper computes at most 3 question values x 8 distinct evidence values, in ordinary bounded decimal notation. It strips the record's leading section label, ignores metadata quantities, and never equates units or asserts eligibility/policy applicability. No threshold or policy answer is hardcoded. Exact signs, equality and high-precision comparisons are tested; ambiguous grouped/dotted/scientific forms are not guessed. Cache numerical guards now preserve signs as well as GPA interpretation. The provider explicitly requests think=false so hybrid models leave the output budget for the required Answer JSON; private Answer.reasoning is still excluded publicly. See Ollama's official thinking API documentation: https://github.com/ollama/ollama/blob/main/docs/capabilities/thinking.mdx.

Arithmetic/sign regressions first failed in 13 cases (12 missing-helper behaviors plus the signed-value cache case); all 20 arithmetic/cache cases then passed. The wire test first failed for the missing think control; all 17 provider cases then passed. The full current offline regression is **223 passed**, Ruff passes, and mypy passes all 29 API modules. This does not establish semantic acceptance.

The qwen2.5:3b candidate, arithmetic-only and explicit-conditional experiments still produced unsupported assumptions or contradictory prose and were rejected; their public outputs are retained. The first installed qwen3:14b test timed out after 300 seconds. A second, explicitly preloaded diagnostic was interrupted when host responsiveness degraded; observed host free physical memory was 2,137,536 KiB of 33,231,568 KiB. No answer was accepted from it. The model was unloaded without deleting user-installed weights. Jibran explicitly selected stronger local inference despite CPU latency; a smaller Qwen3 candidate is downloading. Production model selection and real acceptance remain pending.


## Model-tag compatibility and launcher increment

The generic qwen3:4b download succeeded, but the actual selected revision reports thinking.values=[true] under Ollama 0.40.1. It cannot honor think=false, and its first question timed out after 180.953 seconds. This is a rejected candidate, not a passing semantic result. Selecting this generic tag before checking its metadata was an avoidable diagnostic mistake. The explicit non-thinking Instruct revision is separate in the official catalog (https://registry.ollama.com/library/qwen3/tags). Its download is in progress. No installed model files were deleted.

The startup launcher now reads EMBED_MODEL/LLM_MODEL from the actual ConfigMap rather than maintaining a second hardcoded download list. Before preloading it reads bounded /api/show metadata and rejects models that explicitly permit only thinking. The real thinking-only tag was rejected in .453 seconds before loading/generating. Legacy metadata without thinking controls remains compatible. Six new/updated launcher cases first failed, then all ten launcher cases passed. Full API/evaluator/script regression: **226 passed**; Ruff passed. The original llama3.2:3b with arithmetic hints still emitted a wrong bare yes; that control is retained and is not acceptance evidence.
