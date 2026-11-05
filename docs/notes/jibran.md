# Jibran: sprint ledger and Alishba handoffs

Updated: 5 November 2026, PKT. This is execution state, not a claim that the planned application exists.

| Sprint | Status | Revision / working-tree description | Focused test result | Regression result | Live check | Evidence | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S00 | PASS | 5a40788 + existing plans; new local venv/evidence only | API 7 + indexer 4 passed | Ruff, both mypy, pip check/imports/pins passed | Inventory completed; later services not claimed live | [S00](../evidence/app/sprints/S00.md) | Stop; S01 eligible next |
| S01 | PASS | 5a40788 + public corpus/golden/validation artifacts | 7/7 hashes; audit passes; invalid dataset rejected | 11 starter cases; Ruff and validator mypy passed | Original sources/scan pages inspected; 161 PDF pages | [S01](../evidence/app/sprints/S01.md) | Stop; S02 next |
| S02 | PASS | 5a40788 + validated app/indexer contracts and tests | Red captured; final API 78 + indexer 30 passed | Ruff and both mypy checks passed | Offline config/startup/ASGI checks; no services contacted | [S02](../evidence/app/sprints/S02.md) | Stop; S03 next |
| S03 | PASS | 5a40788 + extraction/OCR and source fidelity fixes | Red→green; 54 indexer + 78 API cases passed | Ruff and both mypy checks passed | 7 real docs; 35 OCR pages; source/table probes pass | [S03](../evidence/app/sprints/S03.md) | Stop; S04 next |
| S04 | PASS | 5a40788 + conservative cleaning/tests/audit | 16 stub failures; final 19 cleaning tests pass | 73 indexer + 78 API; Ruff and indexer mypy pass | 7 hash-verified real outputs; 14 preservation checks pass | [S04](../evidence/app/sprints/S04.md) | Stop; S05 next |
| S05 | PASS | 5a40788 + deterministic page/section chunks and accounting | 26 initial failures; final 29 chunk tests pass | 102 indexer + 78 API; Ruff and indexer mypy pass | 7 real docs × 3 settings; 36 section probes; CI contracts pass | [S05](../evidence/app/sprints/S05.md) | Stop; S06 next |
| S06 | PASS | Working tree: validated batched embedding | 16 new tests pass | 118 indexer cases; Ruff/mypy pass | Real nomic vectors: 768 dimensions; repeat difference 0 | [S06](../evidence/app/sprints/S06.md) | S07 now eligible |
| S07 | PASS | Versioned builds, exclusive writer lock and read-only state | 12 store + 4 reader tests pass | 130 indexer + 89 API; Ruff/mypy pass | 2 real publications; failed partial rebuild preserves active | [S07](../evidence/app/sprints/S07.md) | S08 next |
| S08 | PASS | Read-only version-aware retrieval, model/dimension guard | 15 focused cases pass | 104 API; Ruff/mypy pass | 4 real current/historical source-section probes pass | [S08](../evidence/app/sprints/S08.md) | S09 next |
| S09 | PASS | Integrity/relevance gate before generation | 8 focused cases pass | 112 API; Ruff/mypy pass | 2 real absent queries bypass at explicit provisional floor | [S09](../evidence/app/sprints/S09.md) | S11 now eligible with S10 |
| S10 | PASS | Independent S02 branch: constrained Ollama provider | 7 focused tests pass | API 89; Ruff/mypy pass | Planned 3B answers known clause; format validation deferred S11 | [S10](../evidence/app/sprints/S10.md) | Await S09 before S11 |
| S11 | PASS | Grounding validation, one retry, safe fallback and copyable citation labels | 24 initial red→green; 3 later regression cases pass | 139 API + 130 indexer; Ruff/API mypy pass | Current/historical real answers; 2 refusals; malformed JSON fallback | [S11](../evidence/app/sprints/S11.md) | Stop at requested boundary; S12 next |
| S12 | PASS | Shared bounded sessions | Red→green recorded | Tests/types/Ruff exit 0 | Explicit live gate passed | [S12](../evidence/app/sprints/S12.md) | Continue authorized range |
| S13 | PASS | Safe semantic cache and invalidation | Red→green recorded | Tests/types/Ruff exit 0 | Explicit live gate passed | [S13](../evidence/app/sprints/S13.md) | Continue authorized range |
| S14 | PASS | Bounded truthful readiness | Red→green recorded | Tests/types/Ruff exit 0 | Explicit live gate passed | [S14](../evidence/app/sprints/S14.md) | Continue authorized range |
| S15 | PASS | Correlated query observability | Red→green recorded | Tests/types/Ruff exit 0 | Explicit live gate passed | [S15](../evidence/app/sprints/S15.md) | Continue authorized range |
| S16 | PASS | Indexed poison safety verification | Red→green recorded | Tests/types/Ruff exit 0 | Explicit live gate passed | [S16](../evidence/app/sprints/S16.md) | Continue authorized range |
| S17 | PASS | Fail-closed evaluator and regression gates | Red→green recorded | Tests/types/Ruff exit 0 | Explicit live gate passed | [S17](../evidence/app/sprints/S17.md) | Continue authorized range |
| S18 | PASS | Real and fixture query integration | Red→green recorded | Tests/types/Ruff exit 0 | Explicit live gate passed | [S18](../evidence/app/sprints/S18.md) | Continue authorized range |
| S19 | PASS | Measured configuration and final baselines | Red→green recorded | Tests/types/Ruff exit 0 | Explicit live gate passed | [S19](../evidence/app/sprints/S19.md) | Continue authorized range |
| S20 | PASS | Four controlled stage failures and restoration | Red→green recorded | Tests/types/Ruff exit 0 | Explicit live gate passed | [S20](../evidence/app/sprints/S20.md) | Continue authorized range |
| S21 | TODO | Not started | Not run | Not run | Not run | None | Wait for prerequisites |
| S22 | TODO | Not started | Not run | Not run | Not run | None | Wait for prerequisites |

