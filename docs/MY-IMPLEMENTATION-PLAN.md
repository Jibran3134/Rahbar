# Jibran's implementation plan: verified development sprints

This document is both Jibran's development plan and an execution guide for an LLM coding agent. Implement one sprint capability, test it, fix it, record evidence, and only then start a dependent sprint.

Environment: Windows + PowerShell + Python 3.12. Alishba owns infrastructure/delivery. The assignment deadline is 8 November 2026, 23:59 PKT. The two-day target remains aggressive; a time box expiring never means an unfinished sprint passes.

## 1. Instructions for the LLM implementing this plan

Read the assignment PDF, applicable repository instructions, the ownership/contracts in docs/IMPLEMENTATION-PLAN.md, this execution guide, and the current sprint state before editing. Inspect actual code rather than assuming that proposed modules already exist.

You are implementing Jibran's scope. Alishba owns Dockerfiles, UI, k8s/, .github/, scripts/, Makefile, .gitignore, README, platform documentation and final assembled engineering/disclosure documents. Do not edit her files. Record exact requests for her in docs/notes/jibran.md. You may inspect her files and run existing non-destructive tooling.

### Execution rules

1. Select the earliest eligible incomplete sprint from the dependency table. Work on one sprint at a time.
2. Inspect that sprint's files and existing tests. State the concrete behavior being added and the test commands.
3. Add focused behavior tests for new functionality. Run them before implementing and verify they fail for the intended missing behavior, not an import typo or broken test harness. Infrastructure/data-only sprints use validation checks instead of artificial unit tests.
4. Implement the smallest complete behavior satisfying the sprint. Avoid implementing future sprints speculatively.
5. Run focused tests. Fix failures in implementation or a demonstrably incorrect test; never loosen an assignment requirement merely to turn a test green.
6. Run the impacted existing suite and relevant Ruff/mypy checks. Expand to full cross-component regression at the designated integration gates.
7. Perform the required live check separately when specified. Unit doubles are not substitutes for real OCR, embeddings, Chroma, Redis, model behavior or final Kubernetes evidence.
8. Review the diff for ownership, secrets, compatibility and unrelated edits. Preserve other people's changes.
9. Save actual commands, exit codes, results and remaining limitations in the sprint ledger. Update affected technical documentation and AI attribution.
10. Mark PASS only when all mandatory checks have actually run successfully. Then proceed or yield according to the requested execution mode.

Do not install unpinned dependencies, start indexing on API startup, fabricate metrics/logs, silently skip checks, weaken the evaluator/checker, rewrite golden truth from retrieved results, or update a baseline automatically to hide regression.

Do not commit, push, merge, publish or alter GitHub/account settings unless that action is authorized in the current working session. Preparing and testing local code is part of implementing a requested sprint. Follow applicable tool permission rules.

### Execution modes

- Default: implement exactly one sprint through its acceptance gate, update state, report and stop. This gives Jibran a review boundary.
- Continuous: if Jibran explicitly asks for a range or all sprints, complete them sequentially without asking for confirmation between passed sprints. Never skip a failed prerequisite.
- Resume: read state, inspect the diff and rerun necessary verification. Do not repeat passed work unless new code/configuration invalidates it.
- Verify: run the selected sprint's checks and report findings; change code only if repair was requested.

A missing service is a real blocker for that live gate. Mark the sprint BLOCKED, identify the exact external dependency and preserve completed unit work. In continuous mode, another sprint may run only if its declared prerequisites are already passed and it does not depend on the blocked result. Otherwise stop with a precise handoff. Time elapsed is not approval or test evidence.

## 2. Sprint state and evidence protocol

At the first development sprint, create these Jibran-owned files:

- docs/notes/jibran.md: sprint ledger, blockers and handoff requirements for Alishba.
- docs/evidence/app/sprints/Sxx.md: exact commands, results and evidence for each executed sprint.
- docs/AI-USAGE-JIBRAN.md: specific LLM contributions and Jibran's subsequent changes/review.

Do not create prefilled PASS entries. Initially every sprint is TODO. Use only TODO, IN_PROGRESS, BLOCKED and PASS. A sprint whose evidence becomes invalid returns to IN_PROGRESS or BLOCKED.

Ledger format:

| Sprint | Status | Revision / working-tree description | Focused test result | Regression result | Live check | Evidence | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S00 | TODO | Not started | Not run | Not run | Not run | None | Inspect environment |

Each sprint evidence file records:

- Capability and acceptance criteria.
- Files changed and current commit plus uncommitted-diff description.
- New tests, initial expected failure and final result.
- Exact commands, native exit codes and meaningful result counts.
- Live evidence or a clearly named blocker.
- Relevant risks, unresolved limitations and requests for Alishba.
- Next eligible sprint.

Store raw transcripts where useful, without credentials/private data. A screenshot alone is not a substitute for machine-readable results.

### Required report after each sprint

~~~text
Sprint: Sxx — name
Status: PASS / BLOCKED / IN_PROGRESS
Implemented: concrete observable behavior
Files: paths
Tests: exact commands, exit codes and counts
Live check: observed result or specific blocker
Regression: result
Alishba handoff: exact requirement, or none
Next: earliest eligible sprint and why
~~~

## 3. Windows test commands and pass rules

Use the project venv directly; activation and Bash are unnecessary. Run API/indexer tests from their own directories because their pytest configs set import paths.

~~~powershell
Push-Location api
..\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'API tests failed' }
..\.venv\Scripts\python.exe -m mypy app
if ($LASTEXITCODE -ne 0) { throw 'API type checks failed' }
Pop-Location

Push-Location indexer
..\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Indexer tests failed' }
..\.venv\Scripts\python.exe -m mypy pipeline
if ($LASTEXITCODE -ne 0) { throw 'Indexer type checks failed' }
Pop-Location

.\.venv\Scripts\python.exe -m ruff check api indexer eval corpus
if ($LASTEXITCODE -ne 0) { throw 'Lint failed' }
# After S17 creates evaluator tests:
.\.venv\Scripts\python.exe -m pytest -q eval/tests
if ($LASTEXITCODE -ne 0) { throw 'Evaluator tests failed' }
~~~

