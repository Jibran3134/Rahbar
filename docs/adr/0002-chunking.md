# ADR 0002 - Measured structural chunks and relevance tradeoff

Status: selected from S19 actual nomic/Chroma retrieval measurements on the frozen 17-question dataset. Human/platform review pending. No claim of held-out generalization.

Use page-local canonical sections, paragraph/sentence/word fallback and at most 30 units overlap with a 250-unit cap. Units use unicode-word-4-and-punctuation-v1, an approximation, not model tokens. Stable digest IDs preserve document/version/section/page/content/position identity. No chunk spans pages; section state carries across them. Explicit Markdown headings keep their full labels for CI compatibility.

| Size / overlap | Actual chunks | Original units | Stored units | Amplification | Raw recall@3 | Raw recall@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 250 / 30 | 813 | 60,357 | 62,412 | 1.034047 | 1.000000 | 1.000000 |
| 400 / 50 | 760 | 60,357 | 61,254 | 1.014862 | 0.933333 | 0.933333 |
| 650 / 80 | 742 | 60,357 | 60,445 | 1.001458 | 0.933333 | 0.933333 |

All three indices were actually embedded, published in separate experiment namespaces and queried with the same real query vectors/model and exact evaluator matching. Cache and generation were excluded from these retrieval-only comparisons. Source/golden hashes stayed frozen. Raw recall uses all hits; the API relevance gate further reduces returned evidence.

Select 250/30 for better source-section recall despite extra fragments/overlap. 650/80 preserved the complete selected definition in one 520-unit chunk and stored less duplication, but lost one ordinary source match. The long definition remains covered by three page-48 chunks at 250/30. More context in one chunk is not automatically better embedding discrimination.

Select RELEVANCE_FLOOR=.74 as the smallest tested candidate rejecting both known absent-topic queries. With the assignment-aligned query-level gate, retained recall@5 is .933333 (14/15 answerable questions), versus raw 1.0. The earlier per-passage filter measured .866667 but discarded useful lower-ranked context after a query was accepted; that superseded experiment is preserved separately. Lower .70 retains full recall but admits one absent-topic candidate to generation; .78 loses substantially more answerable evidence. This safety/usefulness tradeoff and residual false refusals are explicit. The final native generated-answer results are separate in eval/results.json, not inferred from this table.

Cache calibration tested .90/.95/.98 on two paraphrases and five near misses with signature checks. .90: two positive hits/one false regular-vs-summer hit; .95: one positive/no false hit; .98: zero positive/no false hit. Select .95. Tiny calibration set is not a guarantee of semantic equivalence; numeric/version/course/topic/negation guards remain required. Evidence: S19-measurements.json, per-type rows/floors/cache pairs; real and fixture final baselines are distinct and created explicitly only after absolute gates.
