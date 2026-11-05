"""Bounded retry, typed provider errors and HTTP reasoning isolation."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.providers.llm.base import ProviderError, ProviderFailureKind
from app.schemas import Answer, Citation, Passage
from app.services.answer import answer_question


def evidence():
    return [Passage(chunk_id="a",text="Deadline is makeup week.",source="p.pdf",section="4.25",page=23,score=.9)]


class Provider:
    name = "scripted"
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []
    def generate(self, question, passages, *, feedback=None):
        self.calls.append((question,feedback))
        value = next(self.replies)
        if isinstance(value,Exception):
            raise value
        return value


def good():
    return Answer(reasoning="NEVER EXPOSE THIS",answer="Deadline is makeup week [p.pdf / 4.25].",
        citations=[Citation(source="p.pdf",section="4.25",page=23)],
        answered_from_context=True,confidence="high")


def ask(provider):
    return answer_question("Question",SimpleNamespace(name="fake",retrieve=lambda q,k:evidence()),provider,Settings())


def test_successful_second_attempt_has_feedback_and_unchanged_question(caplog):
    provider = Provider([ProviderError(ProviderFailureKind.INVALID_JSON),good()])
    result = ask(provider)
    assert result.answered_from_context and len(provider.calls) == 2
    assert provider.calls[1][0] == "Question" and "invalid_json" in provider.calls[1][1]
    assert "NEVER EXPOSE THIS" not in result.model_dump_json() + caplog.text


@pytest.mark.parametrize("kind", [ProviderFailureKind.INVALID_JSON,ProviderFailureKind.INVALID_SCHEMA,
                                 ProviderFailureKind.INVALID_CITATION])
def test_exactly_two_validation_attempts_then_uncited_fallback(kind,caplog):
    provider = Provider([ProviderError(kind),ProviderError(kind),good()])
    result = ask(provider)
    assert len(provider.calls) == 2 and not result.answered_from_context
    assert result.citations == [] and result.confidence == "low"
    assert "fallback" in caplog.text


@pytest.mark.parametrize("kind", [ProviderFailureKind.TIMEOUT,ProviderFailureKind.TRANSPORT])
def test_timeout_or_transport_fails_safely_without_another_network_attempt(kind):
    provider = Provider([ProviderError(kind),good()])
    assert not ask(provider).answered_from_context and len(provider.calls) == 1


def test_bad_citation_retries_and_raw_wrong_type_falls_back():
    bad = good()
    bad.citations[0].page = 999
    provider = Provider([bad,good()])
    assert ask(provider).answered_from_context and len(provider.calls) == 2
    provider = Provider([{"answer":"untyped"},{"answer":"untyped"}])
    assert not ask(provider).answered_from_context and len(provider.calls) == 2


def test_malformed_provider_output_never_causes_unhandled_http_500(monkeypatch):
    from app.main import app
    monkeypatch.setenv("RETRIEVER","stub")
    monkeypatch.setenv("LLM_PROVIDER","stub")
    with TestClient(app) as client:
        app.state.provider = Provider([ProviderError(ProviderFailureKind.INVALID_JSON)]*2)
        result = client.post("/api/ask",json={"question":"What is the policy?"})
    assert result.status_code == 200 and not result.json()["answered_from_context"]
    assert result.json()["citations"] == [] and "reasoning" not in result.json()