For a focused sprint, select its explicit test file, for example from api/: python -m pytest -q tests/test_grounding.py. Test filenames below are proposed; create them as needed, and record actual paths.

Unit tests use local doubles and no live network/model. Live checks run as explicit integration commands or an explicitly marked integration suite. Never silently skip a mandatory live check while calling the sprint complete.

Coverage must measure implemented app code and be at least 60%. Add a pinned coverage tool to Jibran-owned development requirements when needed; coordinate Alishba's CI invocation. Do not use the starter's 83% as final proof. Test quantities are diagnostic, not the correctness goal.

The overall submission checker will continue failing while unrelated work is unfinished. Run it at milestone gates and track findings by owner; an expected missing Dockerfile must not prevent a focused extraction sprint from passing.

## 4. Ordered sprint map

The detailed steps later in this file remain technical references. The sprint map and gates below control execution order and completion.

| Sprint | One capability | Prerequisites | Target |
| --- | --- | --- | --- |
| S00 | Reproducible Windows test environment | None | Day 1 morning |
| S01 | Verified corpus and independent golden truth | S00 | Day 1 morning |
| S02 | Validated runtime/data contracts | S00 | Day 1 morning |
| S03 | Page-aware extraction and real OCR | S01, S02 | Day 1 afternoon |
| S04 | Structure-preserving cleaning | S03 | Day 1 afternoon |
| S05 | Deterministic structure-aware chunking | S04 | Day 1 afternoon |
| S06 | Validated batched embedding | S02 | Day 1 afternoon |
| S07 | Safe versioned index publication | S05, S06 | Day 1 afternoon |
| S08 | Version-aware retrieval and model guardrail | S07 | Day 1 late afternoon |
| S09 | Relevance-based honest abstention | S08 | Day 1 late afternoon |
| S10 | One schema-constrained real provider | S02 | Day 1 late afternoon |
| S11 | Citation validation, retry and fallback | S09, S10 | Day 1 evening |
| S12 | Shared follow-up session handling | S11 | Day 1 evening |
| S13 | Safe semantic cache with invalidation | S12 | Day 1 evening / Day 2 first block |
| S14 | Dependency/model-aware readiness | S07, S13 | Day 1 close / Day 2 first block |
| S15 | Required query observability | S14 | Day 2 first block |
| S16 | Indexed-poison safety verification | S11 | Day 2 first block |
| S17 | Correct evaluator and regression gates | S01, S11 | Day 2 morning |
| S18 | Real/fixture end-to-end integration | S13–S17 | Day 2 morning |
| S19 | Measured chunk/cache/relevance decisions | S18 | Day 2 afternoon |
| S20 | Four controlled failure experiments | S19 | Day 2 afternoon |
| S21 | Final application evidence and technical docs | S20 | Day 2 evening |
| S22 | Clean-clone and release acceptance | S21 + Alishba's platform ready | Day 2 final gate |

S13–S17 means every sprint in that inclusive range. Implement independent branches only to avoid a genuine external blocker; preserve all prerequisites.

Budget roughly 12–14 focused hours each day for Jibran, with meals/breaks and the contingency day available. These are small verification sessions inside that budget, not 23 full agile iterations. If behind, cut optional scope; never shorten safety gates or invent results.

## 5. Sprint specifications

### S00 — Windows environment and baseline

Develop: create the Python 3.12 venv; install pinned requirements; verify executable paths; inventory local Docker/Ollama/OCR prerequisites. No production feature changes.

Validate: run all existing API/indexer tests, Ruff and mypy. Record actual dependency versions and initial failures. Confirm that Windows PowerShell commands work without Make/Ubuntu.

Gate: reproducible baseline, existing failures understood, local URLs agreed, no global Python 3.14 dependency. Native service/OCR requirements handed to Alishba. Reference: technical Step 0.

### S01 — Corpus and independent golden set

Develop: verify source URLs/version pair/scan/table/long definition/exact terms/absent topic; commit sources and checksum manifest; write the required 15+ questions from source documents before tuning.

Validate: fetch verification; document/page counts; manual source-section lookup for every golden relevant entry; category counts; genuine changed clauses; scan text-layer evidence. Validation can be a small report/check rather than contrived tests.

Gate: six documents/forty pages and all seven properties evidenced; minimum 8 ordinary, 2 version, 2 exact, 2 abstain, 1 injection; no retrieval-derived golden truth. Freeze the initial golden revision. Reference: Step 1.

### S02 — Validated configuration and contracts

Develop: settings validation, shared model semantics, internal active-index identity, bounded optional session fields and explicit provider error categories.

Tests: tests/test_config.py and indexer/tests/test_config.py cover invalid ranges, parsing, missing/unsupported provider values, overlap >= size, positive TTL/timeouts and backward-compatible schemas. Preserve existing response tests.

Gate: valid settings parse consistently; bad settings fail clearly; exact configuration/session contracts given to Alishba. No dependency calls during pure configuration tests. Reference: Step 2.

### S03 — Extraction and OCR

Develop: PDF pages, Markdown/text/selected HTML extraction, front matter removal, scan detection/OCR adapter, bounded temporary resources and actionable errors.

Tests: indexer/tests/test_extract.py covers dispatch, source/page numbering, heading preservation, front matter stripping, OCR detection and failures. Use owned test artifacts and doubles for executable calls.

Live check: process a real text PDF, real scanned PDF and selected HTML; inspect the meaningful table and record losses.

Gate: unit suite and actual scan extraction pass; mock-only OCR cannot pass this sprint. Record native package requirements and table before/after. Reference: Step 3.

### S04 — Conservative cleaning

Develop: repeating-header/footer removal and artifact normalization with structure preserved.

Tests: indexer/tests/test_clean.py protects headings, clauses, 2.00, percentages, fees, course codes, table relationships and meaningful hyphens; checks page/source metadata.