## S00 handoff for Alishba

- Python 3.12.10 is available through .venv/Scripts/python.exe with a durable ignored .venv/python-runtime base; no global Python dependency for project checks.
- All 11 starter test cases, Ruff, both mypy checks, package consistency, dependency imports and 22 direct requirement entries passed. The tested resolved dependency snapshot is in docs/evidence/app/sprints/S00-constraints.txt.
- Docker Desktop Linux engine and Poppler work in host-authorized checks; coding sandbox permissions can block them. Unrelated appdev containers were left unchanged.
- minikube and Tesseract were not found on PATH. Supply platform tooling and an OCR executable/container path for later live gates.
- Windows Ollama client is installed but its host model-list endpoint is unreachable. Start/verify it and the selected models before embedding/provider live gates.
- Chroma localhost:8001, Redis localhost:6379 and Ollama localhost:11434 are the planned local endpoints, not verified running services. Confirm a pinned Redis image and separate Rahbar services; match Chroma 1.0.12.
- No branch protection, GitHub settings or branch changes were made. The current branch is main; establish the agreed dev/feature PR workflow before production changes.
- This handoff is written evidence only. No Slack/email/other external message has been sent and Alishba has not confirmed agreement in this session.

S00–S11 have passed. S12–S22 remain TODO. No production feature or corpus work began during S00. S10 was developed independently while the S06 model download blocked; all dependent gates were respected.
## S01 handoff for Alishba

- Real corpus is seven verified public documents, five PDFs with 161 physical pages and two HTML pages. Sources/manifest are in corpus/; all downloaded originals/inspection artifacts remain ignored in corpus/raw/.
- Golden truth is 17 questions: 8 ordinary, 4 version, 2 exact, 2 abstain, 1 injection. Initial source/manifest/golden hashes are frozen before retrieval tuning, with cross-platform normalization for text hashes only.
- Historical academic rules need OCR: 24/26 pages have no extracted text. The separate eight-page startup policy has no text or font layer at all. Provide a working Tesseract/Poppler image path before S03.
- Preserve filenames and section conventions in docs/CORPUS.md. Index only _index.json's seven entries; do not index raw/_inspection/.
- Startup source and historical passages were inspected visually; no OCR pipeline, retrieval score or model safety result is claimed yet.
- All seven checksums and the audit pass; intentionally missing abstention/out-of-range-page data is rejected. API/indexer starter regressions still pass (7 + 4), and Ruff plus audit-utility mypy pass.
- Only local files were prepared; no Git commit, push, account change or external handoff message occurred. At the S01 handoff, S02 had not started; see the S02 record below for its subsequent completion.
## S02 handoff for Alishba

The exact environment/default/range table and payload contracts are in docs/evidence/app/sprints/S02.md and S02-contracts.json. ADR 0004 records the compatible schema decision; Alishba's integration review is still pending.

