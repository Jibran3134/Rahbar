# Indexing and retrieval pipeline

Status through S21: indexing/query stages, shared sessions, cache, truthful readiness, observability, indexed-poison safety and evaluator implemented. Real/fixture integration, measured configuration selection and four controlled failure experiments passed. Platform/release acceptance remains pending. Sections labeled S03-S18 describe their historical implementation state; the S19 final operating point below supersedes provisional defaults and pending-sprint statements.

## Extraction

Implementation: indexer/pipeline/extract.py. Input is a local document plus discovery's doc_version/superseded values; output is a Document containing source-tagged Page records. It never fetches URLs, embeds, indexes or invokes generation.

Supported inputs: PDF, UTF-8/BOM Markdown and text, HTML/HTM. PDF pages retain physical 1-based indices. Other formats have one logical page; HTML must be exposed as page=null by later query/citation code, not cited as physical page 1. Leading Markdown front matter is removed; body headings, numbers and separators remain. Discovery's version metadata is authoritative.

### Visible PDF evidence, not hidden adjacent pages

pdfplumber reads text only inside each page's CropBox/visible bounding box. This is essential for the real current handbook: on physical page 23, 1161 of 1991 character centers lie outside the displayed page. Unclipped extraction interleaved the previous page's heading with the withdrawal clause. Cropping restores the actual visible clause boundary without inventing content.

The same issue affected the original S01 definition estimate. The visible introduction on student handbook physical page 48 contains 237 whitespace-separated words, not the unclipped 314-word estimate. The initial audit is retained as provenance; the corpus documentation records the S03 correction. Golden source questions, pages and meaning were not changed to improve a retrieval result.

### Page-local OCR and limits

- Useful text requires at least 20 alphabetic characters after URLs are excluded. Cover URLs/page numbers alone cannot disguise image-dependent content.
- Pages without useful text are rendered at 300 DPI with PDFium, already supplied by the pinned pdfplumber/PDFium dependencies.
- Visually white thumbnails are preserved as empty physical pages without invoking OCR.
- Nonblank pages use native Tesseract English, single-block mode --psm 6, with a 60-second timeout per invocation.
- Oversized render requests above 16 million pixels fail before bitmap allocation.
- Process one bitmap at a time and explicitly close the image/grayscale/layout resources, including failure paths. A regression test caught that Pillow context exit alone did not release an in-memory bitmap.
- Nonblank OCR returning no text, a missing engine, timeout, corrupt file, unreadable encoding or unsupported format raises an ExtractionError naming the source/page. The function does not return a successful partial document.

The adapter is used sequentially by the one-writer indexer. Native command override is process-local TESSERACT_CMD; default is tesseract on PATH. No extra Python dependency was installed for S03. On Windows the verified runtime lives in ignored .venv/tesseract-5.5.3/.

The pinned PDF renderer does not require Poppler for this implementation. Alishba still needs Tesseract/English data in the Linux indexer image; Poppler remains useful for font/inspection tools. Do not bake the Windows executable path into Kubernetes settings.

### Actual corpus results

| Source | Physical PDF pages | OCR pages | Preserved empty pages |
| --- | ---: | --- | --- |
| 2023 academic rules | 26 | 2 and 4–25 (23 total) | 3 |
| Current academic handbook | 58 | 1, 58 | 2, 56, 57 |
| Student handbook | 64 | 1, 64 | 2, 63 |
| Prospectus rules | 5 | None | None |
| Entrepreneurship policy | 8 | 1–8 | None |

All seven selected documents extracted successfully: 161 physical PDF pages plus two logical HTML pages. Thirty-five pages actually used OCR. The three existing CI Markdown fixtures also extracted with version/superseded metadata intact and front matter absent from content.

See docs/evidence/app/sprints/S03-live.json, S03-source-probes.json and S03-fixtures.json. Full extracted text remains under ignored corpus/raw/_s03-extracted/ rather than being committed with third-party source text.

### OCR choices measured against the originals

