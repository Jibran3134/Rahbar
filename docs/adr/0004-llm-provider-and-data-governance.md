# ADR 0004: provider contracts and data governance

## Status

S02 contracts and S06–S11 embedding/provider/grounding behavior implemented on 5 November 2026 under Jibran's approved sprint plan. Jibran's human review and Alishba's integration review are pending. Sessions/cache/readiness and later acceptance gates remain incomplete.

## Context

The starter accepts provider names whose real implementations raise NotImplementedError and ignores an undeclared session field. Three API replicas will require shared session state, explicit failure handling and one coherent index identity. API and indexer images have independent build contexts, so importing one workload's package into the other is inappropriate.

## Decision

- Configuration accepts `stub` and the selected `ollama-host` mode; both are implemented and tested. Unsupported `hosted` and `ollama-incluster` selections fail during configuration instead of reaching an unimplemented request path. Existing hosted settings remain inert compatibility fields; they do not enable that mode.
- Model generation and embedding selection remain separate. Both workloads read the same embedding model/endpoint/collection keys. S08 implements collection-model and actual query-dimension enforcement; pure settings validation alone is not a live compatibility check.
- Provider failures have five explicit categories: timeout, transport, invalid JSON, invalid schema and invalid citation. S11 implements the fixed two-attempt budget for validation failures, with immediate safe fallback on timeout/transport failure.
- The model's Answer schema is unchanged. AskRequest/AskResponse gain an optional nullable session_id, strictly 1–128 ASCII letters/digits/underscores/hyphens when present. Provided legacy clients can omit it and retain all previous response fields. Until S12, the API does not store/reuse turns and the response session_id remains null.
- Internal active-index identity contains exactly collection, generation, embed_model and dimension. Text identifiers are nonempty and whitespace-free; dimension is a positive integer, not a boolean or string. API validates/freezes the identity with Pydantic; indexer has a frozen dataclass producing the same wire shape. A cross-workload test protects compatibility without production cross-package imports.
- Configuration parsing and schema validation perform no service/model calls. Invalid configuration fails before factories initialize dependencies.

## S06–S11 implementation update

The original S02 decision remains historical context. Real embedding, model/dimension checks, constrained generation and bounded citation validation/recovery are now implemented; sessions/cache/readiness remain pending. Native tests use nomic-embed-text (768 dimensions) and the planned llama3.2:3b, with inventories/digests recorded. The installed 1B profile refused known evidence and is not the verified selected model.

Provider output is strictly parsed and validated. Every returned citation must match request-local source/section/page evidence; every prose sentence must carry the exact inline [source / section] form. One validation retry includes a safe failure category and citation-format feedback. Transport/timeout failures immediately fall back. Repeated invalid output returns a canned uncited false-groundedness response. False provider abstentions are canonicalized; reasoning is excluded from HTTP responses and application logs. Citation syntax does not establish semantic truth or injection robustness.

HTTP calls have configured timeouts and bounded generation output; no hard wall-clock real-time guarantee is asserted. Current relevance/chunk defaults remain provisional; the S11 demonstration's .75 runtime relevance override is not final calibration. Follow-up/session fields are still inert until S12.

## Data governance

S02 sent no questions/documents to external generation services. S06–S11 now send selected public corpus text and test questions to local Ollama on 127.0.0.1:11434; no hosted generation provider was used. Native models and the pinned Chroma image were downloaded from their registries. Embedding/generation endpoints remain configurable, so deployment must verify their actual destinations; changing endpoints can change where corpus/questions travel. No conversation retention layer has been implemented.

LLM keys and Redis URLs are excluded from Settings repr, and invalid-URL diagnostics name the key without reproducing credentials. This is not encryption: do not log raw environment mappings or dataclass serialization containing secrets.

Session TTL defaults to 1800 seconds as a future configuration value. No session persistence or retention guarantee exists yet; S12 must implement bounded Redis history, expiration and isolated unpredictable identifiers. Cache TTL/threshold defaults are also provisional until implementation and S19 measurements. Do not present them as measured privacy/quality guarantees.

## Alternatives and consequences

Keeping every starter provider name selectable postpones unsupported-mode failures until traffic arrives. Rejecting unsupported selections gives an actionable startup error and keeps the two-day scope focused on one real provider.

A shared top-level Python package would require changing image build contexts/packaging owned by Alishba. Separate small data representations with a tested wire contract preserve independent work. Their validation must remain aligned as metadata evolves.

Using a required session field would break existing callers. Optional fields preserve the provided UI/evaluator behavior while allowing future shared turns. Alishba should defer UI reuse logic until S12 supplies actual issued session IDs.

## Validation and remaining work

See docs/evidence/app/sprints/S02.md and S06.md through S11.md for actual red/green/live evidence. No Python requirement pins changed. Shared sessions, cache, full readiness, injection experiments and full evaluator/threshold calibration remain their assigned future sprints. Jibran's human review and Alishba's integration review remain pending.
