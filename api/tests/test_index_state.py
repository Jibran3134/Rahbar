"""Readers only read the published identity, never create collections."""
from types import SimpleNamespace

import pytest


def test_reader_resolves_exact_identity_without_writes():
    from app.retrieval.index_state import resolve_active
    calls = []
    class ReadOnly:
        def get_collection(self, name, **kwargs):
            calls.append(name)
            if name == "rahbar_active":
                return SimpleNamespace(metadata=dict(collection="rahbar__g_a", generation="a",
                    embed_model="nomic-embed-text", dimension=768))
            return SimpleNamespace(metadata={"embed_model":"nomic-embed-text", "dimension":768,
                                            "generation":"a", "hnsw:space":"cosine"}, count=lambda:2)
    active, collection = resolve_active(ReadOnly(), "rahbar")
    assert active.dimension == 768 and collection.count() == 2
    assert calls == ["rahbar_active", "rahbar__g_a"]


@pytest.mark.parametrize("dimension", ["768", 0, True])
def test_reader_rejects_bad_identity(dimension):
    from app.retrieval.index_state import IndexStateError, resolve_active
    client = SimpleNamespace(get_collection=lambda **kw: SimpleNamespace(metadata=dict(
        collection="rahbar__g_a",generation="a",embed_model="nomic-embed-text",dimension=dimension)))
    with pytest.raises(IndexStateError):
        resolve_active(client,"rahbar")