Live check: inspect cleaned scan/table/definition output from S03.

Gate: artifacts removed without destroying selected evidence; extraction suite stays green. Reference: Step 4.

### S05 — Structured deterministic chunks

Develop: section → paragraph → sentence splitting, bounded fallback, overlap, stable IDs and amplification accounting.

Tests: indexer/tests/test_chunk.py covers size/overlap, no infinite loop, stable IDs, section/page/version metadata, multi-page convention and oversized inputs. Check expected properties, not a copy of the implementation algorithm.

Live check: inspect chunks containing the selected long definition and exact-term clauses.

Gate: reproducible chunks, complete metadata and recorded token-count method. No final size choice claimed before S19. Reference: Step 5.

### S06 — Batched embedding

Develop: explicit pinned-model HTTP calls, bounded batches/timeouts and finite consistent vectors.

Tests: indexer/tests/test_embed.py uses a fake HTTP transport for correct model/payload, ordering, count mismatch, inconsistent dimension, NaN/infinity, transport failures and timeouts.

Live check: embed real text with the selected model and record actual dimension and response behavior.

Gate: vector count/order/dimension validated and live embedding works. The API will reuse the same model semantics. Reference: Step 6 embedding portion.

### S07 — Versioned storage and publication

Develop: build/validate a separate collection and publish active identity only after success; retain last-known-good data and define cleanup/single-writer operation.

Tests: indexer/tests/test_store.py and tests/test_index_state.py cover required metadata, partial build failure, failed publication, successful switch, reader non-writing behavior and old generation retention.

Live check: two builds against real local Chroma plus a deliberately failed build. Query the old published data after the failed rebuild.

Gate: active data survives failure; actual model/dimension recorded; publication behavior verified rather than assumed atomic across collections; concurrency limits documented. Reference: Step 6 storage portion.

### S08 — Version-aware retrieval and compatibility

Develop: active generation resolution, query embeddings, current/default and explicit historical filtering, cosine score conversion and invalid-metadata handling.

Tests: tests/test_retrieval.py covers correct query vector/filter/k, unrelated dates/course codes, historical selection, score conversion, empty/small index, model/dimension conflict and no collection writes.

Live check: real current and historical golden questions retrieve their intended passages.

Gate: one request uses one generation; incompatible embedding cannot silently retrieve; current policy is default. Reference: Step 7.

### S09 — Honest abstention before generation

Develop: relevance-floor decision and safe unsupported response.

Tests: tests/test_abstention.py covers no hits, below/at/above floor and invalid evidence. Spy provider must not be called when relevance is insufficient.

Live check: selected absent-topic and answerable questions demonstrate useful answering plus honest refusal; thresholds are provisional until measured.

Gate: unsupported questions yield false groundedness with no invented citations and no generation call. Reference: Step 7 relevance portion.

### S10 — One real constrained provider

Develop: Ollama schema-constrained request, evidence delimiters, instruction/data separation, configured model/temperature and bounded timeouts.

Tests: tests/test_ollama.py inspects requests through a fake transport; checks actual Answer schema, prompt order/delimiters, output parsing and timeout classification.

Live check: real provider returns a schema-valid answer from a known supplied passage.

Gate: one real mode works; stub stays offline; unsupported optional modes rejected clearly. Safety orchestration is not assumed complete until S11. Reference: Step 8 provider portion.

### S11 — Grounding validation and bounded recovery

Develop: per-request source/section/page citation matching, claim-bearing sentence citation checks, contradictory groundedness rejection, one retry and safe fallback.

Tests: tests/test_grounding.py and test_fallback.py cover fabricated sources/pages, missing citations, malformed JSON/schema, successful second attempt, exactly two failed attempts, timeout and hidden reasoning.

Live check: known real question answers with matching evidence; malformed-output simulation proves no unhandled 500. Inspect actual answer claims, not citation syntax alone.

Gate: no fabricated citation escapes; one-retry bound enforced; fallback uncited/untrusted and recorded; existing response contract suite passes. Reference: Step 8 safety portion.

### S12 — Shared sessions and meaningful follow-ups

Develop: bounded Redis turns, session TTL/ID validation, optional compatible fields and bounded follow-up context resolution.

Tests: tests/test_sessions.py uses a Redis double for isolation/TTL/history bounds and verifies a follow-up receives relevant context; independent sessions cannot mix.

Live check: two API clients/processes sharing real Redis continue the same session correctly. Optional UI change is Alishba's work.

Gate: session survives process boundary; standalone client remains compatible; follow-up marker available to cache. Send exact UI contract. Reference: Step 9 session portion.

### S13 — Safe semantic cache and invalidation

Develop: bounded vector candidates, cosine matching, index/config namespace, TTL/entry bounds, safe-cache rules, query-vector reuse and X-Cache.

Tests: tests/test_cache.py covers hit/miss/bypass, threshold boundary, version/numeric near misses, unsafe-answer exclusion, follow-up exclusion, max entries/expiry and generation change. Assert one query embedding is reused.

Live check: real Redis safe paraphrase hit; near miss rejected; changed policy re-indexed and old cached answer inaccessible; follow-up bypass observed.

Gate: a real semantic hit works without unsafe reuse, and indexer still needs no Redis access. Reference: Step 9 cache portion.

### S14 — Truthful readiness

Develop: bounded Chroma/nonempty-active-index/model/dimension/Redis checks; generation-change revalidation; dependency-independent liveness.

Tests: tests/test_readiness.py toggles each dependency/conflict, empty/unpublished index and recovered dependency. Every failure names the correct check and returns 503; /healthz stays 200.

Live check: stop/restore a local dependency and deliberately configure an embedding mismatch. Record precise conflict logs and recovery.

Gate: API can start enough to answer liveness during dependency outage; incompatible state never reports ready. Reference: Step 10 health portion.

### S15 — Required observability

Develop: retrieval/generation latency, cache hit inputs, abstention/fallback counts, tokens in/out, per-request JSON outcomes and request IDs.

