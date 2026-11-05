"""S03 behavior tests use owned PDFs/HTML and OCR doubles, never a live model."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

extraction = importlib.import_module("pipeline.extract")


def write_text_pdf(path: Path, texts: list[str]) -> None:
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=612, height=792)
        if text:
            font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                     NameObject("/Subtype"): NameObject("/Type1"),
                                     NameObject("/BaseFont"): NameObject("/Helvetica")})
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 40 700 Td ({text}) Tj ET".encode("ascii"))
            page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as handle:
        writer.write(handle)


def write_scanned_pdf(path: Path) -> None:
    with Image.new("RGB", (612, 792), "white") as image:
        ImageDraw.Draw(image).rectangle((50, 100, 450, 200), fill="black")
        image.save(path, "PDF", resolution=72)


@pytest.mark.parametrize("extension", [".md", ".txt", ".TXT"])
def test_text_dispatch_preserves_structure_and_metadata(tmp_path: Path, extension: str) -> None:
    path = tmp_path / ("policy" + extension)
    content = "# 4. Registration\n\n4.2 Prerequisite CS1001 requires CGPA 2.00.\n"
    path.write_text(content, encoding="utf-8")
    doc = extraction.extract(str(path), "2026-06", False)
    assert (doc.source, doc.doc_version, doc.superseded) == (path.name, "2026-06", False)
    assert len(doc.pages) == 1 and doc.pages[0].page == 1
    assert doc.pages[0].text == content and not doc.pages[0].ocr


def test_markdown_front_matter_is_not_content(tmp_path: Path) -> None:
    path = tmp_path / "old.md"
    path.write_text("---\ndoc_version: 2023\nsuperseded: true\n---\n# 4. Rules\nEvidence.",
                    encoding="utf-8-sig")
    doc = extraction.extract(str(path), "2023-08", True)
    assert doc.pages[0].text.startswith("# 4. Rules")
    assert "doc_version:" not in doc.pages[0].text
    assert doc.doc_version == "2023-08" and doc.superseded is True


def test_body_separators_and_colons_are_preserved(tmp_path: Path) -> None:
    path = tmp_path / "policy.md"
    text = "# Fee policy\n\n---\nAmount: Rs 12,000\n"
    path.write_text(text, encoding="utf-8")
    assert extraction.extract(str(path), "2026", False).pages[0].text == text


def test_unterminated_front_matter_fails_with_source(tmp_path: Path) -> None:
    path = tmp_path / "broken.md"
    path.write_text("---\ndoc_version: 2023\nNo closing delimiter", encoding="utf-8")
    with pytest.raises(RuntimeError, match="broken.md.*front matter"):
        extraction.extract(str(path), "2023", True)


def test_html_preserves_headings_rows_and_units_without_boilerplate(tmp_path: Path) -> None:
    path = tmp_path / "fees.html"
    path.write_text('''<html><header>Navigation to unrelated policies</header>
      <main><h2>Tuition Fee</h2><p>Per credit hour, Fall 2026.</p>
      <table><tr><th>Program</th><th>Fee</th></tr>
      <tr><td><b>BBA / BS</b></td><td>Rs. 12,000</td></tr></table>
      <p>Security deposit &amp; refunds are separate.</p>
      <div hidden>Hidden text</div><script>do_not_execute()</script></main>
      <footer>Footer contacts</footer></html>''', encoding="utf-8")
    doc = extraction.extract(str(path), "snapshot-2026", False)
    text = doc.pages[0].text
    assert "## Tuition Fee" in text and "Per credit hour, Fall 2026." in text
    assert "| Program | Fee |" in text and "| BBA / BS | Rs. 12,000 |" in text
    assert "Security deposit & refunds are separate." in text
    assert all(term not in text for term in ["Navigation", "do_not_execute", "Footer", "Hidden"])
    assert doc.pages[0].page == 1 and not doc.pages[0].ocr


def test_nested_html_inside_cells_and_line_breaks_do_not_merge_columns(tmp_path: Path) -> None:
    path = tmp_path / "table.htm"
    path.write_text("<h1>Fees</h1><table><tr><td>BS<br>Program</td>"
                    "<td><span>12,000</span> PKR</td></tr></table>", encoding="utf-8")
    assert "| BS Program | 12,000 PKR |" in extraction.extract(str(path), "v1", False).pages[0].text


def test_pdf_keeps_physical_page_numbers_and_does_not_ocr_text_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "rules.PDF"
    write_text_pdf(path, ["1. Rules - prerequisite courses must be passed.",
                          "2. Fees - twelve thousand rupees per credit hour."])

    def forbidden_ocr(image: object) -> str:
        raise AssertionError("OCR was called for a useful text layer")

    monkeypatch.setattr(extraction, "_ocr_image", forbidden_ocr, raising=False)
    doc = extraction.extract(str(path), "2026", False)
    assert [page.page for page in doc.pages] == [1, 2]
    assert all(page.source == "rules.PDF" and not page.ocr for page in doc.pages)
    assert "prerequisite" in doc.pages[0].text and "rupees" in doc.pages[1].text


def test_scan_is_ocrd_and_flagged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "scan.pdf"
    write_scanned_pdf(path)
    calls = []

    def fake_ocr(image: Image.Image) -> str:
        calls.append(image.size)
        return "4.2 Faculty must serve more than one year."

    monkeypatch.setattr(extraction, "_ocr_image", fake_ocr, raising=False)
    doc = extraction.extract(str(path), "2022-05-30", False)
    assert len(calls) == 1 and doc.pages[0].ocr is True
    assert doc.pages[0].page == 1 and "one year" in doc.pages[0].text


def test_genuine_blank_pdf_page_preserved_without_ocr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "blank-page.pdf"
    write_text_pdf(path, ["1. These are genuine policy rules with text.", ""])

    def forbidden_ocr(image: object) -> str:
        raise AssertionError("Blank page must not need the external OCR executable")

    monkeypatch.setattr(extraction, "_ocr_image", forbidden_ocr, raising=False)
    doc = extraction.extract(str(path), "2026", False)
    assert len(doc.pages) == 2 and doc.pages[1].page == 2
    assert doc.pages[1].text == "" and not doc.pages[1].ocr


@pytest.mark.parametrize("failure", [RuntimeError("timeout"), FileNotFoundError("engine missing")])
def test_ocr_failure_names_document_and_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception,
) -> None:
    path = tmp_path / "broken-scan.pdf"
    write_scanned_pdf(path)

    def failing_ocr(image: object) -> str:
        raise failure

    monkeypatch.setattr(extraction, "_ocr_image", failing_ocr, raising=False)
    with pytest.raises(RuntimeError, match="broken-scan.pdf.*page 1.*OCR"):
        extraction.extract(str(path), "v1", False)


def test_empty_ocr_for_nonblank_page_is_not_silent_loss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "unreadable.pdf"
    write_scanned_pdf(path)
    monkeypatch.setattr(extraction, "_ocr_image", lambda image: "", raising=False)
    with pytest.raises(RuntimeError, match="unreadable.pdf.*page 1.*OCR"):
        extraction.extract(str(path), "v1", False)


@pytest.mark.parametrize(("name", "content"), [
    ("broken.pdf", b"not a PDF"), ("bad.txt", b"\xff\xfe\x00bad"),
    ("unsupported.docx", b"not supported"), ("empty.txt", b""),
])
def test_bad_document_fails_instead_of_returning_partial_success(
    tmp_path: Path, name: str, content: bytes,
) -> None:
    path = tmp_path / name
    path.write_bytes(content)
    with pytest.raises(RuntimeError, match=name):
        extraction.extract(str(path), "v1", False)


def test_missing_source_fails_with_filename(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="missing.pdf"):
        extraction.extract(str(tmp_path / "missing.pdf"), "v1", False)


def test_url_text_layer_cannot_hide_scanned_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan = tmp_path / "image.pdf"
    overlay = tmp_path / "url.pdf"
    mixed = tmp_path / "mixed.pdf"
    write_scanned_pdf(scan)
    write_text_pdf(overlay, ["https://example.invalid/public/university-academic-policy.pdf"])
    writer = PdfWriter()
    page = writer.add_page(PdfReader(scan).pages[0])
    page.merge_page(PdfReader(overlay).pages[0])
    with mixed.open("wb") as handle:
        writer.write(handle)
    monkeypatch.setattr(extraction, "_ocr_image", lambda image: "4.25 Deadline is defined here.")
    result = extraction.extract(str(mixed), "2023", True)
    assert result.pages[0].ocr and "4.25" in result.pages[0].text


def test_ocr_adapter_passes_timeout_layout_and_restores_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pytesseract

    original = pytesseract.pytesseract.tesseract_cmd
    monkeypatch.setenv("TESSERACT_CMD", "C:/unit-test-only/tesseract.exe")
    calls = []

    def fake_native(image: object, **kwargs: object) -> str:
        calls.append((pytesseract.pytesseract.tesseract_cmd, kwargs))
        return "recognized text"

    monkeypatch.setattr(pytesseract, "image_to_string", fake_native)
    with Image.new("RGB", (10, 10), "white") as image:
        assert extraction._ocr_image(image) == "recognized text"
    assert calls == [("C:/unit-test-only/tesseract.exe",
                      {"lang": "eng", "config": "--psm 6", "timeout": 60})]
    assert pytesseract.pytesseract.tesseract_cmd == original


def test_oversized_page_is_rejected_before_rendering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pdfplumber.page import Page as PDFPage

    path = tmp_path / "huge.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=10000, height=10000)
    with path.open("wb") as handle:
        writer.write(handle)

    def forbidden_render(*args: object, **kwargs: object) -> None:
        raise AssertionError("Oversized bitmap should never be allocated")

    monkeypatch.setattr(PDFPage, "to_image", forbidden_render)
    with pytest.raises(RuntimeError, match="huge.pdf.*page 1.*OCR render too large"):
        extraction.extract(str(path), "v1", False)


def test_ocr_failure_closes_bitmap_and_restores_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pytesseract

    path = tmp_path / "timeout.pdf"
    write_scanned_pdf(path)
    original = pytesseract.pytesseract.tesseract_cmd
    captured: list[Image.Image] = []
    monkeypatch.setenv("TESSERACT_CMD", "C:/unit-test-only/tesseract.exe")

    def fake_timeout(image: Image.Image, **kwargs: object) -> str:
        captured.append(image)
        raise RuntimeError("Tesseract process timeout")

    monkeypatch.setattr(pytesseract, "image_to_string", fake_timeout)
    with pytest.raises(RuntimeError, match="timeout.pdf.*page 1.*OCR failed"):
        extraction.extract(str(path), "v1", False)
    assert pytesseract.pytesseract.tesseract_cmd == original
    assert len(captured) == 1
    with pytest.raises(ValueError, match="closed image"):
        captured[0].getpixel((0, 0))


def test_off_page_text_does_not_interleave_with_visible_policy(tmp_path: Path) -> None:
    original = tmp_path / "original.pdf"
    path = tmp_path / "clipped.pdf"
    write_text_pdf(original, ["4.25 The current rule mentions the makeup week."])
    writer = PdfWriter()
    page = writer.add_page(PdfReader(original).pages[0])
    stream = DecodedStreamObject()
    stream.set_data(page.get_contents().get_data() +
                    b"\nBT /F1 12 Tf -350 700 Td (HIDDEN PREVIOUS PAGE RULE) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as handle:
        writer.write(handle)
    text = extraction.extract(str(path), "2026", False).pages[0].text
    assert "HIDDEN" not in text and "4.25" in text and "makeup week" in text
