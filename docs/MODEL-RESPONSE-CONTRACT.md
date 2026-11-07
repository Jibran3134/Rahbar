# Model and API response contract

The real profile uses Ollama `llama3.2:3b` through `/api/chat`, with `stream=false`, temperature .2, context 4096 and output budget 512. `format` receives `Answer.model_json_schema()`; the system prompt explains the evidence, citation and refusal rules. The schema is not duplicated as a long JSON string in the prompt. This follows Ollama's [structured-output guidance](https://docs.ollama.com/capabilities/structured-outputs).

The model must return this JSON shape, populated from the supplied evidence:

```json
{
  "reasoning": "Brief internal justification; never returned to the user",
  "answer": "A supported answer [exact-source-filename / exact-section].",
  "citations": [
    {"source": "exact-source-filename", "section": "exact-section", "page": 1}
  ],
  "answered_from_context": true,
  "confidence": "high"
}
```

All fields are required. `confidence` is high, medium or low. A citation page is a 1-based physical PDF page or null for HTML. Extra model/citation fields and incorrect types fail validation. When the transport supplies completion/model/role metadata, incomplete output, token-budget termination, a different model or a non-assistant role is rejected. Schema/citation validation failures get at most one generation retry; transport/timeout failures immediately fall back safely. API defaults and response fields stay compatible with the supplied evaluator.

Citation objects must match request-local retrieved source/section/page triples, and factual prose must carry matching inline labels. The provider may reposition a verified prefix label or append a single verified source label to a bare sentence; it does not invent sources. The returned answer therefore need not be byte-for-byte raw model text. Hidden reasoning is removed by the public `AskResponse` contract, not displayed in the UI or copied into evidence logs.

If the evidence is insufficient, the service returns a canonical refusal with `answered_from_context=false`, low confidence and no citations. If generation cannot be verified, it returns the separate safe verification-failure message with the same ungrounded status. Neither response is cached. Correct JSON/citations alone do not establish that every factual statement is complete or entailed; the frozen real-corpus evaluation and manual source inspection remain necessary. Diagnostic expected strings are not injected into prompts and are not a promise of identical model wording.

The API adds request ID, retrieved references, provider and a server-issued session ID. A cache hit preserves answer/citations/confidence/retrieved references while assigning the current request/session metadata. `X-Cache` reports HIT/MISS/BYPASS; `X-Cache-Reason` explains matching, storage, exclusion or conversation bypass.

The Windows launcher uses Ollama's [documented empty-request preload](https://docs.ollama.com/faq#how-can-i-preload-a-model-into-ollama-to-get-faster-response-times) before opening the app. This reduces cold-load delays without removing request timeouts or promising that every generation succeeds.
