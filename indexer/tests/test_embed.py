"""Offline embedding wire/validation contracts."""
import httpx
import pytest

from pipeline import embed as module
from pipeline.config import get_settings


def test_batches_model_prefix_order_and_no_truncation() -> None:
    requests = []
    def respond(request):
        import json
        payload = json.loads(request.content)
        requests.append(payload)
        assert request.url.path == "/api/embed"
        return httpx.Response(200, json={"embeddings": [[float(t[-1]), 1] for t in payload["input"]]})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        vectors = module.embed(["doc1", "doc2", "doc3"], get_settings(), client=client, batch_size=2)
    assert vectors == [[1, 1], [2, 1], [3, 1]]
    assert [len(r["input"]) for r in requests] == [2, 1]
    assert all(r["model"] == "nomic-embed-text" and r["truncate"] is False for r in requests)
    assert requests[0]["input"][0] == "search_document: doc1"


@pytest.mark.parametrize("response", [{}, {"embeddings": []}, {"embeddings": [[1], [2]]},
    {"embeddings": [[]]}, {"embeddings": [[True]]}, {"embeddings": [["1"]]},
    {"embeddings": [[0, 0]]}, {"embeddings": [[float("nan")]]},
    {"embeddings": [[float("inf")]]}])
def test_invalid_vectors_rejected(response) -> None:
    # JSON cannot encode NaN through httpx's strict json= encoder.
    import json
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(
            200, content=json.dumps(response)))) as client:
        with pytest.raises(module.EmbeddingError):
            module.embed(["one"], get_settings(), client=client)


def test_dimension_must_match_across_batches() -> None:
    replies = iter([[[1, 2]], [[1, 2, 3]]])
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(
            200, json={"embeddings": next(replies)}))) as client:
        with pytest.raises(module.EmbeddingError, match="dimension"):
            module.embed(["one", "two"], get_settings(), client=client, batch_size=1)


@pytest.mark.parametrize("kind", ["timeout", "transport", "status", "json"])
def test_failures_are_actionable_without_echoing_provider_data(kind: str) -> None:
    def respond(request):
        if kind == "timeout":
            raise httpx.ReadTimeout("secret", request=request)
        if kind == "transport":
            raise httpx.ConnectError("secret", request=request)
        return httpx.Response(503 if kind == "status" else 200, text="secret")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(module.EmbeddingError) as error:
            module.embed(["one"], get_settings(), client=client)
    assert "secret" not in str(error.value)


def test_empty_input_is_offline_and_bad_limits_fail() -> None:
    assert module.embed([], get_settings()) == []
    for kwargs in [{"batch_size": 0}, {"batch_size": True}, {"timeout_seconds": 0},
                   {"timeout_seconds": float("inf")}]:
        with pytest.raises(ValueError):
            module.embed(["one"], get_settings(), **kwargs)
    with pytest.raises(ValueError):
        module.embed([" "], get_settings())
