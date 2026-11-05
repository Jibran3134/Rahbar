"""Explicit S03 real-corpus audit; not collected as an offline pytest unit test.

Run from the repository root with the venv Python. OCR needs native Tesseract;
this audit never embeds, queries a model, writes Chroma or modifies golden truth.
Full source/extracted content remains in ignored corpus/raw/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


class FlatText(HTMLParser):
    """Document the difference from naive tag stripping, not a production parser."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def check_source_probes(output: Path) -> dict[str, bool]:
    """Check S01's inspected clauses, not generated answers or retrieval quality."""
    def page(source: str, number: int) -> str:
        path = output / (source + ".txt")
        if not path.exists():
            return ""
        match = re.search(
            rf"--- SOURCE PAGE {number}; OCR=(?:True|False) ---\n(.*?)(?=\n--- SOURCE PAGE|\Z)",
            path.read_text(encoding="utf-8"), re.S,
        )
        return match.group(1) if match else ""

    def clause(text: str, label: str, next_label: str) -> str:
        match = re.search(
            rf"^\s*{re.escape(label)}\.?\s+(.*?)(?=^\s*{re.escape(next_label)}(?:\.|\s)|\Z)",
            text, re.S | re.M,
        )
        return match.group(1) if match else ""

    old = "undergraduate-academic-rules-aug-2023.pdf"
    current = "academic-rules-handbook-jun-2026.pdf"
    startup = "faculty-entrepreneurship-and-technical-start-ups-policy.pdf"
    old_load = clause(page(old, 14), "4.3", "4.4")
    old_deadline = clause(page(old, 16), "4.25", "4.26")
    eligibility = clause(page(startup, 1), "4.2", "4.3")
    current_load = clause(page(current, 19), "4.3", "4.4")
    current_deadline = clause(page(current, 23), "4.25", "4.26")
    definition = page("student-handbook-jun-2026.pdf", 48)
    return {
        "historical_load_clause_association": bool(old_load) and "batch" in old_load.lower(),
        "historical_deadline_clause_association": bool(
            re.search(r"last day of classes", old_deadline, re.I)),
        "startup_eligibility_clause_association": bool(
            re.search(r"more than 1 year", eligibility, re.I)),
        "current_load_clause_association": bool(current_load) and "final year" in current_load.lower(),
        "current_deadline_clause_association": bool(current_deadline)
        and "makeup" in current_deadline.lower(),
        "student_definition_section_preserved": "XII." in definition and "Introduction" in definition,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path("corpus/raw"))
    parser.add_argument("--report", type=Path,
                        default=Path("docs/evidence/app/sprints/S03-live.json"))
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pipeline.extract import extract

    records = json.loads((args.corpus / "_index.json").read_text(encoding="utf-8"))
    output = args.corpus / "_s03-extracted"
    output.mkdir(exist_ok=True)
    results = []
    for entry in records:
        started = time.perf_counter()
        print(f"Extracting {entry['file']}", flush=True)
        try:
            doc = extract(str(args.corpus / entry["file"]), entry["doc_version"], entry["superseded"])
            page_audit = [{"page": page.page, "ocr": page.ocr,
                           "text_characters": len(page.text.strip()),
                           "text_sha256": hashlib.sha256(page.text.encode()).hexdigest()}
                          for page in doc.pages]
            body = "\n".join(f"\n--- SOURCE PAGE {page.page}; OCR={page.ocr} ---\n{page.text}"
                             for page in doc.pages)
            (output / (doc.source + ".txt")).write_text(body, encoding="utf-8")
            results.append({"source": doc.source, "success": True, "pages": page_audit,
                            "ocr_pages": [page.page for page in doc.pages if page.ocr],
                            "empty_pages": [page.page for page in doc.pages if not page.text.strip()],
                            "seconds": round(time.perf_counter() - started, 2)})
            print(f"  {len(doc.pages)} pages; {results[-1]['ocr_pages']} OCR; "
                  f"{results[-1]['seconds']}s", flush=True)
        except Exception as exc:
            results.append({"source": entry["file"], "success": False, "error": str(exc),
                            "seconds": round(time.perf_counter() - started, 2)})
            print(f"  FAILED: {exc}", flush=True)
    passed = bool(results) and all(result["success"] for result in results) and len(results) == len(records)
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "passed": passed,
              "documents": results, "text_outputs": str(output),
              "scope": "Real extraction/OCR only, not retrieval or factuality evaluation"}
    fee_source = args.corpus / "fee-structure-page.html"
    flat = FlatText()
    flat.feed(fee_source.read_text(encoding="utf-8"))
    plain = " ".join(" ".join(flat.parts).split())
    extracted_path = output / "fee-structure-page.html.txt"
    if extracted_path.exists():
        after = extracted_path.read_text(encoding="utf-8")
        before_match = re.search(r"Program\s+Fee\s+BBA / BS\s+Rs\. 12,000", plain)
        table_checks = {"original_table_count": fee_source.read_text(encoding="utf-8").count("<table"),
                        "naive_flattening_merges_row_structure": before_match is not None,
                        "header_preserved": "| Program | Fee |" in after,
                        "program_value_pair_preserved": "| BBA / BS | Rs. 12,000 |" in after,
                        "units_preserved": "per credit hour" in after,
                        "effective_date_preserved": "Fall 2026" in after,
                        "navigation_excluded": "Job Portal" not in after,
                        "note": "Structural table improvement; no invented PDF table-repair claim"}
        args.report.with_name("S03-table-checks.json").write_text(
            json.dumps(table_checks, indent=2), encoding="utf-8")
        if not all(table_checks[key] for key in ("header_preserved", "program_value_pair_preserved",
                                                "units_preserved", "effective_date_preserved")):
            passed = False
    if passed:
        source_checks = check_source_probes(output)
        args.report.with_name("S03-source-probes.json").write_text(
            json.dumps(source_checks, indent=2), encoding="utf-8")
        passed = all(source_checks.values())
        report["source_probes"] = source_checks
    report["passed"] = passed
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"LIVE_EXTRACTION_PASS={passed}", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