Default layout mode 3 split some left-margin clause identifiers away from their paragraphs in the startup and historical rules scans. Mode 6 kept identifiers attached in both inspected cases. At 200 DPI, the startup service-duration digit was misread as a vertical bar; both tested 150 and 300 DPI recovered the original digit. The chosen 300 DPI passed the final original-source probes.

These are targeted source checks, not a measured whole-corpus OCR accuracy score. No string replacement was used to fabricate the expected number. S03-ocr-layout.json and S03-ocr-resolution.json preserve the experiment observations without publishing long original passages.

### HTML structure and meaningful tables

The parser discards semantic navigation/header/footer/script/style/hidden regions and never follows links or executes scripts. It preserves headings, paragraph/list boundaries, decoded entities and pipe-delimited table cells/rows. Merged cells are marked with their original span attributes; missing cell values are not invented.

Real fee table comparison, using the same original HTML:

Before naive tag stripping (header/row boundaries collapsed):

~~~text
Program Fee BBA / BS Rs. 12,000
~~~

After the extractor (actual row delimiters):

~~~text
| Program | Fee |
| BBA / BS | Rs. 12,000 |
~~~

The surrounding per-credit-hour context and Fall 2026 heading are retained. This is a structural comparison to naive tag stripping, not a claim of a formerly deployed extractor or a repaired PDF table. All corresponding table checks passed in S03-table-checks.json.

### What was not recovered or guaranteed

OCR may still miss punctuation, spacing, exact identifiers or complex cell relationships. Unruled/multicolumn PDF tables and scanned annex forms are not reconstructed into guaranteed relational tables; their plain text remains subject to review. Graphical signatures/handwriting are not certified. HTML parsing is not a browser/CSS layout engine.

PDFMiner reports missing CropBox fallback warnings on some originals; native rendering succeeds using the page's MediaBox. Production log-format integration remains S15 work. Blank pages are explicitly retained, not silently renumbered away.

No failed document was silently published, and no claim of perfect extraction, factual correctness, recall or generation safety is made. Linux image OCR must be rechecked on the same source probes; Windows native output is not a cross-platform byte-for-byte guarantee.

## Cleaning — implemented S04

Implementation: indexer/pipeline/clean.py. Returns a new Document and new Page objects; source, physical/logical page numbers, OCR flags, version and superseded state survive. Input objects remain unchanged, making before/after inspection possible. Empty pages are retained. There is no cross-page deduplication, indexing or network access.

Normalization converts CRLF/CR to LF, NBSP and horizontal whitespace to ordinary spaces, removes selected invisible/control artifacts, expands the common ff/fi/fl/ffi/ffl presentation ligatures, trims lines and reduces excessive empty lines to one paragraph separator. It preserves line boundaries, numbered clauses and pipe-delimited HTML table rows. It does not infer relational columns from unstructured PDF whitespace. Numeric strings, currency punctuation, percentages, course codes and heading labels are not rewritten.

Only an explicit discretionary soft hyphen is removed; if it separates letters across a line break, the split word is joined. Ordinary hard hyphens and their line breaks remain, including ambiguous non-/credit and FAST-/NUCES wraps. Uncertain OCR punctuation, mojibake or misrecognized digits remain for source review; no source-specific answer correction is performed.

Running-margin inference applies only to PDFs. A page needs at least eight nonblank lines to contribute. Each first/last nonblank line is checked separately; an eligible label must recur at the same edge on at least three pages and at least 60% of eligible pages. The narrow label vocabulary recognizes handbook, rules and regulations, and university-of labels. It rejects clause/table/Markdown/sentence punctuation, bullet or numeric starts, policy verbs and numeric values other than publication years. Leading/trailing short Arabic or uppercase Roman folios can vary around the same label. Standalone trailing Arabic folios require a repeated offset from physical page number, rather than mere numerical repetition.

