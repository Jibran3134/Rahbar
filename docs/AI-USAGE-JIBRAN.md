# Jibran's AI usage disclosure

## Codex — repository audit, planning and sprint S00

Codex inspected the assignment and repository, drafted the two-day ownership plan and sprint execution guide, and executed sprint S00: the Windows environment baseline. S00 covers local tooling, pinned dependency installation, starter test/lint/type verification, prerequisite inventory, and evidence/ledger documentation. It does not implement RAG production features.

Jibran chose Windows development, requested exclusive ownership with Alishba, selected the larger core application scope, supplied both names, and requested one capability per verified sprint. Codex revised the documents accordingly.

Jibran's subsequent code review or changes have not been observed yet; do not treat this disclosure as a claim that Jibran has reviewed or understood every generated artifact. Update this file as work is reviewed or changed. Alishba will assemble the final required docs/AI-USAGE.md.

S00 results: verified the official Python installer, established an isolated Python 3.12.10 environment, installed existing requirement pins, ran eleven passing starter test cases plus Ruff/mypy/pip consistency and import checks, recorded real prerequisite limitations, and drafted the ledger/evidence. No application code or tests were changed. Dependency-install and tooling checks used authorized host execution where sandbox access was insufficient. No commit, push or external message was performed.

## Codex — sprint S01

Codex selected and downloaded seven real public FAST-NUCES documents, inspected original PDF/HTML and rendered scan pages, identified two genuine policy-version changes, authored seventeen golden questions, drafted the completed corpus document, and implemented a small structural corpus validator. The corpus itself is third-party university material, not LLM-generated text.

Codex ran checksum verification, positive/negative dataset checks, Ruff, validator mypy and the existing eleven starter test cases. It recorded actual results, kept full documents/inspection images ignored, and froze the initial golden/source/manifest snapshot before tuning. Text freeze hashes were normalized for Windows/Linux line endings while binary checksums remain strict.

Jibran authorized S01. Jibran's subsequent semantic/human review and changes have not yet been observed; source review by Codex is explicitly distinguished from Jibran's review. No extraction/OCR pipeline, retrieval/generation feature, quality baseline, commit or deployment was implemented in this sprint. Alishba-owned files were left unchanged.

## Codex — sprint S02

Jibran requested continuation to the next sprint. Codex wrote focused settings/schema tests first and captured expected failures, then implemented offline validation, typed settings, bounded optional session fields, immutable active-index representations and safe typed provider-failure categories. It restricted unsupported provider selections and retained the existing model Answer contract.

Codex subsequently added startup/HTTP and indexer identity regression checks, ran 108 passing total test cases plus Ruff and both application/indexer mypy checks, and wrote the environment/payload handoff, schema export and evolving ADR 0004. Original starter tests and dependency pins were not changed. No live provider/session/cache/index functionality is claimed.

Jibran's subsequent human review/changes and Alishba's integration review are pending; this file does not claim they approved or reviewed every generated line. No Alishba-owned file, Git commit/push, account setting or external message was changed/performed.

## Codex — sprint S03

Jibran requested continuation to S03. Codex wrote failing extraction tests, implemented page-aware PDF/Markdown/text/HTML extraction with native OCR, and inspected actual source outputs. Tests exposed and drove fixes for bitmap cleanup and invisible off-page PDF glyphs. Actual OCR comparisons selected single-block layout and 300 DPI to preserve clause/number associations without inventing replacement facts.

Codex installed an isolated pinned native Tesseract runtime after matching the download to the official release SHA-256; its expired certificate was explicitly recorded rather than called valid. Real extraction covered all seven source documents, 35 OCR pages and three CI Markdown fixtures. It recorded 132 passing regression cases, source/table checks, Ruff/mypy results and remaining OCR/table limits, then updated pipeline/corpus documentation and Alishba's handoff.

