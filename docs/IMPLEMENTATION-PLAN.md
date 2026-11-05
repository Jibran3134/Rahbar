# RAHBAR: two-day Windows implementation plan

Updated: 4 November 2026. This revision replaces the previous Ubuntu-based schedule and ownership assignments.

Target development days: 5–6 November. Assignment deadline: 8 November 2026, 23:59 PKT. Preserve 7 November for recovery.

## 1. Environment and capacity

Development uses Windows, PowerShell, Python 3.12 in a project virtual environment, Docker Desktop in Linux-container mode, minikube, kubectl and Git. Developing inside Ubuntu, a WSL terminal, GNU Make or Bash is not required. Docker Desktop may use WSL 2 internally; Linux containers and Linux CI runners remain appropriate deployment environments.

You are Jibran, the application and RAG lead. You receive the larger, harder, correctness-critical scope: corpus, indexing, retrieval, generation, grounding, cache/sessions, readiness, metrics, evaluation and experiments.

Alishba is the platform and delivery lead: images, Kubernetes, Windows automation, CI/CD, registry publishing, infrastructure evidence and operational documentation. This is substantial required engineering.

Budget approximately 25–28 focused hours for Jibran and 21–24 for Alishba across the two days. Jibran's allocation is intentionally heavier at your request. This is aggressive; the reserved day is contingency, not a guarantee. Cut optional work before sacrificing mandatory validation.

Jibran's detailed low-level sequence is in [MY-IMPLEMENTATION-PLAN.md](MY-IMPLEMENTATION-PLAN.md).

## 2. Exclusive ownership

Every file has one writer. Both partners review PRs, but fix requests go to the file owner.