Here page position means extracted line position: the Page contract has no geometric coordinates. Short cover pages, less frequent labels, unfamiliar labels, OCR-corrupted labels and interior repetitions may remain deliberately. This is a conservative rule for the selected corpus, not a universal header classifier; recurring unnumbered institutional titles can still be ambiguous and need inspection on new corpora. It never removes an interior occurrence because a matching margin was removed elsewhere.

### Observed preservation and losses

The S04 audit verified all seven originals against their binary checksums and all 163 saved extraction-page texts against S03 hashes before cleaning. It processed the actual saved OCR/text outputs, without rerunning OCR or calling services. Changed page counts: historical rules 21/26, current rules 51/58, student handbook 56/64, prospectus 0/5, startup policy 0/8 and both logical HTML pages 1/1. Counts include whitespace normalization, not just removed margins.

Observed removal: the repeated NATIONAL UNIVERSITY OF COMPUTER AND EMERGING SCIENCES header and printed Student Handbook 2026 footer on physical student page 48. Every original interior body line on that page remains in order, including XII. and Introduction. The six S03 source-association probes still pass for real historical/current clauses and the OCR startup eligibility rule. Physical current page 10 retains clause 1.21, 100%, 20% and 2.00. The fee table retains Program/Fee and BBA/BS/Rs.12,000 relationships, per-credit-hour units and Fall 2026 context.

Nineteen owned cleaning tests also protect repeated policy sentences/headings, low-frequency and short-page labels, fee/course-code/hyphen strings, metadata, empty pages, non-PDF margins and idempotence. All 54 prior indexer cases pass. See docs/evidence/app/sprints/S04.md and S04-live.json; full cleaned third-party text remains ignored in corpus/raw/_s04-cleaned/. This is source-preservation evidence, not retrieval accuracy or certification of all OCR content. The S03 OCR/table limitations still apply.

## Chunking — implemented S05 / quality selection pending S19

Implementation: indexer/pipeline/chunk.py. No network/dependency calls or model tokenizer downloads. chunk(doc, size, overlap) rejects invalid/non-integer/bool settings before processing, then returns nonempty bounded chunks without changing its input. The initial 400/50 configuration was provisional; S19 selected 250/30 from real retrieval comparisons (ADR0002).

### Counting and structural boundaries

Counter identifier: unicode-word-4-and-punctuation-v1. The regex counts each run of up to four Unicode word characters as one approximate unit, each nonword/nonwhitespace character as one unit, and whitespace as zero. Thus even huge unspaced words, CJK text and punctuation-only input have a bounded fallback. This is an approximation, not an Ollama tokenizer or a guarantee of model context length. Use the same counter consistently in later size/amplification experiments; provider context limits need separate validation.

PDF numbered clauses use canonical labels such as 4.25 and 1.21. An uppercase Roman policy heading followed by numbered subsections produces labels such as XII.1. A short title directly before an explicit dotted clause can become a section label. Unrecognized initial material has section=preamble. Leading-zero decimal components such as 2.00 are not parsed as clause IDs. Ambiguous OCR/body lines that resemble clause headings remain a heuristic limitation; no arbitrary document layout can be inferred perfectly from plain text.

Explicit Markdown/HTML headings are authoritative and retain their full title, including any number. Numbered body paragraphs below them remain in that authored section until the next explicit heading. This preserves both the real HTML titles (Security Deposit, Description of Grades) and the existing CI truth (2. Academic warning, 1. Tuition). The planted fixture instruction remains source data; chunking does not execute or sanitize it into a claimed provider safety result.

Chunks never cross physical PDF pages. The current section carries across page boundaries and empty pages, but overlap resets at every page or section boundary. Each chunk's page is the page containing all of its text; source/version/superseded fields remain intact. This deliberately favors precise page citations over joining a definition across pages. HTML keeps one logical page internally; later citation output must still use page=null.

Within each page/section, prefer paragraph boundaries, then sentence boundaries, then whole-word boundaries. When none can satisfy size/progress constraints, split at the approximate-unit limit. Preserve original text slices and punctuation inside each piece. Large table rows can be split by this fallback; no invented table header or cell value is added. Normal table rows remain intact when the available budget permits.