Tests: tests/test_observability.py drives success/refusal/cache/fallback paths, scrapes metrics, parses JSON logs and checks no unbounded IDs in metric labels or leaked reasoning/secrets.

Live check: query the real service and save metrics/log samples; mark token estimates honestly.

Gate: all assignment signals available with bounded cardinality and request correlation. Reference: Step 10 metrics portion.

### S16 — Indexed-poison safety test

Develop: focused injection regression coverage and prompt/validation fixes if observed failures require them.

Tests: tests/test_injection.py indexes a poisoned owned fixture in an isolated test collection and verifies the full retrieval-to-answer path does not accept its malicious instruction. Keep the normal unit test suite offline; invoke this network-dependent integration test explicitly.

Live check: run the same attack against the real selected provider, covering malicious source text and a user override attempt. Inspect grounding/citations and save the observed result.

Gate: genuine indexed retrieval and real-provider evidence exist; a memorized stub answer is insufficient. Do not permanently contaminate the normal corpus. Re-run S10/S11 tests after safety changes. Reference: Step 8 injection portion.

### S17 — Evaluator and regression gates

Develop: unique relevant-match recall@3/@5, citation validity, abstention correctness, by-type aggregation, diagnostic output, separate baseline identities and fail-closed gate semantics.

Tests: eval/tests/test_metrics.py and test_gate.py use hand-calculated cases; cover duplicate hits, empty relevance, grounded-without-citations, undefined/nonfinite metrics, 0.05 vs larger recall drop, 0.95 vs lower validity, one failed abstention and wrong/missing baseline.

Live check: score a local stack and produce valid diagnostic JSON; verify a real degraded response dataset makes the runner exit nonzero.

Gate: gate math correct, no vacuous pass, no automatic baseline refresh, CLI stable. Tell Alishba explicit evaluator test command. Reference: Step 11.

### S18 — Complete real/fixture query integration

Develop: only wiring fixes needed to connect all passed capabilities; no new optional features.

Test: full API/indexer/evaluator regression, Ruff/mypy; explicit real-service integration checks. Index actual CI fixture documents with actual embeddings/Chroma and use evidence-based stub generation.

Live check: ordinary/current/historical/exact/abstain/injection, follow-up, cache hit and re-index invalidation. Use distinct fixture and real result/baseline paths. Coordinate Alishba's cluster run without editing her files.

Gate: end-to-end behavior works and fixture CI can call the exact supplied evaluator command. Baselines remain provisional until S19 chooses shipped settings.

### S19 — Measured configuration selection

Develop: reproducible experiment inputs/reporting, not speculative retrieval redesign.

Validate: three size/overlap configurations with identical golden truth; chunk counts/amplification/recall by type. Test two or three cache thresholds on paraphrase/near-miss examples, record rejected false hit; measure relevance floor separately.

Gate: selected settings justified by real results; final real/fixture baselines created explicitly after absolute gates pass; no cache/dataset contamination. Re-run impacted regression if tuning changes code. Reference: Step 12 tuning.

### S20 — Four controlled stage failures

Develop: isolated experiment configurations; restore shipped behavior after each.

Validate: disable OCR, fixed 100-token/no-overlap chunks, top_k=1 and remove superseded filter. Capture symptoms/diagnosis/metrics/remedy. If a perturbation reveals no failure, report honestly and use another assignment-defined experiment.

Gate: four genuine analyses and restored final passing evaluation. Temporary breakage is absent from release diff. Reference: Step 12 failures.

### S21 — Technical documentation and evidence

Develop: complete CORPUS/PIPELINE/FAILURE-ANALYSIS, ADRs 0002–0004, Jibran engineering contributions/disclosure and application evidence.

Validate: every number links to measured output, code line references match final code, real/fixture baselines distinct, no unimplemented required path/starter placeholders hidden. Run submission checker and assign remaining platform failures to Alishba.

Gate: Alishba can assemble final notes/README/release evidence from accurate handoffs. No fabricated hour-long debugging incident or screenshots. Reference: Steps 13–14.

### S22 — Fresh-clone/release acceptance

Develop: only owner-appropriate fixes discovered by reproducibility verification.

Validate: fresh checkout and README path with Alishba; final full tests/types/lint/coverage/eval; required cluster mismatch/deletion/re-index/cache/persistence behavior; protected evaluation-regression PR and corrected green checks.

Gate: same final revision has passing application evidence and Alishba's successful tested SHA-tagged CD release, required submission links and committed real results/baseline. If platform is unavailable, this gate is BLOCKED, not PASS. Reference: Step 15.

## 6. Prompts Jibran can give an LLM

### Start or resume one sprint

~~~text
Read docs/MY-IMPLEMENTATION-PLAN.md and the ownership/contracts in
docs/IMPLEMENTATION-PLAN.md. Implement the earliest eligible incomplete sprint
in Jibran's scope. Inspect the real code and existing sprint ledger first.
Develop only that capability, add meaningful tests, run focused and impacted
regression checks, fix failures, and perform the mandatory live check.
Update the sprint ledger/evidence with actual commands and results.
Do not edit Alishba-owned files. Do not mark skipped or blocked checks PASS.
Stop after this sprint and give the required sprint report.
~~~

### Execute a specific sprint

~~~text
Execute sprint Sxx from docs/MY-IMPLEMENTATION-PLAN.md.
Confirm prerequisites have passed and their evidence is still valid.
Implement, test, repair and verify its acceptance gate.
Record actual results and report completion or the precise blocker.
Do not proceed to the next sprint.
~~~

### Continue a range automatically

~~~text
Execute sprints Sxx through Syy from docs/MY-IMPLEMENTATION-PLAN.md sequentially.
Run each sprint's tests and mandatory live checks before starting dependents.
Update evidence after every sprint and send concise progress updates.
Continue automatically after a passed gate; do not ask for routine confirmation.
If blocked, work only on another eligible independent sprint in the range;
otherwise report the blocker and stop. Respect ownership and existing permissions.
~~~

### Verify without implementing

