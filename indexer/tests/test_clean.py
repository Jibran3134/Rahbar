"""Cleaning must remove supported artifacts without rewriting policy evidence."""

from dataclasses import asdict

import pytest

from pipeline.clean import clean
from pipeline.models import Document, Page


def document(texts: list[str], source: str = "policy.pdf") -> Document:
    return Document(source, "2026-06", True, [
        Page(source, i, text, ocr=i == 2) for i, text in enumerate(texts, 1)
    ])


def body(i: int) -> str:
    return "\n".join([f"Section {i}", "4.25 Withdrawal", "A policy paragraph.",
                      "", "Another paragraph.", "CS-101 remains valid.",
                      "Additional policy context.", "Further policy context.", "Last body line."])


def test_running_margins_removed_without_mutating_metadata_or_input() -> None:
    doc = document([f"NATIONAL UNIVERSITY OF EXAMPLE\n{body(i)}\n"
                    f"Student Handbook 2026 {i}" for i in range(1, 6)])
    before = asdict(doc)
    result = clean(doc)
    assert asdict(doc) == before
    assert result is not doc
    assert (result.source, result.doc_version, result.superseded) == (
        doc.source, doc.doc_version, doc.superseded)
    for old, new in zip(doc.pages, result.pages, strict=True):
        assert new is not old
        assert (new.source, new.page, new.ocr) == (old.source, old.page, old.ocr)
        assert "NATIONAL UNIVERSITY" not in new.text
        assert "Student Handbook" not in new.text
        assert body(new.page) == new.text


@pytest.mark.parametrize("repeated", ["Students must maintain CGPA 2.00.",
                                     "4.25 Withdrawal", "## Academic Rules", "Academic Warning"])
def test_repeated_policy_and_headings_are_not_margin_noise(repeated: str) -> None:
    doc = document([f"{repeated}\n{body(i)}\n{repeated}" for i in range(5)])
    assert [p.text.count(repeated) for p in clean(doc).pages] == [
        p.text.count(repeated) for p in doc.pages]


def test_repeated_running_title_inside_body_is_preserved() -> None:
    doc = document([f"{body(i)}\nStudent Handbook 2026\nMore body.\nEnd." for i in range(5)])
    assert all("Student Handbook 2026" in p.text for p in clean(doc).pages)


@pytest.mark.parametrize("count", [1, 2])
def test_insufficient_pages_do_not_establish_repeated_margins(count: int) -> None:
    doc = document([f"Student Handbook 2026\n{body(i)}" for i in range(count)])
    assert all("Student Handbook 2026" in p.text for p in clean(doc).pages)


def test_low_frequency_header_is_preserved() -> None:
    doc = document([("Student Handbook 2026\n" if i < 3 else "Other title\n") + body(i)
                    for i in range(6)])
    assert "Student Handbook 2026" in clean(doc).pages[0].text


def test_sequential_standalone_pdf_folios_removed_but_numbers_not_guessed() -> None:
    doc = document([f"{body(i)}\n{i + 10}" for i in range(1, 5)])
    assert all(p.text.endswith("Last body line.") for p in clean(doc).pages)
    doc = document([f"{body(i)}\n20" for i in range(1, 5)])
    assert all(p.text.endswith("20") for p in clean(doc).pages)


@pytest.mark.parametrize("source", ["policy.md", "policy.txt", "policy.html"])
def test_non_pdf_margins_remain_content(source: str) -> None:
    doc = document([f"Student Handbook 2026\n{body(i)}\n{i}" for i in range(1, 5)], source)
    assert all("Student Handbook" in p.text and p.text.endswith(str(p.page))
               for p in clean(doc).pages)


def test_structure_and_exact_evidence_survive_normalization() -> None:
    text = ("\ufeff## 4.25  Withdrawal\r\n\r\nCGPA\u00a02.00; 20%; Rs. 12,000; CS-101.\r\n"
            "| Program | Fee |\r\n| BBA / BS | Rs. 12,000 |\r\n\r\n"
            "pre-requisite; FAST-NUCES; final-year; non-\ncredit.\n\nDe\ufb01nition\u200b.\x00")
    result = clean(document([text])).pages[0].text
    assert result == ("## 4.25 Withdrawal\n\nCGPA 2.00; 20%; Rs. 12,000; CS-101.\n"
                      "| Program | Fee |\n| BBA / BS | Rs. 12,000 |\n\n"
                      "pre-requisite; FAST-NUCES; final-year; non-\ncredit.\n\nDefinition.")


def test_only_discretionary_soft_hyphen_wrap_is_joined() -> None:
    result = clean(document(["infor\u00ad\nmation and re\u00adentry; 4.25\nHeading"])).pages[0].text
    assert result == "information and reentry; 4.25\nHeading"


def test_empty_pages_and_document_survive_and_cleaning_is_idempotent() -> None:
    assert clean(document([])).pages == []
    doc = document([" \n\n", "\t A   line \n\n\n Next line\n"])
    result = clean(doc)
    assert [p.text for p in result.pages] == ["", "A line\n\nNext line"]
    assert asdict(clean(result)) == asdict(result)


def test_alternating_folio_positions_and_roman_folios() -> None:
    labels = ["I Student Handbook 2026", "Student Handbook 2026 II",
              "3 Student Handbook 2026", "Student Handbook 2026 4"]
    doc = document([f"{body(i)}\n{label}" for i, label in enumerate(labels)])
    assert all(p.text.endswith("Last body line.") for p in clean(doc).pages)


def test_short_pages_and_imperative_running_label_are_protected() -> None:
    doc = document(["Student Handbook 2026\nOnly one body line." for _ in range(4)])
    assert asdict(clean(doc)) == asdict(doc)
    doc = document([f"Students must read Student Handbook 2026\n{body(i)}" for i in range(4)])
    assert asdict(clean(doc)) == asdict(doc)


def test_margin_label_is_not_removed_from_interior_of_page() -> None:
    doc = document([f"Student Handbook 2026\n{body(i)}\nStudent Handbook 2026\nBody end."
                    for i in range(4)])
    assert all(p.text.count("Student Handbook 2026") == 1 for p in clean(doc).pages)
