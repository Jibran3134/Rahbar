# Corpus: FAST-NUCES public academic and student policies

Owner: Jibran. Source selection and initial golden questions were completed in S01 before chunking/retrieval implementation or tuning. This is public university material, not a synthetic corpus or lecture slides.

## Source snapshot and provenance

Seven documents were downloaded successfully on 4 November 2026. The five PDFs contain **161 physical pages**; HTML is not assigned artificial page counts. Covers/blank pages are included in the transparent PDF totals, but the corpus exceeds forty pages even without them.

Download with the existing corpus/fetch.py. Commit sources.yaml, MANIFEST.md and the validation/golden artifacts; third-party PDFs, HTML, rendered inspection images and local text extracts stay in ignored corpus/raw/. Their copyright remains with the source owner. No authenticated university service was accessed.

| Downloaded file | Verified version | Physical PDF pages | Treatment |
| --- | --- | ---: | --- |
| undergraduate-academic-rules-aug-2023.pdf | August 2023, visually confirmed on title page | 26 | Historical undergraduate rules; superseded=true |
| academic-rules-handbook-jun-2026.pdf | June 2026 | 58 | Current detailed undergraduate rules; superseded=false |
| student-handbook-jun-2026.pdf | June 2026 | 64 | Current student policies and long AI introduction |
| prospectus-academic-rules-and-regulations.pdf | Prospectus 2026 printed on the original pages | 5 | Condensed summary; detailed current handbook governs clause questions |
| faculty-entrepreneurship-and-technical-start-ups-policy.pdf | 30 May 2022, visually confirmed on page 1 | 8 | Fully scanned policy and blank annex forms |
| fee-structure-page.html | Snapshot 4 November 2026; tuition heading specifies Fall 2026 | Not counted | Three tables |
| grading-page.html | Snapshot 4 November 2026 | Not counted | Five tables |

Every URL, byte size and SHA-256 is in [MANIFEST.md](../corpus/MANIFEST.md). The [machine audit](evidence/app/sprints/S01-audit.json) reports page-level text/font/image counts. Dates are source publication labels or explicit snapshot dates; no publication date was inferred solely from a URL.

## All seven required properties

| Requirement | Actual evidence | Consequence for later implementation |
| --- | --- | --- |
| At least six documents / forty pages | Seven documents; 26 + 58 + 64 + 5 + 8 = 161 physical PDF pages | Use actual originals, not the tiny synthetic CI corpus |
| Two versions of the same policy | August 2023 and June 2026 undergraduate academic rules; same policy_family in sources.yaml | Store doc_version/superseded and prefer current rules unless historical version explicitly requested |
| Image-only scanned PDF | All eight entrepreneurship-policy pages have zero extracted text, zero font resources and one image resource each; pdffonts returns no entries | S03 must OCR this source; metadata/font inventory is not OCR completion |
| Meaningful table | Fee page's program/tuition rows and refund timelines; grading tables; current academic handbook grade-point table | Preserve header/value associations, program context, units and effective date |
| Long definitions/context | Student handbook section XII > 1 Introduction on physical page 48, printed page 40: 237 whitespace-separated words on the visible physical page (S03 corrected the initial unclipped 314-word estimate) | A naive 100-token splitter divides the multi-paragraph definition/context; preserve hierarchy and document token-count approximation |
| Deliberately absent topic | Hostel room allotment deadlines and hostel-specific deposits; Transport and Hostel Facilities prospectus excluded | Two realistic must-abstain questions; a generic admission deposit is insufficient hostel evidence |
| Exact terms | Numbered clauses, percentages, CGPA values, program labels and per-credit tuition | Preserve identifiers/numbers; measure exact-term recall later |

The 2023 PDF is also image-dependent: 24 of its 26 pages have no extracted text; only 212 characters are extracted across the entire file. A small cover/URL text layer must not disguise unreadable policy content. Historical golden answers require OCR in S03 before retrieval can succeed.

Current/student PDFs contain blank/cover pages and off-page glyphs that made the initial text audit appear to repeat adjacent pages. S03 now restricts extraction to visible page bounds and verifies real OCR; see PIPELINE.md. Cleaning and chunking remain unimplemented. Historical S01 audit counts are retained as observations of the original unclipped audit.

## Verified historical changes

Original 2023 pages were rendered and read visually, not inferred from current retrieval. Local inspection images remain under corpus/raw/_inspection/.

