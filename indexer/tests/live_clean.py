"""Explicit S04 audit of hash-verified real S03 extraction outputs, no services.

Full cleaned source text stays ignored; committed evidence holds counts/hashes
and selected source-fidelity checks, not republished document passages.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live_extract import check_source_probes  # noqa: E402
from pipeline.clean import clean  # noqa: E402
from pipeline.models import Document, Page  # noqa: E402


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    evidence = root / "docs/evidence/app/sprints"
    raw = root / "corpus/raw"
    output = raw / "_s04-cleaned"
    output.mkdir(exist_ok=True)
    previous = json.loads((evidence / "S03-live.json").read_text(encoding="utf-8"))
    records = json.loads((raw / "_index.json").read_text(encoding="utf-8"))
    extracted = {doc["source"]: doc for doc in previous["documents"]}
    results = []
    documents: dict[str, tuple[Document, Document]] = {}
    for entry in records:
        source = entry["file"]
        text = (raw / "_s03-extracted" / (source + ".txt")).read_text(encoding="utf-8")
        matches = re.findall(
            r"\n--- SOURCE PAGE (\d+); OCR=(True|False) ---\n(.*?)(?=\n\n--- SOURCE PAGE|\Z)",
            text, re.S)
        pages = [Page(source, int(number), body, ocr == "True") for number, ocr, body in matches]
        expected = extracted[source]["pages"]
        assert len(pages) == len(expected), source
        for page, original in zip(pages, expected, strict=True):
            assert page.page == original["page"] and page.ocr == original["ocr"], source
            assert hashlib.sha256(page.text.encode()).hexdigest() == original["text_sha256"], (
                source, page.page, "S03 extraction text hash mismatch")
        assert hashlib.sha256((raw / source).read_bytes()).hexdigest() == entry["sha256"], source
        doc = Document(source, entry["doc_version"], entry["superseded"], pages)
        before = asdict(doc)
        cleaned = clean(doc)
        assert asdict(doc) == before, "Input was mutated"
        assert asdict(clean(cleaned)) == asdict(cleaned), (source, "Not idempotent")
        assert (doc.source, doc.doc_version, doc.superseded) == (
            cleaned.source, cleaned.doc_version, cleaned.superseded)
        audit = []
        for old, new in zip(doc.pages, cleaned.pages, strict=True):
            assert (old.source, old.page, old.ocr) == (new.source, new.page, new.ocr)
            assert bool(old.text.strip()) == bool(new.text.strip()), "Lost a nonempty page"
            removed = [line for line in old.text.splitlines() if line.strip()
                       and line.strip() not in new.text.splitlines()]
            audit.append({"page": new.page, "ocr": new.ocr,
                          "before_characters": len(old.text), "after_characters": len(new.text),
                          "removed_or_normalized_lines": len(removed),
                          "text_sha256": hashlib.sha256(new.text.encode()).hexdigest()})
        body = "\n".join(f"\n--- SOURCE PAGE {p.page}; OCR={p.ocr} ---\n{p.text}"
                         for p in cleaned.pages)
        (output / (source + ".txt")).write_text(body, encoding="utf-8")
        documents[source] = doc, cleaned
        results.append({"source": source, "pages": audit,
                        "changed_pages": sum(a.text != b.text for a, b in zip(
                            doc.pages, cleaned.pages, strict=True))})

    checks = check_source_probes(output)
    current = documents["academic-rules-handbook-jun-2026.pdf"][1]
    student_before, student = documents["student-handbook-jun-2026.pdf"]
    fee = documents["fee-structure-page.html"][1].pages[0].text
    attendance = current.pages[9].text
    checks.update({
        "attendance_clause_and_percentages": all(v in attendance for v in ("1.21", "100%", "20%")),
        "cgpa_exact_decimal": "2.00" in current.pages[9].text,
        "fee_header_and_row": all(v in fee for v in ("| Program | Fee |",
                                                   "| BBA / BS | Rs. 12,000 |")),
        "fee_units_and_effective_date": "per credit hour" in fee and "Fall 2026" in fee,
        "definition_body_words_preserved": (
            # Every original line except the observed running header/footer
            # must still occur, in order, on the same physical page.
            [line.strip() for line in student_before.pages[47].text.splitlines()[1:-1]
             if line.strip()]
            == [line for line in student.pages[47].text.splitlines() if line]),
        "observed_institutional_header_removed": (
            student_before.pages[47].text.startswith("NATIONAL UNIVERSITY OF")
            and not student.pages[47].text.startswith("NATIONAL UNIVERSITY OF")),
        "all_source_bytes_and_extracted_page_hashes_verified": True,
        "metadata_input_immutability_idempotence_and_nonempty_pages": True,
    })
    passed = all(checks.values())
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "passed": passed,
              "scope": "Cleaning saved hash-verified real OCR/text outputs; OCR not rerun",
              "checks": checks, "documents": results, "text_outputs": str(output.relative_to(root))}
    (evidence / "S04-live.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"passed": passed, "checks": checks,
                      "changed_pages": {r["source"]: r["changed_pages"] for r in results}}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
