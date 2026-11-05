"""Stage 1: source text and page-local OCR, before cleaning/chunking."""

from __future__ import annotations

import os
import re
from html.parser import HTMLParser
from pathlib import Path

import pdfplumber
import pytesseract
from PIL import Image

from .models import Document, Page

OCR_DPI = 300
OCR_TIMEOUT_SECONDS = 60
MAX_RENDER_PIXELS = 16_000_000


class ExtractionError(RuntimeError):
    """A document must not be published after an unnoticed extraction failure."""


class _HTMLText(HTMLParser):
    """Preserve source headings and row boundaries; never follow or execute HTML."""

    SKIP = {"head", "header", "nav", "footer", "aside", "script", "style", "noscript", "template"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
            "param", "source", "track", "wbr"}
    BLOCK = {"p", "div", "section", "article", "ul", "ol", "li", "table", "dl", "dt", "dd"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skipped: list[str] = []
        self.row: list[str] = []
        self.cell: list[str] | None = None
        self.lists: list[int | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        hidden = ("hidden" in attributes or attributes.get("aria-hidden") == "true"
                  or "display:none" in (attributes.get("style") or "").replace(" ", "").lower())
        if self.skipped or tag in self.SKIP or hidden:
            if tag not in self.VOID:
                self.skipped.append(tag)
            return
        if self.cell is not None and tag not in {"td", "th", "tr", "table"}:
            if tag in self.BLOCK or tag == "br":
                self.cell.append(" ")
            return
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.cell = []
            # Do not invent duplicated cells when the original has merged columns.
            for span in ("rowspan", "colspan"):
                if attributes.get(span) not in {None, "1"}:
                    self.cell.append(f"[{span}={attributes[span]}] ")
        elif re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "br":
            self.parts.append("\n")
        elif tag in self.BLOCK:
            self.parts.append("\n\n")
            if tag in {"ol", "ul"}:
                self.lists.append(0 if tag == "ol" else None)
            elif tag == "li":
                number = self.lists[-1] if self.lists else None
                if number is None:
                    self.parts.append("- ")
                else:
                    self.lists[-1] = number + 1
                    self.parts.append(f"{number + 1}. ")

    def handle_endtag(self, tag: str) -> None:
        if self.skipped:
            if tag in self.skipped:
                position = len(self.skipped) - 1 - self.skipped[::-1].index(tag)
                del self.skipped[position:]
            return
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()).replace("|", r"\|"))
            self.cell = None
        elif tag == "tr" and self.row:
            self.parts.append("\n| " + " | ".join(self.row) + " |\n")
            self.row = []
        elif self.cell is None and (tag in self.BLOCK or re.fullmatch(r"h[1-6]", tag)):
            self.parts.append("\n\n")
            if tag in {"ul", "ol"} and self.lists:
                self.lists.pop()

    def handle_data(self, data: str) -> None:
        if not self.skipped:
            if self.cell is not None:
                self.cell.append(data)
            else:
                self.parts.append(re.sub(r"\s+", " ", data))

    def text(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n|\n[ \t]+", "\n", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()


def _usable_text(text: str) -> bool:
    # Cover hyperlinks/page numbers alone must not disguise a scanned policy page.
    without_urls = re.sub(r"https?://\S+", "", text)
    return sum(character.isalpha() for character in without_urls) >= 20


def _blank_image(image: Image.Image) -> bool:
    gray = image.convert("L")
    try:
        gray.thumbnail((256, 256))
        minimum = gray.getextrema()[0]
        return isinstance(minimum, (int, float)) and minimum >= 250
    finally:
        gray.close()


def _ocr_image(image: Image.Image) -> str:
    """Run bounded native OCR; optional per-process Windows executable override."""
    original = pytesseract.pytesseract.tesseract_cmd
    try:
        if command := os.environ.get("TESSERACT_CMD"):
            pytesseract.pytesseract.tesseract_cmd = command
        return str(pytesseract.image_to_string(
            image, lang="eng", config="--psm 6", timeout=OCR_TIMEOUT_SECONDS,
        ))
    finally:
        pytesseract.pytesseract.tesseract_cmd = original


def _pdf_pages(path: Path) -> list[Page]:
    pages: list[Page] = []
    number = 0
    try:
        with pdfplumber.open(path) as pdf:
            for number, source_page in enumerate(pdf.pages, 1):
                try:
                    # Some book PDFs retain the previous leaf at negative x positions.
                    # Only glyphs in the displayed page may become evidence for this page.
                    visible_page = source_page.crop(source_page.cropbox or source_page.bbox)
                    try:
                        text = visible_page.extract_text() or ""
                    finally:
                        visible_page.close()
                    used_ocr = False
                    if not _usable_text(text):
                        pixels = source_page.width * source_page.height * (OCR_DPI / 72) ** 2
                        if pixels > MAX_RENDER_PIXELS:
                            raise ExtractionError(f"{path.name}, page {number}: OCR render too large")
                        image = source_page.to_image(resolution=OCR_DPI).original
                        try:
                            if _blank_image(image):
                                text = ""
                            else:
                                try:
                                    text = _ocr_image(image).strip()
                                except Exception as exc:
                                    raise ExtractionError(
                                        f"{path.name}, page {number}: OCR failed ({type(exc).__name__}); "
                                        "check Tesseract/PATH or TESSERACT_CMD"
                                    ) from exc
                                if not text:
                                    raise ExtractionError(
                                        f"{path.name}, page {number}: OCR returned no text on a nonblank page"
                                    )
                                used_ocr = True
                        finally:
                            # Pillow's context exit alone does not release an in-memory bitmap.
                            image.close()
                    pages.append(Page(source=path.name, page=number, text=text, ocr=used_ocr))
                finally:
                    # Release character/layout caches and bitmap before the next page.
                    source_page.close()
    except ExtractionError:
        raise
    except Exception as exc:
        location = f", page {number}" if number else ""
        raise ExtractionError(
            f"{path.name}{location}: PDF extraction failed ({type(exc).__name__})"
        ) from exc
    return pages


def _markdown(text: str, source: str) -> str:
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                return "".join(lines[index + 1:])
        raise ExtractionError(f"{source}: unterminated front matter")
    return text


def extract(path: str, doc_version: str, superseded: bool) -> Document:
    """Return PDF physical pages or one logical text/Markdown/HTML page.

    HTML's logical page 1 is not a physical citation page: query code must expose
    page=None for HTML. Metadata versions come from discovery, not document text.
    No cleaning, chunking, embedding, network fetching or storage runs here.
    """
    source = Path(path)
    try:
        extension = source.suffix.lower()
        if not source.is_file():
            raise ExtractionError(f"{source.name}: source file not found")
        if extension == ".pdf":
            pages = _pdf_pages(source)
        elif extension in {".md", ".txt", ".html", ".htm"}:
            text = source.read_text(encoding="utf-8-sig")
            if extension == ".md":
                text = _markdown(text, source.name)
            elif extension in {".html", ".htm"}:
                parser = _HTMLText()
                parser.feed(text)
                parser.close()
                text = parser.text()
            pages = [Page(source=source.name, page=1, text=text)]
        else:
            raise ExtractionError(f"{source.name}: unsupported document extension {extension}")
        if not pages or not any(page.text.strip() for page in pages):
            raise ExtractionError(f"{source.name}: no readable document content")
        return Document(source=source.name, doc_version=doc_version,
                        superseded=superseded, pages=pages)
    except ExtractionError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise ExtractionError(f"{source.name}: text extraction failed ({type(exc).__name__})") from exc
