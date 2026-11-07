# RAHBAR complete assignment workflow

Team ownership: **Jibran** - application/RAG; **Alishba** - platform/delivery. The diagram describes the implemented design, including current departures from assignment review requirements. Ownership labels do not assert personal authorship; see AI-USAGE.md.

![Complete RAHBAR workflow](diagrams/complete-workflow.svg)

[PNG image](diagrams/complete-workflow.png) | [Scalable SVG](diagrams/complete-workflow.svg) | [Editable Mermaid source](diagrams/complete-workflow.mmd)

Read left to right by lane: **A** prepares and publishes the corpus; **B** answers user questions; **C** tests, protects and releases the implementation. The bottom band shows the Kubernetes controls shared by the workloads.

- `run.cmd` is the normal Windows startup command. It opens localhost:8090 through a loopback gateway to the real Kubernetes Ingress. The first run prepares the deployment; later runs reuse it.
- Only the indexing Job/CronJob writes vector generations. It extracts, cleans, chunks, embeds and stores, then publishes a validated active identity. The API never indexes at startup.
- The UI defaults to independent questions (no session ID sent), enabling safe repeat cache hits without clearing the visible thread. Conversation mode sends the server-issued session ID and contextual turns bypass cache.
- The question path resolves shared Redis history and checks the active embedding identity. Query embedding is needed even for semantic cache lookup. A cache hit skips vector retrieval and generation; follow-ups and forced bypasses skip cache lookup.
- A query fails the relevance gate when no usable retrieved passage clears .74. This is a query-level gate: it does not remove every lower-scoring passage once another passage clears the floor.
- Generation is evidence-only with obvious instruction blocks quarantined. Schema/citation failures get one validation retry; transport/timeouts fall back immediately. Citation validation is not proof that every factual statement is semantically complete.
- Only eligible grounded standalone answers enter semantic cache. Cache namespaces include active generation/model/settings. Redis sessions are shared across replicas.
- CI uses its separate frozen fixture truth/baseline, real embeddings and retrieval, with grounded stub generation. Real local evaluation uses the real corpus/Ollama and its own truth/baseline; these reports are not interchangeable.
- CD reruns verification for the merged SHA, promotes those exact scanned image artifacts, and pulls them into an ephemeral kind cluster for rollout/Ingress/evaluation. It is not permanent public hosting.
- The assignment asks for an independent approval. Actual protection requires zero approvals at Jibran's request, while required CI remains enforced. The diagram does not claim independent approval was obtained.

Implementation references: [indexing](../indexer/pipeline/run.py), [generation](../api/app/services/generation.py), [cache](../api/app/services/cache.py), [retrieval](../api/app/retrieval/chroma.py), [startup](../scripts/run_app.py), [CI](../.github/workflows/verify.yml), [CD](../.github/workflows/cd.yml), and [architecture](ARCHITECTURE.md).

## Editable complete diagram