Overlap is at most the configured number of approximate units. Align its start forward to a whole-word boundary when available; this may reduce overlap. Completely unbroken pathological text uses exact-unit overlap. A candidate boundary must exceed start+overlap, guaranteeing forward progress even at size=1 or overlap=size-1. Boundary inference can still split abbreviations or long table/word content; it is deterministic rather than linguistically exhaustive.

Chunk IDs are SHA-256 of canonical JSON containing algorithm version, source/version/superseded identity, physical/logical page, canonical section, section occurrence within the page, token range and actual text. Repeated content on different pages/occurrences receives distinct IDs; identical inputs/settings reproduce identical output regardless of PYTHONHASHSEED. No Python randomized hash is used.

### Measured structural counts, not quality scores

Original tokens are counted on cleaned content before overlap. Stored tokens count every emitted chunk, including duplicated overlap. Amplification = stored/original (0 for empty input). Indexer chunked log events expose these counts, amplification and token_counter alongside source/chunk count. S06/S07 subsequently implemented embedding/publication.

S05 checked all seven originals and all 163 cleaned-page hashes, deterministic IDs/metadata/size bounds, and exact nonwhitespace content/order preservation with overlap disabled. It inspected the selected long definition, attendance percentages, CGPA, historical/current clauses, scanned eligibility and fee relationships. All 12 source-section probes passed at every candidate setting. Three CI fixtures also retain all five relevant source/section contracts without changing golden truth.

| Approximate size / maximum overlap | Chunks | Original units | Stored units | Amplification | Definition page 48 chunk units |
| --- | ---: | ---: | ---: | ---: | --- |
| 250 / 30 | 813 | 60,357 | 62,412 | 1.034047 | 236, 237, 107 |
| 400 / 50 | 760 | 60,357 | 61,254 | 1.014862 | 388, 181 |
| 650 / 80 | 742 | 60,357 | 60,445 | 1.001458 | 520 |

The definition keeps canonical section XII.1 and physical page 48 throughout; 650/80 keeps its 520 approximate units in one chunk. At 400/50 the inspected second piece starts on a complete word after the overlap fix. These observations do not select 650/80 or establish better retrieval. S07 subsequently published the provisional 400/50 real index. Full recall@3/@5 measurements and quality baselines remain pending. S19 must rerun all candidates through real embeddings/retrieval/evaluation and justify the final parameters in ADR 0002.

Evidence: docs/evidence/app/sprints/S05.md and S05-live.json. Full chunk text is ignored under corpus/raw/_s05-chunks/. Twenty-nine focused cases and all previous extraction/cleaning tests pass. The audit processes real saved cleaned OCR/text outputs; OCR itself was not rerun.

## Embedding and publication — implemented S06/S07

The selected nomic-embed-text model produces 768 dimensions in actual native tests. Indexer uses search_document prefixes, API uses search_query, both send the configured model and truncate=false to /api/embed. Batches default to 32 with a 60-second per-request timeout; shape/count/order, numeric finite nonzero values and consistent dimensions are validated. Failures abort the whole embedding stage; no automatic retries or silent truncation. Runtime evidence records downloaded model digests; a mutable model tag is not an immutable-digest enforcement guarantee.

store validates all chunks/vectors before connecting, acquires an exclusive <base>_writer_lock collection, creates a separate cosine <base>__g_<uuid> collection, writes batches of 128 and validates all stored text/metadata/vectors/counts through readback. Only then does it replace <base>_active metadata with exactly collection/generation/embed_model/dimension and verify the published identity. Required chunk metadata remains source, section, page, doc_version and superseded. Indexer never accesses Redis.

The pinned Chroma image 1.0.12, matching the thin-client pin, was started on loopback port 8001 in the separate rahbar-chroma-sprints container/volume. Its API get_version self-reports 1.0.0, captured separately from the image tag/digest in runtime evidence; final image review must retain that distinction. S07 published a 3-row generation and then the complete 760-row provisional index, retaining both. A third build deliberately wrote only one row then failed. The published 760-row generation and a real vector query remained valid. Old/failed generations are retained; no automatic cleanup exists.

