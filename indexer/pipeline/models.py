"""The shapes passed between stages. Metadata fields are required (section 3.1)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActiveIndex:
    """Wire identity the indexer will publish after validating a complete build.

    Matches app.schemas.ActiveIndex; keeps independent container build contexts.
    Publication/storage logic is implemented in S07, not in this data contract.
    """

    collection: str
    generation: str
    embed_model: str
    dimension: int

    def __post_init__(self) -> None:
        for name in ("collection", "generation", "embed_model"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or any(c.isspace() for c in value):
                raise ValueError(f"{name} must be a nonempty identity without whitespace")
        if type(self.dimension) is not int or self.dimension <= 0:
            raise ValueError("dimension must be a positive integer")

    def metadata(self) -> dict[str, str | int]:
        return {"collection": self.collection, "generation": self.generation,
                "embed_model": self.embed_model, "dimension": self.dimension}


@dataclass
class Page:
    """Text of one page, as extraction produced it."""

    source: str              # file name, e.g. Academic_Rules_Handbook_2026.pdf
    page: int                # 1-based
    text: str
    ocr: bool = False        # True when this page had no text layer and was OCR'd


@dataclass
class Document:
    source: str
    doc_version: str         # e.g. "2026-06"; from corpus/sources.yaml
    superseded: bool         # True for an older version of a policy
    pages: list[Page] = field(default_factory=list)


@dataclass
class Chunk:
    id: str                  # stable: same document + same position gives the same id
    text: str
    source: str
    section: str             # the heading this chunk sits under, e.g. "5.4 Academic Warning"
    page: int
    doc_version: str
    superseded: bool

    def metadata(self) -> dict[str, str | int | bool]:
        """Chroma metadata values must be str, int, float or bool."""
        return {
            "source": self.source,
            "section": self.section,
            "page": self.page,
            "doc_version": self.doc_version,
            "superseded": self.superseded,
        }