```mermaid
flowchart TB
  subgraph START["WINDOWS STARTUP — one command"]
    RUN["run.cmd"] --> SERVICES["Start/check Docker Desktop and Ollama<br/>Download missing models"]
    SERVICES --> SETUP["Start/reuse Rahbar minikube profile<br/>First use: build, apply, index, wait for readiness"]
    SETUP --> LOCAL["Open localhost:8090<br/>Loopback gateway supplies Host: rahbar.local"]
  end

  subgraph INDEX["INDEXING — Job / weekly CronJob; sole vector-store writer"]
    SOURCES["Seven public source documents<br/>PDF + HTML; current + historical versions"]
    SOURCES --> FETCH["Init container: fetch and verify SHA-256<br/>Store snapshots on corpus PVC"]
    FETCH --> EXTRACT["1. Extract<br/>PDF / HTML; OCR for scanned pages"]
    EXTRACT --> CLEAN["2. Clean<br/>Normalize text and preserve document structure"]
    CLEAN --> CHUNK["3. Chunk<br/>250 tokens / 30 overlap<br/>source, section, page, doc_version, superseded"]
    CHUNK --> DOCEMBED["4. Embed<br/>Ollama nomic-embed-text, dimension 768"]
    DOCEMBED --> STORE["5. Store<br/>Exclusive writer lock; new Chroma generation"]
    STORE --> PUBLISH["Verify and publish active identity<br/>collection + generation + model + dimension<br/>Old generation stays available during indexing"]
  end

  subgraph QUERY["QUESTION ANSWERING — API reads the published index; never indexes"]
    USER["User enters a question"] --> UI["nginx UI"]
    UI --> INGRESS["Kubernetes Ingress<br/>/ to UI; /api to API"]
    INGRESS --> API["FastAPI Service and Deployment<br/>3–8 replicas; validate request; request ID"]
    API --> SESSION["Redis session history<br/>Resolve bounded follow-up context"]
    SESSION --> PREP["Resolve compatible active index<br/>Embed query with nomic-embed-text / 768<br/>Mismatch or unavailable dependency: HTTP 503"]
    PREP --> CACHE{"Eligible standalone cache lookup?"}
    CACHE -->|"Yes: semantic match ≥ .95"| HIT{"Redis cache hit?"}
    HIT -->|"Yes: HIT"| RESULT
    HIT -->|"No: MISS"| RETRIEVE
    CACHE -->|"Follow-up / forced BYPASS"| RETRIEVE
    RETRIEVE["Read Chroma top 5<br/>Current documents by default<br/>Explicit policy edition selects historical version"]
    PUBLISH -. "Read published generation" .-> PREP
    RETRIEVE --> RELEVANCE{"Any usable evidence clears<br/>query relevance floor .74?"}
    RELEVANCE -->|No| REFUSE["Safe abstention<br/>Do not invent an answer"]
    RELEVANCE -->|Yes| SAFETY["Quarantine obvious injected instruction blocks<br/>Treat retrieved document text as evidence"]
    SAFETY --> GENERATE["Host Ollama llama3.2:3b<br/>Question + evidence; constrained JSON output"]
    GENERATE --> VALIDATE{"Schema and citation grounding valid?"}
    VALIDATE -->|Yes| VERIFIED["Verified answer + matching citations"]
    VALIDATE -->|"Invalid; retry unused"| RETRY["One validation retry with feedback"]
    RETRY --> GENERATE
    VALIDATE -->|"Still invalid"| FALLBACK["Safe unverified-generation fallback"]
    GENERATE -->|"Timeout / transport failure: no retry"| FALLBACK
    REFUSE --> RESULT
    FALLBACK --> RESULT
    VERIFIED --> RESULT
    RESULT["Return answer / refusal / fallback<br/>Citations, confidence, request ID and cache status<br/>Never expose provider reasoning"]
    RESULT --> SAVE["Save bounded Redis session: 6 turns, TTL 1800s<br/>Cache only eligible grounded standalone answers<br/>No abstentions, fallbacks or follow-ups"]
    SAVE --> DISPLAY["UI safely renders text and citations"]
    PUBLISH -. "New generation changes cache namespace" .-> HIT
  end
  LOCAL --> USER

  subgraph DELIVERY["CI/CD — all publishing and deployment depend on verification"]
    DEV["Jibran: application/RAG<br/>Alishba: platform ownership<br/>Commit changes; open PR to main"]
    DEV --> LINT["CI: Ruff + mypy + workflow checks<br/>Tests and coverage ≥ 60%<br/>Strict Kustomize / kubeconform"]
    LINT --> BUILD["Build API, indexer and UI images<br/>Preserve image artifacts; no PR publishing"]
    BUILD --> SCAN["Trivy gate<br/>Reject fixable HIGH / CRITICAL vulnerabilities"]
    SCAN --> FIXTURE["Fresh kind cluster + Calico + Ingress<br/>Real fixture indexing / embeddings / retrieval<br/>Deterministic grounded stub generation"]
    FIXTURE --> GATE{"Frozen fixture evaluation passes?<br/>Recall@5 drop ≤ .05; citation validity ≥ .95<br/>Required abstentions = 1; defined finite metrics"}
    GATE -->|No| BLOCK["Required CI blocks merge<br/>Fix implementation and rerun; preserve truth/baseline"]
    BLOCK --> DEV
    GATE -->|Yes| MERGE["Protected PR merge to main<br/>Actual required approvals: 0 at Jibran's request<br/>Assignment requests 1 independent approval"]
    MERGE --> CDVERIFY["CD: rerun complete verification for main SHA"]
    CDVERIFY --> HUB["Promote exact scanned image artifacts<br/>Docker Hub: jibran3134/rahbar-api, indexer, ui<br/>Full Git SHA tags; credentials from GitHub Secrets"]
    HUB --> DEPLOY["Pull those SHA images into a fresh kind cluster<br/>Wait for rollout; Ingress UI/API smoke<br/>Run fixture evaluator again"]
    DEPLOY --> EVIDENCE["Preserve actual results, logs and release links<br/>Hosted deployment is ephemeral"]
  end

  subgraph PLATFORM["KUBERNETES CONTROLS — namespace rahbar"]
    STATE["Chroma StatefulSet + 4 GiB PVC<br/>Redis Deployment + 1 GiB PVC / AOF<br/>Corpus PVC 1 GiB; ClusterIP data services"]
    CONFIG["Shared ConfigMap pins embedding name/dimension<br/>No real Secret committed to Git"]
    SECURITY["Calico default-deny + narrow allow rules<br/>Non-root, read-only filesystem, dropped capabilities<br/>Service accounts without mounted API tokens; requests/limits"]
    OBS["startupProbe + /healthz + /readyz<br/>/metrics + structured logs<br/>CPU HPA 3–8 at 70%; zero-unavailable rolling updates"]
  end
  STATE -. "Persistent state" .-> STORE
  STATE -. "Shared sessions/cache" .-> SESSION
  CONFIG -. "Same embedding identity" .-> DOCEMBED
  CONFIG -. "Same embedding identity" .-> PREP
  OBS -. "Readiness controls service membership" .-> API
  SECURITY -. "Enforced traffic / pod controls" .-> API

  classDef index fill:#eaf8f1,stroke:#23845b,color:#123b2b
  classDef query fill:#eaf1ff,stroke:#376bc2,color:#18385d
  classDef delivery fill:#f2edff,stroke:#7850b4,color:#432767
  classDef failure fill:#fff0eb,stroke:#be583a,color:#6e2a18
  class SOURCES,FETCH,EXTRACT,CLEAN,CHUNK,DOCEMBED,STORE,PUBLISH index
  class USER,UI,INGRESS,API,SESSION,PREP,CACHE,HIT,RETRIEVE,RELEVANCE,SAFETY,GENERATE,VALIDATE,VERIFIED,RESULT,SAVE,DISPLAY query
  class DEV,LINT,BUILD,SCAN,FIXTURE,GATE,MERGE,CDVERIFY,HUB,DEPLOY,EVIDENCE delivery
  class REFUSE,FALLBACK,BLOCK failure
```