The exclusive server collection prevents concurrent writers only when every real writer follows this protocol. Crashed writers leave a stale lock; an operator must verify all writers/Jobs stopped before explicitly deleting that exact lock. Never steal a lock based on age. Do not run the legacy dummy writer concurrently with real publication. Clean up only after readers/writers are quiescent and excluding active/previous/in-flight generations. One metadata-modify request is not a cross-collection transaction: a lost acknowledgement can leave the new valid generation active. Never delete it or assume rollback after an uncertain response. Platform/ADR0001 changes remain Alishba's scope.

## Retrieval and relevance — implemented S08/S09

The lazy API constructor does not contact dependencies. Each request resolves one frozen identity, checks model compatibility, embeds its query, validates actual dimension/finiteness/nonzero values and queries only that generation with explicit vectors. It uses min(k,total count), cosine similarity=1-distance, typed required metadata and real physical pages. HTML logical page becomes null. Corrupt metadata fails closed instead of inventing citation identity. Dependency/model conflicts yield sanitized request 503s; full truthful /readyz remains S14 work and is not claimed here.

Current/default filtering requires superseded=false. Historical filtering requires a policy-edition date immediately attached to rules/policy/handbook/edition: full English month/year, YYYY-MM or a policy year. Unrelated fee values, course codes and dates cannot select history. Unknown requested editions do not fall back to current data. Cross-version comparisons and ambiguous date phrasing are not guaranteed. Four original current/historical withdrawal/load probes retrieved the intended source/section within top five (S08-live.json).

The evidence gate removes invalid/out-of-range/nonfinite scores or metadata and applies the inclusive configured relevance floor. No qualifying evidence means a canned low-confidence uncited refusal without generation. S09's observed selected scores: current withdrawal .829208, absent hostel deadline .670716, absent hostel deposit .734348. Its narrow selected-pair floor .781778 rejected both absent questions but later rejected a valid historical withdrawal score .766445. S11 therefore demonstrates an explicit runtime floor .75, retaining the historical question while excluding those two absent topics. The code default .45 is unchanged and does not separate these cases. Neither profile is final calibration: S19 must evaluate all frozen questions, including the lower-scoring historical load clause, before selecting a shipped threshold.

## Constrained generation and grounding — S10/S11

Ollama /api/chat receives the configured model (verified llama3.2:3b), low temperature, Answer JSON schema, stream=false, num_predict=512 and configured HTTP timeout. Trusted system rules precede a JSON user record containing numbered source/section/page/text evidence then the factual question. Embedded strings remain untrusted data; the provider does not execute their instructions. Strict Pydantic validation follows JSON parsing even with schema-constrained generation. HTTP clients are closed according to ownership, and failures are sanitized typed categories. Stub/ollama-host are supported; other modes remain rejected during configuration.

Grounding validation requires each citation object's exact source/section/page triple to occur in this request's usable evidence. No duplicates or unused citation objects; inline [source / section] pairs must match objects. Every nonempty prose sentence/line is conservatively treated as a claim and must end with a matching inline citation. Both citation-before and citation-after terminal punctuation are accepted; decimals/common currency abbreviations and marker-forgery cases are tested. A grounded answer needs evidence and citations. False-groundedness requires low confidence, no citations and explicit insufficient-information wording, then is canonicalized to a safe refusal so extra uncited model claims cannot escape.

These checks establish citation integrity and bounded formatting, not semantic entailment. A correctly cited claim can still misstate its source; manual source inspection and S17/S18 evaluation remain essential. Sentence/abbreviation/heading detection is deliberately conservative and may reject useful but differently formatted answers. Complex text, prompt injection and all-category quality have not been certified; indexed-poison verification remains S16.

