# Failure analysis - actual controlled observations

Executed locally on 5 November 2026 with the frozen real golden set, nomic embeddings, persistent Chroma and selected 250/30 chunks. These are actual failures and limitations, not invented before/after screenshots. Machine evidence: [S20-live.json](evidence/app/sprints/S20-live.json). Native final results are separate in [eval/results.json](../eval/results.json).

The normal application returns recall@5=.933333 after the query-level relevance gate, citation integrity=1.0 and required abstentions=1.0. Integrity scores do not establish semantic correctness; the final report's expect diagnostics and the incomplete historical-load answer remain explicit limitations.

## 1. OCR disabled: ingestion fails before unsafe publication

Perturbation: replace only the real OCR adapter with an empty result, then extract the original eight-page scanned entrepreneurship policy. Rendering/page detection still run. Baseline S03 extracted all eight image-only pages with real Tesseract.

Observed: `faculty-entrepreneurship-and-technical-start-ups-policy.pdf, page 1: OCR returned no text on a nonblank page`. The function raised its contextual ingestion error rather than returning a readable document or silently treating it as empty policy. No incomplete generation was published; the active production index stayed available.

Diagnosis: the scan has no useful text layer, so text-only extraction cannot supply its eligibility clauses. Similar OCR loss affects historical rules. Removing OCR is not an optimization that preserves the corpus.

Remedy: keep page-local bounded OCR, 300 DPI/single-block configuration and English runtime; fail incomplete ingestion. The experiment restored the adapter in a finally block. Evidence does not claim a new recall score for a build that correctly failed before publication. Platform image OCR must still be verified independently.

## 2. Fixed 100-unit windows without overlap: metadata and context loss

Perturbation: flatten each cleaned physical page, cut fixed 100-unit windows with no overlap, and label each window using its first token's section. All source/version/page fields remain present, and actual vectors are built into the isolated rahbar_failure_fixed100 collection.

Observed: 684 chunks, returned-evidence recall@5=.333333 versus normal .933333. Lost relevant matches include q01/q04/q05/q06/q07/q08/q11/q15/q16/q17. Source characters were not fabricated: the problem is cutting through section/definition/table context and attributing mixed text to the first section. A fact can still occur in a window while its canonical source-section match is lost.

Diagnosis: fixed size is insufficient when citations/evaluation depend on structure. The long AI definition and fee relationships become fragmented; crossing clause boundaries destroys the relationship between text and citation identity.

Remedy: preserve explicit sections, paragraph/sentence boundaries and bounded within-section overlap. Do not claim 650-unit chunks are always better: the actual three-way experiment selected 250/30 for retrieval discrimination despite extra fragments. Production chunk code was never replaced by this experiment.

## 3. top_k=1: relevant lower-ranked evidence disappears

Perturbation: query the actual published production generation with one neighbor, leaving model, vectors, corpus and relevance floor unchanged.

Observed: recall@5 computed on the actually returned one result falls to .666667. q03/q04/q07/q15/q17 miss their relevant source-section. Increasing the evaluator's k cannot recover passages the API never returned.

Diagnosis: first-ranked cosine evidence is not necessarily the correct clause. Related theory/lab, normal/summer load and prerequisite statements compete. This is retrieval starvation, not proof that generation ignored available context.

Remedy: keep top_k=5 and the query-level floor. Once at least one valid result clears the floor, keep the valid top-k context; the earlier per-passage filter removed the historical clause even after accepting its question. The model still needs to select/interpret evidence correctly; source retrieval alone does not certify a complete answer.

## 4. Version filter removed: stale evidence leaks even when recall looks healthy

Perturbation: issue actual cosine queries without metadata version/superseded constraints in an isolated experimental path. Do not remove production guards or mutate normal data.

Observed: 21 superseded hits appear across 11 default/current questions. Overall recall@5 remains .933333. This is a genuine version-isolation failure even though the recall number did not decline: a relevant current clause can coexist with a repealed one in the same top-k.

Diagnosis: recall is not a version-leak metric, and a language model may receive conflicting deadlines/conditions. We did not invent a generated wrong answer for this retrieval-only experiment. Historical/current clauses were originally verified to differ in S01.

Remedy: default superseded=false, conservative explicit edition filtering, required metadata validation and one active generation per request. Keep historical requests supported without exposing superseded evidence by default.

## Additional measured generation and cache failures

Native 3B output sometimes omitted inline citations despite valid citation objects. String-pattern constraints were tested and rejected after real runtime warnings about unsupported escaped spaces, malformed JSON and stalls. A deterministic adapter now renders only existing, exact request-local citation objects for a single cited source/section pair; unknown references and ambiguous/missing claim citations still fail validation, retry once and safely fall back. This fixes representation, not semantic entailment.

That usability improvement exposed a real instruction-injection regression: an indexed poisoned record plus a user override produced an optional-prerequisites claim with syntactically valid citations. The original response is retained in S19-injection-escaped-before-quarantine.json. Central generation quarantine now removes obvious assistant-directed instruction blocks/override sentences while retaining factual policy text and original metadata. The same real indexed attacks passed afterward. A supported negative answer `No` was also incorrectly rejected by an overly literal test oracle, which was corrected transparently. Quarantine is conservative and not universal attack detection.

Cache calibration: threshold .90 accepted a source-verified regular/summer course-dropping near miss (regular first-two-week requests require HoD approval; summer dropping is forbidden by clauses 4.19/4.21). Similarity measured .912882. Threshold .95 rejects it and preserves one tested paraphrase hit; .98 loses both paraphrase hits. An earlier withdrawal-scope label was insufficiently justified and is preserved as superseded; the final decision uses the verified dropping distinction. This is an actual cache-decision experiment, not a claim that the live system served a wrong answer.

## Restoration and limits

S20 verified the production active identity stayed identical throughout. The restored native retrieval measured .933333 again, and the saved final native result/baseline gate passed. No generation rerun is claimed by this retrieval-only restoration check. Four perturbations never entered release source; experiment collections are separate and retained for inspection. Final real/fixture baselines remain distinct and were not regenerated to conceal any degradation.

Remaining limits: one answerable scan-based question is rejected by the conservative floor; the long-definition answer can fall back during verification; some terse model replies and the historical-load heading are incomplete. Correct citations are necessary but insufficient for correct answers. Platform rollout, persistence, cgroup memory margin, HPA and protected-PR/CD acceptance remain blocked until the user develops the platform scope.
