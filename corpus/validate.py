"""Validate S01's source snapshot and independently authored golden-set structure.

This is a corpus audit, not the production extractor or the S17 quality evaluator.
Original PDFs stay in ignored raw/. Semantic/manual image review is documented
separately; this script cannot prove that a golden answer is factually correct.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import yaml  # type: ignore[import-untyped]  # Existing PyYAML pin ships without typing stubs.
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


class HtmlAudit(HTMLParser):
    """Count source tables/headings and collect visible text for audit only."""

    def __init__(self) -> None:
        super().__init__()
        self.tables = 0
        self.headings: list[str] = []
        self.text: list[str] = []
        self._heading: list[str] | None = None
        self._hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._hidden += 1
        if tag == "table":
            self.tables += 1
        if re.fullmatch(r"h[1-6]", tag):
            self._heading = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._hidden = max(0, self._hidden - 1)
        if re.fullmatch(r"h[1-6]", tag) and self._heading is not None:
            self.headings.append(" ".join("".join(self._heading).split()))
            self._heading = None

    def handle_data(self, data: str) -> None:
        if not self._hidden:
            self.text.append(data)
            if self._heading is not None:
                self._heading.append(data)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(path: Path) -> str:
    """Keep text snapshots stable across Git's Windows/Linux newline conversion."""
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").encode("utf-8")).hexdigest()


