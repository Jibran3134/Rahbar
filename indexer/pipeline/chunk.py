"""Stage 3: Chunk. Structure-aware, with overlap."""

from __future__ import annotations

import hashlib
import json
import re
from bisect import bisect_right
from dataclasses import dataclass

from .models import Chunk, Document

TOKEN_COUNTER = "unicode-word-4-and-punctuation-v1"
_TOKENS = re.compile(r"\w{1,4}|[^\w\s]", re.UNICODE)
_NUMBER = r"(?:0|[1-9]\d*)"
_CLAUSE = re.compile(rf"^({_NUMBER}(?:\.{_NUMBER})+)\.?\s+\S")
_INTEGER_HEADING = re.compile(r"^([1-9]\d*)\.\s+\S")
_ROMAN_HEADING = re.compile(r"^([IVXLCDM]+)\.\s+\S")
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+?)(?:\s+#+)?$")
_MARKDOWN_PREFIX = re.compile(r"^#{1,6}\s+")
_PARAGRAPH_BOUNDARY = re.compile(r"\n[ \t]*\n")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])[ \t\n]+(?=[A-Z(])")


def count_tokens(text: str) -> int:
    """Approximate units: up to four Unicode word characters or one punctuation.

    Whitespace is not counted. This is deterministic, bounds unspaced input,
    and is NOT the embedding/generation model's tokenizer or context limit.
    """
    return sum(1 for _ in _TOKENS.finditer(text))


@dataclass(frozen=True)
class ChunkingStats:
    original_tokens: int
    stored_tokens: int
    chunk_count: int

    @property
    def amplification(self) -> float:
        return self.stored_tokens / self.original_tokens if self.original_tokens else 0.0


def chunking_stats(doc: Document, chunks: list[Chunk]) -> ChunkingStats:
    """Count source content once, then all actually stored content with overlap."""
    return ChunkingStats(sum(count_tokens(p.text) for p in doc.pages),
                         sum(count_tokens(c.text) for c in chunks), len(chunks))


def _heading(line: str, roman: str | None) -> tuple[str, str | None] | None:
    markdown = _MARKDOWN_HEADING.match(line)
    if markdown:
        # Explicit authored headings are authoritative, including their number
        # and title (the existing CI fixture truth uses this convention).
        return markdown.group(1), None
    title = line
    if match := _ROMAN_HEADING.match(title):
        return match.group(1), match.group(1)
    if match := _CLAUSE.match(title):
        label = match.group(1)
        return (f"{roman}.{label}" if roman else label), roman
    if match := _INTEGER_HEADING.match(title):
        label = match.group(1)
        return (f"{roman}.{label}" if roman else label), roman
    return None


def _plain_heading(line: str, following: str) -> bool:
    # Only infer a short title directly above an explicit numbered clause.
    # Arbitrary wrapped prose is not treated as a heading by capitalization.
    if not _CLAUSE.match(following) or not 1 < len(line.split()) <= 12:
        return False
    if len(line) > 100 or re.search(r"[|.!?;:%]", line):
        return False
    return all(word in {"of", "and", "the", "under", "for", "a", "in", "to"}
               or word[0].isupper() for word in line.split())


def _boundaries(text: str, token_ends: list[int]) -> tuple[list[int], list[int]]:
    """Map paragraph/sentence ends to token offsets without rebuilding text."""
    paragraphs = [bisect_right(token_ends, m.start())
                  for m in _PARAGRAPH_BOUNDARY.finditer(text)]
    # Decimal points and ordinary lower-case abbreviations aren't boundaries.
    sentences = [bisect_right(token_ends, m.start())
                 for m in _SENTENCE_BOUNDARY.finditer(text)]
    return paragraphs, sentences


def chunk(doc: Document, size: int, overlap: int) -> list[Chunk]:
    """Split within page/section: paragraphs, sentences, words, bounded units.

    Section state carries across pages, but chunks/overlap never cross a page.
    Overlap is at most the requested units, aligned to word starts when possible.
    HTML retains logical page 1 here; query citations must expose page=null.
    """
    if type(size) is not int or size <= 0:
        raise ValueError("size must be a positive integer")
    if type(overlap) is not int or not 0 <= overlap < size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")
    chunks: list[Chunk] = []
    section = "preamble"
    roman: str | None = None
    markdown_scope = False
    for page in doc.pages:
        groups: list[tuple[str, str]] = []
        pending: list[str] = []
        lines = page.text.splitlines(keepends=True)
        for index, line in enumerate(lines):
            stripped = line.strip()
            is_markdown = bool(_MARKDOWN_PREFIX.match(stripped))
            heading = _heading(stripped, roman) if is_markdown or not markdown_scope else None
            following = lines[index + 1].strip() if index + 1 < len(lines) else ""
            if heading or (not markdown_scope and _plain_heading(stripped, following)):
                if pending:
                    groups.append((section, "".join(pending)))
                    pending = []
                if heading:
                    section, roman = heading
                    markdown_scope = is_markdown
                else:
                    section = stripped
            pending.append(line)
        if pending:
            groups.append((section, "".join(pending)))
        for group_index, (label, text) in enumerate(groups):
            tokens = list(_TOKENS.finditer(text))
            if not tokens:
                continue
            paragraphs, sentences = _boundaries(text, [t.end() for t in tokens])
            word_boundaries = [i for i, token in enumerate(tokens)
                               if token.start() > 0 and text[token.start() - 1].isspace()]
            start = 0
            while start < len(tokens):
                limit = min(start + size, len(tokens))
                end = limit
                if limit < len(tokens):
                    for boundaries in (paragraphs, sentences, word_boundaries):
                        boundary_index = bisect_right(boundaries, limit) - 1
                        if boundary_index >= 0 and boundaries[boundary_index] > start + overlap:
                            end = boundaries[boundary_index]
                            break
                content = text[tokens[start].start():tokens[end - 1].end()]
                identity = ["chunk-v1", doc.source, doc.doc_version, doc.superseded,
                            page.page, label, group_index, start, end, content]
                digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False,
                                                   separators=(",", ":")).encode()).hexdigest()
                chunks.append(Chunk(digest, content, doc.source, label, page.page,
                                    doc.doc_version, doc.superseded))
                if end == len(tokens):
                    break
                # Boundary eligibility guarantees strict progress, even for
                # overlap=size-1 or a sentence/table row with no whitespace.
                start = end - overlap
                if overlap:
                    next_word = bisect_right(word_boundaries, start - 1)
                    if next_word < len(word_boundaries) and word_boundaries[next_word] <= end:
                        start = word_boundaries[next_word]
    return chunks
