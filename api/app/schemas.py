"""The contracts. Change them only with your partner's review: the UI, the
evaluation script and your tests all depend on these shapes.

`Answer` is what the model must produce (section 3.4). `AskResponse` is what
the API returns to the UI and to eval/run_eval.py. The model's `reasoning` is
never sent to the user.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SessionId = Annotated[str, Field(strict=True, min_length=1, max_length=128,
                                 pattern=r"^[A-Za-z0-9_-]+$")]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    session_id: SessionId | None = None


class ActiveIndex(BaseModel):
    """Internal publication identity, frozen for the lifetime of one request.

    Separate API/indexer images share this wire shape, not Python package imports.
    This type validates metadata only; it does not resolve/publish an index.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    collection: str = Field(strict=True, min_length=1)
    generation: str = Field(strict=True, min_length=1)
    embed_model: str = Field(strict=True, min_length=1)
    dimension: int = Field(strict=True, gt=0)

    @field_validator("collection", "generation", "embed_model")
    @classmethod
    def no_whitespace(cls, value: str) -> str:
        if any(char.isspace() for char in value):
            raise ValueError("Index identity fields must not contain whitespace")
        return value


class Passage(BaseModel):
    """One retrieved chunk, as the retriever hands it to the generator."""

    chunk_id: str
    text: str
    source: str
    section: str
    page: int | None = None
    score: float = Field(description="Similarity, higher is closer (1 - cosine distance).")


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    section: str
    page: int | None = None


class Answer(BaseModel):
    """The model's output contract. Send its JSON schema to the model, then validate."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str
    answer: str
    citations: list[Citation]
    answered_from_context: bool
    confidence: Literal["high", "medium", "low"]


class RetrievedRef(BaseModel):
    """What the response says was retrieved. eval/run_eval.py scores against this."""

    chunk_id: str
    source: str
    section: str
    page: int | None = None
    score: float


class AskResponse(BaseModel):
    request_id: str
    answer: str
    citations: list[Citation]
    answered_from_context: bool
    confidence: Literal["high", "medium", "low"]
    retrieved: list[RetrievedRef]
    provider: str
    session_id: SessionId | None = None
