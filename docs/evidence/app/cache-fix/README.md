# Cache usability and strict model-response fix ? 7 November 2026

Jibran reported only MISS/BYPASS and confirmed he had not reset the conversation between questions. The old UI always forwarded its server-issued session ID after the first answer. Session history deliberately marks contextual turns as follow-ups, which bypass semantic cache. That backend safety rule remains intact. The UI now defaults to independent questions and omits the session ID, while an explicit conversation/follow-up mode retains shared history. No New conversation reset is required for standalone repeat hits.

`X-Cache-Reason` and UI text distinguish a matched cache entry, a miss that stored a verified answer, a non-cacheable refusal/low-confidence answer, explicit bypass and conversation context. The .95 similarity threshold, scope/version/numeric guards, TTL, bounded candidates and generation/configuration namespace remain enforced. The prompt-contract namespace version was updated, so earlier entries cannot cross the contract change.

| Actual real-profile case | Result | Time |
| --- | --- | --- |
| First standalone university-deposit question | MISS; miss_stored; high-confidence verified Rs 20,000 answer | 14.469 s |
| Same question again without a conversation reset | HIT; matched; identical answer/citations/confidence/retrieved fields | 0.328 s |
| Same question with the first request's session ID | BYPASS; conversation_context | 16.640 s |
| Unsupported hostel-specific deposit question | MISS; not_grounded; safe refusal; not cached | 0.438 s |

`after.json` contains the actual HTTP responses. Current request/session metadata changes on reuse; the verified answer and citations stay identical. `shared-replica-hits.json` proves the same answer/citations returned as HIT when directly addressing each of the three API pods. A real fresh Chrome page asked twice in independent mode without clearing its thread: both were HIT, both omitted session_id, and both displayed the supported amount. See browser-hits.png/json. The browser reused the already populated real cache; the MISS-to-HIT transition is the separate HTTP experiment above. No mocks or generated screenshot content were used for live evidence.

The model receives the Pydantic Answer JSON schema through Ollama's format field. Answer/citation objects now forbid extra fields; supplied completion/model/role metadata is checked, including token-budget termination. Schema/citation failures retain one validation retry, transport/timeouts fall back safely, and public responses omit reasoning. See [the exact contract](../../../MODEL-RESPONSE-CONTRACT.md). These checks establish output structure and citation integrity, rather than universal semantic correctness or fixed wording.

A pre-fix CPU run exceeded the 60-second generation timeout, so its fallback was correctly not cached; the next request generated a cacheable answer. See before.json. Startup now issues Ollama's documented empty-request generation-model preload. An interim experiment also duplicated the schema into the system prompt; it timed out once and needed a validation retry on the next request (83.172s), so the final implementation retains the original concise prompt with the schema only in format. interim-expanded-prompt.json preserves that failed test assumption; it is not the final passing run. A namespace change isolates those interim entries. CPU generation can still time out or fail validation; preload is not a latency or correctness guarantee.

Offline verification: all 168 API tests passed, including real HTTP MISS/HIT/BYPASS metadata/identity checks and wrong/incomplete/extra-field model rejection; API mypy passed. All 22 evaluator/script tests passed, including generation preload checks; native Node UI tests and Ruff passed. Pytest initially could not access the sandbox's shared temp directory; the evaluator/script tests passed with host access and a fresh workspace temp directory. Existing indexer code/dependencies and all frozen golden/baseline files were unchanged.

The API/indexer use development image tag cache-fix-v2. A wording-only UI follow-up uses cache-fix-ui-v3: ungrounded responses say No verified answer, so a generation timeout is not misrepresented as proof that the documents lack the answer. The Node UI regression passed for this wording change. Real 17-question baseline evaluation is recorded separately in real-results.json and evaluation.txt after its gate completes. The saved source remains the authoritative implementation; temporary forwards and test browser sessions are closed after verification.


## Final frozen real-corpus evaluation

All 17 questions completed with zero execution errors and an empty gate_failures list. Recall@3/@5 was .933333, citation validity 1.0 and required abstention correctness 1.0. Cache was explicitly bypassed for every evaluation request. Golden questions and baselines were not changed; eval/results.json now contains this actual latest real-profile run, with the previous historical results retained in earlier sprint/platform evidence.

Expected-string diagnostic misses were q01, q07, q08 and q15. q01/q15 returned supported but terse No answers (q15 also repeated a source label), rather than reproducing the expected word passed. q07 remained the documented conservative relevance-floor refusal. q08 exceeded the CPU model deadline and returned the safe verification fallback. JSON structure and citation integrity do not prove semantic completeness. The final implementation preserves those limitations rather than forcing expected strings into responses or weakening evaluation.