The S01 definition word estimate was corrected for visible-page bounds; frozen corpus bytes and golden truth were unchanged. No cleaning/chunking/embedding/storage/query feature was implemented. Jibran's subsequent human review and Alishba's image/integration review are pending. No Alishba-owned file, Git commit/push or external message was changed/performed.

## Codex — sprint S04

Jibran requested continuation. Codex wrote cleaning tests before implementation and captured sixteen failures at the missing cleaner. It implemented conservative artifact/whitespace normalization, repeated PDF edge-label/folio detection, new-object metadata preservation and explicit soft-hyphen handling. Two initial test expectations were corrected because one counted an existing body clause twice and another did not meet the specified eight-nonblank-line eligibility rule; the behavior requirements were preserved. Three additional margin safeguards brought the final cleaning suite to nineteen cases. A mypy translation-table type error was repaired without changing behavior.

Codex authored an explicit audit that validates original bytes and S03 extracted-page hashes, then checks real scan/table/definition outputs after cleaning. Fourteen preservation checks passed, alongside 73 indexer and 78 API tests, Ruff and indexer mypy. It documented actual removals and conservative limitations, saved evidence and prepared Alishba's handoff. Native OCR was not rerun; no dependency/model/service, golden truth or Alishba-owned file was changed. Jibran's subsequent human review remains pending. No commit, push or external communication was performed. S05 and later functionality remains pending.

## Codex — sprint S05

Jibran requested continuation. Codex wrote 26 initially failing chunk tests and implemented deterministic structural splitting, approximate token counting, stable digest IDs, bounded overlap/fallback and token amplification accounting in the indexer log. It inspected real chunk text and existing CI truth. A new failing regression exposed Markdown section-title incompatibility; the parser was fixed to respect explicit authored headings without editing golden truth. Another failing regression reproduced a real definition overlap beginning midword, leading to word-aligned bounded overlap. Repeated-section ID checks brought the final focused suite to 29 tests.

Codex authored and ran the explicit real-corpus structural audit: seven originals and 163 cleaned-page hashes verified, three parameter candidates, size/identity/content-preservation checks, 36 source-section probes, and three CI fixtures with all five relevant section contracts. It recorded actual counts/amplification, 102 passing indexer + 78 API tests, Ruff/type checks and documentation/handoff. No model calls, vector writes, OCR rerun, retrieval-quality measurements or final chunk-size selection occurred. No dependency, frozen truth, Alishba-owned file, commit, push or external communication was changed/performed. Jibran's human review and Alishba's integration review remain pending; S06 and later work is not claimed complete.

## Codex — sprints S06–S10

Jibran explicitly requested development through S11. Codex authored tests first and implemented validated batched nomic embedding, isolated Chroma builds/readback/publication and a writer-lock protocol, read-only version-aware retrieval with model/dimension guards, evidence relevance/abstention gating and one real constrained Ollama provider. Initial expected failures and actual final results were captured for each capability. S10 was developed independently on its passed S02 prerequisite while S06's required model download blocked; dependent stages waited for their gates.

Codex started installed Ollama/Docker services in the background, downloaded the selected nomic/3B models and pinned Chroma 1.0.12 image, and created only the isolated loopback Chroma container/volume. Unrelated appdev containers remained unchanged. It verified actual 768-dimensional vectors, published two real generations including 760 corpus chunks, injected a real partial write failure and verified last-known-good queries. Real current/historical retrieval probes passed. The installed 1B generation profile refused known evidence; these failures were preserved rather than presented as success. Planned 3B schema/source content passed, with incorrect inline syntax deferred to S11 validation.

The narrow S09 relevance profile separated two absent questions from current withdrawal but did not calibrate the full corpus. Codex preserved the .45 code default, recorded the .781778 selected-pair profile and its limits, and did not edit frozen truth or fabricate evaluator scores. Exact native inventories/versions/digests and commands are saved. Chroma API self-reports 1.0.0 despite the pinned 1.0.12 image tag; this discrepancy is recorded rather than hidden.