~~~text
Audit sprint Sxx against its acceptance criteria and run its required checks.
Report actual pass/fail/blocker evidence and any stale prior results.
Do not change production code or mark a skipped check as passed.
~~~

## 7. Technical implementation reference

The following original low-level steps supply details used by the sprint specifications.
Their sequence is background guidance; the sprint dependency table above controls execution.
Do not treat completing a reference paragraph as test evidence.

### Step 0 — Prepare your Windows workspace

Time box: first 45 minutes, including contract agreement.

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r api/requirements-dev.txt -r indexer/requirements-dev.txt
.\.venv\Scripts\python.exe --version
git status --short
~~~

Run existing tests in their configured directories:

~~~powershell
Push-Location api
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
Push-Location indexer
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
~~~

No virtual-environment activation, Ubuntu terminal or Make command is necessary.

#### Independent local services

Use the same database image versions agreed for deployment. The existing Chroma requirements are pinned to client 1.0.12:

~~~powershell
docker run -d --name rahbar-dev-chroma -p 127.0.0.1:8001:8000 chromadb/chroma:1.0.12
# Replace this placeholder with the exact Redis image tag agreed with Alishba:
$redisImage = '<agreed-version-pinned-redis-image>'
docker run -d --name rahbar-dev-redis -p 127.0.0.1:6379:6379 $redisImage
~~~

If those containers already exist, inspect and reuse them rather than blindly deleting state. These local throwaway containers are not your Kubernetes persistence evidence.

Verify Windows Ollama is already running before starting a second server. Pull the agreed generation and embedding models. Use localhost from Python; Alishba handles cluster-to-host routing.

Native OCR needs Windows Tesseract and Poppler executables on PATH or explicitly configured paths. Installing pytesseract/pdf2image alone is insufficient. Tell Alishba the Linux image equivalents immediately. If native OCR setup blocks you, continue extraction tests with a mocked adapter, then exercise real scans in Alishba's image. Mocks do not satisfy real scan evidence.

**Exit check:** Python 3.12 pinned imports and starter tests pass; local service/model URLs are known.

### Step 1 — Verify the corpus before coding retrieval

Files: corpus/sources.yaml, corpus/MANIFEST.md, docs/CORPUS.md, eval/golden.yaml.

1. Inspect sources.example.yaml and choose real downloadable documents.
2. Verify the old/current policy pair first. Read at least two changed clauses and identify which policy supersedes which.
3. Confirm one genuinely image-only scan using text-layer/extraction/page/font evidence.
4. Count documents and actual pages. Meet at least six documents and forty pages. Assignment PDF and synthetic CI fixtures do not count.
5. Identify a table carrying real information and a long definition; record exact document/page/section.
6. Pick a realistic absent topic and confirm the detailed answer is absent across your included corpus.
7. Run the existing fetcher and inspect every failure:

~~~powershell
.\.venv\Scripts\python.exe corpus/fetch.py
.\.venv\Scripts\python.exe corpus/fetch.py --verify
~~~

8. Commit source URLs/checksums; keep third-party PDFs under ignored corpus/raw/.
9. Write golden questions directly from original documents before tuning. Use filenames actually produced by the fetcher and canonical section labels you intend to preserve.
10. Include minimums: 8 ordinary, 2 version-sensitive, 2 exact-term, 2 absent-topic, 1 injection. Add explicit historical-version questions if useful.
11. Relevant passages must be manually verifiable. Do not copy the retriever's current hits as the expected truth.
12. Optional expect strings support human checks; avoid exact generated-prose assertions as the quality gate.

**Exit check:** all seven corpus properties have evidence, and each golden relevant passage is independently locatable.

### Step 2 — Implement validated settings and internal contracts

Files: api/app/config.py, schemas.py; indexer/pipeline/config.py, models.py.

1. Implement the environment keys frozen in the master plan, including relevance floor, Redis/session/cache settings and provider timeouts.
2. Reject invalid chunk settings: size must be positive and 0 <= overlap < size.
3. Validate positive top_k/TTLs/timeouts and threshold domains appropriate to the similarity metric.
4. Keep API/indexer embedding model and endpoint semantics identical. Generation provider selection must not silently choose a different embedding model.
5. Preserve source, section, page, doc_version and superseded on every chunk.
6. Add an internal ActiveIndex type carrying collection, generation, model and dimension; keep one instance throughout a request.
7. Define provider failures distinctly: timeout, transport, malformed JSON, invalid schema, invalid citations.
8. Extend AskRequest with optional bounded session_id and return it compatibly. Missing session_id means a new standalone conversation.
9. Keep existing response fields and strip reasoning from user responses.
10. Give Alishba the exact settings table, session field contract and native-library needs.

Suggested new modules are design aids, not required abstractions: services/index_state.py, validation.py, cache.py and sessions.py. Keep responsibilities small enough to test without a live service.

**Exit check:** invalid configuration fails clearly, starter clients remain compatible and Alishba can configure deployment without guessing.

### Step 3 — Implement page-aware extraction

File: indexer/pipeline/extract.py; focused tests under indexer/tests/.

1. Dispatch PDF, Markdown/text and HTML as needed for the selected corpus.
2. Extract PDF text page by page, preserving original 1-based page numbers and source filename.
3. Detect missing/near-empty usable text. Render/OCR only affected pages, not every page automatically.
4. Mark OCR pages explicitly and log document/page failures.
5. Inspect the selected table manually. Preserve row/column relationships where possible and document losses rather than assuming extraction is correct.
6. For fixture Markdown, preserve headings and remove leading metadata front matter from content. Discovery already reads the version/superseded fields.
7. For HTML, remove scripts/navigation while preserving headings, paragraph boundaries and table rows.
8. Use bounded page rendering and temporary files with cleanup on failure.
9. A corrupt document must not silently produce a published “complete” partial index. Fail with actionable document/page context.
10. Test PDF/HTML/Markdown dispatch, page numbering, front matter removal, OCR routing and failed extraction using small owned/synthetic samples.

