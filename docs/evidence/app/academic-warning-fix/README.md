# Academic-warning answer regression - 7 November 2026

Jibran reported a safe generation fallback for **What is academic warning**, with request ID b83bf449f69b6e5d4670b85e72eb446b. The saved reported-request.txt confirms retrieval completed in about .134 seconds but generation exceeded the 60-second timeout. The highest-ranked chunk's full text was only Academic Warning/Probation. Same-page clauses 5.4-5.5 contain the 2.00 CGPA threshold and semester-end warning condition, but were absent from that original top-five context.

## Change

Dense retrieval still uses the frozen .74 query floor, original query embeddings, version filters and top-k 5. A bounded pool of at most 3 * top-k candidates permits unusable headings to be skipped or expanded. When a PDF hit is just its section title, the API fetches authentic records from the **same fixed Chroma collection, source, physical page, document version and superseded state**. At most 32 records are fetched, up to eight complete blocks and 1800 total characters are included, and the heading keeps its original seed score and citation identity. Context includes original child-section labels. HTML's logical page 1 is not treated as a physical page. Corrupt or cross-identity context fails closed. The API remains read-only and no reindex was required.

The model prompt asks definition questions to state the definition/trigger rather than unrelated procedures. The selected CPU model receives 120 seconds per attempt. There is still only one validation retry, and a timeout/transport error still falls back without a network retry. API pod termination grace, Ingress read/send timeout, Windows gateway timeout and evaluator timeout are coordinated at 360 seconds. A regression test checks these outer budgets exceed two 120-second generation attempts plus a 60-second query embedding allowance and ten-second drain; this is an operational budget, not a hard wall-clock guarantee for every possible network condition. Cache namespace version was changed for the context/prompt policy; old answers cannot cross that change.

Future uncached timeouts explicitly report generation_timeout through X-Cache-Reason and UI text; other unverified generation failures report generation_failure. A genuine source refusal remains not_grounded. Unsupported output is still not cached and reasoning is never exposed.

## Measured diagnosis

- The first diagnostic ran extra Python/Chroma clients inside an API pod and exceeded its 512 MiB cgroup limit (exit 137/OOMKilled). One API replica restarted and recovered while the other two stayed available; replica-recovery.json records this diagnostic-induced event. Subsequent diagnostics ran on the host through short-lived forwards. Normal API memory limits were not raised to accommodate debugging tools.
- host-long-budget-diagnostic.json records the original weak context with an extended diagnostic timeout: the model returned an invalid low-confidence response after 50.218s. Increasing timeout alone did not establish correctness.
- content-bearing-diagnostic.json records an intermediate heading-removal-only experiment (not shipped alone): the best remaining score was .738, below the unchanged relevance floor, and the direct provider diagnostic still returned invalid output. No threshold was lowered.
- parent-page-diagnostic.json records a validated high-confidence response using the actual source context in 66.360s, including 47.589s of prompt evaluation, 15.100s of output generation and 3.629s of model loading. This exceeded the old production deadline even though the answer was valid.

## Actual deployed result

The real Ingress returned a high-confidence supported definition in **71.672s**: academic warning occurs when CGPA drops below 2.00 at the end of a semester, with the June 2026 handbook's Academic Warning/Probation section on page 24. The independent repeat was **HIT in .250s**, with identical answer and citations. See live-response.json. A fresh Chrome page repeated the exact question twice without resetting and displayed two HITs with no session history sent; browser-answer.png/json is the actual deployed UI, not a mock image.

Relevant offline checks passed: 180 API tests, API mypy, 23 evaluator/script tests, Node UI tests and Ruff. Tests cover heading replacement/expansion, original score preservation, bounded whole-block context, source/page/version/superseded identity, physical-page type validation, HTML exclusion, missing-evidence versus generation-timeout diagnostics, and coordinated request/drain budgets. A targeted retrieval rerun after tightening the text bound also passed (26 cases). All three overlays passed namespace, security and source/config drift invariants. The real deployment uses warning-fix-v1; the source index/golden questions/baselines and similarity floors remain unchanged.

The final frozen 17-question evaluation passed with cache bypassed: recall@3/@5=.933333, citation validity=1, required abstention correctness=1, zero execution errors and no gate failures. See real-results.json/evaluation.txt; eval/results.json contains this actual latest run. Expected-string diagnostic misses are q01/q07/q08: a terse supported No answer, the existing relevance-floor refusal, and an incomplete risks discussion. Passing the gate does not establish universal semantic completeness.


## Interrupted broader run and recovery

The first 17-question run encountered a Chroma availability outage during an auxiliary metadata-read diagnostic. The database reached approximately 1527 MiB against its 1536 MiB limit, heartbeat probes timed out, and later evaluator calls received HTTP errors. The failed run is preserved as interrupted-real-results.json/interrupted-evaluation.txt; it was not accepted as a pass. An unbounded administrative metadata read also timed out. Production parent-page lookups always specify limit=32.

For recovery, Chroma alone was restarted with temporary 2048 MiB request/3072 MiB limit while preserving its existing 4 GiB PVC and active generation. All three API replicas became ready again, and the academic-warning answer continued to return from the valid Redis cache. The unchanged real gate then passed while sampling Chroma memory every 15 seconds. The maximum sampled working set was 348 MiB; actual cgroup peak was 390.72 MiB. The original 768 MiB request/1536 MiB limit was restored after this finite workload measurement. A post-restore bounded source lookup and Ingress cached-answer check passed; post-restore-smoke.json records the active answer/context. Temporary extra memory was used only for diagnosis and is not a permanent manifest change. This evidence distinguishes a diagnostic incident from the original user's 60-second generation failure.


The normal app on port 8090 was already running, so the launcher's final check used free port 18091 and closed its own forwarding processes afterwards. The user-owned launcher was not killed. Restart that existing launcher once to load its updated 360-second gateway timeout. No golden questions, baselines, similarity thresholds, embedding model, source snapshots or index generations were modified for this fix.
