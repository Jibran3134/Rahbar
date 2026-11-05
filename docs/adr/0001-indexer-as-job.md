# ADR 0001: keep indexing in a single-writer Job

## Status

Implemented and exercised in the isolated rahbar minikube cluster on 5 November 2026. Codex implemented Alishba's platform scope at Jibran's request. Human review remains pending.

## Context

Three API replicas share one published Chroma index. If each process indexed at startup, one rollout could launch four writers, and every restart would repeat extraction/OCR/embedding. Readiness would either accept incomplete data or wait for a long batch that liveness could interrupt. A corpus update would unnecessarily require restarting query servers.

## Decision

[indexer-job.yaml](../../k8s/base/indexer-job.yaml) runs `python -m pipeline.run` once, with restartPolicy OnFailure, backoffLimit 2 and an 1800-second deadline. It mounts corpus data read-only after a checksum-verifying init container provisions the corpus PVC. It has its own service account, CPU/memory bounds, writable temporary storage and no Kubernetes API token. No application image or API startup handler performs ingestion.

[reindex-cronjob.yaml](../../k8s/base/reindex-cronjob.yaml) runs the same workload weekly, Sunday 02:00 UTC, with concurrencyPolicy Forbid. For a manual rebuild use `kubectl --context rahbar -n rahbar create job --from=cronjob/reindex manual-reindex-<unique-id>`. CronJob concurrency does not prevent independent manual Jobs. All real writers additionally use the exclusive Chroma writer-lock protocol in [store.py](../../indexer/pipeline/store.py). Operators must verify no live writer before recovering a crashed lock; age alone is insufficient.

The writer builds and validates a separate immutable generation before publishing its four-key active identity. APIs resolve that identity for each query and keep one generation through retrieval/cache. A failed pre-publication build leaves old readers functional. An uncertain publication acknowledgement is not proof of rollback: retain valid/previous/in-flight generations, and do not delete the new generation automatically. Reindexing changes cache namespaces without requiring indexer access to Redis.

## Alternatives and consequences

API startup indexing couples batch cost to replicas and restarts. A permanent indexer Deployment would require an extra scheduler/trigger lifecycle and would obscure success/failure compared with Job completion. An init container on every API replica still duplicates the writer and makes rollout depend on ingestion. A Job provides an explicit batch boundary and failure state.

The API's process-only /healthz remains live during dependency outages, while /readyz withholds replicas until a compatible nonempty index and Redis are available. Initial API pods are expected to be unready until the first Job succeeds. Subsequent reindexing uses the existing generation while a replacement is built.

The bootstrap Job's pod template is immutable. The deploy helper preserves an existing bootstrap Job; later builds use new Jobs from the updated CronJob template. Retained generations and completed Jobs consume storage; cleanup requires an explicit quiescent-reader/writer procedure. PVCs survive pod replacement, but deleting the cluster or PVC is a different operation and requires backups/reprovisioning.

## Evidence

P02/indexer.txt records the real Linux image extracting/OCRing seven checksum-verified documents and publishing 813 chunks in 306 seconds. P02/fetch.txt records all source hashes. P02/ingress-queries.json contains an actual cited current-policy answer and an absent-hostel-topic refusal through Ingress. P02/endpoints.txt and hpa.txt show three ready API addresses and usable CPU metrics. These files are under [platform evidence](../evidence/platform/P02). Later security, recovery and release checks are tracked separately; no GitHub protection or remote CD success is inferred from a local Job.