**Exit check:** a text PDF, real scan, fixture Markdown and selected HTML yield inspectable Documents. Save table before/after and OCR losses for PIPELINE.md.

### Step 4 — Implement conservative cleaning

File: indexer/pipeline/clean.py.

1. Normalize line endings and obvious whitespace artifacts without flattening paragraphs.
2. Detect repeated headers/footers using page position and cross-page frequency.
3. Preserve headings, clause numbering, course codes, percentages, decimals such as 2.00, fees and meaningful table rows.
4. Repair line-break hyphenation only with a clear rule; avoid destroying meaningful hyphens.
5. Retain page/source/version/superseded identity.
6. Test removable artifacts and protected content separately.

**Exit check:** the table, long definition and exact numeric rules remain interpretable. Record a removed artifact and something deliberately preserved.

### Step 5 — Implement deterministic structured chunks

File: indexer/pipeline/chunk.py.

1. Identify sections and assign canonical section labels matching the golden-set convention.
2. Split sections into paragraphs, then sentences when over budget.
3. Define a deterministic fallback for an oversized sentence/table row.
4. Use a documented token counter. If approximate, say so and use it consistently across all experiments.
5. Enforce target size and overlap; guard against infinite loops and invalid settings.
6. Keep overlap within sensible section boundaries rather than mixing unrelated headings.
7. Preserve all required metadata. Define which original page represents a cross-page chunk.
8. Generate stable IDs from document identity/version/section/position/content with a deterministic digest, not Python's randomized hash().
9. Count original tokens before overlap and stored tokens after chunking for amplification.
10. Test target bounds, overlap, headings, stable IDs, metadata, page behavior and pathological input.

**Exit check:** identical input/settings yield identical chunks/IDs and no chunk loses identity. Keep (250,30), (400,50), (650,80) as experiment candidates, not unmeasured shipped choices.

### Step 6 — Implement embedding and safe index publication

Files: indexer/pipeline/embed.py, store.py, run.py; API-side index reader.

1. Batch model calls with explicit embedding model, bounded timeout and clear failure messages.
2. Verify vector count equals text count; every vector is finite, nonempty and the same dimension.
3. Create a new uniquely versioned collection configured for cosine distance.
4. Write IDs/text/explicit vectors/metadata in bounded batches. Do not rely on Chroma's implicit embedding function.
5. Record actual model, dimension, generation, corpus/settings identity and build time.
6. Validate count and representative metadata before publication.
7. Use a small Chroma control collection's metadata to publish active collection/generation together. Verify actual client/server behavior; do not assume cross-collection transactions.
8. API resolves that metadata without creating/modifying collections.
9. Preserve old active collection on failed builds and retain previous collections for in-flight requests/rollback.
10. Define bounded cleanup with a grace period. Never delete serving data before replacement validation.
11. Prevent overlapping publishers with a real lock or a documented/tested single-writer/manual-preflight procedure. CronJob Forbid does not block independent manual Jobs.
12. Log stage counts/durations, and return nonzero on incomplete indexing.
13. Test failed publication, successful switch, model/dimension metadata, rebuild behavior and last-known-good reads.

Local invocation after implementation:

~~~powershell
$env:CORPUS_DIR = (Resolve-Path corpus/raw).Path
$env:CHROMA_HOST = '127.0.0.1'
$env:CHROMA_PORT = '8001'
$env:CHROMA_COLLECTION = 'rahbar'
$env:EMBED_MODEL = 'nomic-embed-text'
$env:OLLAMA_URL = 'http://127.0.0.1:11434'
Push-Location indexer
..\.venv\Scripts\python.exe -m pipeline.run
Pop-Location
~~~

**Exit check:** real vectors/metadata exist, failed rebuild preserves old data and only indexer writes Chroma.

### Step 7 — Implement retrieval and compatibility guardrails

Files: api/app/retrieval/chroma.py, index-state helpers, main.py as needed.

1. Resolve one ActiveIndex per request. Reuse it for retrieval and cache even if publication changes mid-request.
2. Compare recorded model/dimension with the API's configured/actual embedding capability. Log expected versus actual values.
3. Refuse readiness on mismatch; do not silently serve incompatible vectors.
4. Avoid eager dependency connections that prevent /healthz from running when Chroma is down. Readiness can report dependency failures.
5. Embed questions with exactly the indexed model and consistent query/document formatting where required.
6. Query explicit vectors with configured top_k and metadata filters; handle small/empty collections safely.
7. Default to nonsuperseded documents. Interpret explicit historical requests conservatively and filter to the requested version.
8. Course numbers, fees and unrelated dates must not accidentally select old policies.
9. Convert cosine distance to higher-is-better similarity consistently.
10. Map valid metadata into Passage objects. Missing source/page information is an integrity issue, not permission to invent it.
11. If no evidence clears RELEVANCE_FLOOR, return an uncited abstention before generation.
12. Test filtering, historical selection, no hits, conversion, mismatches, malformed metadata and threshold boundaries.

**Exit check:** ordinary/current/historical questions retrieve the intended clauses, and unsupported questions cannot automatically proceed to confident generation.

### Step 8 — Implement constrained generation and grounding

Files: api/app/providers/llm/ollama.py, provider base/factory, services/answer.py and validation helpers.

1. Build instructions requiring evidence-only answers, missing-information acknowledgement, schema output and treatment of embedded instructions as data.
2. Delimit numbered evidence and preserve source/section/page identifiers; place the question after the evidence.
3. Use the provider's schema-constrained mechanism with Answer's JSON schema and configured low temperature.
4. Parse and validate with Pydantic even when constrained generation is enabled.
5. Verify each citation source/section/page against evidence retrieved for this request.
6. Require claim-bearing sentences to use the assignment's [source / section] citation form. Add a bounded format/consistency check and document its limits; string checks alone cannot establish factual truth.
7. Reject groundedness claims without evidence/citations or inconsistent abstention responses.
8. On invalid output, retry once with concise validation feedback. Two total attempts, not nested unbounded retries.
9. On repeated invalid output return a safe canned response: false groundedness, no fabricated citations, low confidence, recorded fallback.
10. Handle timeout/transport failures safely with bounded total latency; no traceback/provider secrets in user output.
11. Keep reasoning out of the response and user-facing logs.
12. Support one real provider fully. Remove unused optional implementation placeholders or reject unsupported modes explicitly during configuration.
13. Make CI stub generation use actual retrieved evidence, not memorized correct answers regardless of retrieval.
14. Test malformed JSON, wrong schema, bad citations, successful retry, repeated failure, timeout, empty evidence and reasoning removal.
15. Index poisoned content and test the query path. Also run the real provider against poisoned evidence and record observed behavior; a hard-coded stub alone does not establish model robustness.

