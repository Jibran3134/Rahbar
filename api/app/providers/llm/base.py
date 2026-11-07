"""The LLM provider interface (section 3.5). Swapping providers is one file."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from ...schemas import Answer, Passage

MAX_GENERATION_ATTEMPTS = 2  # Initial attempt plus exactly one validation retry.


class ProviderFailureKind(str, Enum):
    TIMEOUT = "timeout"
    TRANSPORT = "transport"
    INVALID_JSON = "invalid_json"
    INVALID_SCHEMA = "invalid_schema"
    INVALID_CITATION = "invalid_citation"
    INCONSISTENT_ANSWER = "inconsistent_answer"


class ProviderError(RuntimeError):
    """Safe typed failure; raw provider responses/credentials are never arguments."""

    def __init__(self, kind: ProviderFailureKind) -> None:
        if not isinstance(kind, ProviderFailureKind):
            raise ValueError("Unknown provider failure category")
        self.kind = kind
        super().__init__(f"LLM provider failed: {kind.value}")


class LLMProvider(Protocol):
    name: str

    def generate(self, question: str, passages: list[Passage], *, feedback: str | None = None) -> Answer:
        """Answer the question from the passages, as an `Answer`."""
        ...