Only one retry follows JSON/schema/citation validation failure, with safe category feedback and an example exact filename citation; two generation attempts total. Timeout/transport failures fall back immediately without another network attempt. Each provider call uses its configured HTTP timeout and 512-token output cap; this is HTTP timeout behavior, not a hard real-time wall-clock guarantee. Repeated invalid output returns a canned uncited low-confidence false-groundedness response. Failure kind, attempt and fallback are logged without question, raw provider output or reasoning. AskResponse never includes the reasoning field. The deterministic stub quotes a real retrieved sentence with a citation and uses the same validator; it does not memorize golden answers.

The native model's initial incorrect [1/4.25] inline citation was rejected in the full path; the retried current-policy answer used the exact filename and correct makeup-week deadline. Full real-service HTTP evidence and a separately labeled malformed-JSON transport injection are in S11-live.json. Earlier service-outage/high-floor failures are preserved separately. These development checks do not replace Kubernetes acceptance, readiness or final evaluator gates.

## Shared state - S12/S13 implemented; thresholds provisional

Redis sessions use fresh unpredictable IDs, six bounded turns, configurable TTL and transactional append/trim/expire. Existing sessions bypass semantic cache; supported elliptical follow-ups include only the previous user question. Stored assistant answers never become trusted evidence. Two native processes shared a session and correctly retrieved the historical policy. Concurrent turns complete in completion order; clients should serialize turns.

Semantic candidates are bounded sorted sets per immutable generation/model/provider/prompt/settings namespace. One prepared vector is shared with retrieval. Per-entry expiry and transactionally capped candidates enforce TTL and CACHE_MAX_ENTRIES. Cosine threshold and numeric/version/scope/negation/course-code signatures must agree. Only validated grounded non-low-confidence standalone answers are stored. Hits receive fresh request/session IDs. Redis is trusted internal state; manual in-place generation mutation violates publication contracts. Native Monday-to-Tuesday publication demonstrated useful paraphrase HIT, version rejection, follow-up BYPASS and changed-policy invalidation. See ADR0003/S13 evidence; threshold .95 was selected in S19 from explicit small-sample near-miss measurements.

## Probes and telemetry - S14/S15 implemented

healthz is process-only. readyz re-resolves the active identity and checks nonempty cosine data, model, actual query dimension and Redis. Named failures return 503. One outstanding Chroma task per process prevents unbounded threads; operation waits are two seconds and total latency is their sum. Native Redis stop/restore/model-conflict tests failed readiness while liveness stayed 200, then recovered. Final platform checks must assess model/probe contention; no Kubernetes behavior is inferred.

Metrics expose HTTP/retrieval/generation latencies, cache lookups/hits/outcomes, abstentions/fallbacks and in/out tokens labeled actual or estimated. Native usage is actual when returned; unreturned remote usage remains unknown. IDs never label metrics. Correlated query outcome logs contain timings/cache/refusal/fallback/token counts without reasoning, secrets or raw histories. Native samples are in S15.

## Indexed attack and evaluator - S16/S17 implemented

Actual indexed document/user override attacks were protected by bounded validation/fallback. Useful grounded answers were not demonstrated under that poison: this is observed system protection with a usefulness limitation, not universal model robustness. Original failed quality observations remain preserved.

Recall matches unique exact source/section pairs in the first k actual positions. Duplicate relevant/hit pairs cannot inflate scores; empty relevance is undefined. Citation validity matches unique source/section/page triples; grounded-without-citations scores zero. Both are macro means over defined question scores with denominators and by-type recall. Required abstentions need false groundedness, no citations and low confidence. Optional expect strings are diagnostic, not entailment certification.

Dataset hash, runtime configuration/active identity, source revision/content digest and per-question outcomes/timings accompany results. Missing/invalid/cross-dataset baselines and undefined/nonfinite metrics fail closed. Gates allow recall@5 drop at most .05, require citation validity >=.95 and all required abstentions. Explicit --update-baseline bootstraps only after absolute gates; failed runs never refresh a baseline. --bypass-cache supports clean experiments; --responses is explicitly labeled diagnostic replay. The actual CLI rejected a fabricated-citation replay in S17. Real/fixture/probe baselines remain separate; full selection follows S18/S19.