- API accepts RETRIEVER stub/chroma and LLM_PROVIDER stub/ollama-host. Hosted and in-cluster selections fail at configuration time rather than at request execution. Real Ollama generation remains S10 work.
- Supply the frozen configuration keys, including relevance/cache/session/timeout settings. RELEVANCE_FLOOR=0.45 and CACHE_THRESHOLD=0.95 are provisional code defaults, not measured choices; S19 must justify shipped values.
- Both API/indexer read identical embedding endpoint/model/collection keys. Settings parsing is offline; it does not imply a compatible live collection or truthful readiness yet.
- Session payload: optional nullable session_id, strict ASCII letters/digits/underscore/hyphen, 1–128 characters. Existing question-only clients continue to work. The response is currently null; defer UI session reuse until S12 implements ID issuance/history.
- Active-index wire identity has exactly collection, generation, embed_model and positive integer dimension. Cross-image compatibility is tested without production imports between image contexts.
- Provider error categories and the two-attempt constant are available for S10/S11. Retry/fallback behavior is not implemented in S02.
- No new Python/native dependencies. Tesseract/Poppler requirements from S01 still apply before S03 live scan acceptance.
- Final tests: 78 API + 30 indexer cases, Ruff and both mypy checks pass; original 11 starter cases remain included. No external service call, commit, push or message was performed.

At the S02 handoff S03 was next; it subsequently passed as recorded below.
## S03 handoff for Alishba

- PDF/Markdown/text/HTML extraction is implemented and tested. Seven real documents (161 physical PDF pages + two logical HTML pages) extracted successfully, with 35 actual OCR pages. Three CI Markdown fixtures also extracted with metadata/front matter handling intact.
- Native Windows OCR is available in ignored .venv/tesseract-5.5.3/. Set process-local TESSERACT_CMD to its executable for local runs; do not hard-code that Windows path into Linux manifests.
- Install native Tesseract + English language data in the indexer image. Existing pdfplumber/PDFium handles rendering; Poppler is useful for inspection but not required by this extraction code. No Python requirement pin changed.
- Measured source checks selected --psm 6 and 300 DPI, with 60-second OCR timeout, 16-million-pixel render cap, explicit bitmap/layout cleanup and contextual document/page failures.
- The real handbook contains invisible off-page glyphs. Extraction now respects page bounds; do not treat the earlier repeated text as something to globally deduplicate blindly in S04.
- S03 corrected the visible definition word count from the initial unclipped 314 to 237 in CORPUS.md. Frozen source bytes/golden truth were not changed.
- HTML preserves headings/row boundaries/context and has one logical page internally. Later citations must expose HTML page=null.
- Recheck OCR/source probes in the actual Linux image; native versions can change recognition. No perfect OCR/PDF-table/handwriting recovery claim is made.
- Tests: 54 indexer + 78 API cases pass; Ruff and both mypy checks pass; original-source and table checks pass. All results/commands are under docs/evidence/app/sprints/S03.md.
- No Alishba-owned source, commit/push, account setting or external message was changed. At this handoff S04 had not started; its subsequent result is below.

## S04 handoff for Alishba

- Conservative cleaning is implemented in indexer/pipeline/clean.py. No new dependency, environment key, native package or API contract is needed. Existing image requirements from S03 still apply.
- It copies document/page objects, preserves identity and blank-page numbering, normalizes selected artifacts, and infers running PDF margins only from repeated first/last lines. It leaves uncertain OCR content and hard-hyphen wraps unchanged. Exact rules/limits are in PIPELINE.md.
- Seven real S03 outputs were checked against saved page hashes and original corpus checksums, then cleaned; 14 preservation checks passed. OCR was not rerun. Full cleaned text remains ignored, not a Git deliverable. Audit: .venv/Scripts/python.exe indexer/tests/live_clean.py from root after S03 audit outputs exist.
- All 19 cleaning tests and 54 pre-existing indexer tests pass; API regression remains 78 cases. Ruff and indexer mypy pass. Evidence includes the real removal example and preserved definition/table/exact numeric clauses.
- This is a written handoff only; Alishba's image/integration review and Jibran's human review remain pending. No Alishba-owned file, commit, push or external message was changed/performed. At this handoff S05 was next; its subsequent result is below.

## S05 handoff for Alishba

