"""S02 public compatibility and internal publication/failure contracts."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app import schemas
from app.config import get_settings


def test_request_without_session_remains_compatible() -> None:
    request = schemas.AskRequest(question="What is the attendance rule?")
    assert request.session_id is None


def test_session_id_is_retained() -> None:
    request = schemas.AskRequest(question="What about the lab?", session_id="session-123_ABC")
    assert request.session_id == "session-123_ABC"


@pytest.mark.parametrize("session_id", ["", " ", "x" * 129, "../other", "a b", "id\n", 123])
def test_invalid_session_ids_rejected(session_id: object) -> None:
    with pytest.raises(ValidationError):
        schemas.AskRequest.model_validate({"question": "A valid question", "session_id": session_id})


def test_response_session_is_optional_and_reasoning_absent() -> None:
    response = schemas.AskResponse(
        request_id="r1", answer="Not covered", citations=[], answered_from_context=False,
        confidence="low", retrieved=[], provider="stub",
    )
    assert response.session_id is None
    assert "reasoning" not in response.model_dump()


def test_http_contract_remains_compatible_and_rejects_bad_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("RETRIEVER", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    with TestClient(app) as client:
        old_response = client.post("/api/ask", json={"question": "What is the attendance rule?"})
        assert old_response.status_code == 200
        body = old_response.json()
        assert body["provider"] == "stub" and "reasoning" not in body
        assert body["session_id"] is None  # Session persistence is implemented in S12.
        bad_response = client.post("/api/ask", json={"question": "What about labs?",
                                                   "session_id": "../invalid"})
        assert bad_response.status_code == 422


def test_active_index_validates_metadata_and_is_immutable() -> None:
    assert hasattr(schemas, "ActiveIndex"), "S02 requires the ActiveIndex contract"
    identity = schemas.ActiveIndex(
        collection="rahbar-g1", generation="g1", embed_model="nomic-embed-text", dimension=768,
    )
    assert identity.dimension == 768
    with pytest.raises(ValidationError):
        identity.generation = "g2"


@pytest.mark.parametrize("changes", [
    {"collection": ""}, {"generation": " "}, {"embed_model": ""},
    {"dimension": 0}, {"dimension": -1}, {"dimension": True}, {"dimension": "768"},
    {"unexpected": "must-not-be-ignored"},
])
def test_active_index_rejects_invalid_identity(changes: dict) -> None:
    assert hasattr(schemas, "ActiveIndex"), "S02 requires the ActiveIndex contract"
    data = {"collection": "rahbar-g1", "generation": "g1",
            "embed_model": "nomic-embed-text", "dimension": 768}
    with pytest.raises(ValidationError):
        schemas.ActiveIndex.model_validate({**data, **changes})


def test_api_and_indexer_share_model_and_publication_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "indexer"))
    index_config = importlib.import_module("pipeline.config")
    index_models = importlib.import_module("pipeline.models")
    for key, value in {
        "EMBED_MODEL": "same-embedding:v1", "OLLAMA_URL": "http://127.0.0.1:11435",
        "CHROMA_HOST": "127.0.0.1", "CHROMA_PORT": "8001", "CHROMA_COLLECTION": "shared-index",
    }.items():
        monkeypatch.setenv(key, value)
    api_settings, index_settings = get_settings(), index_config.get_settings()
    for field in ("embed_model", "ollama_url", "chroma_host", "chroma_port", "collection"):
        assert getattr(api_settings, field) == getattr(index_settings, field)
    assert hasattr(index_models, "ActiveIndex"), "Indexer must publish the agreed identity shape"
    published = index_models.ActiveIndex(
        collection="shared-index-g1", generation="g1", embed_model="same-embedding:v1", dimension=768,
    ).metadata()
    assert schemas.ActiveIndex.model_validate(published).model_dump() == published


def test_provider_failures_are_typed_and_attempt_budget_is_fixed() -> None:
    from app.providers.llm import base

    assert hasattr(base, "ProviderFailureKind"), "S02 requires explicit failure categories"
    assert base.MAX_GENERATION_ATTEMPTS == 2
    expected = {"timeout", "transport", "invalid_json", "invalid_schema", "invalid_citation"}
    assert {kind.value for kind in base.ProviderFailureKind} == expected
    for kind in base.ProviderFailureKind:
        failure = base.ProviderError(kind)
        assert isinstance(failure, RuntimeError)
        assert failure.kind is kind
        assert kind.value in str(failure)