| Owner | Exclusive files | Work |
| --- | --- | --- |
| Jibran | api/app/**, api/tests/**, api/requirements*.txt, api/pyproject.toml | All application code, contracts, settings, providers, retrieval, safety, cache, sessions, readiness, metrics, app tests/dependencies |
| Jibran | indexer/pipeline/**, indexer/tests/**, indexer/requirements*.txt, indexer/pyproject.toml | All five indexing stages, publication, metadata, tests/dependencies |
| Jibran | corpus/**, eval/** | Corpus, golden questions, evaluator, real/fixture baselines and measurements |
| Jibran | docs/CORPUS.md, docs/PIPELINE.md, docs/FAILURE-ANALYSIS.md | Technical evidence and experimental findings |
| Jibran | docs/adr/0002-chunking.md, docs/adr/0003-semantic-cache.md, docs/adr/0004-llm-provider-and-data-governance.md | Application decisions |
| Jibran | docs/MY-IMPLEMENTATION-PLAN.md, docs/evidence/app/**, docs/notes/jibran.md, docs/AI-USAGE-JIBRAN.md | Personal plan, app evidence and document contributions |
| Alishba | api/Dockerfile, api/.dockerignore, indexer/Dockerfile, indexer/.dockerignore, ui/** | Images, native dependencies, UI deployment/session integration |
| Alishba | k8s/**, .github/**, scripts/**, Makefile, .gitignore | Infrastructure, pipelines, Windows helper scripts |
| Alishba | README.md, LICENSE, docs/ARCHITECTURE.md, docs/adr/0001-indexer-as-job.md | Operational documentation and deployment reasoning |
| Alishba | docs/evidence/platform/**, docs/notes/alishba.md, docs/ENGINEERING-NOTES.md, docs/AI-USAGE.md | Platform evidence and final document assembly |
| Alishba | docs/IMPLEMENTATION-PLAN.md after this revision | Master plan maintenance |

Alishba assembles engineering notes using Jibran's actual measurements/file references and combines AI disclosures into the required final AI-USAGE.md. Jibran reviews technical accuracy; Alishba remains the only writer of assembled documents.

Do not weaken the supplied checker or alter the assignment requirements to hide missing work.

## 3. Independent development

Independent means separate files and independently runnable development paths. The final application and deployment still require scheduled integration.

- Jibran uses localhost Chroma/Redis containers, Windows Ollama and fake clients. Jibran does not wait for manifests or Dockerfiles to implement Python.
- Alishba deploys the existing stub API/UI, exercises the dummy indexer, and builds lint/manifests/build/scan jobs before real application code is ready.
- Each partner uses a separate clone or worktree/branch. Do not switch branches under the other partner in one shared working directory.
- Integrate through reviewed PRs into dev; release through protected main. Both partners commit under their own identities.
- If a contract changes, the owner supplies an exact migration note. No silent changes to environment names, services, CLI flags or response fields.

## 4. Freeze these contracts in the first 45 minutes

| Boundary | Agreed contract |
| --- | --- |
| API entry point | uvicorn app.main:app --host 0.0.0.0 --port 8000; working directory contains app/ |
| Indexer entry point | python -m pipeline.run; working directory contains pipeline/; nonzero exit on failed/incomplete indexing |
| Stub mode | RETRIEVER=stub and LLM_PROVIDER=stub; offline unit tests |
| Production mode | RETRIEVER=chroma and LLM_PROVIDER=ollama-host initially; one fully working real provider required |
| API | POST /api/ask; question length 3–500; preserve existing response fields |
| Sessions | Optional request session_id; omitted means standalone first turn; response may return session_id. Alishba updates UI to reuse it. Follow-ups share Redis state and bypass semantic cache. |
| Probes | /healthz process-only; /readyz requires reachable Chroma, published nonempty active index, compatible model/dimension and reachable Redis; otherwise 503 naming failures |
| UI | nginx port 8080 and writable /tmp; Ingress routes /api directly to API |
| Embedding | Same EMBED_MODEL/service for indexer and API; start with nomic-embed-text; verify actual dimension |
| Generation | Start with llama3.2:3b, temperature 0.2; verify latency/memory early |
| State services | Chroma port 8000; Redis port 6379; both ClusterIP/persistent in Kubernetes |
| Corpus delivery | CORPUS_DIR contains documents and optional _index.json; Alishba provides a fetch/init-volume path for real data and a separate fixture path |
| Cache visibility | X-Cache: HIT, MISS or BYPASS; cached evidence tied to active index generation |
| Evaluation CLI | python eval/run_eval.py --api URL --golden PATH --baseline PATH --out PATH; optional --host; nonzero on failed gate/invalid execution |
| Runtime dependencies | Jibran owns Python pins; Alishba installs them without separate duplicate workflow pins and supplies native OCR libraries |

Jibran implements and Alishba supplies these configuration keys:

RETRIEVER, LLM_PROVIDER, EMBED_MODEL, OLLAMA_URL, LLM_MODEL, TEMPERATURE, CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION, CORPUS_DIR, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, RELEVANCE_FLOOR, REDIS_URL, CACHE_THRESHOLD, CACHE_TTL_SECONDS, CACHE_MAX_ENTRIES, SESSION_TTL_SECONDS, LLM_TIMEOUT_SECONDS, LOG_LEVEL.

Thresholds remain provisional until measured. Credentials belong in Secrets. The cache namespace also includes generation settings/prompt version so different model behavior cannot share stale answers.

### Index publication: Jibran owns the complete implementation

Build a versioned Chroma collection, validate all vectors/metadata/counts, then publish its name and generation together through a small control collection's metadata. Verify the chosen client's publication semantics and test failure around the switch; do not assume a cross-collection transaction.

API only reads Chroma. Indexer alone writes it. Each query resolves one active generation and uses that identity for retrieval/cache throughout the request. Old cache entries become inaccessible by generation and expire by TTL. Retain previous collections for in-flight readers/rollback and document cleanup.

Indexer does not need Redis access, preserving the assignment's API-only Redis network access. Alishba sets CronJob concurrencyPolicy: Forbid. This alone does not prevent separately created manual Jobs: Jibran must implement an actual writer lock or document a reliable single-writer/manual-preflight procedure and its limits.

## 5. Windows setup

Run from the repository root:

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r api/requirements-dev.txt -r indexer/requirements-dev.txt
docker version
kubectl version --client
minikube version
~~~

Do not rely on the current global Python 3.14 environment. Activation is optional; explicit venv executables avoid PowerShell activation-policy issues.

Start the starter API in a dedicated terminal:

~~~powershell
$env:RETRIEVER = 'stub'
$env:LLM_PROVIDER = 'stub'
$env:SERVE_UI_DIR = '../ui'
Push-Location api
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
# After stopping:
Pop-Location
~~~

Use Invoke-RestMethod for JSON; use curl.exe when literal curl behavior is needed. Use PowerShell environment assignment, Join-Path/pathlib and Windows venv paths. Scripts must check native exit codes so a later successful command does not hide an earlier failure.

Alishba adds scripts/dev.ps1 with setup/test/lint/cluster/images/apply/index/eval/check tasks and documents it in README. Until then, use direct commands. Linux CI can retain the Makefile/Bash.

Native OCR needs Windows Tesseract and Poppler executables or a documented container OCR path, not just Python wrappers. Alishba installs Linux equivalents in the indexer image.

Alishba verifies minikube tunnel/Ingress on Windows and documents any elevated permissions required by the installed setup. Local Python calls localhost Ollama; cluster workloads use a verified host address/binding/firewall configuration.

## 6. Day 1: independent build, then integration

Times are PKT. Take meal breaks around 12:30 and 19:00 and short breaks within long blocks.

| Time | Jibran's work | Alishba's work | Checkpoint |
| --- | --- | --- | --- |
| 09:00–09:45 | Python setup, ownership/contracts, application branch | Docker/minikube setup, platform branch, branch protection | Interfaces fixed and independent work possible |
| 09:45–12:30 | Verify seven corpus properties; fetch manifest; write 15+ golden questions before tuning | Dockerfiles, Windows helper, namespace/config/state services, stub API/UI/Ingress | Corpus review and independently deployed stub |
| 13:00–16:00 | Extract/clean/chunk/embed/store and focused tests | Jobs/CronJob, overlays, persistence, probes/resources/security | Real local index; dummy Job works on cluster |
| 16:15–19:00 | Retrieval, version filters, real provider, validation/citations, abstention | CI lint/test/manifests/build/scan, CD skeleton, fixture service provisioning | Real local cited answer and refusal |
| 19:45–22:00 | Sessions/cache, readiness/model guardrail, generation consistency, metrics | Deploy Jibran's image; verify model reachability, policies, PVCs/HPA | Combined full query path |
| 22:00–23:00 | Integration fixes; start evaluator if capacity allows | CI wiring against fixed evaluator CLI; capture platform defects | Day 1 real end-to-end milestone |

Jibran's scope is deliberately heavier. If cache/readiness is unfinished, use the first Day 2 block; Alishba continues CI without editing Python files. Missing the real-answer milestone means optional work stops immediately.

## 7. Day 2: evaluation, evidence, delivery

| Time | Jibran's work | Alishba's work | Checkpoint |
| --- | --- | --- | --- |
| 09:00–11:00 | Finish evaluator/gate tests and Day 1 safety blockers | Bring fixture e2e CI green with real Chroma/embeddings and stub generation | Genuine retrieval scored with separate fixture baseline |
| 11:00–12:30 | Three chunk configurations and category recall | Finish test → SHA build/push → ephemeral deploy → Ingress smoke | Measurements and first full CD attempt |
| 13:00–15:00 | Cache/relevance experiments, four failures, behavior tests | top/endpoints/HPA, deletion/persistence/policies, rollout/undo evidence | Real recorded experiments/demonstrations |
| 15:15–17:00 | Freeze baselines, genuine regression PR, app evidence | Protected merge failed/green proof, successful CD/registry evidence | Working quality gate and protected delivery |
| 17:00–19:00 | Technical docs/ADRs, engineering contributions and disclosure | README, architecture, ADR 0001, final notes/disclosure assembly | Documentation matches shipped behavior |
| 19:45–21:30 | Fresh-clone answers/cache/evaluation checks | Fresh provisioning/Ingress checks and fixes | README works without hidden setup |
| 21:30–23:00 | Final lint/types/tests/evaluation and review | Final manifests/scans/checker/release/submission links | Ready submission package |

No streaming, authentication, UI redesign, second real provider, in-cluster generation or elaborate dashboards. Hybrid retrieval is optional unless needed for acceptable measured behavior; explain exact-term weaknesses honestly.

## 8. Alishba's independent deliverables

1. Three pinned, non-root images with exec startup, build exclusions, indexer OCR native packages and appropriate writable temporary mounts.
2. Namespace rahbar; API 3 replicas; UI; Chroma StatefulSet with claim templates; Redis/PVC; Job/CronJob; four ClusterIP Services; Ingress; ConfigMap/Secret handling; HPA 3–8; ServiceAccounts.
3. Three API probes, requests/limits for every container, maxSurge 1/maxUnavailable 0, termination grace/preStop.
4. Non-root/read-only/drop-capabilities security, token automount disabled where appropriate, default-deny policies with verified DNS/service/model traffic and denied UI-to-Chroma.
5. Portable real/fixture corpus delivery and Windows image/Ingress/model setup.
6. CI: Ruff/mypy, tests/≥60% app coverage, strict Kustomize/kubeconform, builds without PR publishing, Trivy fixable HIGH/CRITICAL gates, ephemeral cluster, fixture indexing/evaluation.
7. CD: test → build/push → deploy, explicit needs, least permissions, GitHub Secrets, Docker Hub SHA tags, rollout wait, Ingress smoke test.
8. Evidence: protection/blocked merge/green merge, resource measurements, endpoints/HPA, pod deletion, persistence, re-index availability, model mismatch, policies, rollout/undo.
9. README, architecture, ADR 0001, assembled notes/disclosure, compatible license verification and Classroom links.

CI uses genuine fixture embeddings/retrieval and a deterministic evidence-based generation stub. Provision embeddings locally in CI; do not rely on a developer's host Ollama or external generation account. Keep fixture and real baselines distinct.

## 9. Integration and final acceptance

Jibran supplies native dependencies/config keys immediately; Alishba supplies verified service URLs/build contexts. At Day 1 noon review corpus and stub deployment. At Day 1 close integrate real answers, refusal, cache/session behavior and readiness. Day 2 morning integrate the evaluator and fixture baseline.

Before freeze:

- Verify 6 documents/40 pages and all seven corpus properties.
- Golden set: minimum 8 ordinary, 2 version, 2 exact, 2 abstain, 1 injection; written before tuning.
- Real five-stage indexing, required metadata, safe publication, same embedding model/dimension, version filtering.
- Constrained real generation, citation checking, retry once/fallback, honest refusal, indexed-poison test and real-provider check.
- Shared sessions, follow-up bypass, safe semantic cache, measured thresholds, re-index invalidation.
- Readiness/liveness, request IDs, all required stage/cache/abstention/fallback/token metrics.
- Three chunk experiments, four failure experiments, real and fixture results/baselines.
- Recall@5 regression fails beyond 5 percentage points, citation validity ≥95%, all must-abstain correct; undefined metrics cannot silently pass.
- Required Kubernetes security/persistence/resources/probes/network/rollout/HPA behavior exercised.
- Lint/types/tests/≥60% coverage/manifests/scans pass; checker reviewed rather than gamed.
- Four ADRs, seven engineering answers, AI disclosure, evidence, README and clean-clone acceptance complete.
- Successful protected SHA-tagged CD release and submission links ready.

If two days prove insufficient, preserve required behavior/evidence, cut optional scope and use contingency. Do not declare completion from passing starter tests or empty deliverable files.

