# ADR 0004: provider contracts and data governance

## Status

Implemented through S21 on 5 November 2026. Native application checks passed; Jibran's human review and Alishba's platform integration review remain pending. S22 release acceptance requires the platform work, which Jibran confirmed has not been developed yet. Earlier implementation states remain in individual sprint reports.

## Context and decision

Three API replicas need one index identity and shared conversation/cache state. The API and indexer have independent build contexts. They use small separate identity representations protected by a wire-contract test, without importing each other's production packages.

Supported modes are `stub` and `ollama-host`; unsupported `hosted` and `ollama-incluster` fail configuration. Hosted compatibility fields do not enable a provider. Configuration parsing makes no network calls. Generation and embedding models remain separate: selected native models are llama3.2:3b and nomic-embed-text (768 dimensions). Runtime digests are recorded in evidence; mutable names do not enforce immutable model contents.

The four-key active identity is collection/generation/embed_model/dimension. Publication validates a new generation before activation; requests resolve one immutable generation and enforce model and actual vector dimension. Conflicts produce sanitized 503 responses with expected/actual model or dimension diagnostics. APIs never build an index at startup.

Generation uses the Answer JSON schema, temperature .2, output cap 512, context 4096 and configured 60-second HTTP timeout. Strict parsing and an independent request-local citation validator follow generation. One validation retry is allowed; timeout/transport failure immediately falls back. Repeated invalid output becomes an uncited low-confidence refusal. Reasoning never reaches HTTP responses or application logs.

The Ollama adapter may render already verified citation objects into inline tags when all triples match supplied evidence and only one source/section pair is involved. It cannot invent objects or repair unknown references. Citation validity is not semantic entailment: the real final report includes an incomplete q17 heading despite valid evidence. Conservative quarantine of obvious assistant-directed overrides passed the actual indexed-document/user attacks after an earlier observed escape. It can remove useful ambiguous text and is not universal injection protection. Failed experiments remain available in S19 evidence.

Selected measured settings are chunks 250/overlap 30, query relevance floor .74 and cache threshold .95. A query with no valid hit clearing the floor refuses; otherwise all valid top-k context is retained. ADRs 0002/0003 and S19 measurements document the limited calibration sample and tradeoffs.

## Shared state and retention

AskRequest/AskResponse retain their existing fields and add optional nullable session_id, restricted to 1-128 ASCII letters/digits/underscores/hyphens. Existing clients can omit it. The API issues unpredictable identifiers; unknown supplied IDs are rotated. Redis stores at most six bounded turns (question 500, answer 1000 characters), with default TTL 1800 seconds refreshed transactionally on append. These IDs are bearer access to conversation state, not authenticated user identities. Supported follow-ups use the preceding user question; stored assistant output never becomes trusted evidence. Clients should serialize concurrent turns, which otherwise complete in completion order.

Semantic cache is internal trusted Redis state: bounded 256 candidates per generation/model/provider/prompt/settings namespace, default logical TTL 3600 seconds, key expiry and pruning. Expired entries are excluded from use; physical bytes may remain until pruning or key expiry. Reindexing changes namespaces without promising immediate deletion of old keys. Only validated grounded non-low-confidence standalone answers are cached. Existing sessions bypass cache; version/numeric/negation/topic guards supplement cosine similarity. This is not a general proof that two questions mean the same thing. API replicas must share Redis and identical settings.

## Data governance

Only public FAST-NUCES corpus material and test questions were sent to local Ollama at 127.0.0.1:11434. No hosted generation provider was used. Model/container downloads contacted their registries. Deployment endpoints remain configurable; platform reviewers must verify their actual destinations before using private data. No private user corpus or account credentials belong in committed evidence.

Session/cache state resides in Redis and contains questions/answers; deployment must control network access, persistence/backups and retention according to its actual requirements. Current tests demonstrate application TTL behavior, not deletion from backups or a production privacy policy. Full original/extracted corpus and runtime environments remain ignored locally.

Settings repr hides Redis URLs and API keys; invalid-URL messages name configuration keys without credentials. This is not encryption. Never log raw environments or serialize secret-bearing settings. Structured query logs contain IDs, chunk IDs, scores, timing, token counts and outcomes; they omit raw conversation histories, provider reasoning and secrets. Public-source failure diagnostics are separately labeled evidence.

## Consequences and validation

Rejecting unsupported modes makes failures actionable before traffic. Optional sessions preserve old callers. Separate packages preserve independent image contexts but require contract tests to stay aligned. Shared Redis and Chroma are required dependencies for real mode; healthz remains process-only and readyz tests dependencies with bounded operation waits.

S02-S21 reports contain actual tests, native probes and rejected approaches. No dependency pins were changed. S19 real returned-evidence recall@5=.933333, citation integrity=1 and required abstentions=1; five diagnostic expect misses remain documented. Fixtures score 1 throughout. These application results do not certify Linux image OCR, Kubernetes probes/HPA/resources, persistence across cluster deletion, protected CI/CD or production release; those are pending S22 platform acceptance.
