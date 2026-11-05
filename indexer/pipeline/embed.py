"""Stage 4: Embed. One vector per chunk, from the pinned model only."""

from __future__ import annotations

import math

import httpx

from .config import IndexerSettings


class EmbeddingError(RuntimeError):
    """Bounded embedding request or vector-integrity failure."""


def embed(texts: list[str], settings: IndexerSettings, *, client: httpx.Client | None = None,
          batch_size: int = 32, timeout_seconds: float = 60) -> list[list[float]]:
    """Explicit nomic document prefix; API query path uses search_query instead.

    No automatic retries or truncation. Fail the complete build on any bad batch.
    The supplied client is caller-owned; otherwise close our client on all paths.
    """
    if type(batch_size) is not int or not 1 <= batch_size <= 128:
        raise ValueError("batch_size must be an integer from 1 to 128")
    if (isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0):
        raise ValueError("timeout_seconds must be finite and positive")
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Embedding inputs must be nonempty text")
    if not texts:
        return []
    connection = client or httpx.Client()
    vectors: list[list[float]] = []
    dimension: int | None = None
    try:
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            try:
                response = connection.post(settings.ollama_url.rstrip("/") + "/api/embed",
                    json={"model": settings.embed_model,
                          "input": ["search_document: " + text for text in batch], "truncate": False},
                    timeout=timeout_seconds)
                response.raise_for_status()
                payload = response.json()
            except httpx.TimeoutException:
                raise EmbeddingError("Embedding request timed out") from None
            except httpx.HTTPError:
                raise EmbeddingError("Embedding HTTP/transport failure") from None
            except ValueError:
                raise EmbeddingError("Embedding response is not valid JSON") from None
            rows = payload.get("embeddings") if isinstance(payload, dict) else None
            if not isinstance(rows, list) or len(rows) != len(batch):
                raise EmbeddingError("Embedding vector count mismatch")
            for row in rows:
                if (not isinstance(row, list) or not row
                        or any(type(v) not in (int, float) or not math.isfinite(v) for v in row)
                        or not any(v != 0 for v in row)):
                    raise EmbeddingError("Embedding vector must be finite, numeric and nonzero")
                if dimension is not None and len(row) != dimension:
                    raise EmbeddingError("Embedding dimension mismatch across batches")
                dimension = len(row)
                vectors.append([float(v) for v in row])
    finally:
        if client is None:
            connection.close()
    return vectors