**Exit check:** real grounded answer/refusal work, fabricated citations cannot escape, and malformed output never causes an unhandled 500.

### Step 9 — Implement Redis sessions and semantic cache

Suggested files: services/sessions.py, cache.py, orchestration changes.

1. Store bounded conversation turns in Redis with SESSION_TTL_SECONDS; validate IDs and prevent accidental session mixing.
2. Missing ID creates a standalone conversation. Existing history conservatively marks follow-up and skips semantic cache reads/writes.
3. Return session_id and tell Alishba the exact payload behavior for UI reuse.
4. Use bounded history to resolve elliptical follow-up questions for retrieval/generation. Merely bypassing cache does not make follow-up answers meaningful.
5. Resolve/check the active index before cache use.
6. Include index generation, embedding model, generation model/temperature and prompt version in cache identity.
7. Embed a standalone question once; reuse its vector for cache comparison and retrieval.
8. Store normalized question vectors and validated answer/evidence records in Redis.
9. Search a bounded candidate set and calculate cosine similarity. Enforce TTL and CACHE_MAX_ENTRIES; do not scan an unbounded database per query.
10. Hit only at/above threshold for compatible identity and intact evidence.
11. Cache only validated in-scope grounded standalone answers. Never cache abstentions, follow-ups, provider failures, invalid answers or fallbacks.
12. New published generation makes old keys inaccessible; TTL later retires them. Test with a changed policy answer, not just a changed string.
13. Set X-Cache HIT/MISS/BYPASS and record counters.
14. Test paraphrase positives and numeric/version/course-code near misses. Add critical-term compatibility rules if measured false hits warrant them.
15. Define Redis outage behavior consistently with readiness and safe request handling.

**Exit check:** useful safe paraphrase hit, near-miss rejection, shared isolated sessions across replicas, follow-up bypass and demonstrated invalidation.

### Step 10 — Implement readiness and complete observability

Files: routes/health.py, routes/metrics.py, main.py, logjson.py and service helpers.

1. /healthz remains process-only 200 regardless of database/model outages.
2. /readyz checks Chroma reachability, published active collection, nonempty contents, model/dimension compatibility and Redis.
3. Bound dependency-check time; return 503 with failed dependency names and nonsecret diagnostics.
4. Revalidate on active generation changes; a startup-only model check is insufficient after re-indexing.
5. Log JSON stdout with propagated/generated request IDs.
6. Per-query outcome includes top_k, IDs, similarity scores, abstention/cache/fallback status and timings.
7. Expose retrieval/generation histograms; cache hit/lookups; abstention/fallback counters; token-in/out counters plus per-request token log fields.
8. Label estimated token counts honestly when provider usage is unavailable.
9. Never use request/session/chunk IDs as Prometheus labels; keep cardinality bounded.
10. Avoid logging credentials, raw reasoning and unrestricted conversation histories.
11. Test each readiness dependency failure and metrics through actual success/failure paths.

**Exit check:** Alishba can demonstrate incompatible-model not-ready behavior and scrape all required metrics.

### Step 11 — Implement evaluator and meaningful gates