## S19 final operating point and limitations

Shipped defaults: CHUNK_SIZE=250, CHUNK_OVERLAP=30, RELEVANCE_FLOOR=.74, CACHE_THRESHOLD=.95. All three candidate indices used the same frozen questions, actual nomic vectors and exact evaluator functions. Raw recall@3/@5: 250/30=1.0; 400/50 and 650/80=.933333. Counts/amplification and by-type data are in S19-measurements.json and ADR0002. The assignment relevance rule is query-level: abstain if no valid hit clears the floor, otherwise retain all valid top-k context. Earlier per-passage filtering incorrectly discarded the historical rule after accepting the question; the superseded measurements are preserved. Final returned-evidence recall@3/@5=.933333, citation integrity=1.0, required abstentions=1.0. Fixture scores are all 1.0. Separate eval/baseline.json and eval/fixtures/baseline.json were written explicitly after passing absolute gates.

Cache candidates .90/.95/.98 yielded respectively 2/1, 1/0, 0/0 positive/false hits on two paraphrases and five near misses. The .90 regular-versus-summer false hit ruled it out. This is calibration, not a general semantic-equivalence guarantee. Final .95 matches the lowest tested threshold with zero false hits.

Model string-pattern experiments were rejected after the runtime ignored escaped spaces and admitted malformed output or stalled on constraints. Final format is the base Answer JSON schema. A deterministic adapter may render existing exact citation objects into inline tags only when every triple matches this request and there is one source/section pair; unknown or ambiguous references are not repaired. Leading known tags can be moved to the displayed sentence end. The independent final per-claim/source/page validator and one-retry/fallback policy still run. Actual native source-public observations and red tests are retained.

Improved rendering exposed a real indexed-poison escape previously hidden by format fallback. The shared generation path now quarantines obvious assistant-directed instruction blocks and user override sentences before generation, preserving original stored documents/IDs and remaining factual text. Empty safe context refuses before generation. Native document/user attacks were rerun after the fix. This conservative pattern guard can falsely remove ambiguous text and is not universal injection detection. No source truth or golden labels were rewritten.

The final real report has five expect-string misses. Two are terse negative answers rather than the literal expected keyword; q07 is a conservative floor refusal, q08 a verification fallback, and q17 returns a heading rather than the requested condition. These are residual usefulness/semantic limits, not hidden by perfect citation-integrity numbers. Citation validity is not answer correctness. The fixture report has no expect misses.

Full Windows extraction/OCR/embedding/publication produced 813 chunks. Actual interpreter OS peak was 238,583,808 bytes (227.53 MiB), excluding separate OCR children; the initial roughly 4-MiB launcher measurement was invalid and retained separately. This is not a pod/cgroup peak or a tested memory-limit margin. Final Kubernetes measurements remain required from platform work.


## Heading-only dense hits and parent-page context

The academic-warning user regression exposed a high-similarity chunk containing only its heading. The query path now retrieves a bounded 3 * top-k pool and expands title-only PDF hits from at most 32 records on the same immutable collection/source/page/version/superseded identity. It includes at most eight intact blocks and 1800 characters. The displayed score/citation identity belong to the original heading seed; added context is authentic indexed text with child-section labels, rather than a new similarity score. Top-k remains five, the .74 relevance floor is unchanged, and HTML logical pages are excluded from this physical-page expansion. Context/prompt cache namespace was versioned.

This is dense retrieval with parent-page context, not a change to the frozen source corpus/chunking/embedding experiments. CPU generation now allows 120s per attempt with 360s outer budgets. The exact reported question returned a supported page-24 answer and a .250s cached repeat; the full real gate still reports recall@5 .933333/citation integrity 1/required abstentions 1. See [academic-warning evidence](evidence/app/academic-warning-fix/README.md) for the interrupted diagnostic run, measured recovery, final results and remaining answer-completeness limits.