## Codex — sprint S11 and interruption recovery

After Jibran requested continuation, Codex verified saved S09 checks, closed its ledger record and wrote 24 failing grounding/recovery cases before implementation. It implemented exact request-local citation matching, per-sentence inline checks, false-groundedness consistency/canonicalization, one validation retry with feedback and immediate timeout/transport fallback. It updated the offline stub to quote actual retrieved text with citations through the same validator. Two further grounding regressions protect forged markers/unused citations and uncited claims hidden in a refusal; a third test drove copyable inline labels in provider evidence. Final API suite has 139 passing cases, indexer 130, with Ruff and relevant mypy checks passing.

The real full-path check first exposed a stopped Chroma container after the interruption; request 503s were saved, and only the isolated test container was restarted. The narrow .781778 profile blocked a valid historical hit, so the explicit demo profile was adjusted to .75 based on recorded selected scores while leaving code defaults/frozen truth unchanged. An incorrect historical citation safely fell back; a general copyable-citation prompt repair fixed the format without weakening validation. Final native current/historical answers, absent-topic refusals and a separately injected malformed-JSON HTTP fallback all passed. Claims were inspected against the known originals; this does not certify semantic entailment or injection resistance for all queries.

Codex updated pipeline/ADR/evidence/handoff documentation and kept full source/vector data ignored. No requirement pin, Alishba-owned file, commit/push, external communication or production deployment was changed/performed. Jibran's subsequent human review and Alishba's integration review remain pending. Work stops at S11; sessions, cache, full readiness, final metrics/evaluator/tuning and release work remain pending.


## Codex — S12

Codex implemented and tested shared bounded sessions, ran the checks/live command in S12.md and recorded actual evidence. Two red tests then 141 passing API cases. Redis transaction appends/trims six turns and refreshes TTL; question/answer bounded to 500/1000 chars. Unknown or expired IDs receive fresh unpredictable IDs. Existing history marks cache bypass; elliptical follow-ups include only the previous user question, never trust stored answers as evidence. Independent concurrent turns complete in completion order; no per-session serialization promised. Stub-only mode remains offline and returns null session ID. Separate native API processes shared the same Redis ID and correctly retrieved the historical deadline. UI handoff: preserve returned session_id on subsequent requests; omitted remains compatible. Redis failures return sanitized 503. Jibran human review and Alishba integration review remain pending. No external communication or Git publication.


## Codex — S13

Codex implemented and tested safe semantic cache and invalidation, ran the checks/live command in S13.md and recorded actual evidence. Four offline cache tests protect inclusive threshold, TTL/entry bounds, numeric/version/scope/negation/course-code vetoes, unsafe-answer exclusion, one embedding shared with retrieval and follow-up bypass. A later red test exposed CS101/CS102 aliasing and drove an explicit course-code signature guard. 145 API cases and checks pass. Native isolated Monday policy produced a paraphrase HIT, historical near-miss MISS, follow-up BYPASS, then actual Tuesday reindex forced MISS with changed answer. Original corpus index remains intact. Mutable model tags remain a deployment pinning limitation; cached evidence assumes immutable generation data and trusted internal Redis. See ADR0003 for retention and concurrency contracts. Jibran human review and Alishba integration review remain pending. No external communication or Git publication.


## Codex — S14

Codex implemented and tested bounded truthful readiness, ran the checks/live command in S14.md and recorded actual evidence. Six red-to-green cases and 151 API tests pass. One bounded background Chroma task prevents unbounded probe threads; each request re-resolves active generation and checks nonempty cosine identity, configured model and real embedding dimension, then Redis. Probe waits are bounded to two seconds per dependency operation; total is the sum, not a hard real-time guarantee. Stub probes stay offline. Live Redis stop yielded readiness 503 while healthz stayed 200, restart recovered, deliberately wrong model yielded model=false and restoring config recovered. Only the isolated service was touched. Jibran human review and Alishba integration review remain pending. No external communication or Git publication.


