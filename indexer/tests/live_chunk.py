"""Explicit S05 structural audit on real, hash-verified S04 cleaned outputs.

No model, storage or retrieval scoring. Chunk text stays in ignored corpus/raw.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.chunk import TOKEN_COUNTER, chunk, chunking_stats, count_tokens  # noqa: E402
from pipeline.clean import clean  # noqa: E402
from pipeline.extract import extract  # noqa: E402
from pipeline.models import Document, Page  # noqa: E402
from pipeline.run import discover  # noqa: E402


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    evidence = root / "docs/evidence/app/sprints"
    raw = root / "corpus/raw"
    output = raw / "_s05-chunks"
    output.mkdir(exist_ok=True)
    previous = json.loads((evidence / "S04-live.json").read_text(encoding="utf-8"))
    expected_docs = {doc["source"]: doc for doc in previous["documents"]}
    entries = json.loads((raw / "_index.json").read_text(encoding="utf-8"))
    documents = []
    for entry in entries:
        source = entry["file"]
        text = (raw / "_s04-cleaned" / (source + ".txt")).read_text(encoding="utf-8")
        matches = re.findall(
            r"\n--- SOURCE PAGE (\d+); OCR=(True|False) ---\n(.*?)(?=\n\n--- SOURCE PAGE|\Z)",
            text, re.S)
        pages = [Page(source, int(n), body, ocr == "True") for n, ocr, body in matches]
        expected = expected_docs[source]["pages"]
        assert len(pages) == len(expected), source
        for page, saved in zip(pages, expected, strict=True):
            assert page.page == saved["page"] and page.ocr == saved["ocr"], source
            assert hashlib.sha256(page.text.encode()).hexdigest() == saved["text_sha256"], source
        assert hashlib.sha256((raw / source).read_bytes()).hexdigest() == entry["sha256"], source
        documents.append(Document(source, entry["doc_version"], entry["superseded"], pages))

    configurations = []
    for size, overlap in [(250, 30), (400, 50), (650, 80)]:
        all_chunks = []
        original = stored = 0
        per_doc = []
        for doc in documents:
            pieces = chunk(doc, size, overlap)
            assert [asdict(c) for c in pieces] == [asdict(c) for c in chunk(doc, size, overlap)]
            assert all(0 < count_tokens(c.text) <= size for c in pieces)
            assert all(c.source == doc.source and c.doc_version == doc.doc_version
                       and c.superseded == doc.superseded and c.section
                       and c.page in {p.page for p in doc.pages} for c in pieces)
            stats = chunking_stats(doc, pieces)
            assert stats.stored_tokens >= stats.original_tokens
            # With overlap disabled, concatenation must preserve every nonspace
            # source character in page order, including clause/table punctuation.
            no_overlap = chunk(doc, size, 0)
            for page in doc.pages:
                recovered = "".join(c.text for c in no_overlap if c.page == page.page)
                assert re.sub(r"\s", "", recovered) == re.sub(r"\s", "", page.text), (
                    doc.source, page.page, "Source content lost/reordered")
            assert chunking_stats(doc, no_overlap).stored_tokens == stats.original_tokens
            original += stats.original_tokens
            stored += stats.stored_tokens
            all_chunks.extend(pieces)
            per_doc.append({"source": doc.source, **asdict(stats), "amplification": stats.amplification})
        assert len({c.id for c in all_chunks}) == len(all_chunks)

        def selected(source: str, section: str, page: int) -> list[str]:
            return [c.text for c in all_chunks
                    if c.source == source and c.section == section and c.page == page]

        def contains(source: str, section: str, page: int, *terms: str) -> bool:
            texts = [" ".join(text.split()).lower() for text in selected(source, section, page)]
            return bool(texts) and all(any(term.lower() in text for text in texts) for term in terms)

        current = "academic-rules-handbook-jun-2026.pdf"
        old = "undergraduate-academic-rules-aug-2023.pdf"
        student = "student-handbook-jun-2026.pdf"
        fee = "fee-structure-page.html"
        probes = {
            "current_prerequisite_1_20": contains(current, "1.20", 9, "passed"),
            "current_attendance_1_21": contains(current, "1.21", 10, "100%", "20%"),
            "current_warning_5_7": contains(current, "5.7", 25, "2.00", "reset"),
            "current_withdrawal_4_25": contains(current, "4.25", 23, "makeup"),
            "historical_withdrawal_4_25": contains(old, "4.25", 16, "last day of classes"),
            "current_load_4_3": contains(current, "4.3", 19, "final year"),
            "historical_load_4_3": contains(old, "4.3", 14, "batch"),
            "scanned_startup_4_2": contains(
                "faculty-entrepreneurship-and-technical-start-ups-policy.pdf", "4.2", 1,
                "more than 1 year"),
            "long_definition_XII_1": contains(student, "XII.1", 48, "privacy", "Generative"),
            "fee_heading_and_table": contains(fee, "Tuition Fee (w.e.f. Fall 2026 semester)", 1,
                                              "per credit hour", "| BBA / BS | Rs. 12,000 |"),
            "security_deposit": contains(fee, "Security Deposit", 1, "20,000"),
            "grading_text_heading": contains("grading-page.html", "Description of Grades", 1, "recent"),
        }
        (output / f"chunks-{size}-{overlap}.jsonl").write_text(
            "\n".join(json.dumps(asdict(c), ensure_ascii=False) for c in all_chunks), encoding="utf-8")
        definition_pieces = selected(student, "XII.1", 48)
        configurations.append({"size": size, "overlap": overlap,
                               "chunk_count": len(all_chunks), "original_tokens": original,
                               "stored_tokens": stored, "amplification": stored / original,
                               "max_chunk_tokens": max(count_tokens(c.text) for c in all_chunks),
                               "definition_chunk_tokens": [count_tokens(t) for t in definition_pieces],
                               "source_probes": probes, "documents": per_doc,
                               "chunk_ids_sha256": hashlib.sha256(
                                   "\n".join(c.id for c in all_chunks).encode()).hexdigest()})
    fixture_chunks = []
    for path, version, superseded in discover(str(root / "eval/fixtures")):
        fixture_chunks.extend(chunk(clean(extract(str(path), version, superseded)), 400, 50))
    fixture_truth = yaml.safe_load((root / "eval/fixtures/golden.fixture.yaml").read_text(
        encoding="utf-8"))
    fixture_sections = {
        question["id"]: all(any(c.source == relevant["source"] and c.section == relevant["section"]
                                for c in fixture_chunks) for relevant in question.get("relevant", []))
        for question in fixture_truth["questions"] if question.get("relevant")}
    assert fixture_sections and all(fixture_sections.values()), fixture_sections
    fixture_checks = {"source_section_contracts": fixture_sections,
                      "planted_instruction_retained_as_source_data": any(
                          "Ignore all previous instructions" in c.text for c in fixture_chunks),
                      "document_count": len({c.source for c in fixture_chunks}),
                      "chunk_count": len(fixture_chunks),
                      "note": "Structural compatibility only; provider attack testing is S16"}
    passed = (all(all(c["source_probes"].values()) for c in configurations)
              and fixture_checks["planted_instruction_retained_as_source_data"])
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "passed": passed,
              "token_counter": TOKEN_COUNTER, "document_count": len(documents),
              "page_count": sum(len(d.pages) for d in documents),
              "scope": "Structural/source checks only; no recall, indexing, models or chosen final size",
              "checks": ["original/source page hashes", "stable output and unique IDs",
                         "metadata and size bounds", "lossless nonspace content/order without overlap",
                         "original/stored token accounting", "12 real canonical-section probes per setting"],
              "configurations": configurations, "text_outputs": str(output.relative_to(root))}
    report["fixtures"] = fixture_checks
    (evidence / "S05-live.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"passed": passed, "configurations": [
        {k: v for k, v in c.items() if k != "documents"} for c in configurations]}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