def validate(golden_path: Path) -> dict:
    sources = yaml.safe_load((ROOT / "corpus/sources.yaml").read_text(encoding="utf-8"))
    entries = json.loads((ROOT / "corpus/raw/_index.json").read_text(encoding="utf-8"))
    golden = yaml.safe_load(golden_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    documents: list[dict] = []
    pdf_text: dict[str, list[str]] = {}
    manual_review: list[dict] = []
    names = {source["name"]: source for source in sources["documents"]}
    if len(names) != len(sources["documents"]) or len(entries) != len(names):
        errors.append("Source names/index count must be unique and complete")
    if len({entry["file"] for entry in entries}) != len(entries):
        errors.append("Downloaded filenames must be unique")
    for entry in entries:
        path = ROOT / "corpus/raw" / entry["file"]
        source = names.get(entry["name"], {})
        if not path.is_file() or digest(path) != entry["sha256"]:
            errors.append(f"Missing/changed bytes: {entry['file']}")
            continue
        if (source.get("doc_version"), source.get("superseded")) != (
            entry["doc_version"], entry["superseded"]
        ):
            errors.append(f"Source/index metadata mismatch: {entry['file']}")
        doc = {key: entry[key] for key in ("file", "sha256", "doc_version", "superseded")}
        doc["bytes"] = path.stat().st_size
        if path.suffix == ".pdf":
            if not path.read_bytes().startswith(b"%PDF-"):
                errors.append(f"Not a real PDF: {path.name}")
                continue
            reader = PdfReader(path)
            pages = []
            pdf_text[path.name] = []
            for number, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                pdf_text[path.name].append(text)
                resources = page.get("/Resources", {})
                resources = resources.get_object() if hasattr(resources, "get_object") else resources
                fonts = resources.get("/Font", {})
                fonts = fonts.get_object() if hasattr(fonts, "get_object") else fonts
                xobjects = resources.get("/XObject", {})
                xobjects = xobjects.get_object() if hasattr(xobjects, "get_object") else xobjects
                images = sum(
                    obj.get_object().get("/Subtype") == "/Image" for obj in xobjects.values()
                )
                pages.append({"page": number, "text_characters": len(text.strip()),
                              "font_resources": len(fonts), "image_resources": images})
            doc.update(kind="pdf", pages=len(pages), page_audit=pages,
                       text_characters=sum(page["text_characters"] for page in pages),
                       image_only=all(page["text_characters"] == 0 for page in pages))
        else:
            parser = HtmlAudit()
            parser.feed(path.read_text(encoding="utf-8"))
            doc.update(kind="html", pages=None, tables=parser.tables, headings=parser.headings,
                       text_characters=len(" ".join(parser.text)))
        documents.append(doc)
    if len(documents) < 6:
        errors.append("At least six verified documents required")
    pdf_pages = sum(doc["pages"] for doc in documents if doc["kind"] == "pdf")
    if pdf_pages < 40:
        errors.append("At least forty actual PDF pages required")
    if not any(doc.get("image_only") for doc in documents):
        errors.append("No verified fully image-only PDF")
    if not any(doc.get("tables", 0) > 0 for doc in documents):
        errors.append("No table-bearing HTML source")
    families: dict[str, list[dict]] = {}
    for source in sources["documents"]:
        if source.get("policy_family"):
            families.setdefault(source["policy_family"], []).append(source)
    if not any(len({s["doc_version"] for s in family}) >= 2
               and {s["superseded"] for s in family} == {True, False}
               for family in families.values()):
        errors.append("No historical/current version pair in one policy family")
    questions = golden.get("questions", [])
    counts = Counter(question.get("type") for question in questions)
    for category, minimum in {"ordinary": 8, "version": 2, "exact": 2,
                              "abstain": 2, "injection": 1}.items():
        if counts[category] < minimum:
            errors.append(f"Insufficient {category} questions")
    if len({q.get("id") for q in questions}) != len(questions):
        errors.append("Golden question IDs must be unique")
    by_file = {doc["file"]: doc for doc in documents}
    for question in questions:
        if not 3 <= len(question.get("question", "")) <= 500:
            errors.append(f"Invalid question length: {question.get('id')}")
        abstain = question.get("must_abstain", False)
        if question.get("type") == "abstain" and (not abstain or question.get("relevant")):
            errors.append(f"Abstention must be marked and have no relevant passages: {question['id']}")
        if not abstain and not question.get("relevant"):
            errors.append(f"Answerable question needs relevant passages: {question['id']}")
        for passage in question.get("relevant", []):
            matched_doc = by_file.get(passage.get("source"))
            if not matched_doc or not passage.get("section"):
                errors.append(f"Unknown source/section: {question['id']}")
                continue
            evidence_page = passage.get("page")
            if matched_doc["kind"] == "pdf" and (
                not isinstance(evidence_page, int) or not 1 <= evidence_page <= matched_doc["pages"]
            ):
                errors.append(f"Invalid physical PDF page: {question['id']}")
            elif matched_doc["kind"] == "pdf":
                page_text = pdf_text[passage["source"]][evidence_page - 1]
                section = passage["section"]
                if not page_text.strip():
                    manual_review.append({"question": question["id"], "source": matched_doc["file"],
                                          "page": evidence_page, "section": section,
                                          "reason": "Image evidence needs visual review/OCR"})
                elif re.fullmatch(r"\d+(?:\.\d+)+", section):
                    if not re.search(r"(?<!\d)" + re.escape(section) + r"(?!\d)", page_text):
                        errors.append(f"Numbered clause absent from stated page: {question['id']}")
                elif section == "XII.1":
                    if "XII." not in page_text or not re.search(r"1\.\s*Introduction", page_text):
                        errors.append(f"Hierarchical section absent: {question['id']}")
                else:
                    errors.append(f"PDF section needs an explicit audit rule: {question['id']}")
            if matched_doc["kind"] == "html" and (
                evidence_page is not None or passage["section"] not in matched_doc["headings"]
            ):
                errors.append(f"Invalid HTML heading/page: {question['id']}")
    freeze_path = golden_path.with_name("golden.freeze.json")
    if freeze_path.exists():
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        if freeze.get("text_hash_format") != "utf8-no-bom-lf":
            errors.append("Unknown text freeze format; explicit snapshot review required")
        for label, path in {"golden_sha256": golden_path,
                            "sources_sha256": ROOT / "corpus/sources.yaml",
                            "manifest_sha256": ROOT / "corpus/MANIFEST.md"}.items():
            if freeze[label] != text_digest(path):
                errors.append(f"Frozen snapshot mismatch: {label}; review rather than overwrite")
    return {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "passed": not errors, "errors": errors, "documents": documents,
            "document_count": len(documents), "pdf_pages": pdf_pages,
            "html_pages_counted_toward_pdf_requirement": 0,
            "questions": len(questions), "question_types": dict(counts),
            "golden_sha256": text_digest(golden_path), "freeze_checked": freeze_path.exists(),
            "image_passages_requiring_manual_review": manual_review,
            "limits": "Structural/byte audit only; semantic truth and scans need original-source review."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=ROOT / "eval/golden.yaml")
    parser.add_argument("--report", type=Path,
                        default=ROOT / "docs/evidence/app/sprints/S01-audit.json")
    args = parser.parse_args()
    try:
        report = validate(args.golden)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"AUDIT FAILED: {exc}")
        return 1
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("passed", "document_count", "pdf_pages",
                                                 "questions", "question_types", "errors")}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