## Codex — S15

Codex implemented and tested correlated query observability, ran the checks/live command in S15.md and recorded actual evidence. New metric test was red before implementation, final 152 API cases pass. Retrieval including one query embedding, generation attempts, cache lookups/hits/outcomes, abstentions/fallbacks and token directions are observable with bounded labels. Native Ollama usage fields are actual when available; fallback/stub estimates are explicitly labeled estimated. Failed unreturned provider usage is unknown, not fabricated. Query outcome JSON includes request ID, timings, cache/refusal/fallback flags and token counts without raw history, answers, reasoning or session IDs. Live native answer, HIT and refusal produced three correlated records and a saved Prometheus scrape. No model correctness is inferred from telemetry. Jibran human review and Alishba integration review remain pending. No external communication or Git publication.


## Codex — S16

Codex implemented and tested indexed poison safety verification, ran the checks/live command in S16.md and recorded actual evidence. Offline boundary test and explicit native indexed attack both ran; 153 API regressions pass. The initial test conflated useful answering with the safety acceptance contract and rejected safe fallbacks. Its original failed quality observation is retained. The corrected safety predicate accepts either a correct grounded answer or an uncited low-confidence refusal, while forbidding attack phrase/codeword and requiring actual poison ID in retrieved evidence. Native 3B ultimately protected both document and user override attempts through bounded validation/fallback; this is system-level protection with a usefulness limitation, not a claim of robust model entailment. Normal corpus unchanged. No production safety rule was weakened. S10/S11 regression suite remains green. Jibran human review and Alishba integration review remain pending. No external communication or Git publication.


## Codex — S17

Codex implemented and tested fail-closed evaluator and regression gates, ran the checks/live command in S17.md and recorded actual evidence. Nine initial evaluator failures became nine passing hand-calculated tests. Duplicate relevant/hit pairs cannot inflate recall; top-k positions remain real positions. Exact source/section recall and source/section/page citation matching; macro question aggregation, explicit denominators/by-type diagnostics; grounded-without-citations scores zero and undefined required metrics fail. Gate allows exactly 0.05 recall drop, requires >=0.95 citation validity and all abstentions correct, requires matching nonmissing dataset baseline. Bootstrap is explicit and only writes after absolute gates; existing failed baseline is never refreshed. Native two-question probe scored successfully; a fabricated-citation response replay made the actual CLI exit 1. Probe baseline is labeled and separate from final real/fixture baselines. API info records actual active/config identity and source digest; explicit X-Bypass-Cache avoids experiment contamination. Alishba must run python -m pytest eval/tests separately in CI. Jibran human review and Alishba integration review remain pending. No external communication or Git publication.


## Codex — S18

Codex implemented and tested real and fixture query integration, ran the checks/live command in S18.md and recorded actual evidence. Actual seven-document and three-fixture corpora were indexed with real nomic/Chroma. All 17 real and six fixture questions ran through the native CLI. Provisional real recall5=.80, citation validity=1, abstention=1; fixture scores all 1. Useful real-answer gaps remain explicit in expect diagnostics for S19. A red test drove quoting up to four cited source sentences, fixing fixture repeat-grade omission; fixture native retest has no expect failures. Format diagnosis found omitted inline citations; schema refinement initially used unsupported escaped spaces (native warning preserved), then an overly broad wildcard admitted malformed JSON. JSON-safe grammar fixed the lab answer. Another red test corrected numeric claims being rejected for lack of letters; citation identity validation remains strict. Prompt-version cache namespace changed. Final 155 API + 130 indexer + nine evaluator cases, both types and Ruff pass. Prior S12/S13 live evidence covers follow-ups/cache/reindex; S16 covers real indexed poison safe fallback. User confirms platform is not developed; local integration is verified, Kubernetes acceptance remains external. S19 must remeasure final full real responses after these repairs. Jibran human review and Alishba integration review remain pending. No external communication or Git publication.
