"""Chunk behavior and source-preservation contracts, independent of services."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, replace

import pytest

from pipeline import chunk as chunking
from pipeline.models import Document, Page


def document(*texts: str) -> Document:
    return Document("policy.pdf", "2026-06", False,
                    [Page("policy.pdf", i, text) for i, text in enumerate(texts, 1)])


@pytest.mark.parametrize("size,overlap", [(0, 0), (-1, 0), (5, -1), (5, 5),
                                          (5, 6), (True, 0), (5, False), (2.5, 0)])
def test_invalid_settings_fail_even_for_empty_document(size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunking.chunk(document(), size, overlap)


def test_empty_pages_do_not_emit_empty_chunks() -> None:
    assert chunking.chunk(document("", " \n\t"), 20, 2) == []


def test_numerical_clauses_and_page_version_identity() -> None:
    doc = document("4.25 Withdrawal\nDeadline is makeup week.\n4.26 Financial support\nOther rule.")
    before = asdict(doc)
    chunks = chunking.chunk(doc, 100, 5)
    assert [c.section for c in chunks] == ["4.25", "4.26"]
    assert "Other rule" not in chunks[0].text
    assert "makeup" not in chunks[1].text
    assert all(c.metadata() == {"source": "policy.pdf", "section": c.section, "page": 1,
                               "doc_version": "2026-06", "superseded": False} for c in chunks)
    assert asdict(doc) == before


def test_markdown_text_headings_and_roman_numeric_hierarchy() -> None:
    doc = document("# Fee Structure\n\n## Security Deposit\n\nRs. 20,000.\n"
                   "## Tuition Fee (w.e.f. Fall 2026 semester)\n\nRs. 12,000.")
    assert [c.section for c in chunking.chunk(doc, 100, 5)] == [
        "Fee Structure", "Security Deposit", "Tuition Fee (w.e.f. Fall 2026 semester)"]
    doc = document("XII. Policy on AI\n1. Introduction\nPrivacy matters.\n"
                   "2. Objectives\nProtect integrity.\nXIII. Other policy\n1. Scope\nNew policy.")
    assert [c.section for c in chunking.chunk(doc, 100, 5)] == [
        "XII", "XII.1", "XII.2", "XIII", "XIII.1"]


def test_decimal_values_and_table_rows_are_not_clause_headings() -> None:
    doc = document("## Fees\n2.00 minimum CGPA\n20% allowance\n"
                   "| CS-101 | Rs. 12,000 |\n2026-27 academic year")
    chunks = chunking.chunk(doc, 100, 0)
    assert len(chunks) == 1 and chunks[0].section == "Fees"
    assert chunks[0].text == doc.pages[0].text


def test_section_continues_across_empty_pages_but_chunks_never_span_pages() -> None:
    doc = document("5.7 Warning\nBeginning of rule.", "", "Continuation: CGPA 2.00.",
                   "5.8 Repeat\nNew rule.")
    chunks = chunking.chunk(doc, 100, 10)
    assert [(c.section, c.page) for c in chunks] == [("5.7", 1), ("5.7", 3), ("5.8", 4)]
    assert "Beginning" not in chunks[1].text
    assert "Continuation" not in chunks[0].text


def test_paragraph_boundary_preferred_when_paragraph_will_not_fit() -> None:
    first = "Alpha beta gamma delta epsilon."
    second = "Zeta eta theta iota kappa lambda mu."
    doc = document(first + "\n\n" + second)
    size = max(chunking.count_tokens(first), chunking.count_tokens(second))
    chunks = chunking.chunk(doc, size, 0)
    assert [c.text for c in chunks] == [first, second]


def test_sentence_boundary_preferred_in_oversized_paragraph() -> None:
    sentences = ["Alpha beta gamma delta.", "Epsilon zeta eta theta.", "Iota kappa lambda mu."]
    chunks = chunking.chunk(document(" ".join(sentences)), 12, 0)
    assert [c.text for c in chunks] == sentences


@pytest.mark.parametrize("size,overlap", [(1, 0), (2, 1), (20, 0), (20, 5), (20, 19)])
def test_bounded_fallback_and_exact_overlap_without_lost_text(size: int, overlap: int) -> None:
    # No punctuation/whitespace boundaries: pathological input still advances.
    text = "x" * 401
    chunks = chunking.chunk(document(text), size, overlap)
    assert chunks and len(chunks) <= chunking.count_tokens(text)
    assert all(0 < chunking.count_tokens(c.text) <= size for c in chunks)
    recovered = chunks[0].text
    for previous, current in zip(chunks, chunks[1:]):
        shared_chars = overlap * 4
        if shared_chars:
            assert previous.text[-shared_chars:] == current.text[:shared_chars]
        recovered += current.text[shared_chars:]
    assert recovered == text


def test_oversized_table_preserves_order_and_values_with_bounded_chunks() -> None:
    row = "| CS-101 | Rs. 12,000 | 20% | " + "longvalue" * 100 + " |"
    chunks = chunking.chunk(document(row), 20, 0)
    assert all(chunking.count_tokens(c.text) <= 20 for c in chunks)
    assert "".join(c.text for c in chunks).replace(" ", "") == row.replace(" ", "")


def test_overlap_never_crosses_sections() -> None:
    chunks = chunking.chunk(document("## Alpha\n" + "alpha " * 50
                                    + "\n## Beta\n" + "beta " * 50), 20, 8)
    assert all("beta" not in c.text.lower() for c in chunks if c.section == "Alpha")
    assert all("alpha" not in c.text.lower() for c in chunks if c.section == "Beta")


def test_stable_distinct_ids_and_identity_changes() -> None:
    doc = document("identical words " * 30, "identical words " * 30)
    chunks = chunking.chunk(doc, 15, 5)
    assert [asdict(c) for c in chunks] == [asdict(c) for c in chunking.chunk(doc, 15, 5)]
    assert len({c.id for c in chunks}) == len(chunks)
    for changed in [replace(doc, doc_version="2023-08"), replace(doc, superseded=True),
                    Document("other.pdf", doc.doc_version, False,
                             [replace(p, source="other.pdf") for p in doc.pages]),
                    document("changed words " * 30)]:
        assert not ({c.id for c in chunks} & {c.id for c in chunking.chunk(changed, 15, 5)})


def test_id_is_independent_of_python_hash_seed() -> None:
    code = ("import json; from pipeline.chunk import chunk; from pipeline.models import Document,Page;"
            "print(json.dumps([c.id for c in chunk(Document('s','v',False,"
            "[Page('s',1,'content '*30)]),12,3)]))")
    results = [subprocess.run([sys.executable, "-c", code], env={**os.environ, "PYTHONHASHSEED": seed},
                              check=True, capture_output=True, text=True).stdout for seed in ("1", "2")]
    assert json.loads(results[0]) == json.loads(results[1])


def test_approximate_counter_bounds_long_words_unicode_and_punctuation() -> None:
    assert chunking.count_tokens("") == chunking.count_tokens(" \n") == 0
    assert chunking.count_tokens("abcd efghi 2.00 20%") == 8
    for text in ["漢" * 101, "!" * 101, "a" * 101]:
        chunks = chunking.chunk(document(text), 5, 1)
        assert len(chunks) > 1 and all(chunking.count_tokens(c.text) <= 5 for c in chunks)


def test_amplification_uses_original_tokens_before_overlap() -> None:
    doc = document("x" * 200)
    chunks = chunking.chunk(doc, 20, 5)
    stats = chunking.chunking_stats(doc, chunks)
    assert stats.original_tokens == 50
    assert stats.stored_tokens == 60 and stats.chunk_count == 3
    assert stats.amplification == 1.2
    no_overlap = chunking.chunk(doc, 20, 0)
    assert chunking.chunking_stats(doc, no_overlap).amplification == 1.0
    assert chunking.chunking_stats(document(), []).amplification == 0.0


def test_markdown_authoritative_section_keeps_full_title_and_numbered_body() -> None:
    doc = document("## 2. Academic warning\n\n2.1 Below 2.00 means a warning.\n\n"
                   "2.2 Three warnings trigger the rule.\n\n## 3. Repeating a course\n"
                   "3.1 Most recent attempt counts.")
    chunks = chunking.chunk(doc, 100, 10)
    assert [c.section for c in chunks] == ["2. Academic warning", "3. Repeating a course"]
    assert "2.1" in chunks[0].text and "2.2" in chunks[0].text


def test_repeated_identical_section_on_same_page_has_distinct_ids() -> None:
    chunks = chunking.chunk(document("## Rule\nSame content.\n## Rule\nSame content."), 100, 0)
    assert len(chunks) == 2 and chunks[0].id != chunks[1].id


def test_normal_word_boundaries_survive_fallback_and_overlap() -> None:
    words = [f"word{i:03d}" for i in range(80)]
    chunks = chunking.chunk(document(" ".join(words)), 20, 5)
    assert all(c.text.split()[0] in words and c.text.split()[-1] in words for c in chunks)
    assert all(chunking.count_tokens(c.text) <= 20 for c in chunks)
    for previous, current in zip(chunks, chunks[1:]):
        shared = [w for w in current.text.split() if w in previous.text.split()]
        assert shared and chunking.count_tokens(" ".join(shared)) <= 5
