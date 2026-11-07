"""Both transports preserve the same citation rendering and provenance guards."""

import json

import httpx
import pytest

from app.config import Settings
from app.providers.llm.hosted import HostedProvider
from app.providers.llm.ollama import OllamaProvider
from app.schemas import Answer, Citation, Passage


@pytest.mark.parametrize("provider_type", [OllamaProvider, HostedProvider])
@pytest.mark.parametrize(
    "text,citation,expected",
    [
        (
            "Fee is Rs. 2.00. Permission is required.",
            ("p.pdf", "4", 1),
            "Fee is Rs. 2.00. [p.pdf / 4] Permission is required. [p.pdf / 4]",
        ),
        (
            "[p.pdf / 4] Permission is required.",
            ("p.pdf", "4", 1),
            "Permission is required. [p.pdf / 4]",
        ),
        (
            "Permission is required [p.pdf / 4].",
            ("p.pdf", "4", 1),
            "Permission is required [p.pdf / 4].",
        ),
        ("Permission is required.", ("invented.pdf", "4", 1), "Permission is required."),
        ("Permission is required.", ("p.pdf", "4", 99), "Permission is required."),
        ("Permission is required [1].", ("p.pdf", "4", 1), "Permission is required [1]."),
    ],
)
def test_rendering_preserves_existing_labels_and_never_invents_provenance(
    provider_type, text, citation, expected
):
    passage = Passage(chunk_id="a", source="p.pdf", section="4", page=1, text="Policy.", score=0.9)
    source, section, page = citation
    payload = Answer(
        reasoning="Synthetic test",
        answer=text,
        citations=[Citation(source=source, section=section, page=page)],
        answered_from_context=True,
        confidence="high",
    ).model_dump_json()

    def respond(request):
        envelope = (
            {"message": {"content": payload}}
            if provider_type is OllamaProvider
            else {"choices": [{"message": {"content": payload}}]}
        )
        return httpx.Response(200, json=envelope)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = provider_type(
            Settings(hosted_base_url="https://example.test/v1", llm_api_key="test"), client=client
        ).generate("Question", [passage])
    assert result.answer == expected
    assert result.citations[0].model_dump() == json.loads(payload)["citations"][0]