- Deterministic chunking and token accounting are implemented. No dependency, executable, environment key or wire-schema change. CHUNK_SIZE/CHUNK_OVERLAP remain configured as before (provisional 400/50); do not present these as quality-selected settings.
- Chunks stay within one physical PDF page and section, carrying section labels across pages. Explicit Markdown/HTML heading titles remain authoritative, including the fixture's numbered full titles. PDF clauses use numeric canonical labels; student policy uses XII.1. HTML query citations must still expose page=null later.
- Counter is approximate unicode-word-4-and-punctuation-v1, not model tokens. Overlap is bounded above by the configured units and aligns to words where possible. S19 must use this same counter for comparable amplification results and measure retrieval separately.
- chunked JSON log events add original_tokens, stored_tokens, amplification and token_counter. Existing source/chunks fields are preserved. run_pipeline still cannot complete until embedding/storage sprints pass.
- Real audit command from root: .venv/Scripts/python.exe indexer/tests/live_chunk.py, after S04 outputs exist. Seven source files / 163 cleaned pages are hash-verified; 12 section probes pass at all three settings, plus all five relevant CI fixture section contracts. Full chunk text stays ignored. At provisional 400/50: 760 chunks, 60,357 original units, 61,254 stored units, amplification 1.014862; no recall or final size choice claimed.
- Final checks: 29 chunk tests, 102 total indexer tests, 78 API tests, Ruff and indexer mypy all pass. No frozen truth or Alishba-owned file was changed. Human/integration reviews remain pending; no external handoff message or Git operation was performed.
- Next S06 needs the selected real Ollama embedding model/service working. This sprint did not check or start that service; S06's mandatory live gate must verify it. Stopped before S06.

## S06–S11 handoff for Alishba

- Real application path is now implemented through grounded answers: validated 768-dimensional nomic embeddings, versioned Chroma publication, read-only request-scoped retrieval, explicit historical filtering, relevance gating, schema-constrained llama3.2:3b generation and strict citation validation/recovery. No Python pins or Alishba-owned files changed.
- Local development services: Ollama 127.0.0.1:11434; separate rahbar-chroma-sprints container/volume on 127.0.0.1:8001. Active base rahbar has 760 real chunks. Image is pinned chromadb/chroma:1.0.12 with captured digest; its API get_version self-reports 1.0.0, recorded honestly in S06-S11-runtime.json. The exercised APIs work with the 1.0.12 client; final image integration still needs review.
- Both workloads use the configured model and explicit nomic search_document/search_query prefixes with truncate=false. Do not use Chroma's implicit embedding function. Native model digests/versions and active identity are in S06-S11-runtime.json.
- Publication control is <base>_active with exactly collection/generation/embed_model/dimension. Every real writer exclusively creates <base>_writer_lock and removes it on completion; crashed/stuck locks require verified no-writer manual recovery. Keep active/previous/failed generations; never delete a generation after an ambiguous publication acknowledgement. See S07.md for the complete single-writer/cleanup limitations.
- API starts without connecting to Chroma and returns sanitized query 503 on unavailable/incompatible state. The observed stopped-container incident confirms this request behavior; /readyz is still the starter placeholder until S14 and must not be presented as final readiness.
- Existing schema is compatible. session_id remains optional/null until S12; no shared sessions or semantic cache yet. Provider retries only validation failures once; timeout/transport immediately fall back. Stub also uses real retrieved text and passes citation validation. Unsupported provider modes remain rejected.
- The demonstration profile uses RELEVANCE_FLOOR=0.75, LLM_PROVIDER=ollama-host, LLM_MODEL=llama3.2:3b and RETRIEVER=chroma. Default 0.45 is unchanged and too low for the two measured absent questions. Earlier .781778 rejected a valid historical question. S19 must calibrate the whole frozen set; .75 is a provisional demo setting, not a final threshold choice.
- Real full-path API checks pass current makeup-week and historical end-of-classes deadlines with correct physical-page citations, two absent hostel refusals, and separately injected malformed provider JSON (two attempts, HTTP 200 safe fallback). Native and injected observations are explicitly distinguished in S11-live.json. Claim entailment/all-category quality and indexed-poison resistance are not certified by citation syntax.
- Final regression: 139 API + 130 indexer cases pass; Ruff and API/indexer relevant mypy pass. Detailed per-sprint commands/exits/failed observations are in S06.md–S11.md. Native checks are explicit live_*.py commands, never collected by default pytest.
- No Git commit/push, branch/account change, deployment publication or external handoff message occurred. Jibran human review and Alishba integration review are pending. Requested S11 boundary reached; S12 is not started.