Files: eval/run_eval.py, eval/tests/**, eval/fixtures/baseline.json, eval/baseline.json, eval/results.json.

1. Define documented exact/canonical source-section matching; do not fuzzy-match unrelated clauses.
2. Recall denominator is unique known relevant passages. Numerator is unique relevant matches within first k results. Duplicates cannot inflate recall above 1.
3. No relevant passages means no recall score, not automatic perfect recall.
4. Citation validity compares actual citations against retrieved source/section/page evidence.
5. Handle no-citation answers explicitly: a purported grounded answer with no citations cannot pass through vacuous 100% validity.
6. Report recall@3/@5 overall and by type, citation validity and must-abstain correctness with denominators.
7. Document macro/micro aggregation. Keep per-question diagnostic output.
8. Missing/nonfinite/undefined required metrics must not silently pass.
9. Gate recall@5 drop greater than 0.05, citation validity below 0.95, and any incorrect must-abstain answer.
10. Test boundaries: exactly 0.05 drop passes; greater fails; 0.95 citations passes; lower fails; one failed abstention fails.
11. Identify dataset, configuration, embedding model, generation and source revision in results/baselines.
12. Keep real and fixture baselines distinct; reject accidental cross-dataset comparison.
13. Baseline creation is explicit and reviewed after absolute gates pass. Never refresh it automatically in CI to conceal regression.
14. Keep the agreed CLI stable and nonzero exits reliable.
15. Tell Alishba the explicit evaluator test invocation: existing API/indexer pytest settings do not automatically discover eval/tests/.
16. Define explicit missing-baseline bootstrap behavior before using --update-baseline; ordinary regression CI must require its baseline.

Example after implementation:

~~~powershell
.\.venv\Scripts\python.exe eval/run_eval.py --api http://127.0.0.1:8000 --golden eval/golden.yaml --baseline eval/baseline.json --out eval/results.json
~~~

For Ingress use Alishba's tested URL and --host rahbar.local when applicable. Fixture output/baseline paths must be separate.

**Exit check:** hand-calculated cases match, each gate demonstrably fails when appropriate, fixture CI uses its own baseline and shipped real metrics are committed.

### Step 12 — Run measured experiments on Day 2

Freeze the golden set before tuning. Reserve time for interpreting results, not just running commands.

#### Chunking

1. Run (250,30), (400,50), (650,80) with the same corpus, embedding model and evaluator.
2. Deliberately select the experimental index and avoid cache contamination.
3. Record recall@3/@5 and by-type results, chunk count, original/stored token counts and amplification.
4. Inspect wrong version/exact questions and the long-definition case.
5. Select the shipped configuration using measured tradeoffs and commit the table.

#### Cache/relevance thresholds

1. Prepare paraphrase-positive and near-miss pairs, including changed years/numbers/course codes.
2. Try two or three thresholds against the same examples.
3. Choose the lowest tested cache threshold with zero false hits; demonstrate at least one useful paraphrase hit.
4. Save the false-hit counterexample rejecting a lower threshold.
5. Independently measure the relevance floor using answerable/absent-topic questions. Cache threshold and retrieval relevance floor are different decisions.
6. State limitations of the small tuning set honestly.

#### Four controlled failure experiments

Use a separate experimental configuration and restore after every run:

1. Disable OCR for the scanned material.
2. Use fixed 100-token chunks without overlap.
3. Reduce top_k to 1.
4. Remove superseded filtering and ask version-sensitive questions.

Record exact change, question, before/after observation, symptom, metric/log evidence, diagnosis and remedy. If a chosen change reveals no failure, report it and try another assignment-defined perturbation. Do not invent a regression.

**Exit check:** three chunk measurements, measured thresholds, four actual analyses and restored final results.

### Step 13 — Hand off application integration

Send Alishba one concise note with:

- Complete configuration and native OCR requirements.
- Supported provider/stub modes.
- Active-index discovery and readiness expectations.
- Session field and cache header contract.
- Real/fixture indexing/evaluator/test commands, baseline paths and exit codes.
- Reproduction steps for model mismatch, absent-topic refusal, cache hit, follow-up bypass and invalidation.

Save app evidence under docs/evidence/app/. Alishba owns platform evidence.

For the protected-branch demonstration, supply a genuine regression such as disabling version filtering. Alishba configures required checks/captures blocked merge; you fix the actual application regression. Do not substitute an unconditional failing shell command.

**Exit check:** Alishba can deploy/evaluate your revision without guessing internals or modifying Python.

### Step 14 — Finish technical documentation

Your deliverables:

1. CORPUS.md: concrete seven-property evidence.
2. PIPELINE.md: OCR/table losses, cleaning rules, token counting, chunk experiments/amplification, metadata, embedding pin/dimension, publication, cache/relevance tuning and evaluation matching/aggregation.
3. FAILURE-ANALYSIS.md: four real experiments and diagnostic signals.
4. ADR 0002: measured chunking choice/alternatives.
5. ADR 0003: Redis, bounded semantic search, safe-cache rules, sessions, invalidation/alternatives.
6. ADR 0004: provider, schema/temperature, outbound data handling, user question/session retention.
7. docs/notes/jibran.md: actual file/line references and findings for engineering questions 1/2/3/5/6, your real debugging incident, and indexer-memory interpretation coordinated with Alishba.
8. docs/AI-USAGE-JIBRAN.md: tools, precise contribution, your changes and reasons; Alishba assembles the final required disclosure.

Do not invent a debugging story lasting an hour. Record real incidents while working. Refresh line references after final code changes.

### Step 15 — Final acceptance

~~~powershell
.\.venv\Scripts\python.exe -m ruff check api indexer eval corpus
Push-Location api
..\.venv\Scripts\python.exe -m mypy app
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
Push-Location indexer
..\.venv\Scripts\python.exe -m mypy pipeline
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
# After evaluator tests exist at this path:
.\.venv\Scripts\python.exe -m pytest -q eval/tests
.\.venv\Scripts\python.exe scripts/check_submission.py
git status --short
~~~

Have Alishba configure coverage tooling and verify at least 60% on implemented app code. The starter's 83% is not final evidence. Native command failures must propagate in PowerShell scripts.

On the final live stack verify:

- Ordinary grounded answer with inline citations and matching citation objects.
- Current policy default and deliberate historical request.
- Exact clause/threshold retrieval.
- Every must-abstain false.
- Real-provider poisoned-evidence behavior.
- Invalid provider output retries once/falls back safely.
- First indexing, Redis/Chroma outage, incompatible model and successful re-index readiness.
- Paraphrase cache hit, near-miss rejection, follow-up bypass and post-reindex invalidation.
- Final metrics/baselines/results match shipped settings and pass gates.
- Fresh-clone README path works together with Alishba.

Your work is complete when these behaviors pass, documentation/evidence is committed and Alishba can release the same revision through protected CI/CD.

### Two-day priorities and recovery

Day 1 morning: environment, corpus and independent golden questions.
Day 1 afternoon: complete real indexing, then retrieval/generation safety.
Day 1 evening: cache/sessions, readiness/metrics and combined end-to-end check.
Day 2 morning: evaluator, CI integration and chunk measurements.
Day 2 afternoon: threshold/failure experiments, final tests and evidence.
Day 2 evening: documentation, clean-clone verification and release review.

Your workload is intentionally larger. Cut optional provider modes, UI ideas, streaming, elaborate abstractions and advanced retrieval first. Preserve real indexing, model guardrail, grounding/refusal, cache/session correctness, evaluation, required experiments and evidence. If needed, use contingency rather than weakening the checker or claiming incomplete work is done.


## Current execution status (5 November 2026)

Jibran's application sprints S00-S21 have passed; see [the ledger and final platform handoff](notes/jibran.md). Jibran authorized local commits directly on main and confirmed that the platform files have not been developed and will be developed separately. Preserve the ownership separation above. S22 fresh-checkout application checks passed, including 299 tests, types/lint/coverage and real/fixture baseline evaluations. Full S22 release acceptance is BLOCKED by the absent platform; local success does not establish a release. [The S22 report](evidence/app/sprints/S22.md) records the exact tested revision, measurements and remaining requirements.