| Clause | 2023 source location | 2026 source location | Verified distinction |
| --- | --- | --- | --- |
| 4.25 | Physical 16 / printed 11 | Physical 23 / printed 17 | Deadline moves from the end of classes to the end of the makeup week |
| 4.3 | Physical 14 / printed 9 | Physical 19 / printed 13 | Earlier permission depends on not getting ahead of the batch; current provision names final-year students and one additional course, including FYP |

Current questions q09/q10 and historical questions q16/q17 exercise both directions. Unchanged warning/attendance rules were not misrepresented as version changes. The current handbook is the application corpus's designated latest edition; this is not a claim of external legal certification.

## Tables and definition review

The fee table is explicitly per credit hour and has a Fall 2026 effective heading. Its neighboring admission/security/miscellaneous amounts are different concepts. Golden q12 requires the program row, units and effective-date context; q05 asks the admission deposit separately.

The grading page's repeated-course explanation is under Description of Grades; q06 targets that prose rather than an unrelated table row. The source tables and long AI introduction were inspected directly from original HTML/PDF text. The scanned entrepreneurship policy's eligibility clause was read from its rendered page; q07 deliberately requires its future OCR path.

No table-repair, OCR-recovery or chunk-quality result is claimed in S01. Those measurements belong to S03/S19/S20.

## Deliberately absent hostel information

The selected student handbook mentions the existence/location of in-campus hostels in section X, physical pages 44–45. It does not provide the selected allotment deadline or hostel-room deposit. These are deliberately more precise than asking whether hostels exist, which would be answerable.

Review combined text searches in text-bearing PDFs/HTML, the historical handbook's academic-only contents and relevant original pages, and visual inspection of all eight scanned entrepreneurship pages. Search-only absence cannot establish facts inside images; the scan's scope was reviewed separately. No dedicated hostel document was selected.

The admission security deposit in q05 is a near-miss distractor for q14. It must not be substituted as a hostel charge. Absence means “not evidenced by this frozen corpus,” not “the university has no such policy anywhere.”

## Golden truth and canonical evidence labels

[eval/golden.yaml](../eval/golden.yaml) has 17 independently source-authored questions: 8 ordinary, 4 version-sensitive, 2 exact-term, 2 must-abstain and 1 user-injection probe. Extra historical questions ensure version filtering is tested both ways.

- source is the fetcher's actual local filename.
- Numeric clauses use the printed identifier, such as 1.20 or 4.25.
- XII.1 means student handbook section XII > subsection 1 Introduction. The future chunker must preserve this hierarchy rather than conflating every subsection 1.
- HTML section names preserve the original heading text with whitespace normalized.
- PDF page is physical, 1-based; HTML page is null.
- Source/section is the existing evaluator's intended primary matching unit. Page is retained for citation verification and original-source inspection; duplicate extracted text must not inflate passage recall.
- expect is a short diagnostic clue, not a sufficient correctness assertion. The source may support a fuller answer.
- Extra review/doc_version fields document provenance and do not change the existing request schema.

Each question's review field records its source check. Scan passages are explicitly flagged for manual review by the structural audit. Codex inspected the originals during S01; Jibran's subsequent human review is pending and is not fabricated.

The [freeze record](../eval/golden.freeze.json) binds the initial golden/source/manifest hashes before tuning. Textual freeze hashes normalize UTF-8 BOM and line endings so Windows/Linux Git checkouts agree; downloaded-file checksums remain strict byte hashes. It is a checksum snapshot, not an unauthorized Git commit. Later genuine label corrections require a documented review and explicit freeze update; never relabel questions to flatter retrieval.

## Reproduce S01 validation

~~~powershell
.\.venv\Scripts\python.exe corpus/fetch.py
.\.venv\Scripts\python.exe corpus/fetch.py --verify
.\.venv\Scripts\python.exe corpus/validate.py
~~~

The validator checks bytes, source metadata, PDF counts/text/font/image layers, HTML tables/headings, question categories/IDs/pages/anchors and the frozen artifact hashes. It does not certify semantic truth, perform OCR, score retrieval or enforce the later live-stack quality gate. Original-source review remains necessary.

A forced refresh can change public HTML/PDF bytes. Do not overwrite the committed manifest/freeze and silently treat a new source snapshot as the old one. Reconcile changed originals explicitly.
