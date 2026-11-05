"""Publication must preserve the last validated generation on failure."""
from dataclasses import replace

import pytest

from pipeline.config import get_settings
from pipeline.models import Chunk
from pipeline.store import store


class Collection:
    def __init__(self, client, name, metadata):
        self.client, self.name, self.metadata, self.rows = client, name, metadata, {}

    def add(self, ids, documents, embeddings, metadatas):
        if self.client.fail_add:
            raise RuntimeError("injected write failure")
        for i,d,e,m in zip(ids,documents,embeddings,metadatas):
            self.rows[i] = (d,e,m)

    def count(self):
        return len(self.rows)

    def get(self, ids, include):
        keys = [i for i in ids if i in self.rows]
        return {"ids": keys, "documents": [self.rows[i][0] for i in keys],
                "embeddings": [self.rows[i][1] for i in keys],
                "metadatas": [self.rows[i][2] for i in keys]}

    def modify(self, metadata):
        if self.client.fail_publish:
            raise RuntimeError("injected publication failure")
        self.metadata = metadata


class Client:
    def __init__(self):
        self.collections = {}
        self.fail_add = self.fail_publish = False

    def create_collection(self, name, metadata=None, **kwargs):
        if name in self.collections:
            raise RuntimeError("collection exists")
        col = self.collections[name] = Collection(self, name, metadata or {})
        return col

    def get_collection(self, name, **kwargs):
        if name not in self.collections:
            raise KeyError(name)
        return self.collections[name]

    def delete_collection(self, name):
        del self.collections[name]


def pieces():
    return [Chunk("one", "Rule one.", "a.pdf", "4.25", 2, "2026-06", False),
            Chunk("two", "Rule two.", "a.pdf", "4.26", 3, "2026-06", False)]


def test_two_builds_switch_only_after_validation_and_retain_old_data():
    client = Client()
    assert store(pieces(), [[1,0],[0,1]], get_settings(), client=client, generation="first") == 2
    first = dict(client.collections["rahbar_active"].metadata)
    assert first == dict(collection="rahbar__g_first", generation="first",
                         embed_model="nomic-embed-text", dimension=2)
    assert store(pieces(), [[1,0],[0,1]], get_settings(), client=client, generation="second") == 2
    assert client.collections["rahbar_active"].metadata["generation"] == "second"
    assert client.collections[first["collection"]].count() == 2
    assert "rahbar_writer_lock" not in client.collections


@pytest.mark.parametrize("failure", ["add", "publish"])
def test_failure_keeps_old_publication_and_releases_lock(failure):
    client = Client()
    store(pieces(), [[1,0],[0,1]], get_settings(), client=client, generation="good")
    setattr(client, "fail_" + failure, True)
    with pytest.raises(RuntimeError):
        store(pieces(), [[1,0],[0,1]], get_settings(), client=client, generation="bad")
    assert client.collections["rahbar_active"].metadata["generation"] == "good"
    assert client.collections["rahbar__g_good"].count() == 2
    assert "rahbar_writer_lock" not in client.collections


def test_existing_writer_lock_prevents_build():
    client = Client()
    client.create_collection("rahbar_writer_lock")
    with pytest.raises(RuntimeError, match="writer"):
        store(pieces(), [[1,0],[0,1]], get_settings(), client=client)
    assert set(client.collections) == {"rahbar_writer_lock"}


@pytest.mark.parametrize("vectors", [[], [[1]], [[1],[1,2]], [[True],[1]], [[0],[1]],
                                    [[float("nan")],[1]]])
def test_bad_vectors_never_create_a_collection(vectors):
    client = Client()
    with pytest.raises(ValueError):
        store(pieces(), vectors, get_settings(), client=client)
    assert not client.collections


def test_bad_metadata_and_duplicate_ids_rejected():
    for bad in [replace(pieces()[0], source=""), replace(pieces()[0], page=0),
                replace(pieces()[0], superseded="false"), replace(pieces()[0], section="")]:
        with pytest.raises(ValueError):
            store([bad], [[1]], get_settings(), client=Client())
    with pytest.raises(ValueError):
        store([pieces()[0],pieces()[0]], [[1],[1]], get_settings(), client=Client())


def test_partial_write_and_corrupt_readback_do_not_publish():
    for mode in ("partial", "corrupt"):
        client = Client()
        store(pieces(), [[1,0],[0,1]], get_settings(), client=client, generation="good")
        create = client.create_collection
        def wrapped_create(name, **kwargs):
            col = create(name, **kwargs)
            if "__g_bad" in name:
                original_add = col.add
                def add(ids, documents, embeddings, metadatas):
                    original_add(ids[:1],documents[:1],embeddings[:1],metadatas[:1])
                    if mode == "partial":
                        raise RuntimeError("partial write")
                    original_add(ids[1:],documents[1:],embeddings[1:],metadatas[1:])
                    col.rows[ids[0]] = ("corrupt",embeddings[0],metadatas[0])
                col.add = add
            return col
        client.create_collection = wrapped_create
        with pytest.raises(RuntimeError):
            store(pieces(), [[1,0],[0,1]], get_settings(), client=client, generation="bad")
        assert client.collections["rahbar_active"].metadata["generation"] == "good"
        assert client.collections["rahbar__g_bad"].count() > 0
