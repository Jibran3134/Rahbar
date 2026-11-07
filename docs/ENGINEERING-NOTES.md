# Engineering notes: Jibran and Alishba

These answers refer to this repository and actual local evidence. Codex implemented the application and, later, Alishba's platform scope at Jibran's request. Human review remains pending. A local cluster result is not a successful protected remote release.

## 1. Indexing in API startup with three replicas

[k8s/base/api.yaml:8](../k8s/base/api.yaml#L8) requests three API replicas and its rolling strategy permits one additional pod. Startup ingestion would therefore produce three or four concurrent writers, repeat OCR/embedding on every restart, couple rollout readiness to batch work, and make corpus changes require an API restart. A reader could observe partially built data if those processes wrote one live collection.

The batch boundary is [indexer-job.yaml:7](../k8s/base/indexer-job.yaml#L7): bounded retries/deadline, `python -m pipeline.run`, and restartPolicy OnFailure at line 16. [reindex-cronjob.yaml](../k8s/base/reindex-cronjob.yaml) schedules the same workload with Forbid. CronJob serialization alone does not cover separate manual Jobs. [store.py:24](../indexer/pipeline/store.py#L24) implements an exclusive Chroma writer lock, verifies a separate generation and publishes its four-key identity; [chroma.py:101](../api/app/retrieval/chroma.py#L101) reads one identity per query. There is no ingestion in API startup. P02 recorded 813 published chunks, followed by three ready endpoints. P04 separately records live reindexing/cache invalidation with unchanged API pod UIDs. ADR0001 documents stale-lock and ambiguous-publication recovery limits.

## 2. Swapping readiness/liveness during a 90-second Chroma slowdown

API probes are in [api.yaml:64](../k8s/base/api.yaml#L64): startup /healthz, liveness /healthz (line 71), readiness /readyz (line 78). The ready probe has an eight-second timeout; dependency operations have bounded waits in [readiness.py:17](../api/app/services/readiness.py#L17). A single outstanding Chroma task avoids unbounded probe threads. /healthz does not contact dependencies.

With the probes swapped, liveness would query the slow store every 20 seconds and restart healthy processes after three failures, roughly a minute plus timeout/scheduling effects into the outage. Three replicas exposed to the same dependency could churn together; restarting them cannot repair Chroma. Meanwhile process-only readiness would admit pods that still cannot answer. With the correct probes, pods remain alive and become unready instead. The actual P04 embedding-conflict experiment showed healthz=200, readyz=503 and an explicit conflict log, then recovery after restoring the pin. Native S14 also exercised dependency outage/recovery. These are measured checks, not a claim that an actual 90-second swapped-probe incident was run.

## 3. CPU HPA while generation is external

[hpa.yaml:11](../k8s/base/hpa.yaml#L11) sets min 3/max 8 and 70% CPU utilization. Its denominator is the API's 100m CPU request in api.yaml. It measures the pod's Python/retrieval/validation/network work, not CPU/GPU usage on Windows Ollama. A request waiting on model output can be slow while the pod's CPU stays low. P02/hpa.txt showed 11%/70% with three replicas; the CI cluster later showed 18%/70%, so the metrics were defined. No eight-replica CPU-load test is claimed.

Useful additional signals are concurrent requests, queue depth, generation latency and upstream saturation/capacity. [metrics.py:51](../api/app/routes/metrics.py#L51) exports stage timing/cache/usage metrics; a queue-depth signal and Prometheus/custom-metrics adapter would need implementation before an HPA could use that metric. Scaling API replicas alone does not add host-model capacity. CI now provisions metrics-server explicitly; its isolated kind setup allows self-signed kubelet certificates only for that test environment.

## 4. Indexer memory, limit, margin and exit code

The actual Linux Job's [cgroup samples and simultaneous kubectl top](evidence/platform/P02/indexer-memory.json) observed memory.peak **343,830,528 bytes = 327.902 MiB**, with memory.max **1,610,612,736 bytes = 1536 MiB**. The configured main-container request/limit are **384/1536 MiB** in [indexer-job.yaml:39](../k8s/base/indexer-job.yaml#L39), with CPU request 250m/limit 2. Observed headroom to the memory limit was **1208.098 MiB**, about 4.68 times peak total capacity. Unlike the earlier Windows 227.53-MiB interpreter sample, this cgroup includes OCR children. The sample is from the initial platform-p01 Linux Job; later security-fixed indexing completed too, but a separate later peak was not sampled. It is a finite-workload measurement, not a universal bound.

The first Job completed 813 chunks in 306 seconds; a later rebuild is recorded separately. The CPU request reserves scheduling capacity and permits burst to two cores; sampled OCR CPU reached about 1.5 cores. The memory request covers the observed peak with some margin; the larger limit accommodates uncertain OCR/document and library variation. Other observed idle/light-load working sets were API roughly 75-112 MiB during initial startup and 188-196 MiB after full evaluation; Chroma grew from 34-209 MiB to 573 MiB; Redis reached 6 MiB and UI 4 MiB. These later observations prompted API memory requests of 256 MiB and Chroma requests of 768 MiB/50m CPU, retaining limits of 512/1536 MiB respectively. The final top output is linked by docs/evidence/README.md. These are measured local settings, not production sizing guarantees; use the committed top outputs and repeat under the actual workload before tightening them.

A memory-limit violation can produce OOMKilled/exit 137; a CPU limit throttles rather than guaranteeing termination. We did not deliberately OOM this data store or claim an observed 137. PVC persistence does not substitute for resource limits or backups.

## 5. Worst recall type and embedding weaknesses

The shipped frozen 17-question native report [eval/results.json](../eval/results.json) has ordinary recall@5=.875, versus 1 for exact/version/injection; abstention recall is undefined. Overall recall@3/@5=.933333, citation integrity=1 and required abstention correctness=1. This corpus did **not** show exact terms as the worst measured type, so claiming it did would be false.

q07's scanned eligibility clause appears in raw top-k but fails the conservative .74 query floor, so the returned answer refuses. Lowering to .70 retained more answerables but admitted one absent-topic candidate in the measured sample. OCR phrasing and semantic similarity can blur exact numbers or eligibility qualifiers; BM25/lexical plus dense hybrid retrieval and reranking are possible remedies, but no unimplemented hybrid system is claimed. Metadata filtering separately handles current/historical editions. Raw retrieval was 1.0 for selected chunks 250/30 before gating; returned-evidence recall was .933333. Citation checks do not establish semantic entailment: original q17 returned a heading, while a later fresh run answered the condition. See PIPELINE.md, FAILURE-ANALYSIS.md and the individual results for the retained misses.

## 6. API-only embedding model change

[ConfigMap](../k8s/base/configmap.yaml) provides the shared EMBED_MODEL. Publication records model and actual dimension; [chroma.py:101](../api/app/retrieval/chroma.py#L101) refuses incompatible requests, while readiness logs expected/actual model and fails. The cache namespace in [cache.py:28](../api/app/services/cache.py#L28) also includes immutable index/model/settings/prompt identity.

P04 changed only the ConfigMap model, restarted the API and observed a new 0/1 READY pod with healthz=200 and readyz=503/model=false. Because maxUnavailable=0, three old replicas with their prior valid environment could remain available while the bad rollout stalled. The experiment restored the pin and restarted, then waited for a healthy rollout. Without the guardrail, same-dimension different-model vectors could return plausible but irrelevant chunks and contaminate cache; unequal dimensions would instead depend on a backend error. Mutable tags can still change model contents without a name change; recorded digests are evidence, not enforcement.

## 7. The real extended debugging incident

The S18-S19 native generation/verification work spanned more than an elapsed hour. Useful retrieved policy text was repeatedly refused because the model returned malformed or misplaced inline citations. The first assumption was that stronger string-pattern constraints would force the desired format. Actual schema experiments ignored escaped spacing, generated malformed output or stalled. `python api/tests/diagnose_generation.py`, the retained S19-prefix-red.txt outputs and per-question raw public-source diagnostics separated retrieval quality from output formatting. Those logs, rather than changing golden truth, identified the problem.

Verified rendering of existing citation objects improved useful output, but then a real indexed-poison attack escaped: earlier formatting fallback had masked the attack. S19-safety-red.txt and `python api/tests/test_injection.py --live` exposed that failure. Conservative instruction quarantine, independent grounding validation and bounded retry/fallback were added, followed by native attack rechecks and final evaluator gates. A separate query-level relevance correction stopped a per-passage filter from discarding valid historical context after accepting a query. Failed attempts remain in evidence; no active-editing stopwatch or fabricated uninterrupted hour is claimed. Source-public diagnostics omit private conversations/provider reasoning.

Platform work also preserved genuine failures: original image vulnerability scans, a helper named platform.py shadowing Python's standard module, PowerShell dropping an empty registry argument, cold image-pull EOF/timeout, a new-pod HTTP startup race and immediate post-rollout Ingress propagation. Each received a specific correction and actual recheck. These are additional observations, not invented replacements for the extended generation incident.


## Final local platform evaluation

P04 real Ingress evaluation after Linux reindexing and the security updates passed the committed baseline: recall@3/@5=.933333, citation integrity=1, required abstentions=1. Diagnostic expect misses in that run were q01, q07 and q15; original S19 misses are retained rather than rewritten. A separate live CI-fixture threshold regression exited 1; restoring .65 exited 0 with the baseline unchanged. The UI visible update/rollback returned identical old-page hashes, then the new version was redeployed. No remote blocked-merge/CI/CD outcome is inferred.


P05 remote follow-through: actual fixture regression CI failed (recall@5=0), the corrected same PR passed (recall@5/citation validity/required abstentions=1), and PR #1 merged with required CI enforced. Golden questions and baseline hashes are identical across the red, corrected and merged commits. GitHub Actions published the three exact tested images as 47fdad99c57f5bddf437bcf318fe1eaee22e1763; registry digests and original hosted artifacts are retained in P05. See SUBMISSION.md for the final release outcome and remaining rubric exceptions. This supplements, rather than rewrites, the earlier local experiment reports.
