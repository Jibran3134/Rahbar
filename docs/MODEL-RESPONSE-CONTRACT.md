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


The CPU profile now permits 120 seconds per generation attempt. At most two validation attempts remain allowed; a transport/timeout failure still falls back immediately. Ingress, the Windows gateway and the evaluator allow 360 seconds, and API pod termination grace is 360 seconds, covering the two attempts plus query embedding/drain allowances in the normal bounded case. Supported facts can therefore take longer to generate than the earlier 60-second budget. Timeout fallbacks are explicitly marked generation_timeout in X-Cache-Reason instead of being described as absent source information.

PDF title-only search hits receive bounded same-generation/source/page/version context before generation. The score remains the original heading similarity, and citations identify that heading on its actual source page. This adds the nearby source clauses without inventing text or raising similarity scores.


A supported conditional answer may explain that a semester result alone cannot determine cumulative standing. The checker distinguishes a leading global refusal from that limitation; it still requires every sentence and citation triple to validate. Contradictory refusal/citation flags produce the typed inconsistent_answer category, with retry advice about answered_from_context, confidence and citations rather than an unrelated citation-only repair. GPA cache scope distinguishes cumulative, semester and unspecified values even when numerical values and embeddings match. This is conservative reuse protection, not a general semantic verifier.


A bounded Decimal helper supplies literal comparison hints when both the question and evidence contain ordinary decimals. It does not establish matching units or policy applicability and is never a cited policy source. The model must still interpret the retrieved rule and identify its actual source. The Ollama request explicitly sets think=false for the tested hybrid-model path; the required JSON reasoning field remains private. Arithmetic assistance and valid citation syntax cannot certify semantic correctness.
