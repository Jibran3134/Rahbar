"""Unit tests for OpenAI-compatible HostedProvider."""
from __future__ import annotations

import json
import httpx
import pytest

from app.config import Settings
from app.providers.llm.base import ProviderError, ProviderFailureKind
from app.providers.llm.hosted import HostedProvider
from app.schemas import Answer, Passage


def sample_passage() -> Passage:
    return Passage(
        chunk_id="chk1",
        text="Minimum CGPA required to avoid academic warning is 2.00.",
        source="handbook.pdf",
        section="5.4",
        page=24,
        score=0.85,
    )


def sample_payload() -> dict:
    return {
        "reasoning": "The rule states 2.00 minimum.",
        "answer": "Minimum CGPA is 2.00 [handbook.pdf / 5.4].",
        "citations": [{"source": "handbook.pdf", "section": "5.4", "page": 24}],
        "answered_from_context": True,
        "confidence": "high",
    }


def test_hosted_provider_requires_base_url_and_api_key() -> None:
    settings = Settings(hosted_base_url="", llm_api_key="")
    with pytest.raises(ValueError, match="HOSTED_BASE_URL"):
        HostedProvider(settings)

    settings_with_url = Settings(hosted_base_url="https://api.groq.com/openai/v1", llm_api_key="")
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        HostedProvider(settings_with_url)


def test_hosted_provider_sends_correct_wire_format() -> None:
    seen_requests = []

    def mock_transport(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        response_body = {
            "choices": [
                {
                    "message": {"role": "assistant", "content": json.dumps(sample_payload())},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 120, "completion_tokens": 45},
        }
        return httpx.Response(200, json=response_body)

    settings = Settings(
        llm_provider="hosted",
        hosted_base_url="https://api.groq.com/openai/v1",
        llm_api_key="test-api-key",
        llm_model="openai/gpt-oss-120b",
        temperature=0.2,
    )

    with httpx.Client(transport=httpx.MockTransport(mock_transport)) as client:
        provider = HostedProvider(settings, client=client)
        ans = provider.generate("What is the minimum CGPA?", [sample_passage()])

    assert isinstance(ans, Answer)
    assert ans.answered_from_context is True
    assert ans.confidence == "high"

    req = seen_requests[0]
    assert req.url == "https://api.groq.com/openai/v1/chat/completions"
    assert req.headers["Authorization"] == "Bearer test-api-key"
    assert req.headers["Content-Type"] == "application/json"

    body = json.loads(req.content)
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["temperature"] == 0.2
    assert body["response_format"] == {"type": "json_object"}
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"


def test_hosted_provider_handles_timeout() -> None:
    def timeout_transport(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Connection timed out")

    settings = Settings(
        hosted_base_url="https://api.groq.com/openai/v1",
        llm_api_key="test-api-key",
    )

    with httpx.Client(transport=httpx.MockTransport(timeout_transport)) as client:
        provider = HostedProvider(settings, client=client)
        with pytest.raises(ProviderError) as exc_info:
            provider.generate("Test", [sample_passage()])
        assert exc_info.value.kind == ProviderFailureKind.TIMEOUT


def test_hosted_provider_handles_http_errors() -> None:
    def error_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "Internal server error"}})

    settings = Settings(
        hosted_base_url="https://api.groq.com/openai/v1",
        llm_api_key="test-api-key",
    )

    with httpx.Client(transport=httpx.MockTransport(error_transport)) as client:
        provider = HostedProvider(settings, client=client)
        with pytest.raises(ProviderError) as exc_info:
            provider.generate("Test", [sample_passage()])
        assert exc_info.value.kind == ProviderFailureKind.TRANSPORT


def test_get_provider_instantiates_hosted() -> None:
    from app.providers.llm import get_provider

    settings = Settings(
        llm_provider="hosted",
        hosted_base_url="https://api.groq.com/openai/v1",
        llm_api_key="test-api-key",
    )
    prov = get_provider(settings)
    assert prov.name == "hosted"
