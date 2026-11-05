"""Stage 5: Store. The only code in the whole system that writes to Chroma."""

from __future__ import annotations

import math
import re
import uuid
from typing import Any

from chromadb.errors import NotFoundError

from .config import IndexerSettings
from .models import ActiveIndex, Chunk


def get_client(settings: IndexerSettings) -> Any:
    import chromadb  # the thin client, from chromadb-client in requirements.txt
    from chromadb.config import Settings as ChromaSettings

    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port,
                               settings=ChromaSettings(anonymized_telemetry=False))


def store(chunks: list[Chunk], vectors: list[list[float]], settings: IndexerSettings, *,
          client: Any = None, generation: str | None = None) -> int:
    """Validate a separate build, then replace one control metadata record.

    An exclusively created server collection is the writer lock. Crashed writers
    leave it in place: manual recovery must verify no writer remains before delete.
    Never delete previous/failed generations automatically or on uncertain publish.
    """
    if not chunks or len(chunks) != len(vectors) or len({c.id for c in chunks}) != len(chunks):
        raise ValueError("Nonempty unique chunks and matching vectors are required")
    dimension = len(vectors[0])
    for chunk, vector in zip(chunks, vectors, strict=True):
        if (not vector or len(vector) != dimension
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in vector)
                or not any(v != 0 for v in vector)):
            raise ValueError("Vectors must have one finite nonzero dimension")
        if (any(not isinstance(s, str) or not s.strip() for s in (
                chunk.id, chunk.text, chunk.source, chunk.section, chunk.doc_version))
                or type(chunk.page) is not int or chunk.page <= 0
                or type(chunk.superseded) is not bool):
            raise ValueError("Chunk identity/metadata is invalid")
    generation = generation or uuid.uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", generation):
        raise ValueError("Invalid generation identity")
    active = ActiveIndex(f"{settings.collection}__g_{generation}", generation,
                         settings.embed_model, dimension)
    connection = client if client is not None else get_client(settings)
    lock_name = settings.collection + "_writer_lock"
    try:
        connection.create_collection(name=lock_name, metadata={"owner": generation},
                                     embedding_function=None)
    except Exception:
        raise RuntimeError("Cannot acquire index writer lock; check service or existing writer") from None
    try:
        collection = connection.create_collection(name=active.collection, embedding_function=None,
            metadata={"hnsw:space": "cosine", "embed_model": active.embed_model,
                      "dimension": dimension, "generation": generation})
        for start in range(0, len(chunks), 128):
            batch = chunks[start:start + 128]
            collection.add(ids=[c.id for c in batch], documents=[c.text for c in batch],
                           embeddings=vectors[start:start + 128], metadatas=[c.metadata() for c in batch])
        if collection.count() != len(chunks):
            raise RuntimeError("Index build count validation failed")
        for start in range(0, len(chunks), 128):
            batch = chunks[start:start + 128]
            saved = collection.get(ids=[c.id for c in batch],
                                   include=["documents", "metadatas", "embeddings"])
            positions = {key: i for i, key in enumerate(saved["ids"])}
            for offset, expected in enumerate(batch):
                if expected.id not in positions:
                    raise RuntimeError("Index build missing stored ID")
                index = positions[expected.id]
                row = saved["embeddings"][index]
                if (saved["documents"][index] != expected.text
                        or saved["metadatas"][index] != expected.metadata()
                        or len(row) != dimension
                        or not all(math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-7)
                                   for a, b in zip(row, vectors[start + offset], strict=True))):
                    raise RuntimeError("Index build readback validation failed")
        control_name = settings.collection + "_active"
        try:
            control = connection.get_collection(name=control_name, embedding_function=None)
        except (KeyError, NotFoundError):
            connection.create_collection(name=control_name, metadata=active.metadata(),
                                         embedding_function=None)
        else:
            control.modify(metadata=active.metadata())
        published = connection.get_collection(name=control_name, embedding_function=None)
        if published.metadata != active.metadata():
            raise RuntimeError("Index publication readback mismatch")
        return len(chunks)
    finally:
        connection.delete_collection(name=lock_name)
