"""Stage 2: Clean. Remove artefacts without destroying structure."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import replace
from pathlib import Path

from .models import Document

_CHARACTER_REPLACEMENTS: dict[str, str | int | None] = {
    "\u00ad": "", "\u200b": "", "\ufeff": "", "\u00a0": " ",
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl",
}
_TEXT_TRANSLATION = str.maketrans(_CHARACTER_REPLACEMENTS)


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # A discretionary soft hyphen is explicit wrap information. Hard hyphens
    # are ambiguous (FAST-NUCES, non-credit) and are never guessed away.
    text = re.sub(r"(?<=[^\W\d_])\u00ad\n[ \t]*(?=[^\W\d_])", "", text)
    text = text.translate(_TEXT_TRANSLATION)
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    text = "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _margin_key(line: str) -> str | None:
    # Deliberately limited running-label vocabulary. Repetition alone cannot
    # establish that a policy sentence, section heading or table row is noise.
    if len(line) > 140 or re.search(r"[|#.;:%]", line):
        return None
    folio = r"(?:\d{1,3}|[IVXLCDM]+)"
    label = re.sub(rf"^{folio}\s+|\s+{folio}$", "", line).strip()
    if re.match(r"\d|[-*]", label):
        return None
    if not re.search(r"handbook|rules and regulations|university of|^page \d+$", label, re.I):
        return None
    if re.search(r"\b(must|shall|should|required|may|not)\b", label, re.I):
        return None
    # Preserve numeric policy values; only a publication year is allowed.
    if re.search(r"\d", re.sub(r"\b(?:19|20)\d{2}\b", "", label)):
        return None
    return label.casefold()


def clean(doc: Document) -> Document:
    """Return a new document; infer only recurring PDF edge labels/folios.

    Page position here means first/last extracted nonblank line, not measured
    geometric coordinates (Page stores text only). Short pages are excluded.
    """
    pages = [replace(page, text=_normalize(page.text)) for page in doc.pages]
    if Path(doc.source).suffix.lower() != ".pdf":
        return replace(doc, pages=pages)
    lines = [page.text.split("\n") if page.text else [] for page in pages]
    eligible = [i for i, rows in enumerate(lines) if len([r for r in rows if r]) >= 8]
    required = max(3, math.ceil(len(eligible) * 0.6))
    removals: set[tuple[int, int]] = set()
    for edge in (0, -1):
        counts = Counter(_margin_key(lines[i][edge]) for i in eligible)
        for i in eligible:
            key = _margin_key(lines[i][edge])
            if key is not None and counts[key] >= required:
                removals.add((i, edge))
    # A lone number must form a consistent printed-page offset across pages;
    # repeated thresholds or arbitrary footer values are not folio evidence.
    offsets = Counter(pages[i].page - int(lines[i][-1]) for i in eligible
                      if re.fullmatch(r"\d{1,3}", lines[i][-1]))
    for i in eligible:
        if re.fullmatch(r"\d{1,3}", lines[i][-1]):
            if offsets[pages[i].page - int(lines[i][-1])] >= required:
                removals.add((i, -1))
    for i, page in enumerate(pages):
        page.text = "\n".join(row for j, row in enumerate(lines[i])
                              if (i, j) not in removals
                              and not (j == len(lines[i]) - 1 and (i, -1) in removals)).strip()
    return replace(doc, pages=pages)
